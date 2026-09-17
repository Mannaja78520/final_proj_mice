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

/* The technical-detail switch: one behaviour, every page.
 *
 * .tech in mice.css hides addresses, ids and ports until somebody asks;
 * body.adv is the asking. The choice lives under the localStorage key
 * hub_adv - the key hub.html chose first, so one preference follows a
 * person across every page. A page joins by including this file and, when
 * it wants the control, a checkbox with id advOn wired to
 * onchange="miceAdv.set(this.checked)".
 */
(function () {
  var KEY = "hub_adv";

  function on() {
    try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; }
  }

  function apply(v) {
    if (!document.body) return;
    document.body.classList.toggle("adv", v);
    var boxes = document.querySelectorAll("#advOn");
    for (var i = 0; i < boxes.length; i++) boxes[i].checked = v;
  }

  function set(v) {
    v = !!v;
    try { localStorage.setItem(KEY, v ? "1" : "0"); } catch (e) {}
    apply(v);
  }

  if (document.body) apply(on());
  else document.addEventListener("DOMContentLoaded", function () { apply(on()); });

  window.miceAdv = { on: on, set: set };
})();

/* Log in from ANY page, not only the hub's own.
 *
 * Asked 2026-09-09, from the Voice app: *where to login in this page, make can
 * login in the page not only in the hub and sync each other*. The page said
 * "log in before doing that" and offered no way to do it - the only login
 * control in the product was the card on the hub page.
 *
 * The session was already shared: it is one cookie on one origin, so logging
 * in anywhere logs you in everywhere. What was missing is the control, and one
 * control is what this is - every page mounts the same component rather than
 * growing a login of its own.
 *
 *   <div id="loginHere"></div>          somewhere sensible on the page
 *   miceLogin.mount(document.getElementById("loginHere"));
 *   miceLogin.required();               when an action came back refused
 *
 * A page that only READS needs none of this: reading is open on purpose.
 */
(function () {
  var mounts = [];
  var who = { authed: false, users: [] };

  function say(el, msg) {
    var s = el.querySelector(".mlStat");
    if (s) s.textContent = msg || "";
  }

  function paint() {
    for (var i = 0; i < mounts.length; i++) {
      var el = mounts[i];
      var inBox = el.querySelector(".mlIn");
      var outBox = el.querySelector(".mlOut");
      if (!inBox || !outBox) continue;
      inBox.hidden = who.authed;
      outBox.hidden = !who.authed;
      // Everything else on the page that waits on a session hears it from
      // here, so there is ONE place that knows whether somebody is logged in.
      try {
        document.dispatchEvent(new CustomEvent("mice-auth",
                                               { detail: { authed: who.authed } }));
      } catch (e) { /* an old browser: the gate simply stays as it is */ }
      var w = el.querySelector(".mlWho");
      if (w) w.textContent = who.user || (who.users && who.users[0]) || "";
      // STILL ON THE SHIPPED PASSWORD (user 2026-09-17): say so until changed.
      var warn = el.querySelector(".mlWarn");
      if (warn) warn.hidden = !(who.authed && who.mustChange);
    }
  }

  function refresh() {
    return fetch("/api/whoami").then(function (r) { return r.json(); })
      .then(function (j) {
        who.authed = !!j.authed;
        who.users = j.users || [];
        who.user = j.user || who.user;
        who.role = j.role || "";
        who.mustChange = !!j.mustChange;
        paint();
        return who.authed;
      })
      .catch(function () {
        // The hub is not answering. Say nothing rather than claiming logged
        // out: a page that logs you out on a hiccup is a page you stop
        // trusting.
        return who.authed;
      });
  }

  function login(el) {
    var user = (el.querySelector(".mlUser") || {}).value || "";
    var pass = (el.querySelector(".mlPass") || {}).value || "";
    if (!pass) { say(el, "type the hub password, then press Log in"); return; }
    say(el, "checking…");
    fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: user, password: pass })
    }).then(function (r) { return r.json().then(function (j) { return [r, j]; }); })
      .then(function (pair) {
        var r = pair[0], j = pair[1];
        var p = el.querySelector(".mlPass");
        if (p) p.value = "";
        if (r.ok && j.ok) {
          who.authed = true;
          who.user = user;
          say(el, "");
          refresh();                  // role and the default-password flag
          // Every page and every tab shares the cookie, so tell them all.
          document.dispatchEvent(new CustomEvent("mice-login", { detail: who }));
          return;
        }
        say(el, j.locked_for > 0
          ? ("too many tries - wait " + j.locked_for + " seconds")
          : (j.error || "that password was not right"));
      })
      .catch(function () {
        say(el, "the hub is not answering. Check it is still running.");
      });
  }

  // Your own account. The hub decides what is allowed and says why not.
  function account(el, path, body, done) {
    say(el, "saving…");
    return fetch(path, { method: "POST", body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        say(el, j.ok ? done : (j.error || "not changed"));
        if (j.ok) {
          ["mlOld", "mlNew", "mlNewName"].forEach(function (c) {
            var i = el.querySelector("." + c); if (i) i.value = ""; });
          refresh();
        }
        return !!j.ok;
      })
      .catch(function () { say(el, "the hub is not answering"); return false; });
  }

  function logout(el) {
    fetch("/api/logout", { method: "POST" })
      .then(function () { who.authed = false; paint();
        document.dispatchEvent(new CustomEvent("mice-login", { detail: who })); })
      .catch(function () { say(el, "logged out here, but the hub did not confirm it"); });
  }

  function mount(el) {
    if (!el) return;
    el.classList.add("mlogin");
    el.innerHTML =
      '<div class="mlIn row" hidden>' +
      '  <span class="lbl">Log in</span>' +
      '  <input class="mlUser" placeholder="username" autocomplete="off">' +
      '  <input class="mlPass" type="password" placeholder="password" autocomplete="new-password">' +
      '  <button class="primary mlGo" type="button">Log in</button>' +
      '</div>' +
      '<div class="mlOut row" hidden>' +
      '  <span class="lbl">Logged in</span><b class="mlWho"></b>' +
      '  <button class="mlOff" type="button">Log out</button>' +
      '  <button class="mlMine" type="button">My account</button>' +
      '</div>' +
      '<div class="mlWarn warn" hidden>This account still uses the default password ' +
      '(admin123). Please change it: press My account.</div>' +
      '<div class="mlAcct row" hidden>' +
      '  <input class="mlOld" type="password" placeholder="current password" autocomplete="current-password">' +
      '  <input class="mlNew" type="password" placeholder="new password (8 or more)" autocomplete="new-password">' +
      '  <button class="primary mlSetPw" type="button">Change password</button>' +
      '  <input class="mlNewName" placeholder="new username" autocomplete="off">' +
      '  <button class="mlSetName" type="button">Change username</button>' +
      '</div>' +
      '<div class="statline mlStat" role="status" aria-live="polite"></div>';
    el.querySelector(".mlGo").onclick = function () { login(el); };
    el.querySelector(".mlOff").onclick = function () { logout(el); };
    el.querySelector(".mlMine").onclick = function () {
      var box = el.querySelector(".mlAcct"); box.hidden = !box.hidden;
    };
    el.querySelector(".mlSetPw").onclick = function () {
      account(el, "/api/users/password", {
        old: el.querySelector(".mlOld").value,
        password: el.querySelector(".mlNew").value }, "password changed");
    };
    el.querySelector(".mlSetName").onclick = function () {
      var name = el.querySelector(".mlNewName").value.trim();
      account(el, "/api/users/rename", { "new": name }, "username changed").then(function (ok) {
        if (ok) who.user = name;
      });
    };
    el.querySelector(".mlPass").onkeydown = function (e) {
      if (e.key === "Enter") login(el);
    };
    mounts.push(el);
    refresh();
  }

  /* An action came back refused. Show the control, put the person in the
   * password box, and hand back the sentence to print where they are looking.
   */
  function required(msg) {
    refresh();
    for (var i = 0; i < mounts.length; i++) {
      var p = mounts[i].querySelector(".mlPass");
      if (p && !who.authed) { p.focus(); break; }
    }
    return msg || "log in first - the box at the top of this page - then try again";
  }

  window.miceLogin = { mount: mount, refresh: refresh, required: required,
                       authed: function () { return who.authed; },
                       role: function () { return who.role || ""; } };
})();

/* miceGate - what a person can SEE and press before they sign in.
 *
 * Asked 2026-09-09: *make our app except the TOOL and module can use with out
 * login, other thing need to be login same as face reconize.* A tool has to
 * work at a venue with nobody logged in; everything else asks first.
 *
 * How a page uses it: put data-needs-login="flash" on the card. If that name
 * is listed in config/page_access.json, the card is replaced by a sign-in box
 * until somebody logs in, and comes back the moment they do. The list is data,
 * so the next card costs one line there and no code here.
 *
 * THIS IS NOT THE LOCK. hub_auth.GATED is, and it answers `401 log in first`
 * to every route that moves a robot, writes a file, replaces firmware or takes
 * a port. This only decides what is shown - so a card the file forgets is a
 * card a stranger can press and be refused by the hub, never a way in.
 *
 * A gated card is briefly visible while /api/whoami is still answering. That
 * is on purpose: shipping them hidden would leave them hidden for good if the
 * script ever failed, and a logged-in person unable to flash a board is worse
 * than a card that shows for a moment.
 */
(function () {
  var rule = null;                  // what /api/access said, read once per page

  function load() {
    if (rule) return Promise.resolve(rule);
    return fetch("/api/access").then(function (r) { return r.json(); })
      .then(function (j) { rule = j || {}; return rule; })
      .catch(function () {
        // The hub is not answering. Gate NOTHING rather than everything: this
        // decides what is shown, and hiding the whole page because one read
        // failed helps nobody. The hub still refuses the actions.
        rule = { ok: false, needLogin: [], words: {} };
        return rule;
      });
  }

  function boxFor(name, w, el) {
    var box = document.createElement("div");
    box.className = "card mg-gate";
    box.setAttribute("data-gate-for", name);
    // Stand exactly where the card stood. The hub shows and hides cards by
    // data-tab, so a box without it would appear on EVERY tab; and a card that
    // spanned the grid leaves a hole if its replacement does not.
    if (el.getAttribute("data-tab"))
      box.setAttribute("data-tab", el.getAttribute("data-tab"));
    if (el.getAttribute("style")) box.setAttribute("style", el.getAttribute("style"));
    var b = document.createElement("b");
    b.textContent = w.title || "Sign in to use this";
    var p = document.createElement("p");
    p.textContent = w.body ||
      "Tools and module pages work without signing in. Everything else asks first.";
    var go = document.createElement("button");
    go.type = "button";
    go.className = "primary";
    go.textContent = w.button || "Sign in";
    go.onclick = function () {
      if (window.miceLogin) window.miceLogin.required();
    };
    // textContent throughout: the words come out of a file a person edits, and
    // a file a person edits is not markup.
    box.appendChild(b); box.appendChild(p); box.appendChild(go);
    return box;
  }

  function boxOf(name) {
    var boxes = document.querySelectorAll("[data-gate-for]");
    for (var i = 0; i < boxes.length; i++)
      if (boxes[i].getAttribute("data-gate-for") === name) return boxes[i];
    return null;
  }

  function apply(authed) {
    var need = (rule && rule.needLogin) || [];
    var w = (rule && rule.words) || {};
    var all = document.querySelectorAll("[data-needs-login]");
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var name = el.getAttribute("data-needs-login");
      var gated = !authed && need.indexOf(name) >= 0;
      // ONE box per kind, however many cards carry that name. The lights page
      // has four of them; four identical explanations stacked up is not an
      // explanation, it is noise. It stands before the first of them.
      var box = boxOf(name);
      if (gated && !box) el.parentNode.insertBefore(boxFor(name, w, el), el);
      if (!gated && box) box.parentNode.removeChild(box);
      // A CLASS, never el.hidden. Cards hide themselves for their own reasons
      // - the pairing card is hidden until another PC appears - and writing
      // el.hidden here would REVEAL such a card the moment somebody logged in.
      // The class hides on top of that and gives the element's own state back
      // untouched when it is removed.
      if (el.classList) el.classList.toggle("mg-off", gated);
    }
  }

  document.addEventListener("mice-auth", function (e) {
    load().then(function () {
      apply(!!(e.detail && e.detail.authed));
    });
  });

  window.miceGate = {
    apply: function (authed) { return load().then(function () { apply(authed); }); },
    rule: function () { return rule; }
  };
})();
