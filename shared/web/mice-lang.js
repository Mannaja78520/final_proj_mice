/* Language switch for every hub page (user 2026-11-21: Thai first, any language
   must work, the next one has to be easy to add).
   HOW A LANGUAGE IS ADDED: one file shared/web/lang/<code>.json
     {"name": "ไทย", "strings": {"<the English text on the page>": "<its translation>"}}
   Nothing else: the hub lists the folder (/lang/index.json) and this file builds
   the picker from it. A text with no entry stays English, so a half-done
   language never breaks a page. Plain ES2015 on purpose: Chrome 75 (Android TV).
   The pick is kept in this browser (localStorage "mice.lang"); Thai is the
   default; changing it reloads the page, which keeps this file simple. */
(function () {
  var KEY = "mice.lang", DEFAULT = "th", SOURCE = "en";
  var ATTRS = ["placeholder", "title", "aria-label"];
  var SKIP = {SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, PRE: 1};
  var dict = null;

  var fallback = DEFAULT;   // the hub's own default (index.json), until a person picks
  function current() {
    try { return localStorage.getItem(KEY) || fallback; } catch (e) { return fallback; }
  }
  function lookup(text) {
    var t = text.replace(/\s+/g, " ").trim();
    if (!t || !dict || !Object.prototype.hasOwnProperty.call(dict, t)) return null;
    return {from: t, to: dict[t]};
  }
  function node(n) {
    if (n.nodeType === 3) {
      if (n.parentNode && SKIP[n.parentNode.nodeName]) return;
      var hit = lookup(n.nodeValue);
      if (hit) n.nodeValue = n.nodeValue.replace(/\S[\s\S]*\S|\S/, hit.to);
      return;
    }
    if (n.nodeType !== 1 || SKIP[n.nodeName]) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var v = n.getAttribute(ATTRS[i]);
      var h = v && lookup(v);
      if (h) n.setAttribute(ATTRS[i], h.to);
    }
    for (var c = n.firstChild; c; c = c.nextSibling) node(c);
  }
  function watch() {
    if (!window.MutationObserver) return;
    new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var m = list[i];
        if (m.type === "characterData") node(m.target);
        else for (var j = 0; j < m.addedNodes.length; j++) node(m.addedNodes[j]);
      }
    }).observe(document.documentElement, {childList: true, subtree: true, characterData: true});
  }
  function get(url, done) {
    var x = new XMLHttpRequest();
    x.open("GET", url);
    x.onload = function () {
      var j = null;
      try { j = JSON.parse(x.responseText); } catch (e) { /* not a language file */ }
      done(x.status === 200 ? j : null);
    };
    x.onerror = function () { done(null); };
    x.send();
  }
  // The picker goes where the "Show technical details" switch is: every page has it.
  function picker(langs) {
    if (!langs || langs.length < 2 || document.getElementById("miceLang")) return;
    var host = document.querySelector(".topbar-adv, header.topbar");
    if (!host) return;
    var sel = document.createElement("select");
    sel.id = "miceLang";
    sel.className = "mini";
    sel.setAttribute("aria-label", "Language");
    sel.title = "Language";
    var cur = current();
    for (var i = 0; i < langs.length; i++) {
      var o = document.createElement("option");
      o.value = langs[i].code;
      o.textContent = langs[i].name;
      if (langs[i].code === cur) o.selected = true;
      sel.appendChild(o);
    }
    sel.onchange = function () {
      try { localStorage.setItem(KEY, sel.value); } catch (e) { /* private mode */ }
      location.reload();
    };
    host.parentNode.insertBefore(sel, host.nextSibling);
  }
  function start() {
    get("/lang/index.json", function (idx) {
      var langs = idx && idx.languages;
      if (idx && idx.default) fallback = idx.default;
      picker(langs);
      var code = current();
      if (code === SOURCE) return;
      get("/lang/" + encodeURIComponent(code) + ".json", function (f) {
        if (!f || !f.strings) return;
        dict = f.strings;
        node(document.body);
        watch();
      });
    });
  }
  window.MiceLang = {current: current, source: SOURCE};
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
