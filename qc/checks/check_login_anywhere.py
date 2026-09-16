"""Log in from any page, and it is the same session everywhere.

Asked 2026-09-09, from the Voice app: *where to login in this page, make can
login in the page not only in the hub and sync each other*. That page answered
a save with "log in before doing that" and offered no way to do it - the only
login control in the whole product was the card on the hub's own page, and the
message sent people to another screen to find it.

The session was ALREADY shared: one cookie, one origin. What was missing was
the control. So there is now one shared component (`miceLogin` in
shared/web/mice.js) that every page mounts, rather than five logins that can
drift apart.

Driven in a real browser, on the VOICE page, asserting on what the hub says
about the session rather than on what the page says about itself:

  * the page offers a login when nobody is logged in;
  * typing the password there really logs in - /api/whoami says so, and that
    is the hub's own answer, not the page's opinion;
  * the same session is then live for the HUB page too, without touching it;
  * and log out ends it everywhere for the same reason.
"""
import json
import time

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "you can log in from any page, and it is one session"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/app/voice/"></iframe>
<script>

async function runTest() {
  var w = document.getElementById('f').contentWindow;
  var d = document.getElementById('f').contentDocument;
  var box = d ? d.getElementById("loginHere") : null;
  if (!box || !box.querySelector(".mlPass")) {
      setTimeout(runTest, 50);
      return;
  }
  
  var out = [];
  try{
    // Both boxes start hidden until the hub says who is logged in. Reading
    // them before that answer lands failed once the voice page grew heavier
    // (2026-09-16): nothing was offered yet, and nothing was wrong.
    for (var i = 0; i < 100; i++){
      var a = box.querySelector(".mlIn"), b = box.querySelector(".mlOut");
      if ((a && !a.hidden) || (b && !b.hidden)) break;
      await new Promise(r => setTimeout(r, 100));
    }

    out.push("mounted:" + (box && box.querySelector(".mlPass") ? "yes" : "no"));

    // START FROM LOGGED OUT. The browser profile is reused between runs and a
    // cookie ignores the PORT, so a session left by the previous run reaches
    // the next hub on a different port. Without this the "offers a login"
    // assertion measures what ran before it, not the component.
    var wasIn = box.querySelector(".mlOut");
    if (wasIn && !wasIn.hidden){
      box.querySelector(".mlOff").click();
      // wait for the logged-out box itself, not a fixed 2.5 s
      for (var j = 0; j < 100; j++){
        var inb = box.querySelector(".mlIn");
        if (inb && !inb.hidden) break;
        await new Promise(r => setTimeout(r, 100));
      }
    }
    var shown = box.querySelector(".mlIn");
    out.push("offersLogin:" + (shown && !shown.hidden ? "yes" : "no"));

    var userField = box.querySelector(".mlUser"); if (userField) userField.value = "super_admin";
    if (box.querySelector(".mlUser")) box.querySelector(".mlUser").value = "super_admin";
    box.querySelector(".mlPass").value = "%s";
    box.querySelector(".mlGo").click();
    await new Promise(r => setTimeout(r, 1400));

    // ask the HUB, not the page: is this browser logged in now?
    var who = await w.fetch("/api/whoami").then(r => r.json());
    out.push("hubSaysAuthed:" + (who.authed ? "yes" : "no"));
    out.push("showsLoggedIn:" + (box.querySelector(".mlOut").hidden ? "no" : "yes"));

    var r2 = await w.fetch("/api/voice/config", {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify({config:{}})});
    out.push("gatedCall:" + (r2.status === 401 ? "refused" : "allowed"));

    box.querySelector(".mlOff").click();
    await new Promise(r => setTimeout(r, 2500));
    var after = await w.fetch("/api/whoami").then(r => r.json());
    out.push("afterLogout:" + (after.authed ? "still-in" : "out"));

    // LOG BACK IN, only so the report can be delivered. qcMark posts to
    // /api/usb/cmd, which is gated - so reporting while logged out is a mark
    // refused four times and then dropped, and the check fails with
    // "(nothing)" while saying nothing about what it actually found. That is
    // exactly how this check failed its first full gate, 2026-09-09: it was
    // the only check whose own last step took away its way of speaking.
    var userField = box.querySelector(".mlUser"); if (userField) userField.value = "super_admin";
    if (box.querySelector(".mlUser")) box.querySelector(".mlUser").value = "super_admin";
    box.querySelector(".mlPass").value = "%s";
    box.querySelector(".mlGo").click();
    await new Promise(r => setTimeout(r, 1400));
    qcMark(out.join(" ").replace(/ /g, "~"));
  }catch(e){ qcMark("ERR~" + String(e.message || e).replace(/ /g, "~")); }
  qcMark("done");
}
runTest();
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    # The voice page, served by the hub like every other app.
    # raw_page, not page(): this drives ANOTHER page in an iframe rather
    # than Studio itself, and it reports straight to the fake module.
    browser.raw_page(DRIVER % (F.HUB_PASSWORD, F.HUB_PASSWORD), base, seconds=25)
    marks = [m.replace("~", " ") for m in fake_serial.qc_marks]
    line = next((m for m in marks if "mounted:" in m), "")
    if not t.ok(line and "ERR" not in " ".join(marks),
                "the voice page ran and reported", marks or "(nothing)"):
        return
    got = dict(p.split(":", 1) for p in line.split() if ":" in p)

    t.eq(got.get("mounted"), "yes", "the voice page carries a login of its own")
    t.eq(got.get("offersLogin"), "yes",
         "and offers it when nobody is logged in")
    t.eq(got.get("hubSaysAuthed"), "yes",
         "logging in THERE really logs in - the hub says so, not the page")
    t.eq(got.get("showsLoggedIn"), "yes", "and the page then says who is in")
    t.ok(got.get("gatedCall") == "allowed",
         "a gated action from that page goes through afterwards",
         "this is the whole point: the save that was refused now works without "
         "walking to another screen; got %r" % got.get("gatedCall"))
    t.ok(got.get("afterLogout") == "out",
         "logging out there ends the session everywhere",
         "one cookie, one origin - so it must end in both directions too; "
         "got %r" % got.get("afterLogout"))

    # ---- one component, not one per page ------------------------------
    js = (F.CODE / "shared" / "web" / "mice.js").read_text(encoding="utf-8",
                                                           errors="replace")
    t.contains(js, "window.miceLogin", "the login lives in the shared script")
    for rel in ("apps/voice/index.html", "apps/camera/index.html",
                "main_python/web/rgb.html"):
        page = (F.CODE / rel).read_text(encoding="utf-8", errors="replace")
        t.contains(page, "miceLogin.mount",
                   "%s mounts the shared one rather than growing its own" % rel)
