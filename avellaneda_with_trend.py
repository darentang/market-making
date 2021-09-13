from typing import Tuple
import matplotlib
import numpy as np

class CircularBuffer:
    def __init__(self, length):
        self.length = length
        self.data = []

    def append(self, x) -> None:
        self.data.append(x)
        if len(self.data) > self.length:
            self.data.pop(0)

    def __len__(self) -> int:
        return len(self.data)

    def mean(self) -> float:
        return np.mean(self.data)

    def std(self) -> float:
        return np.std(self.data)

    def is_empty(self) -> bool:
        return len(self.data) == 0

    def is_ready(self) -> bool:
        return len(self.data) == self.length


class AvellanedaWithTrend:
    def __init__(self, gamma, ticksize, lookback=20, dt=1):
        self.gamma = gamma
        self.mu = 0
        self.dt = dt
        self.sigma = 0
        self.s = None
        self.bid_ask_spread = 0
        self.ticksize = ticksize
        self.s_buffer: CircularBuffer = CircularBuffer(lookback)

    def set_a_rule(self, a_rule):
        self.a_rule = a_rule

    def set_k_rule(self, k_rule):
        self.k_rule = k_rule


    def update_order_book(self, best_bid: float, best_ask: float):
        self.best_bid = best_bid
        self.best_ask = best_ask

        self.bid_ask_spread = (self.best_ask - self.best_bid) / self.ticksize

        
        s = (self.best_bid + self.best_ask) / 2

        if self.s is not None:
            self.s_buffer.append((s - self.s)/self.dt)

        self.s = s

    def get_A(self) -> float:
        return 0.9

    def get_k(self) -> float:
        return 0.9

    def round_to_tick(self, x: float) -> float:
        return np.round(x / self.ticksize) * self.ticksize

    def get_bid_ask(self, q: float, mu: float = None, variance: float = None) -> Tuple[float, float]:
        if self.s_buffer.is_empty() and (mu is None and variance is None):
            return None, None

        A: float = self.get_A()
        k: float = self.get_k()
        if mu is None:
            # mu: float = self.s_buffer.mean()
            mu = 0
        if variance is None:
            variance: float = (self.s_buffer.std())**2
        
        log_part = 1 / self.gamma * np.log(1 + self.gamma/k)
        sqrt_part = np.sqrt(variance*self.gamma/2/k/A*(1+self.gamma/k)**(1+k/self.gamma))
        
        delta_bid =  log_part + (-mu/self.gamma/variance + (2*q + 1)/2) * sqrt_part
        delta_ask =  log_part + (mu/self.gamma/variance - (2*q - 1)/2) * sqrt_part
        print(delta_bid, delta_ask)
        # print(self.s_buffer.data)
        return self.s - delta_bid * self.bid_ask_spread / 2 * self.ticksize, self.s + delta_ask * self.bid_ask_spread / 2 * self.ticksize

    def is_ready(self) -> bool:
        return self.s_buffer.is_ready()


