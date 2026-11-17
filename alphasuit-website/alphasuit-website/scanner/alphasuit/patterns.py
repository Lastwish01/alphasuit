"""
Alphasuit pattern engine.

Pure functions: DataFrame(open, high, low, close, volume) -> list of setups.
Core patterns (10): VCP, Head & Shoulders, Inverse H&S, Double Top, Double Bottom,
Cup & Handle, Ascending Triangle, Descending Triangle, Bull Flag, Bear Flag.
Extras (6): Symmetrical Triangle, Rising Wedge, Falling Wedge, Flat Base/Darvas,
52-Week High Breakout, Trend Pullback.

status:  "forming"  -> pattern is built, price approaching the trigger level
         "breakout" -> trigger level crossed recently (breakdown for bearish setups)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from scipy.stats import linregress

LABELS = {
    "vcp": "VCP",
    "head_shoulders": "Head & Shoulders",
    "inverse_head_shoulders": "Inverse Head & Shoulders",
    "double_top": "Double Top",
    "double_bottom": "Double Bottom",
    "cup_handle": "Cup & Handle",
    "ascending_triangle": "Ascending Triangle",
    "descending_triangle": "Descending Triangle",
    "bull_flag": "Bull Flag",
    "bear_flag": "Bear Flag",
    "symmetrical_triangle": "Symmetrical Triangle",
    "rising_wedge": "Rising Wedge",
    "falling_wedge": "Falling Wedge",
    "flat_base": "Flat Base / Darvas Box",
    "high_breakout": "52-Week High Breakout",
    "trend_pullback": "Trend Pullback",
}
CORE = list(LABELS)[:10]
EXTRA = list(LABELS)[10:]


# --------------------------------------------------------------------------- helpers
class Ctx:
    def __init__(self, df: pd.DataFrame, market: str, tf: str):
        self.df = df
        self.o = df["open"].to_numpy(float)
        self.h = df["high"].to_numpy(float)
        self.l = df["low"].to_numpy(float)
        self.c = df["close"].to_numpy(float)
        self.v = df["volume"].to_numpy(float)
        self.n = len(df)
        self.market = market
        self.tf = tf
        self.is_daily = tf == "1d"
        self.order = 6 if tf == "4h" else 5
        self.min_pole = 0.18 if market == "crypto" else 0.12
        lr = np.diff(np.log(self.c[-121:]))
        self.sig = float(max(np.std(lr), 0.004)) if len(lr) > 10 else 0.02
        self.vavg = self.v[-21:-1].mean() if self.n > 21 else self.v.mean()
        self.vr = float(self.v[-1] / self.vavg) if self.vavg > 0 else 1.0
        self._cache = {}

    def sma(self, n):
        k = ("s", n)
        if k not in self._cache:
            self._cache[k] = pd.Series(self.c).rolling(n).mean().to_numpy()
        return self._cache[k]

    def ema(self, n):
        k = ("e", n)
        if k not in self._cache:
            self._cache[k] = pd.Series(self.c).ewm(span=n, adjust=False).mean().to_numpy()
        return self._cache[k]

    def rsi(self, n=14):
        d = pd.Series(self.c).diff()
        up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        rs = up / dn.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


def zigzag(h, l, order=5):
    """Alternating confirmed swing highs/lows: [(idx, price, 'H'|'L'), ...]"""
    hi = argrelextrema(h, np.greater_equal, order=order)[0]
    lo = argrelextrema(l, np.less_equal, order=order)[0]
    pts = [(int(i), float(h[i]), "H") for i in hi] + [(int(i), float(l[i]), "L") for i in lo]
    pts.sort(key=lambda p: (p[0], p[2]))
    out = []
    for p in pts:
        if out and out[-1][0] == p[0]:
            continue
        if out and out[-1][2] == p[2]:
            if (p[2] == "H" and p[1] >= out[-1][1]) or (p[2] == "L" and p[1] <= out[-1][1]):
                out[-1] = p
        else:
            out.append(p)
    return out


def _rel(a, b):
    return abs(a - b) / ((a + b) / 2)


def _clamp(x, lo=0, hi=100):
    return int(max(lo, min(hi, round(x))))


def _res(pattern, direction, status, score, entry, stop, target, lines=None, notes=""):
    return {
        "pattern": pattern,
        "direction": direction,
        "status": status,
        "score": _clamp(score),
        "entry": None if entry is None else float(entry),
        "stop": None if stop is None else float(stop),
        "target": None if target is None else float(target),
        "lines": lines or [],
        "notes": notes,
    }


def _vol_bonus(x, status, strong=1.4):
    if status == "breakout":
        return 10 if x.vr >= strong else (4 if x.vr >= 1.1 else -6)
    return 0


# --------------------------------------------------------------------------- double top / bottom
def d_double(x: Ctx, zz, top: bool):
    ext = "H" if top else "L"
    exts = [p for p in zz if p[2] == ext]
    cl = x.c[-1]
    for j in range(len(exts) - 1, max(len(exts) - 4, 0), -1):
        i1, v1, _ = exts[j - 1]
        i2, v2, _ = exts[j]
        gap = i2 - i1
        if gap < 10 or gap > 90 or x.n - 1 - i2 > 30:
            continue
        sim = _rel(v1, v2)
        if sim > 0.035:
            continue
        pre = x.c[max(0, i1 - 60): i1 + 1]
        if top:
            neck = x.l[i1: i2 + 1].min()
            peak = max(v1, v2)
            depth = (peak - neck) / peak
            trend = v1 / pre.min() - 1
            if i2 + 1 < x.n and x.h[i2 + 1:].max() > peak * 1.015:
                continue
        else:
            neck = x.h[i1: i2 + 1].max()
            peak = min(v1, v2)
            depth = (neck - peak) / neck
            trend = pre.max() / v1 - 1
            if i2 + 1 < x.n and x.l[i2 + 1:].min() < peak * 0.985:
                continue
        if depth < max(0.06, 1.2 * x.sig * np.sqrt(gap)) or trend < max(0.12, 1.0 * x.sig * np.sqrt(min(60, i1 + 1))):
            continue
        # status
        if top:
            if cl < neck:
                if (neck - cl) / neck > 0.06:
                    continue
                status = "breakout"
                prox = 1
            else:
                if (cl - neck) > 0.6 * (peak - neck):
                    continue
                status = "forming"
                prox = 1 - (cl - neck) / (peak - neck)
            entry, stop, target = neck * 0.999, peak * 1.01, neck - (peak - neck)
            pat, dirn = "double_top", "bearish"
        else:
            if cl > neck:
                if (cl - neck) / neck > 0.06:
                    continue
                status = "breakout"
                prox = 1
            else:
                if (neck - cl) > 0.6 * (neck - peak):
                    continue
                status = "forming"
                prox = 1 - (neck - cl) / (neck - peak)
            entry, stop, target = neck * 1.001, peak * 0.99, neck + (neck - peak)
            pat, dirn = "double_bottom", "bullish"
        score = (45 + (1 - sim / 0.035) * 15 + min(depth / 0.15, 1) * 10 + min(trend / 0.3, 1) * 5
                 + (12 if status == "breakout" else prox * 10) + _vol_bonus(x, status))
        lines = [(i1, neck, x.n - 1, neck, "Neckline"), (i1, v1, i2, v2, "Tops" if top else "Bottoms")]
        return _res(pat, dirn, status, score, entry, stop, target, lines,
                    f"Two {'tops' if top else 'bottoms'} within {sim*100:.1f}% of each other, neckline {neck:.2f}")
    return None


# --------------------------------------------------------------------------- head & shoulders
def d_hs(x: Ctx, zz, inverse: bool):
    ext = "L" if inverse else "H"
    exts = [p for p in zz if p[2] == ext]
    cl = x.c[-1]
    for k in range(len(exts) - 1, max(len(exts) - 3, 1), -1):
        (ia, va, _), (ih, vh, _), (ib, vb, _) = exts[k - 2], exts[k - 1], exts[k]
        if ih - ia < 6 or ib - ih < 6 or ib - ia > 130 or x.n - 1 - ib > 20:
            continue
        if _rel(va, vb) > 0.10:
            continue
        pre = x.c[max(0, ia - 60): ia + 1]
        if not inverse:
            if vh < max(va, vb) * 1.03:
                continue
            n1i = ia + int(np.argmin(x.l[ia: ih + 1])); n1 = x.l[n1i]
            n2i = ih + int(np.argmin(x.l[ih: ib + 1])); n2 = x.l[n2i]
            if va / pre.min() - 1 < 0.08:
                continue
        else:
            if vh > min(va, vb) * 0.97:
                continue
            n1i = ia + int(np.argmax(x.h[ia: ih + 1])); n1 = x.h[n1i]
            n2i = ih + int(np.argmax(x.h[ih: ib + 1])); n2 = x.h[n2i]
            if pre.max() / va - 1 < 0.08:
                continue
        if n2i == n1i:
            continue
        slope = (n2 - n1) / (n2i - n1i)
        neck_at = lambda i: n1 + slope * (i - n1i)
        neck_now = neck_at(x.n - 1)
        if abs(neck_now / n1 - 1) > 0.12:
            continue
        head_h = abs(vh - neck_at(ih))
        rs_h = abs(vb - neck_at(ib))
        if head_h <= 0 or rs_h / head_h < 0.35:
            continue
        if not inverse:
            if cl < neck_now:
                if (neck_now - cl) / neck_now > 0.06:
                    continue
                status, prox = "breakout", 1
            else:
                if cl > vb or (cl - neck_now) / neck_now > 0.08:
                    continue
                status, prox = "forming", 1 - (cl - neck_now) / (vb - neck_now + 1e-9)
            entry, stop, target = neck_now * 0.999, vb * 1.01, neck_now - head_h
            pat, dirn = "head_shoulders", "bearish"
        else:
            if cl > neck_now:
                if (cl - neck_now) / neck_now > 0.06:
                    continue
                status, prox = "breakout", 1
            else:
                if cl < vb or (neck_now - cl) / neck_now > 0.08:
                    continue
                status, prox = "forming", 1 - (neck_now - cl) / (neck_now - vb + 1e-9)
            entry, stop, target = neck_now * 1.001, vb * 0.99, neck_now + head_h
            pat, dirn = "inverse_head_shoulders", "bullish"
        sym = 1 - _rel(va, vb) / 0.10
        score = (48 + sym * 12 + min(head_h / (abs(vh) * 0.10), 1) * 8
                 + (12 if status == "breakout" else max(prox, 0) * 10) + _vol_bonus(x, status))
        lines = [(n1i, n1, x.n - 1, neck_now, "Neckline"), (ia, va, ih, vh, "Left → Head"), (ih, vh, ib, vb, "Head → Right")]
        return _res(pat, dirn, status, score, entry, stop, target, lines,
                    f"Neckline {neck_now:.2f}, head {vh:.2f}")
    return None


# --------------------------------------------------------------------------- cup & handle
def d_cup(x: Ctx, zz):
    if x.n < 80:
        return None
    cl = x.c[-1]
    Hs = [p for p in zz if p[2] == "H" and x.n - 160 <= p[0] <= x.n - 25]
    best = None
    for a, ha, _ in Hs:
        b = a + int(np.argmin(x.l[a:]))
        if b - a < 15 or b > x.n - 8:
            continue
        r = b + int(np.argmax(x.h[b:]))
        if r - b < 15 or x.n - 1 - r > 30:
            continue
        hr = x.h[r]
        depth = (ha - x.l[b]) / ha
        if not (0.12 <= depth <= 0.45) or not (0.92 * ha <= hr <= 1.04 * ha):
            continue
        if depth < 0.9 * x.sig * np.sqrt(r - a):
            continue
        pre = x.c[max(0, a - 60): a + 1]
        if ha / pre.min() - 1 < max(0.15, 1.0 * x.sig * np.sqrt(len(pre))):
            continue
        seg = x.c[a: r + 1]
        t = np.linspace(-1, 1, len(seg))
        coef = np.polyfit(t, seg, 2)
        fit = np.polyval(coef, t)
        ss_res = ((seg - fit) ** 2).sum()
        ss_tot = ((seg - seg.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        if coef[0] <= 0 or r2 < 0.65:
            continue
        if not (0.25 <= (b - a) / (r - a) <= 0.75):
            continue
        handle_low = x.l[r:].min() if r < x.n - 1 else hr
        hd = (hr - handle_low) / hr
        if hd > 0.15 or hd > 0.5 * depth:
            continue
        if handle_low < x.l[b] + 0.5 * (ha - x.l[b]):
            continue
        pivot = max(ha, hr)
        if cl > pivot * 1.0:
            if cl / pivot - 1 > 0.05:
                continue
            status, prox = "breakout", 1
        elif cl >= pivot * 0.95:
            status, prox = "forming", 1 - (pivot - cl) / (pivot * 0.05)
        else:
            continue
        entry = pivot * 1.001
        stop = max(handle_low * 0.99, entry * 0.88)
        target = entry + (ha - x.l[b])
        hv = x.v[r:].mean() if r < x.n - 1 else x.v[-1]
        dry = hv < x.v[a:r + 1].mean() * 0.9
        score = (46 + r2 * 14 + (6 if dry else 0) + (10 if 0.15 <= depth <= 0.35 else 4)
                 + (12 if status == "breakout" else max(prox, 0) * 10) + _vol_bonus(x, status))
        cand = _res("cup_handle", "bullish", status, score, entry, stop, target,
                    [(a, ha, r, hr, "Cup rims"), (a, pivot, x.n - 1, pivot, "Pivot")],
                    f"Cup depth {depth*100:.0f}%, handle {hd*100:.0f}%, pivot {pivot:.2f}")
        if best is None or cand["score"] > best["score"]:
            best = cand
    return best


# --------------------------------------------------------------------------- triangles & wedges
def d_channels(x: Ctx, zz):
    out = {}
    cl = x.c[-1]
    for win in (45, 70, 100):
        start = x.n - win
        if start < 0:
            continue
        H = [p for p in zz if p[2] == "H" and p[0] >= start][-4:]
        L = [p for p in zz if p[2] == "L" and p[0] >= start][-4:]
        if len(H) < 2 or len(L) < 2 or len(H) + len(L) < 5:
            continue
        if H[-1][0] - H[0][0] < 15 or L[-1][0] - L[0][0] < 15:
            continue
        hx = np.array([p[0] for p in H], float); hy = np.array([p[1] for p in H])
        lx = np.array([p[0] for p in L], float); ly = np.array([p[1] for p in L])
        sh, sl = linregress(hx, hy), linregress(lx, ly)
        i0 = int(min(hx[0], lx[0]))
        span = x.n - 1 - i0
        up_at = lambda i: sh.intercept + sh.slope * i
        lo_at = lambda i: sl.intercept + sl.slope * i
        up_now, lo_now = up_at(x.n - 1), lo_at(x.n - 1)
        if up_now <= lo_now:
            continue
        mean = x.c[i0:].mean()
        dh, dl = sh.slope * span / mean, sl.slope * span / mean
        w0, w1 = up_at(i0) - lo_at(i0), up_now - lo_now
        if w0 <= 0 or w1 / w0 > 0.75:
            continue
        res = max(np.abs(hy - up_at(hx)).max(), np.abs(ly - lo_at(lx)).max()) / mean
        if res > 0.025:
            continue
        flat = 0.03
        if abs(dh) <= flat and dl >= 0.04:
            kind, bias = "ascending_triangle", "bullish"
        elif abs(dl) <= flat and dh <= -0.04:
            kind, bias = "descending_triangle", "bearish"
        elif dh <= -0.03 and dl >= 0.03:
            kind, bias = "symmetrical_triangle", "neutral"
        elif dh >= 0.05 and dl >= 0.05 and dl > dh * 1.15 and len(H) + len(L) >= 6:
            kind, bias = "rising_wedge", "bearish"
        elif dh <= -0.05 and dl <= -0.05 and dh < dl * 1.15 and len(H) + len(L) >= 6:
            kind, bias = "falling_wedge", "bullish"
        else:
            continue

        def broke_recent(side):
            idxs = range(max(0, x.n - 6), x.n - 1)
            if side == "up":
                return any(x.c[i] <= up_at(i) * 1.002 for i in idxs)
            return any(x.c[i] >= lo_at(i) * 0.998 for i in idxs)

        up_break = cl > up_now * 1.002
        dn_break = cl < lo_now * 0.998
        status, direction = "forming", bias
        if up_break:
            if bias in ("bearish",) or (cl / up_now - 1) > 0.06 or not broke_recent("up"):
                continue
            status, direction = "breakout", "bullish"
        elif dn_break:
            if bias == "bullish" or (lo_now / cl - 1) > 0.06 or not broke_recent("dn"):
                continue
            status, direction = "breakout", "bearish"
        else:
            dist_up, dist_dn = (up_now - cl) / up_now, (cl - lo_now) / lo_now
            prox_dist = dist_up if bias == "bullish" else dist_dn if bias == "bearish" else min(dist_up, dist_dn)
            if prox_dist > 0.06:
                continue
        touches = len(H) + len(L)
        score = 50 + min((touches - 4) * 4, 12) + (1 - res / 0.025) * 10
        if status == "breakout":
            score += 15 + _vol_bonus(x, status)
        else:
            pd_ = prox_dist
            score += (1 - pd_ / 0.06) * 10
        lines = [(int(hx[0]), up_at(hx[0]), x.n - 1, up_now, "Resistance"),
                 (int(lx[0]), lo_at(lx[0]), x.n - 1, lo_now, "Support")]
        if direction == "bullish":
            entry = up_now * 1.002
            stop = max(lo_now * 0.99, entry * 0.90)
            target = entry + w0
        elif direction == "bearish":
            entry = lo_now * 0.998
            stop = min(up_now * 1.01, entry * 1.10)
            target = entry - w0
        else:
            entry = stop = target = None
        note = f"Resistance {up_now:.2f} / support {lo_now:.2f}, {touches} touches"
        if entry is None:
            note += " - trade the break either way"
        cand = _res(kind, direction, status, score, entry, stop, target, lines, note)
        if kind not in out or cand["score"] > out[kind]["score"]:
            out[kind] = cand
    return list(out.values())


# --------------------------------------------------------------------------- flags
def d_flag(x: Ctx, up: bool):
    best = None
    n = x.n
    cl = x.c[-1]
    for fl in range(4, 26):
        p = n - 1 - fl
        if p < 20:
            break
        for pl in (5, 8, 12, 16, 20):
            a = p - pl
            if a < 0:
                continue
            if up:
                lo_i = a + int(np.argmin(x.l[a: p + 1]))
                if lo_i >= p:
                    continue
                lo_p, hi_p = x.l[lo_i], x.h[p]
                pole = hi_p / lo_p - 1
                if pole < max(x.min_pole, 3.5 * x.sig * np.sqrt(pl)) or x.h[p + 1:].max() > hi_p * 1.02:
                    continue
                pb = x.l[p + 1:].min()
                retr = (hi_p - pb) / (hi_p - lo_p)
                fcl = x.c[p + 1:]
                drift = np.polyfit(np.arange(len(fcl)), fcl, 1)[0] * len(fcl) / fcl.mean()
                if retr > 0.45 or not (-0.15 <= drift <= 0.02):
                    continue
                upper = x.h[p + 1:-1].max() if fl > 1 else hi_p
                brk = cl > upper
                if brk and cl / upper - 1 > 0.05:
                    continue
                if not brk and (upper - cl) / upper > 0.08:
                    continue
                entry = upper * 1.001
                stop = max(pb * 0.99, entry * 0.88)
                target = entry + (hi_p - lo_p)
                dirn, pat = "bullish", "bull_flag"
                pts = (lo_i, lo_p, p, hi_p, "Pole")
                lines = [pts, (p, upper, n - 1, upper, "Flag top")]
            else:
                hi_i = a + int(np.argmax(x.h[a: p + 1]))
                if hi_i >= p:
                    continue
                hi_p, lo_p = x.h[hi_i], x.l[p]
                pole = 1 - lo_p / hi_p
                if pole < max(x.min_pole, 3.5 * x.sig * np.sqrt(pl)) or x.l[p + 1:].min() < lo_p * 0.98:
                    continue
                rally = x.h[p + 1:].max()
                retr = (rally - lo_p) / (hi_p - lo_p)
                fcl = x.c[p + 1:]
                drift = np.polyfit(np.arange(len(fcl)), fcl, 1)[0] * len(fcl) / fcl.mean()
                if retr > 0.45 or not (-0.02 <= drift <= 0.15):
                    continue
                lower = x.l[p + 1:-1].min() if fl > 1 else lo_p
                brk = cl < lower
                if brk and lower / cl - 1 > 0.05:
                    continue
                if not brk and (cl - lower) / lower > 0.08:
                    continue
                entry = lower * 0.999
                stop = min(rally * 1.01, entry * 1.12)
                target = entry - (hi_p - lo_p)
                dirn, pat = "bearish", "bear_flag"
                lines = [(hi_i, hi_p, p, lo_p, "Pole"), (p, lower, n - 1, lower, "Flag bottom")]
            status = "breakout" if brk else "forming"
            vol_pole = x.v[a: p + 1].mean()
            dry = x.v[p + 1:].mean() < 0.9 * vol_pole if vol_pole > 0 else False
            tight = 1 - min(retr / 0.5, 1)
            score = (48 + min(pole / (x.min_pole * 2), 1) * 14 + tight * 10 + (6 if dry else 0)
                     + (12 if brk else 4) + _vol_bonus(x, status))
            cand = _res(pat, dirn, status, score, entry, stop, target, lines,
                        f"Pole {pole*100:.0f}% in {pl} bars, flag {fl} bars, retrace {retr*100:.0f}%")
            if best is None or cand["score"] > best["score"]:
                best = cand
    return best


# --------------------------------------------------------------------------- VCP
def d_vcp(x: Ctx, zz):
    if not x.is_daily or x.n < 150:
        return None
    c, cl = x.c, x.c[-1]
    s50, s150 = x.sma(50), x.sma(150)
    if not (cl > s50[-1] > s150[-1]):
        return None
    if x.n >= 200:
        s200 = x.sma(200)
        if not s150[-1] > s200[-1]:
            return None
    yr = min(x.n, 252)
    hi52, lo52 = x.h[-yr:].max(), x.l[-yr:].min()
    if cl < 0.75 * hi52 or cl < 1.3 * lo52:
        return None
    pts = [p for p in zz if p[0] >= x.n - 140]
    pairs = [(a, b, (a[1] - b[1]) / a[1]) for a, b in zip(pts, pts[1:]) if a[2] == "H" and b[2] == "L"]
    if len(pairs) < 2:
        return None
    m = int(np.argmax([p[2] for p in pairs[:-1]]))
    seq = pairs[m:]
    if not (3 <= len(seq) <= 6):
        return None
    depths = [p[2] for p in seq]
    if depths[0] > 0.45 or depths[0] < 0.15:
        return None
    if any(depths[i + 1] > depths[i] * 0.97 for i in range(len(depths) - 1)):
        return None
    if depths[-1] > 0.12 or depths[-1] > 0.6 * depths[0]:
        return None
    base_start = seq[0][0][0]
    pivot = x.h[base_start:].max()
    last_low = seq[-1][1][1]
    if cl > last_low * 1.0 and cl >= pivot * 0.999:
        if cl / pivot - 1 > 0.05:
            return None
        status, prox = "breakout", 1
    else:
        dist = (pivot - cl) / pivot
        if dist > 0.06 or cl < last_low:
            return None
        status, prox = "forming", 1 - dist / 0.06
    entry = pivot * 1.001
    stop = max(last_low * 0.99, entry * 0.90)
    target = entry + max(entry * depths[0], 2 * (entry - stop))
    dry = x.v[-10:].mean() < 0.85 * x.v[-50:].mean()
    score = (50 + min((len(seq) - 3) * 6 + 6, 14) + (10 if depths[-1] <= 0.08 else 4) + (8 if dry else 0)
             + (12 if status == "breakout" else prox * 8) + (_vol_bonus(x, status, 1.4)))
    lines = [(base_start, pivot, x.n - 1, pivot, "Pivot")]
    return _res("vcp", "bullish", status, score, entry, stop, target, lines,
                f"{len(seq)} contractions: " + " → ".join(f"{d*100:.0f}%" for d in depths) + f", pivot {pivot:.2f}")


# --------------------------------------------------------------------------- extras
def d_flat_base(x: Ctx, zz):
    if x.n < 100:
        return None
    cl = x.c[-1]
    max_rng = 0.18 if x.market == "crypto" else 0.12
    best = None
    for L in (25, 35, 50):
        seg_h, seg_l = x.h[-L - 1:-1], x.l[-L - 1:-1]
        top, bot = seg_h.max(), seg_l.min()
        rng = (top - bot) / top
        if rng > max_rng:
            continue
        if x.c[-L - 1] / x.c[-L - 61] - 1 < 0.15 or cl < x.sma(50)[-1]:
            continue
        if cl > top:
            if cl / top - 1 > 0.04:
                continue
            status, prox = "breakout", 1
        elif cl >= top * 0.97:
            status, prox = "forming", 1 - (top - cl) / (top * 0.03)
        else:
            continue
        entry = top * 1.001
        stop = max(bot * 0.99, entry * 0.88)
        target = entry + max(2 * (entry - stop), (top - bot) * 2)
        score = 50 + (1 - rng / max_rng) * 15 + (4 if L >= 35 else 0) + (12 if status == "breakout" else prox * 8) + _vol_bonus(x, status)
        cand = _res("flat_base", "bullish", status, score, entry, stop, target,
                    [(x.n - L - 1, top, x.n - 1, top, "Box top"), (x.n - L - 1, bot, x.n - 1, bot, "Box bottom")],
                    f"{L}-bar base, range {rng*100:.1f}%")
        if best is None or cand["score"] > best["score"]:
            best = cand
    return best


def d_high_breakout(x: Ctx, zz):
    if not x.is_daily or x.n < 200:
        return None
    cl = x.c[-1]
    hi = x.h[-253:-1].max()
    if cl > hi:
        if cl / hi - 1 > 0.04 or x.vr < 1.2:
            return None
        status = "breakout"
    elif cl >= hi * 0.98:
        status = "forming"
    else:
        return None
    entry = hi * 1.001
    stop = max(x.l[-10:].min() * 0.99, entry * 0.90)
    target = entry + 2 * (entry - stop)
    score = (62 if status == "breakout" else 48) + (8 if status == "breakout" else (1 - (hi - cl) / (hi * 0.02)) * 8) + _vol_bonus(x, status, 1.6)
    return _res("high_breakout", "bullish", status, score, entry, stop, target,
                [(x.n - 252 if x.n > 252 else 0, hi, x.n - 1, hi, "52W high")], f"52-week high {hi:.2f}, volume {x.vr:.1f}x average")


def d_pullback(x: Ctx, zz):
    if x.n < 120:
        return None
    e21, e50 = x.ema(21), x.ema(50)
    cl = x.c[-1]
    rsi = x.rsi()
    if not (e21[-1] > e50[-1] and e50[-1] > e50[-20] and cl > e50[-1] * 0.99):
        return None
    if rsi[-25:-1].max() < 62 or not (38 <= rsi[-1] <= 55):
        return None
    near21 = abs(cl - e21[-1]) / e21[-1] <= 0.015
    near50 = abs(cl - e50[-1]) / e50[-1] <= 0.015
    if not (near21 or near50):
        return None
    top = x.h[-20:].max()
    if not (0.04 <= (top - cl) / top <= 0.18) or cl <= x.o[-1]:
        return None
    entry = x.h[-1] * 1.001
    stop = x.l[-5:].min() * 0.99
    if entry - stop <= 0:
        return None
    target = max(top, entry + 1.5 * (entry - stop))
    score = 55 + (6 if near50 else 4) + (5 if x.v[-1] > x.vavg else 0) + (5 if x.c[-1] > x.sma(50)[-1] else 0)
    return _res("trend_pullback", "bullish", "forming", score, entry, stop, target,
                [], f"Uptrend pullback to {'EMA50' if near50 else 'EMA21'}, RSI {rsi[-1]:.0f}")


# --------------------------------------------------------------------------- orchestration
def scan_df(df: pd.DataFrame, market: str, tf: str = "1d", min_score: int = 55):
    """Run every detector on one instrument. Returns a list of setup dicts."""
    if df is None or len(df) < 90:
        return []
    df = df[["open", "high", "low", "close", "volume"]].astype(float).dropna()
    if len(df) < 90 or df["close"].iloc[-1] <= 0:
        return []
    x = Ctx(df, market, tf)
    zz = zigzag(x.h, x.l, x.order)
    found = []
    for fn in (
        lambda: d_double(x, zz, True), lambda: d_double(x, zz, False),
        lambda: d_hs(x, zz, False), lambda: d_hs(x, zz, True),
        lambda: d_cup(x, zz), lambda: d_flag(x, True), lambda: d_flag(x, False),
        lambda: d_vcp(x, zz), lambda: d_flat_base(x, zz),
        lambda: d_high_breakout(x, zz), lambda: d_pullback(x, zz),
    ):
        try:
            r = fn()
        except Exception:  # a single bad detector must never kill a scan
            r = None
        if r:
            found.append(r)
    try:
        found.extend(d_channels(x, zz))
    except Exception:
        pass
    out = []
    for r in found:
        if r["score"] < min_score:
            continue
        r["price"] = float(x.c[-1])
        r["volume_ratio"] = round(x.vr, 2)
        r["timeframe"] = tf
        if r["entry"] and r["stop"] and r["target"] and abs(r["entry"] - r["stop"]) > 0:
            r["rr"] = round(abs(r["target"] - r["entry"]) / abs(r["entry"] - r["stop"]), 2)
        else:
            r["rr"] = None
        r["label"] = LABELS[r["pattern"]]
        out.append(r)
    out.sort(key=lambda r: -r["score"])
    return out


def evaluate_outcome(rec: dict, df: pd.DataFrame):
    """
    Track a past setup. rec: direction, entry, stop, target, status, scanned_on, outcome, triggered.
    Returns (outcome, outcome_date, triggered) where outcome in pending|open|target|stopped|expired.
    Stop is assumed hit first if both stop and target fall within one bar (conservative).
    """
    if rec["direction"] not in ("bullish", "bearish") or not rec.get("entry"):
        return "na", None, 0
    after = df[df.index > pd.Timestamp(rec["scanned_on"])]
    bull = rec["direction"] == "bullish"
    triggered = bool(rec.get("triggered")) or rec["status"] == "breakout"
    entry, stop, target = rec["entry"], rec["stop"], rec["target"]
    bars_pending = bars_open = 0
    for ts, r in after.iterrows():
        if not triggered:
            bars_pending += 1
            if (bull and r["high"] >= entry) or (not bull and r["low"] <= entry):
                triggered = True
            elif bars_pending > 15:
                return "expired", str(ts.date()), 0
            else:
                continue
        bars_open += 1
        hit_stop = r["low"] <= stop if bull else r["high"] >= stop
        hit_tgt = r["high"] >= target if bull else r["low"] <= target
        if hit_stop:
            return "stopped", str(ts.date()), 1
        if hit_tgt:
            return "target", str(ts.date()), 1
        if bars_open > 40:
            return "expired", str(ts.date()), 1
    return ("open" if triggered else "pending"), None, int(triggered)


# bias + plain-English description (used by the pattern library page)
INFO = {
    "vcp": ("bullish", "Minervini's Volatility Contraction Pattern: a stage-2 uptrend whose pullbacks get progressively shallower on drying volume, ready to break out of the pivot."),
    "head_shoulders": ("bearish", "Three peaks with a higher middle peak after an uptrend. A close below the neckline signals trend reversal."),
    "inverse_head_shoulders": ("bullish", "Three troughs with a deeper middle trough after a downtrend. A close above the neckline signals a reversal up."),
    "double_top": ("bearish", "Two similar highs separated by a meaningful pullback. A break below the middle trough confirms the reversal."),
    "double_bottom": ("bullish", "Two similar lows separated by a rally. A break above the middle peak confirms the reversal."),
    "cup_handle": ("bullish", "O'Neil's rounded base followed by a short, shallow handle on lighter volume; buy the break of the rim."),
    "ascending_triangle": ("bullish", "Flat resistance with rising lows - buyers are getting more aggressive into a breakout."),
    "descending_triangle": ("bearish", "Flat support with falling highs - sellers press until support gives way."),
    "bull_flag": ("bullish", "A sharp rally (the pole) followed by a tight, slightly down-sloping pause; continuation on the break of the flag."),
    "bear_flag": ("bearish", "A sharp drop followed by a weak, slightly up-sloping bounce; continuation lower on the break of the flag."),
    "symmetrical_triangle": ("neutral", "Converging highs and lows. Direction is decided by the breakout side."),
    "rising_wedge": ("bearish", "Both trendlines rise but converge - momentum fades, usually resolving down."),
    "falling_wedge": ("bullish", "Both trendlines fall but converge - selling pressure fades, usually resolving up."),
    "flat_base": ("bullish", "A tight sideways box (Darvas-style) after an advance; breakout above the box top."),
    "high_breakout": ("bullish", "Price clearing its 52-week high on expanding volume - strength begets strength."),
    "trend_pullback": ("bullish", "A healthy dip to the 21/50 EMA inside an established uptrend, with RSI reset."),
}

SHAPES = {
    "vcp": "2,24 10,4 18,20 26,7 34,17 42,10 50,14 58,3",
    "head_shoulders": "2,24 10,12 16,20 26,4 36,20 44,12 52,20 58,26",
    "inverse_head_shoulders": "2,4 10,16 16,8 26,24 36,8 44,16 52,8 58,2",
    "double_top": "2,24 14,6 24,18 36,6 46,20 58,28",
    "double_bottom": "2,4 14,22 24,10 36,22 46,8 58,2",
    "cup_handle": "2,6 8,16 16,24 28,26 40,20 48,8 52,12 58,4",
    "ascending_triangle": "2,24 14,6 22,20 32,6 40,16 50,6 58,2",
    "descending_triangle": "2,4 14,22 22,8 32,22 40,12 50,22 58,28",
    "bull_flag": "2,28 14,4 22,8 30,6 38,12 46,10 58,2",
    "bear_flag": "2,2 14,26 22,22 30,24 38,18 46,20 58,28",
    "symmetrical_triangle": "2,4 12,24 22,8 32,20 42,12 50,16 58,10",
    "rising_wedge": "2,26 14,16 22,20 34,10 42,13 52,6 58,10",
    "falling_wedge": "2,4 14,14 22,10 34,20 42,17 52,24 58,20",
    "flat_base": "2,26 10,8 18,10 28,8 38,10 46,9 58,2",
    "high_breakout": "2,24 14,14 24,18 34,10 44,12 52,8 58,2",
    "trend_pullback": "2,26 16,14 26,20 34,10 44,18 52,6 58,2",
}
