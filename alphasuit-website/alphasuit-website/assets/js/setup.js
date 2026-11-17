(async function () {
  const $ = s => document.querySelector(s), esc = AS.esc;
  const q = new URLSearchParams(location.search);
  const c = q.get("c") || "", p = q.get("p") || "", m = q.get("m") === "crypto" ? "crypto" : "stocks";
  const msg = $("#chartmsg");
  try {
    if (!/^[A-Za-z0-9_.-]+$/.test(c) || !/^[a-z_]+$/.test(p)) throw new Error("bad link");
    const [chart, list] = await Promise.all([AS.fetchJSON("data/charts/" + c + ".json"), AS.fetchJSON("data/" + m + ".json")]);
    AS.demoBanner(list);
    const r = (list.results || []).find(x => x.chart === c && x.pattern === p) || {};
    $("#sym").textContent = chart.symbol; $("#symsub").textContent = (chart.name || "") + " · " + chart.exchange + " · " + chart.timeframe;
    document.title = chart.symbol + " · " + (r.label || "pattern") + " — Alphasuit";
    $("#back").href = m + ".html";
    const dc = r.direction === "bullish" ? "up" : r.direction === "bearish" ? "down" : "";
    $("#chips").innerHTML = '<span class="chip gold">' + esc(r.label || p) + '</span><span class="chip ' + dc + '">' + esc(r.direction || "") + '</span><span class="chip info">' +
      (r.status === "breakout" ? (r.direction === "bearish" ? "breakdown" : "breakout") : "forming") + '</span><span class="chip">score ' + (r.score || "—") + "</span>";
    if (r.entry) $("#levels").innerHTML = '<div class="levels"><div><span>Entry</span><b>' + AS.fmtPrice(r.entry) + '</b></div><div><span>Stop-loss</span><b class="down">' + AS.fmtPrice(r.stop) +
      '</b></div><div><span>Target</span><b class="up">' + AS.fmtPrice(r.target) + '</b></div><div><span>Risk : Reward</span><b>' + (r.rr ? "1 : " + r.rr : "—") + "</b></div></div>";
    if (r.notes) $("#notes").textContent = r.notes + ".";
    const intraday = chart.timeframe !== "1d";
    const ch = LightweightCharts.createChart($("#chart"), {
      layout: { background: { color: "#0f1420" }, textColor: "#8c97ad" }, grid: { vertLines: { color: "#161d2d" }, horzLines: { color: "#161d2d" } },
      rightPriceScale: { borderColor: "#1e2638" }, timeScale: { borderColor: "#1e2638", timeVisible: intraday }, crosshair: { mode: 0 }, autoSize: true });
    const cs = ch.addCandlestickSeries({ upColor: "#34d399", downColor: "#f87171", borderVisible: false, wickUpColor: "#34d399", wickDownColor: "#f87171" });
    cs.setData(chart.candles.map(k => ({ time: k[0], open: k[1], high: k[2], low: k[3], close: k[4] })));
    const vs = ch.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol" });
    ch.priceScale("vol").applyOptions({ scaleMargins: { top: .82, bottom: 0 } });
    vs.setData(chart.candles.map(k => ({ time: k[0], value: k[5], color: k[4] >= k[1] ? "rgba(52,211,153,.35)" : "rgba(248,113,113,.35)" })));
    if (r.entry) { [["entry", "#e8c46a", "Entry"], ["stop", "#f87171", "Stop"], ["target", "#34d399", "Target"]].forEach(a => r[a[0]] && cs.createPriceLine({ price: r[a[0]], color: a[1], lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: a[2] })); }
    const times = new Set(chart.candles.map(k => k[0]));
    ((chart.lines || {})[p] || []).forEach(l => {
      if (l.t1 === l.t2 || !times.has(l.t1) || !times.has(l.t2)) return;
      const pts = [{ time: l.t1, value: l.p1 }, { time: l.t2, value: l.p2 }].sort((a, b) => a.time < b.time ? -1 : 1);
      ch.addLineSeries({ color: "#60a5fa", lineWidth: 2, priceLineVisible: false, lastValueVisible: false, title: l.label }).setData(pts);
    });
    ch.timeScale().fitContent();
    msg.textContent = "Chart from the latest nightly scan · blue lines mark the detected pattern structure.";
  } catch (e) { msg.textContent = "Chart not available (" + e.message + "). Go back to the scanner and pick the setup again."; }
})();
