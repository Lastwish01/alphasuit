(function () {
  const $ = s => document.querySelector(s), out = $("#out");
  const make = () => {
    const f = n => ($("#" + n).value || "").trim();
    const post = { id: Date.now(), date: new Date().toISOString().slice(0, 10), kind: f("kind"), title: f("title"), body: f("body") };
    if (f("symbol")) post.symbol = f("symbol").toUpperCase();
    if (post.kind === "plan") { if (f("direction")) post.direction = f("direction"); ["entry", "stop", "target"].forEach(k => f(k) && (post[k] = f(k))); }
    if ($("#pinned").checked) post.pinned = true;
    return post;
  };
  $("#make").onclick = () => {
    const p = make();
    if (!p.title) { out.value = "Please type a title first."; return; }
    out.value = JSON.stringify(p, null, 2) + ",";
  };
  $("#copy").onclick = async () => { try { await navigator.clipboard.writeText(out.value); $("#copy").textContent = "Copied ✓"; } catch (e) { out.select(); document.execCommand("copy"); } };
})();
