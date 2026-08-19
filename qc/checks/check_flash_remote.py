"""A PC that never built firmware can still flash the board on its cable.

At a venue there is one laptop with PlatformIO on it and several without. The
board is plugged into whichever machine is nearest. esptool has to run on the
PC holding the cable, so the IMAGE travels and the command does not:

    POST /api/flash/send     this PC gives its image to the hub that has the cable
    POST /api/flash/remote   that hub receives it and writes it

Both are driven here against one hub talking to itself, which is the whole
round trip: log in, send, receive, unpack, flash. The fake esptool records the
files it was handed, so what is asserted is the BYTES that reached the board —
not what the sending page believed it sent.

The awkward cases are the point of the rest of it: an unauthenticated caller,
a part that tries to escape the temp folder, a Content-Length that would eat
the hub's memory, and whether the received image is cleaned up afterwards.
"""
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "firmware"
TITLE = "firmware sent from another PC, written by the PC with the cable"
SLOW = True

# Records what it was actually asked to write: every --port, every offset and
# the sha of each file. A flash that wrote the wrong bytes still prints all the
# cheerful progress lines, so the check reads the files, not the output.
FAKE = '''import hashlib, json, sys
argv = sys.argv[1:]
out = {"argv": argv, "files": []}
for i, a in enumerate(argv):
    if a.endswith(".bin"):
        try:
            b = open(a, "rb").read()
        except OSError:
            b = b""
        out["files"].append({"at": argv[i-1], "name": a.replace(chr(92), "/").split("/")[-1],
                             "sha": hashlib.sha256(b).hexdigest()[:16], "n": len(b)})
open(RECORD, "w").write(json.dumps(out))
print("esptool.py v4.9.0")
print("Writing at 0x00010000... (100 %)")
print("Hash of data verified.")
print("Hard resetting via RTS pin...")
'''



# The other half is the screen: a board on ANOTHER PC's cable has to appear,
# say whose cable it is, ask for a login on that machine, and send the image
# there rather than trying to write it from here. Driven with the network
# stubbed, so what is asserted is the request that left the page.
PAGE_FAR = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("FR " + s); qcMark("done"); }
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (typeof w.paintFirmware !== 'function') return done("missing=paintFirmware");

    var posted = null, watched = [];
    var reply = function(o){
      return Promise.resolve({
        json: function(){ return Promise.resolve(o); },
        text: function(){ return Promise.resolve(JSON.stringify(o)); }
      });
    };
    w.MY_PC = 'THIS-PC';
    w.fetch = function(u, o){
      u = String(u);
      if (u.indexOf('/api/flash/images') >= 0)
        return reply({esptool: true, images: [
          {type:'nong', env:'mice_nong', ready:true, bytes:1400000, built_at:1}]});
      if (u.indexOf('/api/allmods') >= 0)
        return reply({modules: [{id:7, name:'armB', dev:'hub:10.0.0.5/usb:COM7',
                                 host:'FAR-PC', hostIp:'10.0.0.5', type:'lift'}]});
      if (u.indexOf('/api/flash/send') >= 0){ posted = o && o.body; return reply({ok:true}); }
      if (u.indexOf('/api/flash/at') >= 0){ watched.push(u); return reply({done:true, percent:100}); }
      if (u.indexOf('/api/flash') >= 0) return reply({running:false});
      if (u.indexOf('/api/mine') >= 0) return reply({host:'THIS-PC', modules: []});
      return reply({modules: [], ports: []});
    };

    await w.paintFirmware();
    var go = [].slice.call(d.querySelectorAll('.fwgo')).filter(function(b){
      return /cable on FAR-PC/.test(b.textContent); })[0];
    if (!go) return done("row=none");
    var label = go.textContent.replace(/[^A-Za-z0-9-]+/g, "_");

    go.click();
    await new Promise(function(r){ setTimeout(r, 600); });
    var asked = !d.getElementById('fcLogin').hidden;
    d.getElementById('fcUser').value = 'ann';
    d.getElementById('fcPass').value = 'sekret';
    d.getElementById('fcGo').click();
    await new Promise(function(r){ setTimeout(r, 2500); });

    var body = posted ? JSON.parse(posted) : {};
    done(["row=" + label,
          "asked=" + (asked ? "yes" : "no"),
          "to=" + (body.to || "none"),
          "port=" + (body.port || "none"),
          "type=" + (body.type || "none"),
          "user=" + (body.user || "none"),
          "pass=" + (body.password ? "sent" : "no"),
          "watch=" + (watched.length ? "far" : "local")].join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,60)); }
}, 4000);
</script>
"""

def _fake(tmp):
    rec = tmp / "record.json"
    f = tmp / "fake_esptool.py"
    f.write_text("RECORD = %r\n" % str(rec) + FAKE, encoding="utf-8")
    return '"%s" "%s"' % (sys.executable, f), rec



def _bare_post(base, path, data, fake_len=0):
    """POST with NO session cookie, and optionally a lying Content-Length.

    qc.post carries the QC login on every call, which is right for driving the
    hub and useless for asking whether the gate is there at all. http.client is
    used rather than urllib because only a hand-written header can claim to be
    sending 900 MB while sending nothing.
    """
    import http.client
    host = base.split("//", 1)[1]
    c = http.client.HTTPConnection(host, timeout=15)
    try:
        c.putrequest("POST", path, skip_accept_encoding=True)
        c.putheader("Content-Type", "application/json")
        c.putheader("Content-Length", str(fake_len or len(data)))
        c.endheaders()
        c.send(data)
        r = c.getresponse()
        return r.status, r.read(2000)
    finally:
        c.close()


def _wait(base, limit=25.0):
    end = time.time() + limit
    while time.time() < end:
        s = json.loads(F.get(base + "/api/flash")[1])
        if not s["running"]:
            return s
        time.sleep(0.05)
    return json.loads(F.get(base + "/api/flash")[1])


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="qc_remote_"))
    cmd, rec = _fake(tmp)
    os.environ["MICE_ESPTOOL"] = cmd
    try:
        fake_serial.reset()
        base, main = F.start_hub()
        port = fake_serial.PORT

        im = main.flash_image("nong")
        if not im["ready"]:
            t.give_up("no nong firmware built on this PC — pio run -e mice_nong")
            return

        # ---- 1. the whole round trip ---------------------------------
        # `to` is this same hub: sending to yourself exercises both halves,
        # including the login, without needing a second machine in QC.
        r = json.loads(F.post(base + "/api/flash/send", json.dumps({
            "to": "127.0.0.1", "port": port, "type": "nong",
            "user": "mice", "password": F.HUB_PASSWORD}).encode())[1])
        t.ok(r.get("ok") is not False, "a hub can send its firmware to another PC",
             "hub said: " + json.dumps(r)[:300])
        done = _wait(base)
        t.ok(done.get("ok"), "and that PC writes it to the board on its cable",
             done.get("error", ""))

        got = json.loads(rec.read_text(encoding="utf-8")) if rec.is_file() else {}
        t.ok(got, "esptool was actually run", "no record written")
        t.contains(" ".join(got.get("argv", [])), port,
                   "on the cable that was named, not another one")

        # The bytes that reached esptool are the bytes this PC built. Comparing
        # the shas is the only thing that catches an image that travelled but
        # arrived truncated, re-encoded, or from the wrong module type.
        want = {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
                for _off, p in im["parts"]}
        sent = {f["name"]: f["sha"] for f in got.get("files", [])}
        t.eq(len(sent), len(want), "every part of the image arrived")
        t.ok(all(sent.get(n) == s for n, s in want.items()),
             "byte for byte, each one",
             "wanted %r, got %r" % (want, sent))
        offs = [f["at"] for f in got.get("files", [])]
        # Offsets are written as they are everywhere else in this project -
        # 0x1000, not 4096 - and the check compares the same spelling esptool
        # was handed, because that is what reaches the board.
        t.eq(sorted(offs), sorted(str(o) for o, _p in im["parts"]),
             "and each at the offset it belongs at")

        # ---- 2. the folder it arrived in does not stay ---------------
        left = [p for p in Path(tempfile.gettempdir()).glob("mice_fw_*")]
        t.ok(not left, "the received image is removed once it is written",
             "left behind: %r" % [str(p) for p in left[:3]])

        # ---- 3. it is not open to the network -----------------------
        code, _b = _bare_post(base, "/api/flash/remote",
                              json.dumps({"port": port, "type": "nong",
                                          "parts": []}).encode())
        t.eq(code, 401, "overwriting a board from another PC needs a login")

        # ---- 4. a part cannot escape the folder it is unpacked into --
        # Asserted on the path esptool was HANDED, not on whether some file
        # appeared somewhere: a part that escaped would land outside every
        # folder this check knows to look in, which is the whole problem.
        rec.unlink(missing_ok=True)
        F.post(base + "/api/flash/remote", json.dumps({
            "port": port, "type": "nong", "from": "somewhere",
            "parts": [{"off": "0x10000", "name": "../../../evil.bin",
                       "b64": "QUJDRA=="}]}).encode())
        _wait(base)
        out = json.loads(rec.read_text(encoding="utf-8")) if rec.is_file() else {}
        paths = [a for a in out.get("argv", []) if a.endswith(".bin")]
        t.ok(paths, "a part named ../../../evil.bin still reaches the writer")
        # RESOLVED, because a path can walk out of a folder while still
        # carrying its name: temp/mice_fw_x/../../../evil.bin reads as though
        # it were inside and is not. The first version of this assertion
        # passed against exactly that, which is why it is spelled this way.
        homes = [Path(a).resolve().parent.name for a in paths]
        t.ok(all(h.startswith("mice_fw_") for h in homes),
             "but it cannot be written outside the folder it arrived in",
             "esptool was handed files in: %r" % homes)

        # ---- 5. and a huge one is refused before it is read ----------
        code, _b = _bare_post(base, "/api/flash/remote", b"{}",
                              fake_len=900 * 1048576)
        t.ok(code >= 400, "a body far too big to be firmware is refused",
             "a hub that reads it anyway is one header away from being down")
    finally:
        os.environ.pop("MICE_ESPTOOL", None)

        # ---- 6. the screen offers it, and sends it where it belongs --
        if not browser.available():
            return                      # the static half above still ran
        fake_serial.reset()
        browser.raw_page(PAGE_FAR, base, seconds=30)
        w = {}
        for m in fake_serial.qc_marks:
            if m.startswith("FR "):
                for part in m[3:].split(" "):
                    k, _, v = part.partition("=")
                    w[k] = v
        if not t.ok(w, "the Firmware screen reported back",
                    "%r" % (fake_serial.qc_marks[-3:],)):
            return
        t.contains(w.get("row", ""), "FAR-PC",
                   "a board on another PC's cable is offered, and says whose")
        t.eq(w.get("asked"), "yes",
             "and asks for a login on THAT PC, which has its own accounts")
        t.eq(w.get("to"), "10.0.0.5", "the image is sent to that PC")
        t.eq(w.get("port"), "COM7", "for the cable the board is actually on")
        t.eq(w.get("user"), "ann", "with the login that was typed")
        t.eq(w.get("pass"), "sent", "and its password")
        t.eq(w.get("watch"), "far",
             "and the write is watched on that PC, not on this one")

