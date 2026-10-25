"""Real Gacha page clicks through the Hub to fake boards; async faults stay faults."""
import json
import os
import tempfile
import time
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "gacha"
TITLE = "Gacha controls reach the board and wait for async result, phase and faults"
SLOW = True

DRIVER = r"""
<iframe id="app" src="/app/gacha/#machines" style="width:1280px;height:850px"></iframe>
<script>
function mark(k,v){return qcMark('GUI~'+k+'='+v);}
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
window.addEventListener('load',async()=>{
 try {
  const f=document.getElementById('app'), w=f.contentWindow, d=f.contentDocument;
  if(!await qcWaitFor(()=>d.querySelector('#mTable tbody button'),15000)) throw Error('page did not draw');
  const button=text=>[...d.querySelectorAll('#mTable button')].find(b=>b.textContent.includes(text));
  button('add balls').click(); await sleep(300);
  button('Tune').click();
  await mark('tuning',!!d.getElementById('t_intake_0'));
  d.getElementById('t_intake_0').value='0';
  [...d.getElementById('t_intake_0').parentNode.querySelectorAll('button')].find(b=>b.textContent==='Save').click();
  await sleep(300);
  const messages=[];
  new MutationObserver(()=>messages.push(d.getElementById('mStat').textContent)).observe(d.getElementById('mStat'),{childList:true,subtree:true});
  button('Test 1 Pocket').click();
  await qcWaitFor(()=>/One pocket: jam/.test(d.getElementById('mStat').textContent),6000);
  await mark('jam',d.getElementById('mStat').textContent);
  await mark('phase',messages.some(s=>s.includes('pause')&&s.includes('ms left')));
  button('Estimate Hall Advance').click();
  await qcWaitFor(()=>/Hall advance estimate: board reports done/.test(d.getElementById('mStat').textContent),6000);
  await mark('calib',d.getElementById('mStat').textContent);
  button('Test All Pockets').click();
  await qcWaitFor(()=>/Pocket test: board reports done/.test(d.getElementById('mStat').textContent),6000);
  await mark('test',d.getElementById('mStat').textContent);
  button('Drain Machine').click();
  await qcWaitFor(()=>/Drain: jam/.test(d.getElementById('mStat').textContent),6000);
  await mark('drain',d.getElementById('mStat').textContent);
  button('to loading').click(); await sleep(150); button('Stop motion').click();
  await qcWaitFor(()=>/stopped/.test(d.getElementById('mStat').textContent),5000);
  await mark('stop',d.getElementById('mStat').textContent);
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
    with tempfile.TemporaryDirectory(prefix="mice_gacha_ui_") as folder:
        cfg = Path(folder) / "gacha.json"
        cfg.write_text(json.dumps({"machines": [{"id": "g1", "dev": "usb:COM99:70", "label": "QC", "item": "ball"}],
                                   "items": {"ball": {"label": "Ball"}}, "event": {"open": True}}), encoding="utf-8")
        old = {k: os.environ.get(k) for k in ("MICE_GACHA_CONFIG", "MICE_GACHA_DATA")}
        os.environ["MICE_GACHA_CONFIG"] = str(cfg)
        os.environ["MICE_GACHA_DATA"] = str(Path(folder) / "data")
        base, main = F.start_hub()
        board = fake_serial.GACHAS[70]
        line, status = board.line, board.status
        job = {"cmd": "", "at": 0, "stop": False}

        def motion_status():
            s = status()
            s.update(stock=3, pos_known=False, cfg={"magnets": 8, "slots": 4, "per_slot": 2, "drop": 1})
            cmd, age = job["cmd"], time.monotonic() - job["at"]
            busy = bool(cmd) and age < 1.1 and not job["stop"]
            s.update(state="turning" if busy else "idle", motion_result="turning" if busy else
                     ("stopped" if job["stop"] else "jam" if cmd.startswith(("GSPIN", "GDRAIN")) else "done"),
                     phase="pause" if busy else None, phase_ms_left=900 if busy else 0,
                     at_hall=True, testing=busy and cmd.startswith("GTEST"), test_total=4,
                     test_done=min(4, int(age * 4)) if cmd.startswith("GTEST") else 0)
            return s

        def command(c):
            if c.split()[0] in ("GSPIN", "GTEST", "GCALIB", "GDRAIN", "GHOME", "STOP"):
                fake_serial.gacha_wire.append((70, c))
                if c == "STOP":
                    job["stop"] = True
                else:
                    job.update(cmd=c, at=time.monotonic(), stop=False)
                return "OK accepted"
            return line(c)

        board.line, board.status = command, motion_status
        try:
            browser.raw_page(DRIVER, base, seconds=40)
        finally:
            browser.kill()
            board.line, board.status = line, status
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    got = dict(m[4:].split("=", 1) for m in fake_serial.qc_marks if m.startswith("GUI~") and "=" in m)
    t.ok("error" not in got and bool(got), "actual Gacha page runs", got)
    for key in ("tuning", "phase", "narrow"):
        t.ok(got.get(key) == "true", "Gacha %s behavior" % key, got)
    for key, phrase in (("jam", "One pocket: jam"), ("calib", "board reports done"),
                        ("test", "4/4 pockets"), ("drain", "Drain: jam"), ("stop", "stopped")):
        t.ok(phrase in got.get(key, ""), "Gacha %s reports the board result" % key, got)
    wire = [c for b, c in fake_serial.gacha_wire if b == 70]
    for cmd in ("GSPIN 1", "GCALIB", "GTEST 4", "GDRAIN 3", "GHOME", "STOP", "GCFG intake 0"):
        t.ok(cmd in wire, "%s reached the fake board through the Hub" % cmd, wire)
