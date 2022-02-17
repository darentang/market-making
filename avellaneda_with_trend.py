from typing import Tuple
import matplotlib
import numpy as np

class CircularBuffer:
    def __init__(self, n):
        self.n = n
        self.data = []
        self.time = []
        self.first = None
    
    def add(self, x, t=None):
        self.data.append(x)
        if t:
            self.time.append(t)
        if len(self.data) > self.n:
            self.data.pop(0)
            if t:
                self.time.pop(0)

    def var(self):
        return np.var(np.diff(self.data))

    def gradient(self):
        return np.polyfit(self.time, self.data, 1)[0]

    def ready(self):
        return len(self.data) == self.n


class AvellanedaWithTrend:
    def __init__(self, gamma, lookback=100):
        self.gamma = gamma
        self.mu = 0
        self.sigma = 0
        self.s = None
        self.s_buffer: CircularBuffer = CircularBuffer(lookback)
        self.mu_buffer: CircularBuffer = CircularBuffer(lookback)


    def update_s(self, s: float):
        self.s = s
        self.s_buffer.add(s)
    
    def update_mu(self, mu: float, time: float):
        self.mu_buffer.add(mu, time)

    def get_A(self) -> float:
        return 0.9

    def get_k(self) -> float:
        return 0.9

    def round_to_tick(self, x: float) -> float:
        return np.round(x / self.ticksize) * self.ticksize

    def get_bid_ask(self, q: float) -> Tuple[float, float]:
        if not self.is_ready():
            return None, None

        A: float = self.get_A()
        k: float = self.get_k()
        
        mu: float = self.mu_buffer.gradient() * 0
        variance: float = self.s_buffer.var()
        
        log_part = 1 / self.gamma * np.log(1 + self.gamma/k)
        sqrt_part = np.sqrt(variance*self.gamma/2/k/A*(1+self.gamma/k)**(1+k/self.gamma))
        
        delta_bid =  log_part + (-mu/self.gamma/variance + (2*q + 1)/2) * sqrt_part
        delta_ask =  log_part + (mu/self.gamma/variance - (2*q - 1)/2) * sqrt_part
        return delta_bid, delta_ask

    def is_ready(self) -> bool:
        return self.s_buffer.ready() and self.mu_buffer.ready()


