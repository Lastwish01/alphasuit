"""Build the list of instruments to scan (cached on disk, refreshed weekly)."""
from __future__ import annotations

import csv
import io
import json
import time

import requests

from .config import Config, DATA_DIR
from .data import LEVERAGED, STABLES, UA, get_json

CACHE_TTL = 7 * 24 * 3600

# Small built-in fallback so the scanner still works if the NSE/BSE list endpoints are unreachable.
FALLBACK_NSE = (
    "RELIANCE TCS HDFCBANK ICICIBANK INFY SBIN BHARTIARTL ITC LT HINDUNILVR KOTAKBANK AXISBANK BAJFINANCE "
    "MARUTI SUNPHARMA TITAN ULTRACEMCO ASIANPAINT NTPC POWERGRID ONGC TATAMOTORS TATASTEEL JSWSTEEL ADANIENT "
    "ADANIPORTS WIPRO HCLTECH TECHM NESTLEIND M&M BAJAJFINSV INDUSINDBK DRREDDY CIPLA GRASIM COALINDIA "
    "HINDALCO EICHERMOT BRITANNIA APOLLOHOSP DIVISLAB HEROMOTOCO SBILIFE HDFCLIFE TRENT BEL HAL DLF "
    "PIDILITIND SIEMENS ABB IRCTC PFC RECLTD CANBK BANKBARODA PNB IDFCFIRSTB FEDERALBNK AUBANK "
    "POLYCAB DIXON PERSISTENT COFORGE LTIM MPHASIS TVSMOTOR BAJAJ-AUTO ASHOKLEY CUMMINSIND VOLTAS "
    "HAVELLS CROMPTON JUBLFOOD DMART NAUKRI ZOMATO PAYTM NYKAA INDIGO MUTHOOTFIN CHOLAFIN SHRIRAMFIN "
    "LUPIN AUROPHARMA TORNTPHARM ZYDUSLIFE ALKEM MAXHEALTH FORTIS GODREJCP DABUR MARICO COLPAL TATAPOWER "
    "ADANIGREEN ADANIPOWER NHPC SJVN IRFC RVNL BHEL SAIL NMDC VEDL JINDALSTEL APLAPOLLO ASTRAL SUPREMEIND "
    "DEEPAKNTR PIIND SRF AARTIIND NAVINFLUOR TATAELXSI KPITTECH CDSL BSE ANGELONE MCX LICI IOC BPCL GAIL "
    "HINDPETRO PETRONET OIL TORNTPOWER JSWENERGY SUZLON INOXWIND ZEEL SUNTV PVRINOX"
).split()


def _cache_path(name):
    return DATA_DIR / f"universe_{name}.json"


def _cached(name):
    f = _cache_path(name)
    if f.exists() and time.time() - f.stat().st_mtime < CACHE_TTL:
        try:
            return json.loads(f.read_text())
        except Exception:
            return None
    return None


def _save(name, items):
    _cache_path(name).write_text(json.dumps(items))


def _get_text(url, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": "https://www.nseindia.com/"}
    h.update(headers or {})
    r = requests.get(url, headers=h, timeout=30)
    r.raise_for_status()
    return r.text


def load_nse():
    key = "nse_" + Config.NSE_UNIVERSE
    c = _cached(key)
    if c:
        return c
    items = []
    try:
        if Config.NSE_UNIVERSE == "nifty500":
            txt = _get_text("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv")
            for r in csv.DictReader(io.StringIO(txt)):
                items.append({"market": "stocks", "exchange": "NSE", "symbol": r["Symbol"].strip(),
                              "name": r["Company Name"].strip(), "ticker": r["Symbol"].strip() + ".NS",
                              "isin": r.get("ISIN Code", "").strip()})
        else:
            txt = _get_text("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
            for r in csv.DictReader(io.StringIO(txt)):
                r = {k.strip(): (v or "").strip() for k, v in r.items()}
                if r.get("SERIES") != "EQ":
                    continue
                items.append({"market": "stocks", "exchange": "NSE", "symbol": r["SYMBOL"],
                              "name": r.get("NAME OF COMPANY", r["SYMBOL"]), "ticker": r["SYMBOL"] + ".NS",
                              "isin": r.get("ISIN NUMBER", "")})
    except Exception:
        items = []
    if not items:  # fallback: bundled list or user-supplied data/custom_nse.csv
        custom = DATA_DIR / "custom_nse.csv"
        syms = [s.strip() for s in custom.read_text().split() if s.strip()] if custom.exists() else FALLBACK_NSE
        return [{"market": "stocks", "exchange": "NSE", "symbol": s, "name": s, "ticker": s + ".NS", "isin": ""} for s in syms]
    _save(key, items)
    return items


def load_bse(nse_isins):
    """BSE-listed equities that are NOT dual-listed on NSE (those are already covered)."""
    if not Config.BSE_ENABLED:
        return []
    c = _cached("bse")
    items = c
    if items is None:
        items = []
        try:
            j = get_json(
                "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w",
                {"Group": "", "Scripcode": "", "industry": "", "segment": "Equity", "status": "Active"},
                headers={"Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"},
            )
            for r in j or []:
                code = str(r.get("SCRIP_CD", "")).strip()
                if not code.isdigit():
                    continue
                sid = (r.get("scrip_id") or r.get("SCRIP_ID") or code).strip()
                items.append({"market": "stocks", "exchange": "BSE", "symbol": sid,
                              "name": (r.get("Scrip_Name") or r.get("SCRIP_NAME") or sid).strip(),
                              "ticker": code + ".BO", "isin": (r.get("ISIN_NUMBER") or "").strip()})
        except Exception:
            items = []
        if items:
            _save("bse", items)
    return [i for i in items if not i["isin"] or i["isin"] not in nse_isins]


def stock_universe():
    nse = load_nse()
    isins = {i["isin"] for i in nse if i.get("isin")}
    return nse + load_bse(isins)


def crypto_universe():
    j = get_json(f"{Config.CRYPTO_API_BASE}/api/v3/ticker/24hr")
    rows = []
    for t in j or []:
        s = t["symbol"]
        if not s.endswith("USDT") or s in LEVERAGED:
            continue
        base = s[:-4]
        if base in STABLES or base.endswith(("UP", "DOWN", "BULL", "BEAR")) and len(base) > 4:
            continue
        rows.append((float(t.get("quoteVolume", 0)), s, base))
    rows.sort(reverse=True)
    out = []
    for qv, s, base in rows[: Config.CRYPTO_TOP_N]:
        if qv < Config.MIN_TURNOVER_USD:
            continue
        out.append({"market": "crypto", "exchange": "BINANCE", "symbol": base + "/USDT", "name": base,
                    "ticker": s, "isin": ""})
    return out
