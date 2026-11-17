"""
Google Sheets as the stock-data source (via GOOGLEFINANCE + "Publish to web" CSV links).

Sheet layout (one TAB per ~250 symbols; generate it with `python manage.py sheet-setup`):
    row 1 : label of each block, e.g.  NSE:RELIANCE          (every 7th column)
    row 2 : =GOOGLEFINANCE("NSE:RELIANCE","all",TODAY()-380,TODAY(),"DAILY")   -> spills Date,Open,High,Low,Close,Volume
Publish each tab: File > Share > Publish to web > pick the tab > "Comma-separated values (.csv)".
Put the links (comma separated) in SHEETS_CSV_URLS.  The links only expose price data - never put private data in this sheet.
"""
from __future__ import annotations

import io
import pickle
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .config import Config, DATA_DIR
from .data import UA

IST = timezone(timedelta(hours=5, minutes=30))
CACHE_FILE = DATA_DIR / "sheets_cache.pkl"
_frames: dict | None = None
_lock = threading.Lock()


def urls():
    return [u.strip() for u in Config.SHEETS_CSV_URLS.split(",") if u.strip()]


def enabled():
    return bool(urls())


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def _parse_dates(col):
    s = col.astype(str).str.strip()
    s = s.where(~s.isin(["", "nan", "None"]))
    for kw in ({"format": "%m/%d/%Y %H:%M:%S"}, {"format": "%Y-%m-%d %H:%M:%S"}, {"format": "%Y-%m-%d"},
               {"format": "%m/%d/%Y"}, {"dayfirst": True}):
        d = pd.to_datetime(s, errors="coerce", **kw)
        if d.notna().sum() >= max(10, 0.8 * s.notna().sum()):
            return d.dt.normalize()
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def parse_csv(text: str) -> dict:
    """Published-CSV text of one tab -> {label: DataFrame(open,high,low,close,volume)}"""
    raw = pd.read_csv(io.StringIO(text), header=None, dtype=str, keep_default_na=False)
    out = {}
    if raw.shape[0] < 4:
        return out
    labels = raw.iloc[0]
    starts = [i for i, v in enumerate(labels) if str(v).strip() and ":" in str(v)]
    for c in starts:
        if c + 5 >= raw.shape[1]:
            continue
        blk = raw.iloc[2:, c:c + 6]
        blk.columns = ["date", "open", "high", "low", "close", "volume"]
        df = pd.DataFrame({"date": _parse_dates(blk["date"]), **{k: _num(blk[k]) for k in ("open", "high", "low", "close", "volume")}})
        df = df.dropna()
        df = df[(df["close"] > 0) & (df["high"] >= df["low"])]
        if df.empty:
            continue
        df = df.drop_duplicates("date", keep="last").set_index("date").sort_index()
        # drop today's still-forming candle (GOOGLEFINANCE updates it intraday)
        now = datetime.now(IST)
        if df.index[-1].date() == now.date() and now.hour < 16:
            df = df.iloc[:-1]
        out[str(labels.iloc[c]).strip().upper()] = df
    return out


def _fetch(u):
    last = None
    for i in range(3):
        try:
            r = requests.get(u, headers={"User-Agent": UA}, timeout=90)
            if r.status_code == 200 and r.text:
                return r.text
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(f"sheet download failed: {last}")


def refresh() -> dict:
    """Download every published tab, parse, cache. -> {'ok': bool, 'symbols': n, 'errors': [...]}"""
    global _frames
    frames, errs = {}, []
    for u in urls():
        try:
            frames.update(parse_csv(_fetch(u)))
        except Exception as e:
            errs.append(str(e)[:120])
    good = {k: v for k, v in frames.items() if len(v) >= 90}
    st = {"symbols": len(good), "skipped_short": len(frames) - len(good), "errors": errs, "ok": len(good) >= 1}
    if good:
        with _lock:
            _frames = good
        try:
            CACHE_FILE.write_bytes(pickle.dumps(good))
        except Exception:
            pass
    elif CACHE_FILE.exists():           # sheet unreachable: use the last good copy if it's recent (<3 days)
        age = datetime.now().timestamp() - CACHE_FILE.stat().st_mtime
        if age < 3 * 86400:
            _frames = pickle.loads(CACHE_FILE.read_bytes())
            st.update(ok=True, symbols=len(_frames), from_cache=True)
    return st


def universe() -> list:
    items = []
    for label in sorted(_frames or {}):
        ex, sym = label.split(":", 1)
        items.append({"market": "stocks", "exchange": "BSE" if ex in ("BOM", "BSE") else "NSE", "symbol": sym, "name": sym,
                      "ticker": label, "isin": ""})
    return items


def get(label: str):
    df = (_frames or {}).get(label.upper())
    if df is None or len(df) < 90:
        return None
    r = df["close"] / df["close"].shift(1)
    bad = r[(r < 0.6) | (r > 1.8)]          # unadjusted split/bonus jump: keep only bars after it
    if len(bad):
        df = df[df.index > bad.index[-1]]
    return df.copy() if len(df) >= 90 else None


# ------------------------------------------------------------------ setup helper
def build_setup_tabs(symbols, exchange="NSE", per_tab=250, days=380):
    """-> list of TSV strings (one per tab) ready to paste into cell A1 of a new Google Sheet tab."""
    tabs = []
    for i in range(0, len(symbols), per_tab):
        chunk = symbols[i:i + per_tab]
        row1, row2 = [], []
        for s in chunk:
            label = f"{exchange}:{s}"
            row1 += [label] + [""] * 6
            row2 += [f'=GOOGLEFINANCE("{label}","all",TODAY()-{days},TODAY(),"DAILY")'] + [""] * 6
        tabs.append("\t".join(row1) + "\n" + "\t".join(row2) + "\n")
    return tabs
