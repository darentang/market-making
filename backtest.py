import os
import pandas as pd
import numpy as np
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

    def loop(self):
        for i, row in self.events.iterrows():
            print(i, row)

    
    
    





if __name__ == "__main__":
    dirname = "SOLBUSD100-09122021182710"

    orderbook = MockOrderBook(dirname)
    orderbook.loop()
