#!/usr/bin/env python3
"""
Nightly scan -> JSON files that the static website reads.

  python scanner/generate.py all        # stocks + crypto
  python scanner/generate.py stocks
  python scanner/generate.py crypto
  --site DIR   where the website lives (default: the folder above /scanner)

Writes  DIR/data/stocks.json, DIR/data/crypto.json and DIR/data/charts/*.json
A market's files are only replaced when its scan succeeded - a failed scan never wipes yesterday's results.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from alphasuit import bhav, data, patterns, sheets, universe  # noqa: E402
from alphasuit.config import Config  # noqa: E402

SHOW_LEVELS = os.environ.get("SHOW_LEVELS", "0") == "1"   # entry/stop/target are NOT written unless you turn this on
CHART_BARS = 220


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)


def rnd(x):
    x = float(x)
    return round(x, 2) if abs(x) >= 1 else round(x, 6)


def tstamp(df, i, tf):
    i = max(0, min(int(i), len(df) - 1))
    ts = df.index[i]
    return int(ts.timestamp()) if tf != "1d" else ts.strftime("%Y-%m-%d")


def liquid(df, market, tf):
    last = df.tail(20)
    turnover = float((last["close"] * last["volume"]).mean())
    if market == "stocks":
        return df["close"].iloc[-1] >= Config.MIN_PRICE_INR and turnover >= Config.MIN_TURNOVER_INR
    return turnover * (6 if tf == "4h" else 1) >= Config.MIN_TURNOVER_USD


def analyse(item, tf, fetcher):
    try:
        df = fetcher(item["market"], item["ticker"], tf)
    except Exception as e:
        return {"error": str(e)}
    if df is None or len(df) < 90:
        return {"skipped": True}
    if item["market"] == "stocks":
        age = (pd.Timestamp.now(tz="UTC").tz_localize(None) - df.index[-1]).days
        if age > 6:                      # suspended / stale
            return {"skipped": True}
    if not liquid(df, item["market"], tf):
        return {"skipped": True}
    setups = patterns.scan_df(df, item["market"], tf, Config.MIN_SCORE)
    if not setups:
        return {"ok": True, "setups": []}
    start = max(0, len(df) - CHART_BARS)
    tail = df.iloc[start:]
    stem = safe(f"{item['market']}-{item['exchange']}-{item['symbol']}-{tf}")
    lines = {}
    for s in setups:
        out = []
        for (a, pa, c, pc, label) in s["lines"]:
            if a < start and c != a:       # clamp lines that begin before the visible window
                pa = pa + (pc - pa) * (start - a) / (c - a)
                a = start
            if c <= start:
                continue
            out.append({"t1": tstamp(df, a, tf), "p1": rnd(pa), "t2": tstamp(df, c, tf), "p2": rnd(pc), "label": label})
        lines[s["pattern"]] = out
    chart = {
        "symbol": item["symbol"], "name": item["name"], "exchange": item["exchange"], "timeframe": tf, "market": item["market"],
        "candles": [[tstamp(tail, k, tf), rnd(r.open), rnd(r.high), rnd(r.low), rnd(r.close), int(r.volume)]
                    for k, r in enumerate(tail.itertuples())],
        "lines": lines,
    }
    rows = []
    for s in setups:
        row = {"exchange": item["exchange"], "symbol": item["symbol"], "name": item["name"], "timeframe": tf,
               "pattern": s["pattern"], "label": s["label"], "direction": s["direction"], "status": s["status"],
               "score": s["score"], "price": rnd(s["price"]), "volume_ratio": s["volume_ratio"], "notes": s["notes"],
               "asof": str(df.index[-1])[:10], "chart": stem}
        if SHOW_LEVELS and s["entry"]:
            row.update(entry=rnd(s["entry"]), stop=rnd(s["stop"]), target=rnd(s["target"]), rr=s["rr"])
        rows.append(row)
    return {"ok": True, "rows": rows, "chart": (stem, chart), "setups": setups}


def scan_market(market, items, tfs, fetcher, workers=None):
    rows, charts = [], {}
    scanned = errors = 0
    first_error = None
    jobs = [(it, tf) for it in items for tf in tfs]
    with ThreadPoolExecutor(max_workers=workers or Config.SCAN_WORKERS) as ex:
        for f in as_completed([ex.submit(analyse, it, tf, fetcher) for it, tf in jobs]):
            r = f.result()
            if "error" in r:
                errors += 1
                first_error = first_error or r["error"]
            elif r.get("skipped"):
                continue
            else:
                scanned += 1
                if r.get("rows"):
                    rows += r["rows"]
                    charts[r["chart"][0]] = r["chart"][1]
    rows.sort(key=lambda r: (-r["score"], r["symbol"]))
    ok = scanned > 0 and errors / max(len(jobs), 1) < 0.8
    return {"ok": ok, "rows": rows, "charts": charts, "scanned": scanned, "errors": errors, "jobs": len(jobs), "first_error": first_error}


def write_market(market, res, site: Path, demo=False):
    out = site / "data"
    cdir = out / "charts"
    cdir.mkdir(parents=True, exist_ok=True)
    for p in cdir.glob(f"{market}-*.json"):      # remove this market's old charts, keep the other market's
        p.unlink()
    for stem, chart in res["charts"].items():
        (cdir / f"{stem}.json").write_text(json.dumps(chart, separators=(",", ":")))
    payload = {"market": market, "updated": now_iso(), "scanned": res["scanned"], "count": len(res["rows"]),
               "demo": demo, "levels": SHOW_LEVELS, "results": res["rows"]}
    (out / f"{market}.json").write_text(json.dumps(payload, separators=(",", ":")))


def stock_items_and_fetcher():
    notes = []
    data.USE_SHEETS[0] = data.USE_BHAV[0] = False
    src = Config.STOCK_DATA_SOURCE
    if src != "yahoo":
        if src == "auto":
            src = "sheets" if sheets.enabled() else "nse"
        if src == "sheets":
            try:
                st = sheets.refresh()
                data.USE_SHEETS[0] = st["ok"]
                notes.append(f"Google Sheet: {st['symbols']} symbols {st['errors'] or ''}")
            except Exception as e:
                notes.append(f"Google Sheet failed: {e}")
        if not data.USE_SHEETS[0]:
            try:
                st = bhav.refresh()
                data.USE_BHAV[0] = st["ok"]
                notes.append(f"NSE files: {st['days_cached']} days cached")
            except Exception as e:
                notes.append(f"NSE files unavailable: {e}")
    items = sheets.universe() if data.USE_SHEETS[0] else universe.stock_universe()
    source = "Google Sheet" if data.USE_SHEETS[0] else ("NSE files" if data.USE_BHAV[0] else "Yahoo")
    notes.append(f"using {source}")
    return items, data.fetch_ohlcv, notes


def run(market, site: Path):
    t0 = time.time()
    if market == "stocks":
        items, fetcher, notes = stock_items_and_fetcher()
        tfs = ["1d"]
    else:
        items, fetcher, notes = universe.crypto_universe(), data.fetch_ohlcv, []
        tfs = Config.CRYPTO_TIMEFRAMES or ["1d"]
    print(f"[{market}] {len(items)} symbols; {'; '.join(notes)}", flush=True)
    res = scan_market(market, items, tfs, fetcher)
    msg = f"[{market}] scanned {res['scanned']}, setups {len(res['rows'])}, errors {res['errors']}, {time.time()-t0:.0f}s"
    if res["ok"]:
        write_market(market, res, site)
        print(msg + " -> files written", flush=True)
    else:
        print(msg + f" -> FAILED, old results kept ({res['first_error']})", flush=True)
    return res["ok"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("market", choices=["stocks", "crypto", "all"])
    ap.add_argument("--site", default=str(HERE.parent))
    a = ap.parse_args()
    site = Path(a.site).resolve()
    ok = True
    for m in (["stocks", "crypto"] if a.market == "all" else [a.market]):
        try:
            ok = run(m, site) and ok
        except Exception as e:
            print(f"[{m}] crashed: {e}", flush=True)
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
