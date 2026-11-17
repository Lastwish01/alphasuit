"""Creates SAMPLE data (made-up stocks) so the website shows something before your first real scan.
Run:  python scanner/make_demo.py      The nightly scan replaces it with real results."""
import os, sys
from pathlib import Path
os.environ.update(MIN_SCORE="60", MIN_TURNOVER_INR="1", MIN_PRICE_INR="1", MIN_TURNOVER_USD="1", SCAN_WORKERS="2")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate
from demo_synth import path

SHAPES = {
    "DBOT": [(0, 100), (60, 100), (100, 70), (120, 88), (145, 70.6), (165, 86)],
    "DTOP": [(0, 60), (60, 60), (100, 90), (120, 74), (145, 89.5), (165, 76)],
    "HNS": [(0, 60), (50, 60), (80, 90), (95, 78), (125, 105), (150, 79), (170, 91), (185, 80)],
    "IHNS": [(0, 140), (50, 140), (80, 100), (95, 114), (125, 80), (150, 112), (170, 99), (185, 111)],
    "ASC": [(0, 50), (60, 90), (75, 100), (90, 88), (105, 100), (118, 92), (130, 100), (141, 95.5), (152, 99.2)],
    "DESC": [(0, 150), (60, 110), (75, 100), (90, 112), (105, 100), (118, 108), (130, 100), (141, 104), (152, 100.8)],
    "BULLFLAG": [(0, 80), (80, 100), (100, 100.5), (110, 130), (120, 124), (135, 123), (140, 125)],
    "BEARFLAG": [(0, 120), (80, 100), (100, 99), (110, 74), (120, 79), (135, 80), (140, 78.5)],
    "VCP": [(0, 40), (200, 100), (215, 126), (240, 100), (255, 128), (275, 112), (290, 129), (300, 122.5), (310, 129.2), (318, 126), (326, 128.4)],
}
FRAMES = {}
for i, (k, pts) in enumerate(SHAPES.items()):
    FRAMES[f"SAMPLE-{k}"] = path(pts, noise=0.003, seed=i + 1)
    FRAMES[f"SAMPLE-{k}/USDT"] = path(pts, noise=0.003, seed=i + 1)
FRAMES4H = {"SAMPLE-DBOT/USDT": path(SHAPES["DBOT"], noise=0.003, seed=1, freq="4h")}

def fetch(market, ticker, tf="1d"):
    return FRAMES.get(ticker) if tf == "1d" else FRAMES4H.get(ticker)

site = Path(__file__).resolve().parent.parent
stocks = [{"market": "stocks", "exchange": "NSE", "symbol": k, "name": "Sample company (demo data)", "ticker": k} for k in FRAMES if "/" not in k]
crypto = [{"market": "crypto", "exchange": "BINANCE", "symbol": k, "name": k.split("/")[0], "ticker": k} for k in FRAMES if "/" in k]
for market, items, tfs in (("stocks", stocks, ["1d"]), ("crypto", crypto, ["1d", "4h"])):
    res = generate.scan_market(market, items, tfs, fetch, workers=2)
    assert res["ok"], res
    generate.write_market(market, res, site, demo=True)
    print(market, "sample setups:", len(res["rows"]))
