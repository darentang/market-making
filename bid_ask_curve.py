import numpy as np
import matplotlib.pyplot as plt
from avellaneda_with_trend import AvellanedaWithTrend
from market_maker import BidAskGenerator


def main():
    N = 20
    q = np.linspace(-10, 10, N)
    bid_ask_spreads = np.linspace(1, 5, N)
    optimal_spread = np.zeros((N, N))

    bid_ask_generator = BidAskGenerator(0.9, 0.01)
    bid_ask_generator.s = 0

    for i in range(N):
        bid_ask_generator.bid_ask_spread = bid_ask_spreads[i] 

        bids, asks = bid_ask_generator.get_bid_ask(q, 0, 1)
        optimal_spread[i, :] = (asks) / (bid_ask_spreads[i] / 2 * 0.01)


    print(optimal_spread)

    X, Y = np.meshgrid(q, bid_ask_spreads)
    fig = plt.figure()
    ax = plt.axes(projection='3d')
    ax.plot_surface(X, Y, optimal_spread)


if __name__ == "__main__":
    main()
    plt.show()