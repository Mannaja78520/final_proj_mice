"""Real Gacha page clicks through the Hub to fake boards; async faults stay faults."""
import json
import os
import re
import subprocess
import sys
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
  await mark('zero_tuning',['pause','over','ret','advance'].every(k=>d.getElementById('t_'+k+'_0').value==='0'));
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
  const outside=await fetch('/api/gacha/machine',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({machine:'g1',cmd:'GSPIN 1'})}).then(r=>r.json());
  if(!outside.ok)throw Error('external-client busy fixture did not start');
  button('Estimate Hall Advance').click();
  await qcWaitFor(()=>d.getElementById('mStat').textContent==='ERR busy',5000);
  await mark('busy',d.getElementById('mStat').textContent);
  button('Stop motion').click();await sleep(300);
  f.style.width='390px'; await sleep(300);
  await mark('narrow',d.documentElement.scrollWidth<=w.innerWidth);
  const mod=document.createElement('iframe'); mod.style='width:390px;height:850px';mod.src='/mod?dev=usb%3ACOM99%3A70';document.body.appendChild(mod);
  const md=()=>mod.contentDocument;
  if(!await qcWaitFor(()=>md()&&md().getElementById('gaC_advance'),12000))throw Error('generated module page did not draw');
  await mark('module_hall',md().getElementById('gaHall').textContent);
  await mark('module_pos',md().getElementById('gaPos').textContent);
  await mark('module_zero',['pause','return','overshoot','advance'].every(k=>md().getElementById('gaC_'+k).value==='0'));
  const mb=cmd=>[...md().querySelectorAll('button')].find(b=>b.getAttribute('onclick')==="gaCmd('"+cmd+"')");
  mb('GSPIN 1').click();
  await qcWaitFor(()=>md().getElementById('gaPhase').textContent.includes('ms left'),6000);
  await mark('module_phase',md().getElementById('gaPhase').textContent);
  await qcWaitFor(()=>md().getElementById('gaNow').textContent.includes('jam'),6000);
  await mark('module_jam',md().getElementById('gaNow').textContent);
  const advance=md().getElementById('gaC_advance');advance.value='0';advance.dispatchEvent(new mod.contentWindow.Event('change'));
  mb('GCALIB').click();await sleep(250);
  await mark('module_narrow',md().documentElement.scrollWidth<=mod.contentWindow.innerWidth);
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
        generated = Path(folder) / "generated"
        built = subprocess.run([sys.executable, str(F.FIRMWARE / "tools/gen_tables.py"), "--types", "gacha", "--out", str(generated)],
                               capture_output=True, text=True, timeout=60)
        if not t.ok(built.returncode == 0, "actual gacha-only module page generates", built.stderr[-500:]):
            return
        header = (generated / "web/ModuleUI.h").read_text(encoding="utf-8")
        html = re.search(r'R"rawliteral\((.*)\)rawliteral"', header, re.S).group(1)
        module_page = main.module_ui_html
        main.module_ui_html = lambda: html.replace("<head>", "<head>" + main.SHIM, 1)
        board = fake_serial.GACHAS[70]
        line, status = board.line, board.status
        job = {"cmd": "", "at": 0, "stop": False}

        def motion_status():
            s = status()
            s.update(stock=3, pos_known=False, cfg={"magnets": 8, "slots": 4, "per_slot": 2, "drop": 1,
                     "pause": 0, "overshoot": 0, "return": 0, "advance": 0})
            cmd, age = job["cmd"], time.monotonic() - job["at"]
            duration = 2.8 if cmd.startswith("GSPIN") else 1.1
            busy = bool(cmd) and age < duration and not job["stop"]
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
                    if motion_status()["state"] != "idle":
                        return "ERR busy"
                    job.update(cmd=c, at=time.monotonic(), stop=False)
                return "OK accepted"
            return line(c)

        board.line, board.status = command, motion_status
        try:
            browser.raw_page(DRIVER, base, seconds=40)
        finally:
            browser.kill()
            board.line, board.status = line, status
            main.module_ui_html = module_page
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    got = dict(m[4:].split("=", 1) for m in fake_serial.qc_marks if m.startswith("GUI~") and "=" in m)
    t.ok("error" not in got and bool(got), "actual Gacha page runs", got)
    for key in ("tuning", "zero_tuning", "phase", "narrow", "module_zero", "module_narrow"):
        t.ok(got.get(key) == "true", "Gacha %s behavior" % key, got)
    for key, phrase in (("jam", "One pocket: jam"), ("calib", "board reports done"),
                        ("test", "4/4 pockets"), ("drain", "Drain: jam"), ("stop", "stopped")):
        t.ok(phrase in got.get(key, ""), "Gacha %s reports the board result" % key, got)
    wire = [c for b, c in fake_serial.gacha_wire if b == 70]
    for cmd in ("GSPIN 1", "GCALIB", "GTEST 4", "GDRAIN 3", "GHOME", "STOP", "GCFG intake 0"):
        t.ok(cmd in wire, "%s reached the fake board through the Hub" % cmd, wire)
    t.ok(got.get("module_hall") == "Hall detected" and got.get("module_pos") == "reference unknown",
         "generated module page does not infer geometric center or pocket reference", got)
    t.ok("jam" in got.get("module_jam", "") and "ms left" in got.get("module_phase", ""),
         "generated module page shows final fault and live countdown", got)
    t.ok(wire.count("GCALIB") >= 2 and "GCFG advance 0" in wire,
         "generated module-page controls reach the fake board", wire)
    t.ok(got.get("busy") == "ERR busy", "actual HTTP200 board refusal is shown instead of generic API200 or done", got)
