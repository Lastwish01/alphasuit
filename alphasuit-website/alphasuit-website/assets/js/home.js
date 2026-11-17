(async function () {
  const $ = s => document.querySelector(s);
  const [core, extra] = [window.PATTERNS.core, window.PATTERNS.extra];
  $("#coreTiles").innerHTML = core.map(k => AS.patTile(k)).join("");
  $("#extraTiles").innerHTML = extra.map(k => AS.patTile(k)).join("");
  try {
    const [s, c] = await Promise.all([AS.fetchJSON("data/stocks.json"), AS.fetchJSON("data/crypto.json")]);
    AS.demoBanner(s.demo ? s : c);
    $("#nStocks").textContent = s.count; $("#nScanned").textContent = (s.scanned || 0).toLocaleString("en-IN"); $("#nCrypto").textContent = c.count;
    $("#updatedLine").textContent = "Last update — Stocks: " + AS.fmtDT(s.updated) + " · Crypto: " + AS.fmtDT(c.updated);
  } catch (e) { $("#updatedLine").textContent = "The first scan is running — results appear here shortly."; }
})();
