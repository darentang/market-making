import asyncio
import os
import time
from binance import AsyncClient, BinanceSocketManager, Client
from pprint import pprint
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor


class OrderBook:
    def __init__(self, ticker: str, interval: int = 0, orderbook_fname: str = "orderbook.csv", market_fname: str = "market.csv",
        dirname: str = "."):
        self.ticker = ticker
        self.client = Client()
        self.orderbook_update_callback = None
        self.trade_update_callback = None
        self.interval = interval
        self.print = False

        self.orderbook_fname = os.path.join(dirname, orderbook_fname)
        self.market_fname = os.path.join(dirname, market_fname)

        with open(self.orderbook_fname, "w") as f:
            f.write(",".join([
                "time", "best_bid", "best_ask"
            ]))
            f.write("\n")
            
        with open(self.market_fname, "w") as f:
            f.write(",".join([
                "time", "price", "quantity"
            ]))
            f.write("\n")

    def get_best_bids(self, depth: int):
        return OrderedDict({k: self.bids[k] for k in sorted(self.bids.keys(), reverse=True)[:depth]})

    def get_best_asks(self, depth: int):
        return OrderedDict({k: self.asks[k] for k in sorted(self.asks.keys(), reverse=False)[:depth]})

    async def write_trade_activities(self, res):
        with open(self.market_fname, "a") as f:
            f.write(",".join(map(str, [
                time.time(),
                res["p"],
                res["q"]
            ])))
            f.write("\n")

    async def write_orderbook(self):
        with open(self.orderbook_fname, "a") as f:
            f.write(",".join(map(str, [
                time.time(),
                self.get_best_bid(),
                self.get_best_ask()
            ])))
            f.write("\n")


    async def print_best_bid_ask(self, depth: int):
        print("best bids")
        pprint(self.get_best_bids(depth))
        print("best asks")
        pprint(self.get_best_asks(depth))

    async def get_depth_from_socket(self, tscm):
        res = await tscm.recv()    
        self.last_update_id = res["lastUpdateId"]
        self.bids = {x[0]: float(x[1]) for x in res["bids"]}
        self.asks = {x[0]: float(x[1]) for x in res["asks"]}
        await self.on_receive_orderbook()
        if self.print:
            await self.print_best_bid_ask(5)

    async def on_receive_orderbook(self):
        if self.orderbook_update_callback:
            await self.orderbook_update_callback()
        await self.write_orderbook()

    async def on_receive_trade(self, res):
        if self.trade_update_callback:
            await self.trade_update_callback(res)
        await self.write_trade_activities(res)

    def get_best_bid(self) -> str:
        return max(list(self.bids.keys()))

    def get_best_ask(self) -> str:
        return min(list(self.asks.keys()))

    async def get_agg_trade_from_socket(self, tscm):
        res = await tscm.recv()
        await self.on_receive_trade(res)

    async def depth_update_loop(self):
        async_client = await AsyncClient.create()
        bm = BinanceSocketManager(async_client)

        ts_depth = bm.depth_socket(self.ticker, depth=BinanceSocketManager.WEBSOCKET_DEPTH_20, interval=self.interval)
        
        async with ts_depth as tscm_depth:
            while True:
                await self.get_depth_from_socket(tscm_depth)
                
        await async_client.close_connection()

    async def trade_update_loop(self):
        async_client = await AsyncClient.create()
        bm = BinanceSocketManager(async_client)

        ts_agg = bm.trade_socket(self.ticker)
        async with ts_agg as tscm_agg:
            while True:                
                await self.get_agg_trade_from_socket(tscm_agg)
        await async_client.close_connection()
        
    def get_loop(self):
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.depth_update_loop())
        asyncio.ensure_future(self.trade_update_loop())
        return loop


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    ob = OrderBook("SOLBUSD")
    ob.print = True
    loop.run_until_complete(ob.depth_update_loop())