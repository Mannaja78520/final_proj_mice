// WCAG AA text contrast of everything visible in a document. contrastAudit(doc) -> ["<ratio> <text> [<element>]"]
// for text below 4.5:1 (3:1 at 18px and up). Shared by qc/checks/check_theme_contrast.py.
function contrastAudit(doc) {
  var win = doc.defaultView;
  function parse(c) {
    var m = c.match(/rgba?\(([^)]+)\)/);
    if (m) { var p = m[1].split(",").map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; }
    var s = c.match(/color\(srgb ([^)]+)\)/);
    if (s) { var q = s[1].split(/[ \/]+/).map(Number); return {r: q[0] * 255, g: q[1] * 255, b: q[2] * 255, a: q.length > 3 ? q[3] : 1}; }
    return {r: 0, g: 0, b: 0, a: 0};
  }
  function lum(c) {
    function f(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }
  function bgOf(e) {
    var stack = [];
    for (var n = e; n; n = n.parentElement) stack.push(win.getComputedStyle(n).backgroundColor);
    var base = {r: 255, g: 255, b: 255};
    for (var i = stack.length - 1; i >= 0; i--) {
      var c = parse(stack[i]);
      if (c.a > 0) base = {r: base.r * (1 - c.a) + c.r * c.a, g: base.g * (1 - c.a) + c.g * c.a, b: base.b * (1 - c.a) + c.b * c.a};
    }
    return base;
  }
  var out = [], seen = {}, all = doc.querySelectorAll("button,a,label,span,p,h1,h2,h3,td,div,b,i,small");
  for (var k = 0; k < all.length; k++) {
    var e = all[k];
    if (e.children.length > 0 && !/^(BUTTON|A)$/.test(e.tagName)) continue;
    var t = (e.textContent || "").trim();
    if (!t || t.length > 60) continue;
    var cs = win.getComputedStyle(e);
    if (cs.visibility === "hidden" || cs.display === "none" || !e.getClientRects().length || +cs.opacity < 0.5 || e.disabled) continue;
    var fg = parse(cs.color), bg = bgOf(e);
    var mix = {r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a)};
    var a = lum(mix), b = lum(bg), r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (r < (parseFloat(cs.fontSize) >= 18 ? 3 : 4.5)) {
      var key = t.slice(0, 28);
      if (!seen[key]) { seen[key] = 1; out.push(r.toFixed(2) + " " + key + " [" + String(e.id || e.className || e.tagName).slice(0, 24) + "]"); }
    }
  }
  return out;
}
