"""Synthetic OHLCV generators used to test the pattern engine."""
import numpy as np
import pandas as pd


def _idx(n, freq):
    end = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    return pd.bdate_range(end=end, periods=n) if freq == "B" else pd.date_range(end=pd.Timestamp.now().floor("4h") - pd.Timedelta(hours=4), periods=n, freq="4h")


def path(waypoints, noise=0.004, seed=1, vol_base=1_000_000, vol_fn=None, freq="B"):
    """waypoints: [(bar_index, price), ...] linearly interpolated (in log space) + noise."""
    rng = np.random.default_rng(seed)
    xs = [w[0] for w in waypoints]
    ys = np.log([w[1] for w in waypoints])
    n = xs[-1] + 1
    close = np.exp(np.interp(np.arange(n), xs, ys)) * (1 + rng.normal(0, noise, n))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, noise / 3, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, noise / 2, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, noise / 2, n)))
    vol = vol_base * (1 + rng.normal(0, 0.15, n)).clip(0.3)
    if vol_fn:
        vol = vol_fn(vol, n)
    idx = _idx(n, freq)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def with_base(prefix_pts, pts):
    """prepend a long drift-up prefix so SMAs/trend filters have history"""
    return path(prefix_pts + pts)


def random_walk(n=300, seed=0, drift=0.0003, vol=0.018):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = 100 * np.exp(np.cumsum(r))
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, n)))
    vol_ = 1e6 * (1 + rng.normal(0, 0.3, n)).clip(0.2)
    idx = _idx(n, "B")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol_}, index=idx)
