/* The one behaviour every mice page shares: which theme it is wearing.
 * =====================================================================
 *
 * Served at /mice.js by the hub, and compiled into the board's flash by
 * firmware/tools/gen_tables.py, exactly like mice.css - so the hub, the module
 * website, Nong Studio and the help page all get the same code from one file,
 * whether the page came over WiFi or through a cable.
 *
 * WHY THE LIST IS NOT IN HERE
 * ---------------------------
 * The themes are DISCOVERED by reading the stylesheet at runtime, not listed.
 * Adding a theme is then one block in shared/web/themes.css and nothing else -
 * which is what was asked for on 2026-08-19, and the same promise the module,
 * command and servo registries already keep. A list in this file would be a
 * second place to update, and second places do not get updated.
 */
(function () {
  var KEY = "mice_theme";

  function themes() {
    // Every `:root[data-theme="x"]` rule in the loaded stylesheets, in the
    // order they are written. --theme-name and --theme-note come from inside
    // the block itself, so a theme names itself.
    var out = [], seen = {};
    var sheets = document.styleSheets;
    for (var i = 0; i < sheets.length; i++) {
      var rules;
      try { rules = sheets[i].cssRules; } catch (e) { continue; }  // cross-origin
      if (!rules) continue;
      for (var j = 0; j < rules.length; j++) {
        var sel = rules[j].selectorText || "";
        var m = sel.match(/\[data-theme=["']?([\w-]+)["']?\]/);
        if (!m || seen[m[1]]) continue;
        seen[m[1]] = 1;
        var name = (rules[j].style.getPropertyValue("--theme-name") || "").trim();
        var note = (rules[j].style.getPropertyValue("--theme-note") || "").trim();
        out.push({
          id: m[1],
          name: name.replace(/^["']|["']$/g, "") || m[1],
          note: note.replace(/^["']|["']$/g, "")
        });
      }
    }
    return out;
  }

  function get() {
    try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; }
  }

  function set(id) {
    // The attribute goes on <html>, not <body>: the page background is painted
    // from the root element, and a theme applied to body leaves the margins
    // and the overscroll area wearing the old one.
    if (id) document.documentElement.setAttribute("data-theme", id);
    else document.documentElement.removeAttribute("data-theme");
    try { localStorage.setItem(KEY, id || ""); } catch (e) { /* private mode */ }
    document.dispatchEvent(new CustomEvent("micetheme", { detail: { id: id } }));
  }

  // Applied as early as this file runs, before anything is painted. A theme
  // that arrives after the first paint is a flash of the wrong colours, which
  // is worse than not having themes.
  var saved = get();
  if (saved) document.documentElement.setAttribute("data-theme", saved);

  /* Build a picker wherever a page wants one. The page provides the element;
     this fills it, because the LIST is not the page's business. */
  function picker(el) {
    if (!el) return null;
    var all = themes();
    var now = get();
    el.innerHTML = "";
    var sel = document.createElement("select");
    sel.setAttribute("aria-label", "Colour theme");
    all.forEach(function (t) {
      var o = document.createElement("option");
      o.value = t.id;
      o.textContent = t.name;
      // The DEFAULT is the first block in the file, not a name written here.
      // Naming it meant renaming the default theme silently preselected
      // nothing - which is the one thing this file promised could not happen.
      if (t.id === now || (!now && t === all[0])) o.selected = true;
      sel.appendChild(o);
    });
    var note = document.createElement("span");
    note.className = "mini";
    function say() {
      var t = all.filter(function (x) { return x.id === sel.value; })[0];
      note.textContent = t && t.note ? t.note : "";
    }
    sel.onchange = function () { set(sel.value); say(); };
    el.appendChild(sel);
    el.appendChild(note);
    say();
    return sel;
  }

  window.miceTheme = { list: themes, get: get, set: set, picker: picker };
})();
