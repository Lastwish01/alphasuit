/* Shared helpers + site header/footer. Everything on the site is plain HTML/CSS/JS - no server needed. */
window.AS = (function () {
  const BRAND = "Alphasuit";
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // safe rich text: escape first, then add links, **bold** and line breaks
  const rich = t => esc(t)
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="nofollow noopener noreferrer">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
  const fmtPrice = v => v == null ? "—" : (v >= 1000 ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : v >= 1 ? v.toFixed(2) : Number(v).toPrecision(4));
  const dtf = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
  const fmtDT = iso => { if (!iso) return "—"; const d = new Date(iso); return isNaN(d) ? esc(iso) : dtf.format(d) + " IST"; };
  const fetchJSON = async url => {
    const r = await fetch(url + "?v=" + Math.floor(Date.now() / 300000), { cache: "no-store" });
    if (!r.ok) throw new Error(url + " → " + r.status);
    return r.json();
  };
  const patTile = (key, withDesc) => {
    const P = window.PATTERNS && window.PATTERNS.info[key]; if (!P) return "";
    const cls = P.bias === "bullish" ? "bull" : P.bias === "bearish" ? "bear" : "neut";
    const chip = P.bias === "bullish" ? "up" : P.bias === "bearish" ? "down" : "gold";
    return '<div class="card pat ' + cls + '"><svg viewBox="0 0 60 30" preserveAspectRatio="none"><polyline points="' + P.shape + '"/></svg><b>' + esc(P.label) +
      '</b><span class="chip ' + chip + '" style="align-self:flex-start">' + P.bias + "</span>" + (withDesc ? '<p style="margin:0;font-size:.86rem">' + esc(P.desc) + "</p>" : "") + "</div>";
  };
  const demoBanner = d => {
    const el = document.getElementById("demo-banner");
    if (el && d && d.demo) el.innerHTML = '<div class="demo-banner">⚠ Sample data shown — these are made-up stocks. Real results appear after your first scan runs.</div>';
  };
  const postCard = p => {
    const lv = (p.entry || p.stop || p.target)
      ? '<div class="plan-levels"><div><span>Entry</span><b>' + esc(p.entry || "—") + '</b></div><div><span>Stop-loss</span><b class="down">' + esc(p.stop || "—") +
        '</b></div><div><span>Target</span><b class="up">' + esc(p.target || "—") + "</b></div></div>" : "";
    const dir = p.kind === "plan" && p.direction ? '<span class="chip ' + (p.direction === "bullish" ? "up" : "down") + '">' + esc(p.direction) + "</span>" : "";
    return '<article class="card post' + (p.pinned ? " pin" : "") + '"><div class="meta"><span class="chip ' + (p.kind === "plan" ? "gold" : "info") + '">' +
      (p.kind === "plan" ? "Trade plan" : "Market update") + "</span>" + (p.symbol ? '<span class="chip">' + esc(p.symbol) + "</span>" : "") + dir +
      (p.pinned ? '<span class="chip gold">📌 pinned</span>' : "") + "<span>" + esc(p.date || "") + "</span></div><h3>" + esc(p.title) + "</h3>" + lv +
      (p.body ? '<div class="body">' + rich(p.body) + "</div>" : "") +
      (p.kind === "plan" ? '<p class="dim" style="font-size:.76rem;margin:12px 0 0">Shared for education only — not advice or a recommendation. Do your own analysis.</p>' : "") + "</article>";
  };

  // ---- header & footer
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const links = [["stocks.html", "Stocks"], ["crypto.html", "Crypto"], ["patterns.html", "Patterns"], ["feed.html", "Feed"]];
  const hdr = document.getElementById("site-header");
  if (hdr) hdr.outerHTML = '<header class="nav"><div class="wrap"><a class="logo" href="index.html"><i>α</i>' + BRAND + '</a><nav class="nav-links" id="navlinks">' +
    links.map(l => '<a href="' + l[0] + '"' + (page === l[0] || (page === "setup.html" && l[0] === "stocks.html") ? ' class="on"' : "") + ">" + l[1] + "</a>").join("") +
    '</nav><div class="nav-right"><a class="btn gold sm" href="stocks.html">Open scanner</a><button class="menu-btn" aria-label="Menu" onclick="document.getElementById(\'navlinks\').classList.toggle(\'open\')">☰</button></div></div></header>';
  const ftr = document.getElementById("site-footer");
  if (ftr) ftr.outerHTML = '<footer><div class="wrap"><div class="cols"><div><a class="logo" href="index.html" style="padding:0"><i>α</i>' + BRAND +
    '</a><p style="margin-top:12px;max-width:320px;font-size:.9rem">Daily chart-pattern scanning for Indian stocks (NSE + BSE) and crypto. Free to use.</p></div>' +
    '<div><b>Scanners</b><a href="stocks.html">Stock scanner</a><a href="crypto.html">Crypto scanner</a><a href="patterns.html">Pattern library</a></div>' +
    '<div><b>Updates</b><a href="feed.html">Market feed</a></div>' +
    '<div><b>Legal</b><a href="legal.html#terms">Terms</a><a href="legal.html#privacy">Privacy</a><a href="legal.html#disclaimer">Educational &amp; risk disclaimer</a></div></div>' +
    '<div class="disc edu"><b style="color:var(--gold)">For educational purposes only.</b> ' + BRAND + ' is an educational and informational tool that shows how technical chart patterns appear in publicly available market data. It is not a SEBI-registered investment adviser or research analyst. Nothing here is a recommendation or an offer to buy or sell any security or crypto asset. You alone are responsible for your trading decisions and their results.</div>' +
    '<div class="disc" style="margin-top:14px;padding-top:14px">© ' + new Date().getFullYear() + " " + BRAND + '. Pattern detection is probabilistic; past setups do not guarantee future results. Trading involves substantial risk of loss. Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noopener" style="display:inline;color:var(--muted);text-decoration:underline">TradingView Lightweight Charts™</a>.</div></div></footer>';
  return { esc, rich, fmtPrice, fmtDT, fetchJSON, patTile, demoBanner, postCard };
})();
