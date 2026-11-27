/* The hub's own-password dialogs: choose a password, keep a recovery code, use one.
 * =====================================================================================
 *
 * Served at /mice-password.js by the hub (the shared scripts route). NOT compiled
 * into a board's flash: a board has its own login, and this talks to the hub's
 * /api/recovery/* routes. mice-ui.js and miceLogin load it beside the login.
 *
 * Three things a person can meet (user 2026-11-27: plain words, skippable):
 *
 *   1. FIRST LOGIN on the shipped password: "Please choose your own password".
 *      Skippable with "Remind me later" (hidden for a day, per account, in this
 *      browser; the login box keeps its warning line either way).
 *   2. THE RECOVERY CODE, shown ONCE after a password is set. The hub keeps
 *      only a hash of it, so this is the only time it can be copied or printed.
 *   3. FORGOT PASSWORD on the login box: name + recovery code + new password.
 *
 * All text is plain English here; mice-lang.js translates it like the rest of
 * the page (entries in shared/web/lang/*.json). THIS FILE IS NOT THE LOCK: the
 * hub checks everything again (hub_auth.Auth, hub_recovery.Throttle).
 */
(function () {
  if (window.micePassword) return;
  var SNOOZE_MS = 24 * 3600 * 1000;
  var open = null;                     // the dialog on screen, if any

  function h(tag, props, kids) {
    var el = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "text") el.textContent = props[k];
      else if (k === "class") el.className = props[k];
      else if (k.slice(0, 2) === "on") el[k] = props[k];
      else el.setAttribute(k, props[k]);
    });
    (kids || []).forEach(function (c) { if (c) el.appendChild(c); });
    return el;
  }

  function post(path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
                         body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().catch(function () { return {}; })
        .then(function (j) { j.status = r.status; return j; }); })
      .catch(function () { return { ok: false, error: "the hub is not answering" }; });
  }

  function store(op, key, val) {                       // browser storage may be blocked
    try {
      if (op === "get") return window.localStorage.getItem(key);
      window.localStorage.setItem(key, val);
    } catch (e) { /* no snooze memory: the dialog simply asks again */ }
    return null;
  }

  function close() {
    if (open && open.parentNode) open.parentNode.removeChild(open);
    open = null;
  }

  // One box. `build(panel, say)` fills it; focus goes to the first field.
  function dialog(title, build, opts) {
    close();
    var say = h("div", { class: "statline", role: "status", "aria-live": "polite" });
    var panel = h("div", { class: "report-panel", role: "dialog", "aria-modal": "true",
                           "aria-label": title }, [h("h2", { text: title })]);
    build(panel, function (msg, bad) {
      say.textContent = msg || "";
      say.className = "statline" + (bad ? " err" : "");
    });
    panel.appendChild(say);
    open = h("div", { class: "report-modal", "data-mice-password": "1" }, [panel]);
    open.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !(opts && opts.sticky)) close();
    });
    document.body.appendChild(open);
    var f = panel.querySelector("input,button");
    if (f) f.focus();
    return panel;
  }

  function field(label, type, extra) {
    var input = h("input", Object.assign({ type: type, autocomplete: "off",
                                           "aria-label": label, placeholder: label }, extra || {}));
    return input;
  }

  // ---- 2. the recovery code, once -------------------------------------------
  function showCode(code, then) {
    dialog("Your recovery code", function (panel) {
      panel.appendChild(h("p", { text: "Keep this code somewhere safe. If you ever forget " +
        "your password, it lets you choose a new one. It works one time, and the hub cannot show it again." }));
      var box = h("div", { class: "card", "data-recovery-code": "1",
                           style: "font:600 22px/1.4 ui-monospace,Consolas,monospace;" +
                                  "letter-spacing:.08em;text-align:center;user-select:all" });
      box.textContent = code;
      panel.appendChild(box);
      var row = h("div", { class: "row" });
      row.appendChild(h("button", { type: "button", text: "Copy", onclick: function () {
        var b = this;
        var ok = function () { b.textContent = "Copied"; };
        if (navigator.clipboard && navigator.clipboard.writeText)
          navigator.clipboard.writeText(code).then(ok, function () {});
        else { var r = document.createRange(); r.selectNodeContents(box);
               var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }
      } }));
      row.appendChild(h("button", { type: "button", text: "Save as a file", onclick: function () {
        var a = h("a", { href: "data:text/plain;charset=utf-8," + encodeURIComponent(
          "Mice hub recovery code: " + code + "\r\nUse it once on the login box (Forgot password) " +
          "to choose a new password.\r\n"), download: "mice-hub-recovery-code.txt" });
        document.body.appendChild(a); a.click(); a.parentNode.removeChild(a);
      } }));
      row.appendChild(h("button", { type: "button", text: "Print", onclick: function () {
        var w = window.open("", "_blank");
        if (!w) return;
        w.document.write("<pre style='font:20px monospace'>Mice hub recovery code\n\n" +
                          code + "\n\nUse it once (Forgot password) to choose a new password.</pre>");
        w.document.close(); w.print();
      } }));
      panel.appendChild(row);
      var tick = h("input", { type: "checkbox", id: "mpSaved" });
      var done = h("button", { type: "button", class: "primary", disabled: "disabled", text: "Done",
                               onclick: function () { close(); if (then) then(); } });
      tick.onchange = function () { done.disabled = !tick.checked; };
      panel.appendChild(h("label", { class: "checkbox-row", for: "mpSaved" },
                          [tick, h("span", { text: "I have saved this code" })]));
      panel.appendChild(h("div", { class: "report-actions" }, [done]));
    }, { sticky: true });
  }

  // ---- 1. choose your own password ------------------------------------------
  function choose(user) {
    dialog("Please choose your own password", function (panel, say) {
      panel.appendChild(h("p", { text: "This hub still uses the password it ships with. " +
        "Anyone who has read the manual knows it. Choose your own now; it takes a few seconds." }));
      var a = field("New password (8 to 32 characters, no spaces)", "password",
                    { autocomplete: "new-password", maxlength: "32" });
      var b = field("Type it again", "password", { autocomplete: "new-password", maxlength: "32" });
      var save = h("button", { type: "button", class: "primary", text: "Save my password" });
      var later = h("button", { type: "button", text: "Remind me later", onclick: function () {
        store("set", "mice.pw.snooze." + (user || ""), String(Date.now() + SNOOZE_MS));
        close();
      } });
      save.onclick = function () {
        if (a.value !== b.value) { say("The two passwords are not the same.", true); return; }
        say("Saving…");
        save.disabled = true;
        post("/api/users/password", { user: user, password: a.value }).then(function (j) {
          save.disabled = false;
          if (!j.ok) { say(j.error || "That password was not saved.", true); return; }
          document.dispatchEvent(new CustomEvent("mice-login", { detail: { user: user } }));
          if (j.recoveryCode) showCode(j.recoveryCode); else close();
        });
      };
      b.onkeydown = function (e) { if (e.key === "Enter") save.onclick(); };
      panel.appendChild(a); panel.appendChild(b);
      panel.appendChild(h("div", { class: "report-actions" }, [save, later]));
    });
  }

  // ---- 3. forgot password ----------------------------------------------------
  function forgot() {
    dialog("Forgot your password?", function (panel, say) {
      panel.appendChild(h("p", { text: "Type your user name, your recovery code and a new password." }));
      var who = field("User name", "text", { autocomplete: "username" });
      var code = field("Recovery code", "text", { autocapitalize: "characters", spellcheck: "false" });
      var a = field("Choose the new password", "password", { autocomplete: "new-password", maxlength: "32" });
      var b = field("Type it again", "password", { autocomplete: "new-password", maxlength: "32" });
      var go = h("button", { type: "button", class: "primary", text: "Set the new password" });
      var timer = null;
      function wait(n) {
        clearInterval(timer);
        var t = function () {
          if (n <= 0) { clearInterval(timer); go.disabled = false; say(""); return; }
          go.disabled = true;
          say("Too many tries. Please wait, then try again. (" + n + "s)", true);
          n -= 1;
        };
        t(); timer = setInterval(t, 1000);
      }
      go.onclick = function () {
        if (a.value !== b.value) { say("The two passwords are not the same.", true); return; }
        say("Checking…");
        go.disabled = true;
        post("/api/recovery/use", { user: who.value.trim(), code: code.value, password: a.value })
          .then(function (j) {
            go.disabled = false;
            if (j.ok) {
              a.value = b.value = code.value = "";
              showCode(j.recoveryCode, function () {
                document.dispatchEvent(new CustomEvent("mice-login", { detail: {} }));
              });
              return;
            }
            if (j.wait > 0) { wait(j.wait); return; }
            say(j.error || "That did not work.", true);
          });
      };
      b.onkeydown = function (e) { if (e.key === "Enter") go.onclick(); };
      [who, code, a, b].forEach(function (i) { panel.appendChild(i); });
      panel.appendChild(h("p", { class: "mini", text: "No code? On the hub PC, open \u201cReset Hub Password\u201d " +
        "from the launchers folder. It only works on that PC." }));
      panel.appendChild(h("div", { class: "report-actions" }, [go,
        h("button", { type: "button", text: "Close", onclick: function () { clearInterval(timer); close(); } })]));
    });
  }

  // ---- a new recovery code (logged in, password asked again) -----------------
  function newCode() {
    dialog("Make a new recovery code", function (panel, say) {
      panel.appendChild(h("p", { text: "Type your password to make a new recovery code. The old code stops working." }));
      var pw = field("Your password", "password", { autocomplete: "current-password" });
      var go = h("button", { type: "button", class: "primary", text: "Make a new code" });
      go.onclick = function () {
        say("Checking…");
        post("/api/recovery/code", { password: pw.value }).then(function (j) {
          if (j.ok && j.recoveryCode) { pw.value = ""; showCode(j.recoveryCode); }
          else say(j.error || "That did not work.", true);
        });
      };
      pw.onkeydown = function (e) { if (e.key === "Enter") go.onclick(); };
      panel.appendChild(pw);
      panel.appendChild(h("div", { class: "report-actions" }, [go,
        h("button", { type: "button", text: "Close", onclick: close })]));
    });
  }

  // ---- when to offer -----------------------------------------------------------
  function check() {
    return fetch("/api/whoami").then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.authed || !j.mustChange || open) return false;
      var until = parseInt(store("get", "mice.pw.snooze." + (j.user || "")) || "0", 10);
      if (until && Date.now() < until) return false;
      choose(j.user);
      return true;
    }).catch(function () { return false; });
  }

  // "Forgot password?" under every login box, and "New recovery code" in every
  // account panel. Boxes are drawn by other scripts at other times, so this
  // watches for them instead of asking each page to call a function.
  function decorate() {
    var forms = document.querySelectorAll(".mlogin .mlIn, #loginForm");
    for (var i = 0; i < forms.length; i++) {
      var f = forms[i];
      if (f.parentNode.querySelector("[data-mice-forgot]")) continue;
      var link = h("button", { type: "button", class: "secondary", "data-mice-forgot": "1",
                               text: "Forgot password?", onclick: forgot });
      f.parentNode.insertBefore(link, f.nextSibling);
    }
    var accts = document.querySelectorAll(".mlogin .mlAcct, #userBox");
    for (var k = 0; k < accts.length; k++) {
      var p = accts[k];
      if (p.querySelector("[data-mice-newcode]")) continue;
      p.appendChild(h("button", { type: "button", "data-mice-newcode": "1",
                                  text: "Make a new recovery code", onclick: newCode }));
    }
  }

  document.addEventListener("mice-login", function () { setTimeout(check, 300); });
  document.addEventListener("mice-recovery-code", function (e) {
    if (e.detail && e.detail.code) showCode(e.detail.code);
  });
  function start() {
    decorate();
    if (window.MutationObserver) new MutationObserver(decorate).observe(document.body,
      { childList: true, subtree: true });
    check();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();

  window.micePassword = { check: check, forgot: forgot, newCode: newCode, showCode: showCode,
                          choose: choose, close: close };
})();
