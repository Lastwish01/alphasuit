window.PATTERNS={
 "core": [
  "vcp",
  "head_shoulders",
  "inverse_head_shoulders",
  "double_top",
  "double_bottom",
  "cup_handle",
  "ascending_triangle",
  "descending_triangle",
  "bull_flag",
  "bear_flag"
 ],
 "extra": [
  "symmetrical_triangle",
  "rising_wedge",
  "falling_wedge",
  "flat_base",
  "high_breakout",
  "trend_pullback"
 ],
 "info": {
  "vcp": {
   "label": "VCP",
   "bias": "bullish",
   "desc": "Minervini's Volatility Contraction Pattern: a stage-2 uptrend whose pullbacks get progressively shallower on drying volume, ready to break out of the pivot.",
   "shape": "2,24 10,4 18,20 26,7 34,17 42,10 50,14 58,3"
  },
  "head_shoulders": {
   "label": "Head & Shoulders",
   "bias": "bearish",
   "desc": "Three peaks with a higher middle peak after an uptrend. A close below the neckline signals trend reversal.",
   "shape": "2,24 10,12 16,20 26,4 36,20 44,12 52,20 58,26"
  },
  "inverse_head_shoulders": {
   "label": "Inverse Head & Shoulders",
   "bias": "bullish",
   "desc": "Three troughs with a deeper middle trough after a downtrend. A close above the neckline signals a reversal up.",
   "shape": "2,4 10,16 16,8 26,24 36,8 44,16 52,8 58,2"
  },
  "double_top": {
   "label": "Double Top",
   "bias": "bearish",
   "desc": "Two similar highs separated by a meaningful pullback. A break below the middle trough confirms the reversal.",
   "shape": "2,24 14,6 24,18 36,6 46,20 58,28"
  },
  "double_bottom": {
   "label": "Double Bottom",
   "bias": "bullish",
   "desc": "Two similar lows separated by a rally. A break above the middle peak confirms the reversal.",
   "shape": "2,4 14,22 24,10 36,22 46,8 58,2"
  },
  "cup_handle": {
   "label": "Cup & Handle",
   "bias": "bullish",
   "desc": "O'Neil's rounded base followed by a short, shallow handle on lighter volume; buy the break of the rim.",
   "shape": "2,6 8,16 16,24 28,26 40,20 48,8 52,12 58,4"
  },
  "ascending_triangle": {
   "label": "Ascending Triangle",
   "bias": "bullish",
   "desc": "Flat resistance with rising lows - buyers are getting more aggressive into a breakout.",
   "shape": "2,24 14,6 22,20 32,6 40,16 50,6 58,2"
  },
  "descending_triangle": {
   "label": "Descending Triangle",
   "bias": "bearish",
   "desc": "Flat support with falling highs - sellers press until support gives way.",
   "shape": "2,4 14,22 22,8 32,22 40,12 50,22 58,28"
  },
  "bull_flag": {
   "label": "Bull Flag",
   "bias": "bullish",
   "desc": "A sharp rally (the pole) followed by a tight, slightly down-sloping pause; continuation on the break of the flag.",
   "shape": "2,28 14,4 22,8 30,6 38,12 46,10 58,2"
  },
  "bear_flag": {
   "label": "Bear Flag",
   "bias": "bearish",
   "desc": "A sharp drop followed by a weak, slightly up-sloping bounce; continuation lower on the break of the flag.",
   "shape": "2,2 14,26 22,22 30,24 38,18 46,20 58,28"
  },
  "symmetrical_triangle": {
   "label": "Symmetrical Triangle",
   "bias": "neutral",
   "desc": "Converging highs and lows. Direction is decided by the breakout side.",
   "shape": "2,4 12,24 22,8 32,20 42,12 50,16 58,10"
  },
  "rising_wedge": {
   "label": "Rising Wedge",
   "bias": "bearish",
   "desc": "Both trendlines rise but converge - momentum fades, usually resolving down.",
   "shape": "2,26 14,16 22,20 34,10 42,13 52,6 58,10"
  },
  "falling_wedge": {
   "label": "Falling Wedge",
   "bias": "bullish",
   "desc": "Both trendlines fall but converge - selling pressure fades, usually resolving up.",
   "shape": "2,4 14,14 22,10 34,20 42,17 52,24 58,20"
  },
  "flat_base": {
   "label": "Flat Base / Darvas Box",
   "bias": "bullish",
   "desc": "A tight sideways box (Darvas-style) after an advance; breakout above the box top.",
   "shape": "2,26 10,8 18,10 28,8 38,10 46,9 58,2"
  },
  "high_breakout": {
   "label": "52-Week High Breakout",
   "bias": "bullish",
   "desc": "Price clearing its 52-week high on expanding volume - strength begets strength.",
   "shape": "2,24 14,14 24,18 34,10 44,12 52,8 58,2"
  },
  "trend_pullback": {
   "label": "Trend Pullback",
   "bias": "bullish",
   "desc": "A healthy dip to the 21/50 EMA inside an established uptrend, with RSI reset.",
   "shape": "2,26 16,14 26,20 34,10 44,18 52,6 58,2"
  }
 }
};
