"""The login dialogs in a real browser: choose your own password, keep the code, forgot password.

User 2026-11-27: the first login on the shipped password asks to change it in plain
words (skippable), the recovery code is shown once, Forgot password is on the login
box. Driven in headless Edge on the real Home page at phone width (360 px), because
a dialog that runs off a phone screen is one nobody can finish. Asserted on what the
hub answered afterwards (the account really has a new password) and not on the
words alone.
"""
import json
import urllib.error
import urllib.request

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "login dialogs: own-password prompt, recovery code once, forgot password, at 360 px"
SLOW = False

DRIVER = """
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function mark(k, v){ qcMark("L~" + k + "~" + v); }
async function until(f, win, ms){
  var end = Date.now() + (ms || 15000);
  while (Date.now() < end){ try { var v = f(win); if (v) return v; } catch (e) {} await sleep(150); }
  return null;
}
async function frame(lang, width){
  localStorage.setItem("mice.lang", lang);
  var f = document.createElement("iframe");
  f.style.cssText = "width:" + width + "px;height:760px;border:0";
  document.body.appendChild(f);
  f.src = "/";
  await until(function(){ var d = f.contentDocument; return d.readyState === "complete" && f.contentWindow.micePassword && d.getElementById("loginForm"); });
  await sleep(800);
  return f;
}
function dlg(w){ return w.document.querySelector("[data-mice-password]"); }
async function run(){
  // ---- English, 360 px wide: the whole flow
  var f = await frame("en", 360), w = f.contentWindow, d = f.contentDocument;
  mark("forgotLink", d.querySelector("[data-mice-forgot]") ? 1 : 0);
  mark("firstRunHint", d.getElementById("loginFirstRun").hidden ? 0 : 1);
  var r = await w.fetch("/api/login", {method: "POST", body: JSON.stringify({user: "shipped", password: "admin123"})});
  mark("loginStatus", r.status);
  d.dispatchEvent(new w.CustomEvent("mice-login", {detail: {user: "shipped"}}));
  var box = await until(function(){ return dlg(w); });
  mark("promptShown", box ? 1 : 0);
  if (box){
    mark("promptTitle", box.querySelector("h2").textContent);
    var p = box.querySelector(".report-panel").getBoundingClientRect();
    mark("fits360", (p.left >= 0 && p.right <= 360 && d.documentElement.scrollWidth <= 360) ? 1 : 0);
    var ins = box.querySelectorAll("input");
    ins[0].value = "Brand-new-pass-1"; ins[1].value = "different-pass-2";
    var btns = box.querySelectorAll("button");
    btns[0].click(); await sleep(400);
    mark("mismatch", box.querySelector(".statline").textContent);
    ins[1].value = "Brand-new-pass-1"; btns[0].click();
    var code = await until(function(){ var c = d.querySelector("[data-recovery-code]"); return c && c.textContent; });
    mark("codeShown", code || "");
    var done = d.querySelector("[data-mice-password] .report-actions .primary");
    mark("doneLockedFirst", done && done.disabled ? 1 : 0);
    var tick = d.getElementById("mpSaved"); tick.checked = true; tick.onchange();
    mark("doneOpensAfterTick", done.disabled ? 0 : 1);
    var q = d.querySelector("[data-recovery-code]").getBoundingClientRect();
    var cb = d.querySelector("[data-recovery-code]");
    mark("code360", (q.right <= 360 && cb.scrollWidth <= cb.clientWidth + 1) ? 1 : 0);
    done.click(); await sleep(300);
    mark("closedAfterDone", dlg(w) ? 0 : 1);
  }
  // ---- remind me later: the second account says "later" and is not asked again today
  await w.fetch("/api/logout", {method: "POST"});
  await w.fetch("/api/login", {method: "POST", body: JSON.stringify({user: "later", password: "admin123"})});
  d.dispatchEvent(new w.CustomEvent("mice-login", {detail: {user: "later"}}));
  box = await until(function(){ return dlg(w); });
  var later = Array.prototype.filter.call(box ? box.querySelectorAll("button") : [], function(b){ return b.textContent === "Remind me later"; })[0];
  if (later) later.click();
  await sleep(300);
  mark("laterCloses", dlg(w) ? 0 : 1);
  d.dispatchEvent(new w.CustomEvent("mice-login", {detail: {user: "later"}}));
  await sleep(1500);
  mark("laterNotAskedAgain", dlg(w) ? 0 : 1);
  // ---- forgot password: a wrong code is refused in words, nothing is changed
  await w.fetch("/api/logout", {method: "POST"});
  d.querySelector("[data-mice-forgot]").click();
  box = await until(function(){ return dlg(w); });
  mark("forgotTitle", box ? box.querySelector("h2").textContent : "");
  var fi = box.querySelectorAll("input");
  fi[0].value = "shipped"; fi[1].value = "AAAA-AAAA-AAAA-AAAA"; fi[2].value = "Whatever-pass-1"; fi[3].value = "Whatever-pass-1";
  Array.prototype.filter.call(box.querySelectorAll("button"), function(b){ return b.textContent === "Set the new password"; })[0].click();
  await until(function(){ var s = box.querySelector(".statline"); return s && s.textContent && s.textContent !== "Checking…"; });
  mark("forgotRefused", box.querySelector(".statline").textContent);
  w.micePassword.close();
  // ---- Chinese: the dialog text follows the chosen language
  var g = await frame("zh", 360), gw = g.contentWindow;
  await gw.fetch("/api/login", {method: "POST", body: JSON.stringify({user: "zhuser", password: "admin123"})});
  g.contentDocument.dispatchEvent(new gw.CustomEvent("mice-login", {detail: {user: "zhuser"}}));
  var zb = await until(function(){ return dlg(gw); });
  await sleep(600);
  mark("zhTitle", zb ? zb.querySelector("h2").textContent : "");
  localStorage.setItem("mice.lang", "en");
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, main = F.start_hub()
    auth = main.auth()
    for name in ("shipped", "later", "zhuser"):
        auth.add_user(name, "admin123")
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=90)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("L~"):
            _, k, v = m.split("~", 2)
            got[k] = v
    t.ok("closedAfterDone" in got, "the page got through the whole flow", sorted(got))
    t.eq(got.get("forgotLink"), "1", "Forgot password? is on the Home login box")
    t.eq(got.get("loginStatus"), "200", "the shipped login worked in the page")
    t.eq(got.get("promptShown"), "1", "the first login on the shipped password opens the choose-your-own box")
    t.ok("choose your own password" in got.get("promptTitle", "").lower(), "in plain words", got.get("promptTitle"))
    t.eq(got.get("fits360"), "1", "the box fits a 360 px screen and the page does not scroll sideways")
    t.ok("not the same" in got.get("mismatch", ""), "two different passwords are refused in words", got.get("mismatch"))
    code = got.get("codeShown", "")
    t.ok(len(code) == 19 and code.count("-") == 3, "then the recovery code is shown", code)
    t.eq(got.get("code360"), "1", "and fits the phone screen")
    t.eq(got.get("doneLockedFirst"), "1", "Done stays locked until 'I have saved this code' is ticked")
    t.eq(got.get("doneOpensAfterTick"), "1", "and opens when it is")
    t.eq(got.get("closedAfterDone"), "1", "and Done closes the box")
    t.eq(got.get("laterCloses"), "1", "Remind me later closes the box")
    t.eq(got.get("laterNotAskedAgain"), "1", "and the same account is not asked again straight away")
    t.ok("Forgot" in got.get("forgotTitle", ""), "Forgot password opens its box", got.get("forgotTitle"))
    t.ok("did not work" in got.get("forgotRefused", ""), "a wrong recovery code is refused in words", got.get("forgotRefused"))
    t.ok("密码" in got.get("zhTitle", ""), "in Chinese the box is in Chinese", got.get("zhTitle"))
    # what the hub really did: the page's new password is the account's password now
    req = urllib.request.Request(base + "/api/login", method="POST",
                                 data=json.dumps({"user": "shipped", "password": "Brand-new-pass-1"}).encode())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    t.eq(status, 200, "the hub really has the new password (asserted on its answer, not on the page)")
    t.ok(auth.has_recovery("shipped"), "and a recovery code is on file for it")
    t.ok(auth.must_change("later") and not auth.has_recovery("later"),
         "'Remind me later' changed nothing on the account")
    browser.kill()
    for name in ("shipped", "later", "zhuser"):
        auth.remove_user(name)
