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


/* ONE ANSWER TO -CAN I DRIVE THE ROBOT- , FOR ALL THREE SCREENS.
 * ==============================================================
 * The hub page, the board's own website and Nong Studio each used to decide
 * this for themselves and each said it differently: a coloured dot, a badge of
 * channel names, a status line. Three vocabularies for one question, and only
 * one of them ever said what to DO about it.
 *
 * So the states live here, in the file every screen already loads - served at
 * /mice.js by the hub and compiled into the board's flash, so it works with no
 * hub in sight.
 *
 * Every state carries what to do next, because that is the whole point: -not
 * connected- tells an operator nothing they did not already know. The wording
 * was written by Gemini Pro on 2026-08-20, kept short on purpose - it is read
 * by somebody standing next to a robot, not sitting down with a manual.
 *
 * The ORDER is the design. A port held by another program is reported before
 * -no robot found-, because the second is what it looks like and the first is
 * what it is; and a login is reported before staleness, because logging in is
 * what fixes it. Each state answers a different next action - that is the test
 * for whether a state deserves to exist at all.
 */
(function () {
  var STALE_MS = 3000;          // six missed pushes at the board's 500ms rate

  function read(f) {
    f = f || {};
    var age = (typeof f.ageMs === "number") ? f.ageMs : null;

    if (f.portBusy)
      return st("busy", "The cable is held by another program.",
                "Close it, or reach this board through the hub.");
    if (f.needLogin)
      return st("login", "Login required.", "Enter the hub password.");
    if (!f.cable && !f.wifi && !f.viaHub)
      return st("none", "No robot found.",
                "Plug in a cable, or put the board on the WiFi.");
    if (!f.everHeard)
      return st("waiting", "Waiting for the robot.",
                "Check that it has power and has finished starting.");
    if (age !== null && age >= (f.staleMs || STALE_MS))
      return st("stale", "No answer for " + secs(age) + ".",
                "What is on screen is the last thing it sent, not what " +
                "it is doing now.");
    if (f.cable)
      return st("cable", "Connected over the cable.", "", true);
    if (f.viaHub)
      return st("hub", "Connected through the hub.", "", true);
    return st("wifi", "Connected over WiFi.", "", true);
  }

  function st(state, says, next, ok) {
    return { state: state, says: says, next: next || "", ok: !!ok };
  }

  function secs(ms) {
    var s = Math.round(ms / 1000);
    if (s < 60) return s + " seconds";
    var m = Math.round(s / 60);
    return m + (m === 1 ? " minute" : " minutes");
  }

  window.miceLink = { read: read, STALE_MS: STALE_MS };
})();
