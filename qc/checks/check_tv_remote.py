"""The actual TV page uses selected Nong HOME, correct telemetry and show status."""
import json
from urllib.parse import parse_qs, urlsplit

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "TV selects Nong, sends native saved HOME and restarts only the chosen show"
SLOW = True

DRIVER = r"""
<iframe id="app" src="/app/tv/" style="width:1280px;height:850px"></iframe>
<script>
function mark(k,v){return qcMark('TV~'+k+'='+v);}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
window.addEventListener('load',async()=>{
 try {
  const f=document.getElementById('app'), w=f.contentWindow, d=f.contentDocument;
  if(!await qcWaitFor(()=>w.app&&d.getElementById('targetDev'),12000)) throw Error('TV did not load');
  clearInterval(w.app.pollTimer); await qcWaitFor(()=>!w.app.pollBusy,5000);
  await w.app.goHome(); await w.app.playSequence('second.yaml');
  await mark('empty',!w.app.activeDev && d.querySelector('[onclick="app.goHome()"]').disabled);
  await fetch('/api/qc/tv?case=one'); await w.app.poll();
  await mark('target',w.app.activeDev);
  await mark('joint',d.getElementById('jval_1').textContent);
  await mark('progress',d.getElementById('playProgress').style.width+'|'+d.getElementById('curTime').textContent+'|'+d.getElementById('totTime').textContent);
  await w.app.goHome(); await qcWaitFor(()=>!w.app.pollBusy,5000);
  await w.app.playSequence('second.yaml'); await qcWaitFor(()=>!w.app.pollBusy,5000);
  await w.app.stop(); await qcWaitFor(()=>!w.app.pollBusy,5000);
  await w.app.resume(); await qcWaitFor(()=>!w.app.pollBusy,5000);
  await fetch('/api/qc/tv?case=stale'); await w.app.poll();
  await w.app.goHome(); await w.app.playSequence('first.yaml');
  await mark('stale',!w.app.activeDev);
  await fetch('/api/qc/tv?case=two'); await w.app.poll();
  await mark('multiple',!w.app.activeDev);
  d.getElementById('targetDev').value='usb:COM99'; d.getElementById('targetDev').dispatchEvent(new Event('change'));
  await mark('selected',w.app.activeDev);
  f.style.width='390px'; await sleep(300);
  await mark('narrow',d.documentElement.scrollWidth<=w.innerWidth);
 }catch(e){await mark('error',e.message);}
 await qcMark('done');
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found")
    fake_serial.reset()
    base, main = F.start_hub()
    state, plays, calls = {"case": "empty"}, [], []
    route, modules = main.Handler.route, main.modules_here
    start, status, stop = main.show.start, main.show.status, main.show.stop

    def module_list(force=False):
        nong = {"type": "nong", "name": "QC Nong", "best": "usb:COM99", "routes": [{"dev": "usb:COM99", "kind": "usb"}]}
        other = {"type": "gacha", "name": "First is not Nong", "best": "usb:COM99:70"}
        case = state["case"]
        return ([other] if case == "empty" else [other, dict(nong, stale=True)] if case == "stale"
                else [other, nong, dict(nong, best="usb:COM99:68", name="Second Nong")] if case == "two"
                else [other, nong])

    def start_show(dev, steps, loop=None, name="", *args):
        plays.append({"dev": dev, "steps": steps, "name": name})
        return {"ok": True}

    def routed(self, method):
        path = urlsplit(self.path)
        calls.append((method, self.path))
        if path.path == "/api/qc/tv":
            state["case"] = parse_qs(path.query)["case"][0]
            return self.send_json({"ok": True})
        if path.path == "/api/list":
            return self.send_json({"files": ["first.yaml", "second.yaml"]})
        if path.path == "/api/seqsteps":
            return self.send_json({"steps": [{"pose": [80.0] * 10, "t": 900, "hold": 0}]})
        return route(self, method)

    main.Handler.route, main.modules_here = routed, module_list
    main.show.start = start_show
    main.show.status = lambda: {"running": True, "name": "second.yaml", "at_ms": 2500, "total_ms": 10000,
                                "entering": False, "error": ""}
    main.show.stop = lambda *a, **k: None
    fake_serial.NONG.joints = [90, 140, 90, 90, 90, 40, 90, 90, 90, 90.5]
    try:
        browser.raw_page(DRIVER, base, seconds=35)
    finally:
        browser.kill()
        main.Handler.route, main.modules_here = route, modules
        main.show.start, main.show.status, main.show.stop = start, status, stop
    got = dict(m[3:].split("=", 1) for m in fake_serial.qc_marks if m.startswith("TV~") and "=" in m)
    t.ok("error" not in got and bool(got), "the actual TV page runs", got)
    for k in ("empty", "stale", "multiple", "narrow"):
        t.ok(got.get(k) == "true", "TV %s guard/layout" % k, got)
    t.ok(got.get("target") == "usb:COM99" and got.get("selected") == "usb:COM99", "TV uses the chosen Nong route", got)
    t.ok(got.get("joint") == "140°", "TV displays actual module.joints telemetry", got)
    t.ok(got.get("progress") == "25%|2.5s|10.0s", "TV uses at_ms and total_ms", got)
    homes = [c for _, c in fake_serial.wire if c.strip() == "HOME"]
    t.ok(len(homes) == 1, "one native HOME reached Nong; missing/stale targets send none", fake_serial.wire[-25:])
    t.ok(len(plays) == 2 and all(p["dev"] == "usb:COM99" and p["name"] == "second.yaml" for p in plays),
         "restart keeps the chosen clip; Home never posts an all90 show", plays)
    t.ok(not any("/api/status" in p for _, p in calls), "TV uses the Hub modules endpoint", calls[-10:])
