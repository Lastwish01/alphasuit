(async function () {
  const el = document.getElementById("feed"); if (!el) return;
  const limit = +(el.dataset.limit || 15), compact = el.dataset.compact === "1";
  let kind = "", shown = limit, posts = [];
  const more = document.getElementById("more");
  const draw = () => {
    const rows = posts.filter(p => !kind || p.kind === kind);
    el.innerHTML = rows.slice(0, shown).map(AS.postCard).join("") || '<div class="card empty">No posts yet.</div>';
    if (more) more.style.display = rows.length > shown ? "" : "none";
  };
  try {
    const d = await AS.fetchJSON("data/feed.json");
    posts = (Array.isArray(d) ? d : d.posts || []).filter(p => p && p.title && p.published !== false);
    posts.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0) || String(b.date || "").localeCompare(String(a.date || "")));
    if (compact && !posts.length) { const s = document.getElementById("feed-section"); if (s) s.style.display = "none"; }
    draw();
  } catch (e) { if (compact) { const s = document.getElementById("feed-section"); if (s) s.style.display = "none"; } else el.innerHTML = '<div class="card empty">Could not load the feed.</div>'; }
  const tabs = document.getElementById("feedTabs");
  if (tabs) tabs.onclick = e => { const a = e.target.closest("a"); if (!a) return; e.preventDefault(); kind = a.dataset.k; shown = limit; tabs.querySelectorAll("a").forEach(x => x.classList.toggle("on", x === a)); draw(); };
  if (more) more.onclick = () => { shown += limit; draw(); };
})();
