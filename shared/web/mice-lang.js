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
  var ATTRS = ["placeholder", "title", "aria-label", "alt"];   // alt: drawn icons and QR codes (2026-11-23)
  var SKIP = {SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, PRE: 1};
  var dict = null;
  var loaded = null;        // the language this page was translated into

  var fallback = DEFAULT;   // the hub's own default (index.json), until a person picks
  function current() {
    try { return localStorage.getItem(KEY) || fallback; } catch (e) { return fallback; }
  }
  function lookup(text) {
    var t = text.replace(/\s+/g, " ").trim();
    if (!t || !dict || !Object.prototype.hasOwnProperty.call(dict, t)) return null;
    if (!dict[t]) return null;      // an empty entry = not translated yet: keep the page's own text
    // A text that translates to itself (e.g. "Nong Studio") must not be written back: the write is
    // itself a mutation, so the observer in watch() would see it again, forever (zh/ja hub page froze
    // with hubTab=tools, found 2026-11-22).
    if (dict[t] === t) return null;
    return {from: t, to: dict[t]};
  }
  function translatedAttribute(value) {
    if (!value) return null;
    var exact = lookup(value);
    var translated = exact ? exact.to : pattern(value);
    return translated && translated !== value ? translated : null;
  }
  function node(n) {
    if (n.nodeType === 3) {
      if (n.parentNode && SKIP[n.parentNode.nodeName]) return;
      var hit = lookup(n.nodeValue);
      if (hit) n.nodeValue = n.nodeValue.replace(/\S[\s\S]*\S|\S/, hit.to);
      return;
    }
    if (n.nodeType !== 1 || n.nodeName === "SCRIPT" || n.nodeName === "STYLE") return;
    for (var i = 0; i < ATTRS.length; i++) {
      var value = translatedAttribute(n.getAttribute(ATTRS[i]));
      if (value) n.setAttribute(ATTRS[i], value);
    }
    if (SKIP[n.nodeName]) return;     // code and text boxes keep their text, but their placeholder/title above are translated (2026-11-23)
    for (var c = n.firstChild; c; c = c.nextSibling) node(c);
  }
  function pageTitle() {                         // the browser tab's own title (2026-11-23)
    var h = lookup(document.title || "");
    if (h) document.title = h.to;
  }
  function watch() {
    if (!window.MutationObserver) return;
    new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var m = list[i];
        if (m.type === "characterData") node(m.target);
        else if (m.type === "attributes") {      // a title / label set after the first pass (tool tiles, dialogs)
          var value = translatedAttribute(m.target.getAttribute(m.attributeName));
          if (value) m.target.setAttribute(m.attributeName, value);
        }
        else for (var j = 0; j < m.addedNodes.length; j++) node(m.addedNodes[j]);
      }
    }).observe(document.documentElement, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
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
    var corner = document.querySelector("header.topbar .topbar-end");
    var host = corner || document.querySelector(".topbar-adv, header.topbar");
    if (!host) return;
    var sel = document.createElement("select");
    sel.id = "miceLang";
    sel.className = "mini";
    // Natural width: inside a flex or grid header a bare select stretched across
    // the screen (Chrome 75 on the TV VM, 2026-11-21).
    sel.style.cssText = "width:auto;max-width:11em;flex:0 0 auto;align-self:center;border:0;background:transparent;" +
      "font-weight:600;color:inherit;min-height:0;padding:2px 0";
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
    // A globe beside the language's own name, in a bordered pill: the sign everybody knows for
    // "language" (user 2026-11-22: a bare drop-down was not recognised as the language switch).
    // Inline SVG, not an emoji: the TV browser has no emoji font for it.
    var pill = document.createElement("label");
    pill.className = "lang-pick";
    pill.title = "Language";
    pill.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9.5"/>' +
      '<path d="M2.5 12h19M12 2.5c3 3 3 16 0 19M12 2.5c-3 3-3 16 0 19"/></svg>';
    pill.appendChild(sel);
    if (corner) corner.insertBefore(pill, corner.firstChild);     // top-right, before the technical switch
    else host.parentNode.insertBefore(pill, host.nextSibling);
  }
  function applyPack(code) {
    node(document.body);
    document.documentElement.lang = code;
    pageTitle();
    watch();
  }
  function start() {
    get("/lang/index.json", function (idx) {
      var langs = idx && idx.languages;
      if (idx && idx.default) fallback = idx.default;
      picker(langs);
      var code = current();
      loaded = code;
      if (code === "off") return;     // QC: the page exactly as written
      // English is the source language, but a page may carry Thai text of its own
      // (lang/en.json, optional) that English must turn back into English.
      get("/lang/" + encodeURIComponent(code) + ".json", function (f) {
        if (!f || !f.strings) return;
        dict = f.strings;
        // Help is written in Thai: its texts come from a second file, only on the Help page.
        if (location.pathname.indexOf("/help") === 0) {
          return get("/lang/help/" + encodeURIComponent(code) + ".json", function (h) {
            if (h && h.strings) for (var k in h.strings) if (Object.prototype.hasOwnProperty.call(h.strings, k)) dict[k] = h.strings[k];
            applyPack(code);
          });
        }
        applyPack(code);
      });
    });
  }
  // One setting for every page of every app on this hub (same origin, same storage). A page that
  // is already open when the language is changed in another tab offers a reload instead of
  // reloading by itself: Studio may hold unsaved work.
  var NOTE = {
    th: ["เปลี่ยนภาษาแล้ว", "โหลดหน้านี้ใหม่"], en: ["Language changed", "Reload this page"],
    zh: ["语言已更改", "重新加载此页面"], ja: ["言語が変更されました", "このページを再読み込み"]
  };
  function changedElsewhere(code) {
    if (document.getElementById("miceLangNote") || !document.body) return;
    var n = NOTE[code] || NOTE.en, d = document.createElement("div");
    d.id = "miceLangNote";
    d.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:99999;background:#222;color:#fff;" +
      "padding:8px 12px;border-radius:8px;font:14px sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.4)";
    d.appendChild(document.createTextNode(n[0] + " "));
    var b = document.createElement("button");
    b.textContent = n[1];
    b.onclick = function () { location.reload(); };
    d.appendChild(b);
    document.body.appendChild(d);
  }
  window.addEventListener("storage", function (e) {
    if (e.key === KEY && e.newValue && e.newValue !== loaded) changedElsewhere(e.newValue);
  });
  // A link to another program (a partner app on its own address) carries the language, so an app
  // that reads ?lang= can follow the hub. Harmless to one that does not.
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || current() === "off") return;
    try {
      var u = new URL(a.href, location.href);
      if ((u.protocol === "http:" || u.protocol === "https:") && u.origin !== location.origin &&
          !u.searchParams.get("lang")) {
        u.searchParams.set("lang", current());
        a.href = u.href;
      }
    } catch (err) { /* a link the browser cannot parse is left as it is */ }
  }, true);
  // Browser dialogs (confirm / alert / prompt) are not in the page, so the observer never sees
  // them: Studio's "Replace it?" question stayed Thai or English whatever language was picked
  // (case review 2026-11-23). Translate the whole text, else line by line, keeping the line breaks.
  // An entry whose key holds {} matches any text there ("Delete {}?"): the pieces come back in the
  // translation's own {} slots, in order, so a dialog that names a file still translates.
  var holes = null;
  function pattern(line) {
    if (!holes) {
      holes = [];
      for (var k in dict) {
        if (Object.prototype.hasOwnProperty.call(dict, k) && dict[k] && k.indexOf("{}") >= 0) {
          var re = new RegExp("^" + k.split("{}").map(function (x) { return x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("(.+?)") + "$");
          holes.push([re, dict[k]]);
        }
      }
    }
    var t = line.replace(/\s+/g, " ").trim();
    for (var i = 0; i < holes.length; i++) {
      var m = holes[i][0].exec(t);
      if (m) { var n = 0; return holes[i][1].replace(/\{\}/g, function () { return m[++n] || ""; }); }
    }
    return null;
  }
  function say(text) {
    if (typeof text !== "string" || !dict) return text;
    var whole = lookup(text);
    if (whole) return whole.to;
    return text.split("\n").map(function (ln) {
      var h = lookup(ln);
      return h ? h.to : (pattern(ln) || ln);
    }).join("\n");
  }
  ["confirm", "alert", "prompt"].forEach(function (name) {
    var orig = window[name];
    if (typeof orig !== "function") return;
    window[name] = function (msg) {
      var args = Array.prototype.slice.call(arguments);
      args[0] = say(msg);
      return orig.apply(window, args);
    };
  });
  window.MiceLang = {current: current, source: SOURCE, say: say};
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
