"""Studio's Zero position lock opens with the HUB login, not a browser-only one.

User 2026-09-17 (A26-43): *Zero position lock: user admin pass admin123 -> That
user name and password do not match*. `zeroUnlock()` compared the boxes with a
pair kept in localStorage, defaulting to manny/12345678 - the demo login that
admin/admin123 replaced everywhere else. The hub accepted admin/admin123; this
one lock did not, and it had its own "Change login" that changed nothing on the
hub or the board.

Now the lock asks the hub's /api/login. Asserted by driving Studio: the right
hub login opens the panel, a wrong one does not, and Set zero then reaches the
module (`fake_serial.wire`).
"""
import browser
import fake_serial
import qc as F

AREA = "auth"
TITLE = "the zero-position lock in Studio opens with the hub login"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof zeroUnlock !== "function" || !haveUsb()) return setTimeout(step, 300);
    var panel = document.getElementById("zeroPanel");
    document.getElementById("zUser").value = "admin";
    document.getElementById("zPass").value = "not-the-password";
    zeroUnlock().then(function(){
      qcMark("Zwrong=" + (panel.style.display === "none" ? "locked" : "OPEN"));
      document.getElementById("zUser").value = "admin";
      document.getElementById("zPass").value = "admin123";
      return zeroUnlock();
    }).then(function(){
      qcMark("Zright=" + (panel.style.display === "none" ? "locked" : "open"));
      return robotZeroSet();
    }).then(function(){ qcMark("done"); })
      .catch(function(e){ qcFail(e); });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def run(t):
    web = F.CODE / "nong/main_python_set_nong/web"
    js = (web / "app_parts/robot_link.js").read_text(encoding="utf-8", errors="replace")
    fn = js[js.find("function zeroUnlock"):]
    fn = fn[:fn.find("\nfunction zeroLock")]
    t.ok('"/api/login"' in fn,
         "the zero lock asks the hub to check the login")
    t.ok("12345678" not in fn and "nongZeroCred" not in fn,
         "and no longer compares with a browser-only password",
         "manny/12345678 in localStorage refused admin/admin123 (A26-43)")

    if not browser.available():
        t.give_up("headless Edge not found — the source half above still ran")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=24)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks[-4:])
    t.eq(_mark(marks, "Zwrong"), "locked", "a wrong password keeps it locked")
    t.eq(_mark(marks, "Zright"), "open", "the hub login admin/admin123 opens it")
    t.ok(any(c == "SETZERO" for _, c in fake_serial.wire),
         "Set zero then reached the module",
         [c for _, c in fake_serial.wire][-5:])
