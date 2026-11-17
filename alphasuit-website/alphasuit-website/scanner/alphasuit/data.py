"""
Market-data providers.

* Indian stocks  : Yahoo Finance chart endpoint (NSE = SYMBOL.NS, BSE = CODE.BO)
* Crypto         : Binance public market-data API (spot, USDT pairs)

Yahoo's endpoint is unofficial. It is fine to launch with, but a commercial product should
move to a licensed feed (e.g. NSE data vendor / broker API) - implement `fetch_ohlcv` for it.
"""
from __future__ import annotations

import threading
import time

import pandas as pd
import requests

from .config import Config

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_tl = threading.local()


def _session():
    s = getattr(_tl, "s", None)
    if s is None:
        s = _tl.s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
    return s


def get_json(url, params=None, retries=3, timeout=20, headers=None):
    last = None
    for i in range(retries):
        try:
            r = _session().get(url, params=params, timeout=timeout, headers=headers)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 400):
                return None
            last = f"HTTP {r.status_code}"
            time.sleep(1.5 * (i + 1) * (3 if r.status_code == 429 else 1))
        except requests.RequestException as e:
            last = str(e)
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"fetch failed: {last}")


# ----------------------------------------------------------------------------- Yahoo (stocks)
def fetch_yahoo(ticker: str, rng="1y", interval="1d") -> pd.DataFrame | None:
    for host in ("query1", "query2"):
        try:
            j = get_json(f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}",
                         {"range": rng, "interval": interval, "includePrePost": "false"}, retries=2)
            break
        except RuntimeError:
            j = None
    if not j:
        return None
    try:
        res = j["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        off = res.get("meta", {}).get("gmtoffset", 19800)
    except (KeyError, IndexError, TypeError):
        return None
    df = pd.DataFrame({
        "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"],
    }, index=pd.to_datetime(pd.Series(ts) + off, unit="s").dt.normalize())
    df = df.dropna()
    df = df[~df.index.duplicated(keep="last")]
    return df if len(df) else None


# ----------------------------------------------------------------------------- Binance (crypto)
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "USDD", "EUR", "EURI", "AEUR", "UST", "XUSD", "USD1", "PAXG"}
LEVERAGED = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def fetch_binance(symbol: str, interval="1d", limit=300) -> pd.DataFrame | None:
    j = get_json(f"{Config.CRYPTO_API_BASE}/api/v3/klines",
                 {"symbol": symbol, "interval": interval, "limit": limit})
    if not j:
        return None
    now_ms = int(time.time() * 1000)
    rows = [r for r in j if int(r[6]) < now_ms]  # closed candles only
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume", "ct", "qv", "n", "tb", "tq", "x"])
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms")
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df


USE_SHEETS = [False]
USE_BHAV = [False]   # switched on by scanner.run_scan when the NSE files are available


def fetch_ohlcv(market: str, ticker: str, tf: str = "1d") -> pd.DataFrame | None:
    if market == "stocks":
        if USE_SHEETS[0] and ":" in ticker:
            from . import sheets
            return sheets.get(ticker)
        if ticker.endswith(".NS") and USE_BHAV[0]:
            from . import bhav
            return bhav.get(ticker[:-3])
        return fetch_yahoo(ticker, "1y", "1d")
    return fetch_binance(ticker, tf, 300)


def fetch_live_chart(market: str, ticker: str, tf: str = "1d") -> pd.DataFrame | None:
    """For the in-page chart (includes the forming candle)."""
    if market == "stocks":
        return fetch_yahoo(ticker, "1y", "1d")
    j = get_json(f"{Config.CRYPTO_API_BASE}/api/v3/klines", {"symbol": ticker, "interval": tf, "limit": 300})
    if not j:
        return None
    df = pd.DataFrame(j, columns=["t", "open", "high", "low", "close", "volume", "ct", "qv", "n", "tb", "tq", "x"])
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="ms")
    return df[["open", "high", "low", "close", "volume"]].astype(float)
