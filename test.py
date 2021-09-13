import time
from multiprocessing import Process
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from market_maker import MarketMaker

fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
mid_price, = ax1.plot([], [], 'k')
vwap_price, = ax1.plot([], [], 'k--')
trades = ax1.scatter([], [], marker="o", c="b")
bids = ax1.scatter([], [], marker="^", c="g")
asks = ax1.scatter([], [], marker="v", c="r")
best_bid, = ax1.plot([], [], 'g', alpha=0.5)
best_ask, = ax1.plot([], [], 'r', alpha=0.5)

equity, = ax2.plot([], [], "k")

inventory, = ax3.plot([], [], "k")

def run_order_book_loop(*args, **kwargs):
    mm = MarketMaker(*args, **kwargs)
    loop = mm.orderbook.get_loop()
    print("hi im loopin")
    loop.run_forever()
    


def live_plot(i: int):
    state = pd.read_csv("state.csv")
    if len(state) == 0:
        return mid_price, trades, 
    market = pd.read_csv("market.csv")
    orders = pd.read_csv("orders.csv")
    orderbook = pd.read_csv("orderbook.csv")

    bids_data = orders.query("side == 'BUY' and action == 'SUBMIT'")
    asks_data = orders.query("side == 'SELL' and action == 'SUBMIT'")

    mid_price.set_data(state.time, state.mid_price)
    vwap_price.set_data(state.time, state.vwap)
    best_bid.set_data(orderbook.time, orderbook.best_bid)
    best_ask.set_data(orderbook.time, orderbook.best_ask)

    trades.set_offsets(market[["time", "price"]].values)
    trades.set_sizes(market.quantity*5)

    bids.set_offsets(bids_data[["time", "limit"]].values)
    asks.set_offsets(asks_data[["time", "limit"]].values)

    equity.set_data(state.time, state.equity)
    
    inventory.set_data(state.time, state.inventory)

    ax3.set_xlim(min(state.time), max(state.time))
    ax3.set_ylim(min(state.inventory), max(state.inventory))

    ax2.set_xlim(min(state.time), max(state.time))
    ax2.set_ylim(min(state.equity), max(state.equity))

    ax1.set_xlim(min(state.time), max(state.time))
    ax1.set_ylim(min(state.mid_price), max(state.mid_price))
    
    time.sleep(1)

    return mid_price, trades, equity, inventory

if __name__ == "__main__":
    run_live = True
    if run_live:    
        loop_process = Process(target=run_order_book_loop, args=("SOLBUSD", 100, 50))
        loop_process.start()
    
    ani = FuncAnimation(fig, live_plot, blit=False, interval=20)
    plt.show()

    if run_live:
        loop_process.join()
    
