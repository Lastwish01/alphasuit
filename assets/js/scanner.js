(function () {
  const M = document.body.dataset.market, L = window.PATTERNS.info;
  const $ = s => document.querySelector(s), esc = AS.esc;
  let all = [], showLevels = false;
  const f = { q: "", dir: "", st: "", pat: "", extra: "", min: 0 };
  let sort = { k: "score", d: -1 };

  async function load() {
    try {
      const d = await AS.fetchJSON("data/" + M + ".json");
      all = d.results || []; showLevels = !!d.levels;
      AS.demoBanner(d);
      $("#updated").textContent = d.updated ? "Updated " + AS.fmtDT(d.updated) + " · " + d.scanned.toLocaleString("en-IN") + (M === "stocks" ? " stocks" : " pairs") + " scanned" : "Waiting for the first scan";
      setup(); render();
    } catch (e) { $("#rows").innerHTML = '<tr><td colspan="8" class="empty">Could not load results. Please refresh.</td></tr>'; }
  }

  function setup() {
    const counts = {}; all.forEach(r => counts[r.pattern] = (counts[r.pattern] || 0) + 1);
    const el = $("#patChips");
    el.innerHTML = '<button class="pill on" data-p="">All <b>' + all.length + "</b></button>" +
      Object.keys(counts).sort((a, b) => counts[b] - counts[a]).map(k => '<button class="pill" data-p="' + esc(k) + '">' + esc((L[k] || {}).label || k) + " <b>" + counts[k] + "</b></button>").join("");
    el.onclick = e => { const b = e.target.closest(".pill"); if (!b) return; f.pat = b.dataset.p; el.querySelectorAll(".pill").forEach(x => x.classList.toggle("on", x === b)); render(); };
    const opts = M === "stocks" ? [["", "NSE + BSE"], ["NSE", "NSE"], ["BSE", "BSE"]] : [["", "All timeframes"], ["1d", "Daily"], ["4h", "4-hour"]];
    $("#extraFilter").innerHTML = opts.map(o => '<option value="' + o[0] + '">' + o[1] + "</option>").join("");
    const head = [["symbol", "Symbol"], ["label", "Pattern"], ["direction", "Bias"], ["status", "Status"], ["score", "Score", 1], ["price", "Price", 1]];
    if (showLevels) head.push(["entry", "Entry", 1], ["stop", "Stop", 1], ["target", "Target", 1], ["rr", "R:R", 1]);
    head.push(["volume_ratio", "Vol ×", 1]);
    $("#thead").innerHTML = "<tr>" + head.map(h => '<th data-k="' + h[0] + '"' + (h[2] ? ' class="num"' : "") + ">" + h[1] + "</th>").join("") + "</tr>";
    document.querySelectorAll("#tbl th").forEach(th => th.onclick = () => {
      const k = th.dataset.k; sort = { k, d: sort.k === k ? -sort.d : (["symbol", "label", "direction", "status"].includes(k) ? 1 : -1) }; render();
    });
  }

  function visible() {
    const q = f.q.trim().toLowerCase();
    const rows = all.filter(r => (!f.pat || r.pattern === f.pat) && (!f.dir || r.direction === f.dir) && (!f.st || r.status === f.st) &&
      (!f.extra || (M === "stocks" ? r.exchange === f.extra : r.timeframe === f.extra)) && r.score >= f.min &&
      (!q || r.symbol.toLowerCase().includes(q) || (r.name || "").toLowerCase().includes(q)));
    const k = sort.k;
    rows.sort((a, b) => { const x = a[k], y = b[k]; if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * sort.d; });
    return rows;
  }

  function render() {
    const rows = visible(), cols = showLevels ? 11 : 7;
    $("#count").textContent = rows.length + " setup" + (rows.length === 1 ? "" : "s");
    if (!rows.length) { $("#rows").innerHTML = '<tr><td colspan="' + cols + '" class="empty">' + (all.length ? "No setups match these filters." : "No setups yet — the scanner runs automatically every night.") + "</td></tr>"; return; }
    $("#rows").innerHTML = rows.map(r => {
      const dc = r.direction === "bullish" ? "up" : r.direction === "bearish" ? "down" : "gold";
      const st = r.status === "breakout" ? (r.direction === "bearish" ? "breakdown" : "breakout") : "forming";
      const href = "setup.html?m=" + M + "&c=" + encodeURIComponent(r.chart) + "&p=" + encodeURIComponent(r.pattern);
      return '<tr class="row" data-href="' + href + '"><td class="sym"><b>' + esc(r.symbol) + "</b><small>" + esc(r.exchange) + (M === "crypto" ? " · " + esc(r.timeframe) : (r.name ? " · " + esc(r.name).slice(0, 24) : "")) + "</small></td>" +
        "<td>" + esc(r.label) + '</td><td><span class="chip ' + dc + '">' + esc(r.direction) + '</span></td><td><span class="chip ' + (r.status === "breakout" ? "info" : "") + '">' + st + "</span></td>" +
        '<td class="num"><span class="bar"><i style="width:' + r.score + '%"></i></span>' + r.score + '</td><td class="num">' + AS.fmtPrice(r.price) + "</td>" +
        (showLevels ? '<td class="num">' + AS.fmtPrice(r.entry) + '</td><td class="num">' + AS.fmtPrice(r.stop) + '</td><td class="num">' + AS.fmtPrice(r.target) + '</td><td class="num">' + (r.rr ? r.rr.toFixed(1) : "—") + "</td>" : "") +
        '<td class="num">' + (r.volume_ratio ? r.volume_ratio.toFixed(1) + "×" : "—") + "</td></tr>";
    }).join("");
  }

  $("#rows").addEventListener("click", e => { const tr = e.target.closest("tr.row"); if (tr) location.href = tr.dataset.href; });
  $("#q").oninput = e => { f.q = e.target.value; render(); };
  const seg = (id, key) => { const el = $(id); el.onclick = e => { const b = e.target.closest("button"); if (!b) return; f[key] = b.dataset.v; el.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); render(); }; };
  seg("#dirSeg", "dir"); seg("#stSeg", "st");
  $("#extraFilter").onchange = e => { f.extra = e.target.value; render(); };
  $("#minScore").onchange = e => { f.min = +e.target.value; render(); };
  load();
})();
