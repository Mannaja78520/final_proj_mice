"""The pins page says which board each speaker wire goes to - rendered, not read.

A24-41, user 2026-09-08: *use TPA3118-30W with lift module, i use PCM5102 in
main and use TPA to use my 12V Speaker*. So the lift's speaker is a CHAIN of
two boards: I2S into a PCM5102A DAC, its line out into a TPA3118 amp, then the
12V speaker. With both boards in hand the question is which one each of the
three wires goes to - the chip only ever talks to the DAC - and the answer has
to be on the Hardware-pins page, under the GPIO box of that very wire.

This drives the real module page (served the way the hub serves it for a cable,
`/mod?dev=usb:COM99`) with the board's answers to PIN?, PIN VALID, AMP VALID and
AMP? stood in - built from amps.json the way the firmware builds them, which
check_amp_kind proves by running the generated table. Then it picks every amp in
turn and reads the DOM: only that amp's pins are shown, each with the line
amps.json gives it, the wiring sentence is on screen, and a fresh lift opens on
the chain. check_amp_kind holds the data; this holds what a person sees.
"""
import json
import re
import sys

import browser
import fake_serial
import qc as F

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402  (JSONC loader - amps.json carries comments)

AREA = "modsite"
TITLE = "the pins page says which board each speaker wire goes to"
SLOW = True

AUDIO = ("i2s_bclk", "i2s_lrc", "i2s_dout")

PAGE = """
<style>html,body{margin:0}#f{width:1200px;height:900px;border:0}</style>
<iframe id="f" src="/mod?dev=usb%3ACOM99"></iframe>
<script>
var AMPS = __AMPS__, PINS = __PINS__, VALID = __VALID__, CUR = "__CUR__";
function done(s){ qcMark("AMPWIRE " + s); qcMark("done"); }
qcWaitFor(function(){
  var fr = document.getElementById("f");
  return fr && fr.contentWindow && fr.contentDocument
      && fr.contentDocument.readyState === "complete"
      && fr.contentDocument.body && fr.contentDocument.body.children.length
      && typeof fr.contentWindow.loadPins === "function";
}, 8000).then(function(){
  var w = document.getElementById("f").contentWindow;
  var d = w.document;
  // The board's own answers, so the page runs exactly its real code path.
  w.cmd = function(c){
    var ans = {"AMP VALID": AMPS, "PIN?": PINS, "PIN VALID": VALID,
               "AMP?": AMPS.filter(function(a){ return a.id === CUR; })[0]};
    return Promise.resolve(c in ans ? JSON.stringify(ans[c]) : "");
  };
  return w.loadPins().then(function(){
    var sel = d.getElementById("ampSel");
    qcMark("AMPWIRE opened=" + (sel ? sel.value : "-"));
    var i = 0;
    (function next(){
      if (i >= AMPS.length) { done("end"); return; }
      var a = AMPS[i++], s = d.getElementById("ampSel");
      if (!s) { done("no-picker"); return; }
      s.value = a.id; s.dispatchEvent(new w.Event("change"));
      var row = {id: a.id, shown: {}};
      ["i2s_bclk", "i2s_lrc", "i2s_dout"].forEach(function(k){
        var box = d.getElementById("pin_" + k);
        if (!box) return;
        var to = box.parentNode.querySelector(".wireto");
        row.shown[k] = to ? to.textContent : "";
      });
      row.wiring = d.getElementById("pinGroups").textContent.indexOf(a.wiring) >= 0;
      qcMark("AMPWIRE " + JSON.stringify(row)).then(next);
    })();
  });
}).catch(function(e){ done("ERR=" + String(e).slice(0, 80)); });
</script>
"""


def _board_json(amps):
    """AMP VALID as the board sends it (ampJson in the generated AmpTable.h)."""
    return [{"id": k, "label": a["label"], "mode": a["mode"],
             "pins": ",".join(a["pins"]), "mono": a["mono"],
             "wiring": a["wiring"], "to": a["to"]} for k, a in amps.items()]


def _lift_default():
    hdr = (F.FIRMWARE / "config" / "esp32_hardware_lift_module.h").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r'LIFT_AUDIO_AMP_DEFAULT\s+"([^"]+)"', hdr)
    return m.group(1) if m else ""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    amps = registry.load(F.FIRMWARE / "config" / "amps.json", {}).get("amps", {})
    cur = _lift_default()
    if not t.ok(cur in amps, "the lift's default amp is in amps.json", cur):
        return
    # PIN? and PIN VALID in the board's own shape (HwConfig::listJson and
    # validPinsJson): the lift's speaker pins, and GPIOs with their classes.
    pins = {"i2s_bclk": {"gpio": 27, "label": "I2S BCLK", "group": "audio", "out": True},
            "i2s_lrc": {"gpio": 14, "label": "I2S LRC", "group": "audio", "out": True},
            "i2s_dout": {"gpio": 2, "label": "I2S DOUT", "group": "audio", "out": True},
            "sd_cs": {"gpio": 5, "label": "SD CS", "group": "sd", "out": True}}
    valid = [{"g": g, "c": "strap" if g in (0, 2, 5, 12, 15) else "ok", "n": "pwm"}
             for g in (0, 2, 4, 5, 12, 13, 14, 15, 27, 32, 33)]
    page = (PAGE.replace("__AMPS__", json.dumps(_board_json(amps)))
                .replace("__PINS__", json.dumps(pins))
                .replace("__VALID__", json.dumps(valid))
                .replace("__CUR__", cur))

    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(page, base, seconds=30)

    marks = [m[len("AMPWIRE "):] for m in fake_serial.qc_marks
             if m.startswith("AMPWIRE ")]
    if not t.ok(marks, "the module page reported back",
                "it never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    t.contains(marks, "opened=%s" % cur,
               "a fresh lift opens the pins page on its own chain (%s)" % cur)
    rows = {}
    for m in marks:
        if m.startswith("{"):
            r = json.loads(m)
            rows[r["id"]] = r
    t.ok("end" in marks, "the page went through every amp", marks[-2:])
    for key, a in amps.items():
        r = rows.get(key)
        if not t.ok(r, "the page showed %s" % key):
            continue
        t.eq(sorted(r["shown"]), sorted(a["pins"]),
             "%s shows only the pins it wires" % key)
        for k in a["pins"]:
            t.eq(r["shown"].get(k), "goes to " + a["to"][k],
                 "%s: the %s box says where its wire goes" % (key, k))
        t.ok(r["wiring"], "%s: its wiring sentence is on the page" % key)
    chain = rows.get(cur, {}).get("shown", {})
    t.ok(chain and all("PCM5102A" in v for v in chain.values()),
         "on the lift's chain all three wires go to the PCM5102A, not the amp", chain)
