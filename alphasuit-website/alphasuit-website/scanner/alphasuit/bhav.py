"""
NSE end-of-day data from the exchange's own daily "bhavcopy" file (all stocks in ONE file per day):
  https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv

First run downloads ~1 year of files (once), afterwards only the new day. Files are cached in DATA_DIR/bhav.
Prices are NOT split/bonus adjusted, so history is cut at any suspicious one-day jump (see get()).
If NSE can't be reached, the scanner automatically falls back to Yahoo (see scanner.run_scan).
"""
from __future__ import annotations

import gzip
import io
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .config import Config, DATA_DIR
from .data import UA

CACHE = DATA_DIR / "bhav"
CACHE.mkdir(parents=True, exist_ok=True)
URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
IST = timezone(timedelta(hours=5, minutes=30))
MIN_DAYS_OK = 120
_frames: dict | None = None


def _today():
    return datetime.now(IST).date()


def _path(d):
    return CACHE / f"{d:%Y%m%d}.csv.gz"


def _marker(d):
    return CACHE / f"{d:%Y%m%d}.none"


def parse(text: str) -> pd.DataFrame | None:
    """Raw NSE csv text -> compact frame [symbol, open, high, low, close, volume] (EQ series only)."""
    if "SYMBOL" not in text[:400].upper():
        return None
    df = pd.read_csv(io.StringIO(text), skipinitialspace=True)
    df.columns = [c.strip().upper() for c in df.columns]
    need = {"SYMBOL", "SERIES", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"}
    if not need <= set(df.columns):
        return None
    df["SERIES"] = df["SERIES"].astype(str).str.strip()
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip()
    df = df[df["SERIES"] == "EQ"]
    out = pd.DataFrame({
        "symbol": df["SYMBOL"],
        "open": pd.to_numeric(df["OPEN_PRICE"], errors="coerce"),
        "high": pd.to_numeric(df["HIGH_PRICE"], errors="coerce"),
        "low": pd.to_numeric(df["LOW_PRICE"], errors="coerce"),
        "close": pd.to_numeric(df["CLOSE_PRICE"], errors="coerce"),
        "volume": pd.to_numeric(df["TTL_TRD_QNTY"], errors="coerce"),
    }).dropna()
    out = out[(out["close"] > 0) & (out["high"] >= out["low"])]
    return out if len(out) > 100 else None


def _download(d):
    """-> 'ok' | 'none' (no file that day: holiday/not yet published) | 'err'"""
    url = URL.format(d=f"{d:%d%m%Y}")
    for i in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://www.nseindia.com/", "Accept": "*/*"}, timeout=40)
            if r.status_code == 404:
                return "none"
            if r.status_code == 200:
                df = parse(r.text)
                if df is None:
                    return "err"
                with gzip.open(_path(d), "wt") as f:
                    df.to_csv(f, index=False)
                return "ok"
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return "err"


def cached_days():
    return sorted(p.stem.replace(".csv", "") for p in CACHE.glob("*.csv.gz"))


def refresh(days: int = 380, workers: int = 5) -> dict:
    """Download any missing daily files, prune old ones, (re)load the in-memory frames."""
    global _frames
    today = _today()
    wanted = [today - timedelta(n) for n in range(days)]
    wanted = [d for d in wanted if d.weekday() < 5]
    todo = [d for d in wanted if not _path(d).exists() and not _marker(d).exists()]
    stats = {"downloaded": 0, "no_file": 0, "errors": 0}
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for d, res in zip(todo, ex.map(_download, todo)):
                if res == "ok":
                    stats["downloaded"] += 1
                elif res == "none":
                    stats["no_file"] += 1
                    if (today - d).days >= 4:           # old missing day = exchange holiday; remember it
                        _marker(d).write_text("holiday")
                else:
                    stats["errors"] += 1
    cutoff = f"{today - timedelta(days + 15):%Y%m%d}"
    for p in list(CACHE.glob("*.csv.gz")) + list(CACHE.glob("*.none")):
        if p.name[:8] < cutoff:
            p.unlink()
    stats["days_cached"] = len(cached_days())
    stats["ok"] = stats["days_cached"] >= MIN_DAYS_OK
    _frames = None
    if stats["ok"]:
        load()
    return stats


def load():
    global _frames
    parts = []
    for p in sorted(CACHE.glob("*.csv.gz")):
        try:
            df = pd.read_csv(p)
            df["date"] = pd.Timestamp(datetime.strptime(p.name[:8], "%Y%m%d"))
            parts.append(df)
        except Exception:
            continue
    if not parts:
        _frames = {}
        return _frames
    big = pd.concat(parts, ignore_index=True).sort_values(["symbol", "date"])
    _frames = {sym: g.set_index("date")[["open", "high", "low", "close", "volume"]] for sym, g in big.groupby("symbol", sort=False)}
    return _frames


def get(symbol: str) -> pd.DataFrame | None:
    """Daily OHLCV for one NSE symbol. History before any suspected split/bonus is dropped."""
    global _frames
    if _frames is None:
        load()
    df = _frames.get(symbol)
    if df is None or len(df) < 30:
        return None
    r = df["close"] / df["close"].shift(1)
    bad = r[(r < 0.6) | (r > 1.8)]
    if len(bad):
        df = df[df.index > bad.index[-1]]     # keep only bars AFTER the jump day
    return df.copy() if len(df) >= 90 else None
