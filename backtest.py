import os
import asyncio

import pandas as pd
import numpy as np

from market_maker import MarketMaker

class MockEventLoop:
    def __init__(self, loop):
        self.loop = loop

    def run_forever(self):
        asyncio.run(self.loop())        

class MockOrderBook:
    def __init__(self, dirname: str):
        self.market = pd.read_csv(os.path.join(dirname, "market.csv"))
        self.orderbook = pd.read_csv(os.path.join(dirname, "orderbook.csv"))

        market_events = pd.DataFrame({"time": self.market.time, "id": self.market.index})
        market_events = market_events.assign(type="MARKET")

        orderbook_events = pd.DataFrame({"time": self.orderbook.time, "id": self.orderbook.index})
        orderbook_events = orderbook_events.assign(type="ORDERBOOK")

        self.events = pd.concat([market_events, orderbook_events]).sort_values("time")
        
        self.best_bid = None
        self.best_ask = None    

        self.trade_update_callback = None
        self.orderbook_update_callback = None



    async def loop(self):
        for i, row in self.events.iterrows():
            if row.type == "MARKET":
                market_event = self.market.iloc[row.id]

                await self.on_trade_update({'p': market_event.price, 'q': market_event.quantity})

            if row.type == "ORDERBOOK":
                orderbook_event = self.orderbook.iloc[row.id]

                self.best_bid = float(orderbook_event.best_bid)
                self.best_ask = float(orderbook_event.best_ask)

                await self.on_orderbook_update()

    def get_loop(self):
        return MockEventLoop(self.loop)

    async def on_trade_update(self, res):
        if self.trade_update_callback:
            await self.trade_update_callback(res)

    async def on_orderbook_update(self):
        if self.orderbook_update_callback:
            await self.orderbook_update_callback()

    def get_best_bid(self) -> float:
        return self.best_bid

    def get_best_ask(self) -> float:
        return self.best_ask




if __name__ == "__main__":
    dirname = "SOLBUSD100-09122021182710"
    orderbook = MockOrderBook(dirname)
    market_maker = MarketMaker("SOLBUSD", 100, orderbook=orderbook, dirname=dirname)

    market_maker.orderbook.get_loop().run_forever()