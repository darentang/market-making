import sys
import datetime
import os
import asyncio
from order_book import OrderBook



if __name__ == "__main__":
    ticker = sys.argv[1]
    interval = int(sys.argv[2])
    time_str = datetime.datetime.now().strftime("%m%d%Y%H%M%S")
    dir_name = f"{ticker}{interval}-{time_str}"
    os.mkdir(dir_name)
    ob = OrderBook(ticker, interval, os.path.join(dir_name, "orderbook.csv"), os.path.join(dir_name, "market.csv"))
    loop = ob.get_loop()
    loop.run_forever()