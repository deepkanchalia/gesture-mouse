"""One-Euro filter — smooths noisy hand-tracking coordinates.

This is the single most important piece for making the cursor feel like
magic instead of a broken toy. It filters out jitter when your hand is
still, but stays responsive when you move fast (low lag).

Reference: Casiez, Roussel & Vogel (2012), "1€ Filter".
"""

import math


class _LowPass:
    def __init__(self):
        self._prev = None

    def __call__(self, value, alpha):
        if self._prev is None:
            self._prev = value
        else:
            self._prev = alpha * value + (1 - alpha) * self._prev
        return self._prev


class OneEuroFilter:
    def __init__(self, freq=60.0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        # min_cutoff: lower = smoother but more lag when still
        # beta: higher = less lag on fast moves (follows quicker)
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x = _LowPass()
        self._dx = _LowPass()
        self._prev_x = None

    @staticmethod
    def _alpha(cutoff, freq):
        tau = 1.0 / (2 * math.pi * cutoff)
        te = 1.0 / freq
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x):
        if self._prev_x is None:
            self._prev_x = x
        dx = (x - self._prev_x) * self.freq
        edx = self._dx(dx, self._alpha(self.d_cutoff, self.freq))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        self._prev_x = x
        return self._x(x, self._alpha(cutoff, self.freq))


class Vec2Filter:
    """Two One-Euro filters, one per axis."""

    def __init__(self, **kw):
        self._fx = OneEuroFilter(**kw)
        self._fy = OneEuroFilter(**kw)

    def __call__(self, x, y):
        return self._fx(x), self._fy(y)
