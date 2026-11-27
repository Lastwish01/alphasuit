document.getElementById("coreT").innerHTML = window.PATTERNS.core.map(k => AS.patTile(k, true)).join("");
document.getElementById("extraT").innerHTML = window.PATTERNS.extra.map(k => AS.patTile(k, true)).join("");
