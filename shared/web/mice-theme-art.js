/* Pictures that follow a theme PACK (hub pages only; not in a board's flash).
 * ========================================================================
 * A pack can swap any picture by name ("images": {"apps/tv": "tv.svg"}).
 * Dark/light pictures themselves are CSS (shared/web/img-dark.css, keyed on
 * <html data-mode="dark"> which mice.js sets from the theme's --theme-mode).
 */
(function () {
  "use strict";
  var IMG = /^(\/img\/)([A-Za-z0-9_\/-]+?)(\.dark)?\.(png|webp|svg)(\?.*)?$/;
  var swaps = {};          // "apps/tv" -> url, from the active pack
  var timer = 0;

  function path(img) {
    var raw = img.getAttribute("data-src0") || img.getAttribute("src") || "";
    try { raw = new URL(raw, location.href).pathname; } catch (e) { /* keep raw */ }
    return IMG.exec(raw);
  }

  function setSrc(img, url, base) {
    if (img.getAttribute("src") === url) return;
    if (!img.hasAttribute("data-src0")) img.setAttribute("data-src0", base);
    img.setAttribute("src", url);
  }

  function paint(img) {
    var m = path(img);
    if (!m) return;
    var base = m[1] + m[2] + "." + m[4], key = m[2];
    if (swaps[key]) return setSrc(img, swaps[key], base);
    // Dark pictures: shared/web/img-dark.css swaps them for data-mode="dark" (any dark theme).
    // Only when a pack stops naming this picture do we go back to the original.
    if (img.hasAttribute("data-src0")) img.setAttribute("src", img.getAttribute("data-src0"));
  }

  function all() {
    var list = document.querySelectorAll("img");
    for (var i = 0; i < list.length; i++) paint(list[i]);
  }

  function load() {
    var id = document.documentElement.getAttribute("data-theme") || "";
    if (!id) { swaps = {}; return all(); }
    fetch("/api/themes/images?id=" + encodeURIComponent(id))
      .then(function (r) { return r.json(); })
      .then(function (d) { swaps = (d && d.images) || {}; all(); })
      .catch(function () { swaps = {}; all(); });
  }

  function soon() { clearTimeout(timer); timer = setTimeout(all, 60); }

  document.addEventListener("micemode", all);
  document.addEventListener("micetheme", load);
  if (window.MutationObserver) {
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++)
        if (muts[i].addedNodes.length) return soon();
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
