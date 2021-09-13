from enum import Enum
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
        return 2 / self.bid_ask_spread


class OrderState(Enum):
    PENDING = 0
    SUBMITTED = 1
    FILLED = 2
    CANCELED = -1

class Order:
    def __init__(self, id: int, ticker: str, quantity: float, limit: float, side: Side, expiry: float):
        self.ticker = ticker
        self.quantity = quantity
        self.limit = limit
        self.side = side
        self.state = OrderState.PENDING       
        self.expiry_time = time.time() + expiry
        self.id = id
        self.order_fname = "orders.csv"
        with open(self.order_fname, "w") as f:
            f.write(",".join([
                "time", "id", "action", "limit", "quantity", "side"
            ]))
            f.write("\n")
  
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


class MarketMaker:
    def __init__(self, ticker: str, interval: int, lookback: int = 20):
        self.client = Client()
        self.ticker = ticker
        ticksize = 0.01
        self.orderbook = OrderBook(ticker, interval)
        self.bid_ask_generator = BidAskGenerator(1, ticksize, lookback, 1 if not interval else 0.01)
        
        self.inventory = 0
        self.cash = 0

        self.orders = {
            Side.BUY: None,
            Side.SELL: None
        }

        self.order_id = 0

        self.expiry = 1
        self.quantity = 1
        self.comission = 0.1 / 100  
        
        self.orderbook.orderbook_update_callback = self.on_orderbook_update
        self.orderbook.trade_update_callback = self.on_trade_update

        self.init_logs()

    def init_logs(self):
        self.state_fname = "state.csv"
        with open(self.state_fname, "w") as f:
            f.write(",".join([
                "time", "cash", "inventory", "equity", "mid_price", "vwap"
            ]))
            f.write("\n")





    def get_equity(self) -> float:
        return self.inventory * (self.bid_ask_generator.s or 0) + self.cash

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
        # print("Equity:", self.get_equity(), "Inventory:", self.inventory)
        self.bid_ask_generator.update_order_book(self.orderbook.get_best_bid(), self.orderbook.get_best_ask())
        await self.check_expiry()

        buy_order: Order = self.orders[Side.BUY]
        sell_order: Order = self.orders[Side.SELL]

        buy_state: OrderState = buy_order.state if buy_order else None
        sell_state: OrderState = sell_order.state if sell_order else None

        if not self.bid_ask_generator.is_ready():
            return

        await asyncio.create_task(self.write_state())

        if buy_state == OrderState.SUBMITTED and sell_state == OrderState.SUBMITTED:
            return

        await self.requote()

    async def requote(self, side: Side = Side.BOTH):
        bid, ask = self.bid_ask_generator.get_bid_ask(self.inventory)

        if side == Side.BUY or side == Side.BOTH:
            buy_order: Order = self.orders[Side.BUY]
            if not buy_order or bid != buy_order.limit:
                if buy_order:
                    await buy_order.cancel()
                order =self.orders[Side.BUY] = Order(self.order_id, self.ticker, self.quantity, bid, Side.BUY, self.expiry) 
                self.order_id += 1
                if order.limit >= self.bid_ask_generator.best_bid:
                    await self.fill(order)
        
        if side == Side.SELL or side == Side.BOTH:
            sell_order: Order = self.orders[Side.SELL]
            if not sell_order or ask != sell_order.limit:
                if sell_order:
                    await sell_order.cancel()
                order = self.orders[Side.SELL] = Order(self.order_id, self.ticker, self.quantity, ask, Side.SELL, self.expiry)
                self.order_id += 1
                if order.limit <= self.bid_ask_generator.best_ask:
                    await self.fill(order)



    async def write_state(self):
        with open(self.state_fname, "a") as f:
            f.write(",".join(map(str, [
                time.time(),
                self.cash,
                self.inventory,
                self.get_equity(),
                self.bid_ask_generator.s,
                self.bid_ask_generator.vwap
            ])))
            f.write("\n")



    async def fill(self, order):
        if order.state == OrderState.SUBMITTED:
            await order.fill()

            if order.side == Side.BUY:
                self.inventory += order.quantity
                self.cash -= order.quantity * order.limit * (1 + self.comission)

            if order.side == Side.SELL:
                self.inventory -= order.quantity
                self.cash += order.quantity * order.limit * (1 - self.comission)

            # await self.requote()    


    async def on_trade_update(self, res):
        price = float(res["p"])

        buy_order: Order = self.orders[Side.BUY]
        sell_order: Order = self.orders[Side.SELL]

        if buy_order and price <= buy_order.limit and buy_order.state == OrderState.SUBMITTED:
            await self.fill(buy_order)

        if sell_order and price >= sell_order.limit and sell_order.state == OrderState.SUBMITTED:
            await self.fill(sell_order)
        
    


if __name__ == "__main__":
    
    mm = MarketMaker("SRMBUSD", 0)
    loop = mm.orderbook.get_loop()
    loop.run_forever()