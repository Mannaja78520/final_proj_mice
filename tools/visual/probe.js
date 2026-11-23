// What a person notices at a glance, as numbers. One function, shared by the screenshot tool
// (tools/visual/shoot.js) and the QC check (check_visual_language.py), so they cannot disagree.
// latin = plain English words still showing (only meaningful in zh/ja).
// visualProbe(doc) -> {thai: [visible Thai texts], overflowX, stuck: [dialogs pinned at the top-left]}
function visualProbe(doc) {
  var win = doc.defaultView, r = { thai: [], overflowX: doc.documentElement.scrollWidth > win.innerWidth + 2, stuck: [], latin: [] };
  var w = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT), n;
  while ((n = w.nextNode())) {
    var t = n.nodeValue.trim(), e = n.parentElement;
    if (!t || !e || /^(SCRIPT|STYLE|OPTION|TEXTAREA)$/.test(e.tagName)) continue;
    if (/^[A-Za-z][A-Za-z ,.'()\/-]{2,}$/.test(t) && win.getComputedStyle(e).display !== "none" && e.getClientRects().length && !e.closest("[data-user-text],code,pre,.tech,.adv")) r.latin.push(t.slice(0, 160));
    if (/[฀-๿]/.test(t)) {
      var cs = win.getComputedStyle(e);
      if (cs.visibility !== "hidden" && cs.display !== "none" && e.getClientRects().length && !e.closest("[data-user-text]")) r.thai.push(t.slice(0, 60));
    }
  }
  var sel = "dialog[open],[role=dialog],.modal,.popup,.popover,.sheet,[class*=dialog],[class*=popup]";
  var list = doc.querySelectorAll(sel);
  for (var i = 0; i < list.length; i++) {
    var d = list[i], b = d.getBoundingClientRect(), c2 = win.getComputedStyle(d);
    if (c2.display === "none" || c2.visibility === "hidden" || !b.width) continue;
    if (b.left < 4 && b.top < 4 && (c2.position === "fixed" || c2.position === "absolute")) r.stuck.push((d.className || d.tagName) + "@" + Math.round(b.left) + "," + Math.round(b.top));
  }
  return r;
}
