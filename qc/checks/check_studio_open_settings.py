"""Studio settings that never reach the real robot open without a login (A49-2).

User 2026-10-23: "setting ขอให้มีแบบไม่ใส่รหัสสำหรับ setting ที่ไม่ซีเรียสกับหุ่นจริง
ใส่รหัสกับที่ซีเรียสจริงๆ". The list is DATA: settings_open.json beside Studio's
page names the cards (by id) that show while nobody is logged in; every other
Robot / Setup card stays behind the login card. In a real browser, logged out:

  * the Setup tab shows the login card AND the listed cards (the 3D look,
    the save prompt);
  * cards that change what the robot is tuned to (Rig setup, Servo offset,
    Movement safety, This robot) stay hidden;
  * the Robot tab shows only the login card (every card there talks to a board).
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio: harmless settings open without a login, robot ones keep it"
SLOW = True

WEB = F.CODE / "nong" / "main_python_set_nong" / "web"
LOCKED = ["Rig setup", "Servo offset", "Movement safety", "This robot", "Robot link", "Zero position"]

DRIVER = """
<style>html,body{margin:0}iframe{width:1280px;height:800px;border:0}</style>
<iframe id="s" src="/studio/"></iframe>
<script>
function say(k, v){ return qcMark("SO " + k + "=" + String(v).replace(/[\\s|=]+/g, "~")); }
function shown(d){
  return [...d.querySelectorAll("[data-stab]")].filter(c => c.offsetParent !== null)
    .map(c => { var h = c.querySelector("h2"); return h ? h.firstChild.textContent.split("(")[0].split(" \\u2014")[0].trim() : ""; }).join(";");
}
window.addEventListener("load", async function(){
  try{
    var f = document.getElementById("s"), w = f.contentWindow;
    await qcWaitFor(function(){ return typeof w.showTab === "function" && w.eval("OPEN_WITHOUT_LOGIN.length"); }, 20000);
    // QC's own browser is logged in to the hub; log THIS page out the way
    // Studio does when the hub says the session ended (currentUser = null).
    w.eval("currentUser = null");
    await say("user", w.eval("currentUser") || "none");
    w.showTab("setup");
    await say("setup", shown(f.contentDocument));
    w.showTab("robot");
    await say("robot", shown(f.contentDocument));
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    data = json.loads((WEB / "settings_open.json").read_text(encoding="utf-8"))
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for cid in data["open"]:
        t.ok(('id="%s"' % cid) in html, "settings_open.json names a card that exists: " + cid, cid)
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=45)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("SO "):
            k, _, v = m[3:].partition("=")
            got[k] = v.replace("~", " ")
    setup = got.get("setup", "").split(";")
    t.ok(got.get("user") == "none", "the page is opened with nobody logged in", got)
    t.ok("Login Required" in setup and "Model" in " ".join(setup) and "Saving" in setup,
         "Setup, logged out: the login card plus the 3D look and the save prompt", got)
    t.ok(not [n for n in LOCKED if any(s.startswith(n) for s in setup)],
         "Setup, logged out: nothing that changes what the robot is tuned to", got)
    t.ok(got.get("robot") == "Login Required", "Robot, logged out: only the login card", got)
