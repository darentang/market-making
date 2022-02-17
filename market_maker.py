import os
from enum import Enum
from posixpath import dirname
import time
from datetime import datetime
import asyncio
import numpy as np

from binance import Client

from order_book import OrderBook
from avellaneda_with_trend import AvellanedaWithTrend

class Side(Enum):
    BUY = 1
    SELL = -1
    BOTH = 0

class BidAskGenerator(AvellanedaWithTrend):

    def get_A(self):
        return 0.9 

    def get_k(self):
        return 2


class OrderState(Enum):
    PENDING = 0
    SUBMITTED = 1
    FILLED = 2
    CANCELED = -1

class ExponentialAvg:
    def __init__(self, gamma):
        self.gamma = gamma
        self.price_quantity_sum = 0
        self.quantity_sum = 0

    def update(self, price, quantity):
        self.price_quantity_sum = price*quantity*self.gamma + self.price_quantity_sum*(1 - self.gamma)
        self.quantity_sum = quantity*self.gamma + self.quantity_sum*(1 - self.gamma)

    def get_avg(self):
        if self.quantity_sum:
            return self.price_quantity_sum / self.quantity_sum
        return None

class Order:
    def __init__(self, id: int, ticker: str, quantity: float, 
        limit: float, side: Side, expiry: float, dirname: str = "."):
        self.ticker = ticker
        self.quantity = quantity
        self.limit = limit
        self.side = side
        self.state = OrderState.PENDING       
        self.expiry_time = time.time() + expiry
        self.id = id
        self.order_fname = os.path.join(dirname, "orders.csv")  
        self.submit()        

    def submit(self):
        self.state = OrderState.SUBMITTED
        self.write_trade("SUBMIT")
        
    async def cancel(self):
        if self.state == OrderState.CANCELED or self.state == OrderState.FILLED:
            return
        self.state = OrderState.CANCELED
        self.write_trade("CANCEL")
        

    async def fill(self):
        self.state = OrderState.FILLED
        self.write_trade("FILL")

    def write_trade(self, action: str):
        with open(self.order_fname, "a") as f:
            f.write(",".join(map(str, [
                time.time(),
                self.id,
                action,                
                self.limit,
                self.quantity,
                self.side.name
            ])))

            f.write("\n")


class OrderFactory:
    def __init__(self, ticker: str, dirname: str = "."):
        self.ticker = ticker
        self.order_fname = os.path.join(dirname, "orders.csv")
        self.dirname = dirname
        with open(self.order_fname, "w") as f:
            f.write(",".join([
                "time", "id", "action", "limit", "quantity", "side"
            ]))
            f.write("\n")
        
        self.id = -1
    
    def submit_buy(self, quantity: float, price: float, expiry: int):
        self.id += 1
        return Order(self.id, self.ticker, quantity, price, Side.BUY, expiry, dirname=self.dirname)

    def submit_sell(self, quantity: float, price: float, expiry: int):
        self.id += 1
        return Order(self.id, self.ticker, quantity, price, Side.SELL, expiry, dirname=self.dirname)



class MarketMaker:
    def __init__(self, ticker: str, interval: int, lookback: int = 20, orderbook: OrderBook = None, dirname=".",
        smoothing_gamma: float = 0.1, gamma: float = 0.9, expiry: float = 60, buy_size: float = 1):
        self.client = Client()
        self.expon_avg = ExponentialAvg(smoothing_gamma)
        self.ticker = ticker
        self.orderbook = orderbook or OrderBook(ticker, interval, dirname=dirname)
        self.bid_ask_generator = BidAskGenerator(gamma, lookback)
        self.inventory = 0
        self.hinventory = 0
        self.hedge_price = 0
        self.cash = 0

        self.orders = {
            Side.BUY: None,
            Side.SELL: None
        }

        self.orderfactory = OrderFactory(ticker, dirname)

        self.expiry = expiry
        self.quantity = buy_size
        self.comission = 0.1 / 100  
        
        self.orderbook.orderbook_update_callback = self.on_orderbook_update
        self.orderbook.trade_update_callback = self.on_trade_update

        self.hedge_symbol = "BNBBUSD"

        self.state_fname = os.path.join(dirname, "state.csv")

        with open(self.state_fname, "w") as f:
            f.write(",".join([
                "time", "cash", "inventory", "hinventory", "equity", "mid_price", "hedge_price"
            ]))
            f.write("\n")

        hist = self.client.get_aggregate_trades(symbol=ticker)
        for res in hist:
            self.update_based_on_trade(float(res["p"]), float(res["q"]), float(res["T"])/1000)
            if self.bid_ask_generator.is_ready():
                break

    def get_equity(self) -> float:
        return self.inventory * (self.bid_ask_generator.s or 0) + self.hinventory * self.hedge_price + self.cash

    async def check_expiry(self):
        now = time.time()
        buy_order: Order = self.orders[Side.BUY]
        sell_order: Order = self.orders[Side.SELL]
        if not buy_order or not sell_order:
            return
        
        if buy_order.expiry_time < now:
            await buy_order.cancel()
        
        if sell_order.expiry_time < now:
            await sell_order.cancel()

    async def on_orderbook_update(self):
        await self.update_hedge_price()
        if not self.expon_avg.get_avg():
            return
        
        if not self.bid_ask_generator.is_ready():
            return

        await self.check_expiry()

        buy_order: Order = self.orders[Side.BUY]
        sell_order: Order = self.orders[Side.SELL]

        buy_state: OrderState = buy_order.state if buy_order else None
        sell_state: OrderState = sell_order.state if sell_order else None


        await asyncio.create_task(self.write_state())

        if buy_state == OrderState.SUBMITTED and sell_state == OrderState.SUBMITTED:
            return

        await self.requote()

    async def update_hedge_price(self):
        res = self.client.get_orderbook_ticker(symbol=self.hedge_symbol)
        self.hedge_price = 0.5*(float(res["bidPrice"]) + float(res["askPrice"]))
        

    async def requote(self, side: Side = Side.BOTH):
        d_bid, d_ask = self.bid_ask_generator.get_bid_ask(self.inventory)
        print(d_bid, d_ask)
        bid, ask = self.expon_avg.get_avg() - d_bid, self.expon_avg.get_avg() + d_ask
        if side == Side.BUY or side == Side.BOTH:
            buy_order: Order = self.orders[Side.BUY]
            if not buy_order or bid != buy_order.limit:
                if buy_order:
                    await buy_order.cancel()
                self.orders[Side.BUY] = self.orderfactory.submit_buy(self.quantity, bid, self.expiry)
        
        if side == Side.SELL or side == Side.BOTH:
            sell_order: Order = self.orders[Side.SELL]
            if not sell_order or ask != sell_order.limit:
                if sell_order:
                    await sell_order.cancel()
                self.orders[Side.SELL] = self.orderfactory.submit_sell(self.quantity, ask, self.expiry)



    async def write_state(self):
        with open(self.state_fname, "a") as f:
            f.write(",".join(map(str, [
                time.time(),
                self.cash,
                self.inventory,
                self.hinventory,
                self.get_equity(),
                self.expon_avg.get_avg(),
                self.hedge_price
            ])))
            f.write("\n")



    async def fill(self, order):
        if order.state == OrderState.SUBMITTED:
            await order.fill()
            hedge_quantity = order.limit * order.quantity / self.hedge_price            
            if order.side == Side.BUY:
                self.inventory += order.quantity
                self.hinventory -= hedge_quantity
                self.cash -= order.quantity * order.limit * (1 + self.comission)
                self.cash += hedge_quantity * self.hedge_price * (1 - self.comission)

            if order.side == Side.SELL:
                self.inventory -= order.quantity
                self.hinventory += hedge_quantity
                self.cash += order.quantity * order.limit * (1 - self.comission)
                self.cash -= hedge_quantity * self.hedge_price * (1 + self.comission)

    def update_based_on_trade(self, price, quantity, t=None):
        if not t:
            t = time.time()
        self.bid_ask_generator.update_s(price)
        self.expon_avg.update(price, quantity)
        self.bid_ask_generator.update_mu(self.expon_avg.get_avg(), t)

    async def on_trade_update(self, res):
        price = float(res["p"])
        quantity = float(res["q"])

        self.update_based_on_trade(price, quantity)
        buy_order: Order = self.orders[Side.BUY]
        sell_order: Order = self.orders[Side.SELL]

        if buy_order and price <= buy_order.limit and buy_order.state == OrderState.SUBMITTED:
            await self.fill(buy_order)
            await self.requote(side=Side.BUY)

        if sell_order and price >= sell_order.limit and sell_order.state == OrderState.SUBMITTED:
            await self.fill(sell_order)
            await self.requote(side=Side.SELL)
        
    


if __name__ == "__main__":
    
    mm = MarketMaker(
        "SOLBUSD", 
        interval=0, 
        lookback=100,
        smoothing_gamma=0.01,
        gamma=0.9,
        expiry=60,
        buy_size=10,
        dirname="SOLBUSD2"
    )
    loop = mm.orderbook.get_loop()
    loop.run_forever()