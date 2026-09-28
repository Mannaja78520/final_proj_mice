"""Sound to the robot from a browser: several sources at once, each switchable,
on both roads (user 2026-09-28).

The user asked to hear the played audio AND the microphone through the robot at
the same time, each with its own on/off, from the PC (through the hub) and from
a phone (straight to the board, no hub). This drives the real module page in a
browser with made-up sources in place of the microphone and the shared screen
(a browser under test has neither), and reads what actually left the page:

  * through the hub: /api/stream/start, then 16-bit PCM chunks to
    /api/stream/feed, and /api/stream/stop at the end;
  * on the board's own address: a WebSocket to /ws/audio that says
    `START 22050` first and then carries the same PCM;
  * two loud sources summed must not clip: the mix goes through a limiter,
    because two full-scale sources added together used to wrap round and
    crack. Measured as the share of samples sitting at full scale;
  * a source switched off while sending is gone from the mix, and the rest
    keeps going;
  * a song file picked on the device plays into the mix.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "sound to the robot mixes song, PC sound and microphone, on both roads"
SLOW = True

DRIVER = """
<style>html,body{margin:0}iframe{width:900px;height:700px;border:0}</style>
<iframe id="hub" src="%s"></iframe>
<iframe id="direct" src="%s"></iframe>
<iframe id="talk" src="%s"></iframe>
<script>
function done(s){ qcMark("CM " + s); qcMark("done"); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
// a made-up source: a sine at `amp` of full scale, as a MediaStream
function tone(w, freq, amp){
  var c = new w.AudioContext(), o = c.createOscillator(), g = c.createGain();
  o.frequency.value = freq; g.gain.value = amp;
  var dst = c.createMediaStreamDestination();
  o.connect(g); g.connect(dst); o.start();
  return dst.stream;
}
function stats(bufs){
  var n = 0, full = 0, peak = 0;
  bufs.forEach(function(b){
    var a = new Int16Array(b);
    for (var i = 0; i < a.length; i++) {
      var v = Math.abs(a[i]); n++;
      if (v >= 32700) full++;
      if (v > peak) peak = v;
    }
  });
  return {n: n, full: n ? full / n : 0, peak: peak};
}
function wav(seconds){
  var rate = 22050, n = rate * seconds, b = new ArrayBuffer(44 + n * 2), v = new DataView(b);
  function s(o, t){ for (var i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); }
  s(0,'RIFF'); v.setUint32(4, 36 + n * 2, true); s(8,'WAVE'); s(12,'fmt ');
  v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
  v.setUint32(24,rate,true); v.setUint32(28,rate*2,true); v.setUint16(32,2,true);
  v.setUint16(34,16,true); s(36,'data'); v.setUint32(40,n*2,true);
  for (var i = 0; i < n; i++) v.setInt16(44 + i*2, Math.round(12000*Math.sin(2*Math.PI*330*i/rate)), true);
  return new Blob([b], {type:'audio/wav'});
}
function ready(id){
  var f = document.getElementById(id);
  return f && f.contentWindow && f.contentDocument && f.contentDocument.readyState === "complete"
      && typeof f.contentWindow.castToggle === "function";
}
qcWaitFor(function(){ return ready("hub") && ready("direct") && ready("talk"); }, 15000).then(async function(){
  var out = [];
  try{
    // ---------------- through the hub ----------------
    var w = document.getElementById("hub").contentWindow, d = w.document;
    var feeds = [], calls = [];
    var real = w.fetch;
    w.fetch = function(u, o){
      u = String(u);
      if (u.indexOf("/api/stream/") >= 0) {
        calls.push(u.replace(/^.*\\/api\\/stream\\//, ""));
        if (u.indexOf("/feed") >= 0) feeds.push(o.body);
        return Promise.resolve(new w.Response('{"ok":true}', {status: 200}));
      }
      return real.apply(w, arguments);
    };
    w.navigator.mediaDevices.getUserMedia = async function(){ return tone(w, 440, 0.9); };
    w.navigator.mediaDevices.getDisplayMedia = async function(){ return tone(w, 660, 0.9); };
    d.getElementById("cast_mic").checked = true;
    await w.castToggle();
    await sleep(1200);
    var one = stats(feeds);
    out.push("hubstart=" + (calls[0] === "start" ? "yes" : calls[0]));
    out.push("hubchunks=" + feeds.length);
    out.push("hubbytes=" + (feeds[0] ? feeds[0].byteLength : 0));
    out.push("onepeak=" + one.peak);

    // a second loud source, switched on while it plays
    feeds.length = 0;
    d.getElementById("cast_pc").checked = true;
    await w.castSource("pc", true);
    await sleep(1500);
    var two = stats(feeds.slice(2));
    out.push("both=" + Object.keys(w.castSrc).sort().join("+"));
    out.push("twofull=" + two.full.toFixed(4));
    out.push("twopeak=" + two.peak);

    // the microphone off; the PC sound carries on
    d.getElementById("cast_mic").checked = false;
    await w.castSource("mic", false);
    feeds.length = 0;
    await sleep(800);
    out.push("after=" + Object.keys(w.castSrc).join("+"));
    out.push("stillsending=" + (stats(feeds).peak > 1000 ? "yes" : "no"));
    w.castStop("qc");
    await sleep(200);
    out.push("hubstop=" + (calls.indexOf("stop") >= 0 ? "yes" : "no"));

    // ---------------- straight to the board ----------------
    var x = document.getElementById("direct").contentWindow, e = x.document;
    var sent = [], urls = [];
    x.WebSocket = function(u){
      urls.push(String(u)); var me = this; this.readyState = 1; this.bufferedAmount = 0;
      setTimeout(function(){ if (me.onopen) me.onopen(); }, 20);
    };
    x.WebSocket.prototype.send = function(m){ sent.push(m); };
    x.WebSocket.prototype.close = function(){};
    x.navigator.mediaDevices.getUserMedia = async function(){ return tone(x, 440, 0.5); };
    var dt = new x.DataTransfer();
    dt.items.add(new x.File([wav(3)], "song.wav", {type: "audio/wav"}));
    e.getElementById("castFile").files = dt.files;
    e.getElementById("cast_song").checked = true;
    e.getElementById("cast_mic").checked = true;
    await x.castToggle();
    await sleep(1500);
    // every socket the page opened: its own status socket (/ws) may open too
    out.push("wsurl=" + (urls.some(function(u){ return /\\/ws\\/audio$/.test(u); })
                         ? "ok" : encodeURIComponent(urls.join(","))));
    out.push("wsfirst=" + (typeof sent[0] === "string" ? sent[0].replace(/ /g, "_") : "binary"));
    var bin = sent.filter(function(m){ return typeof m !== "string"; });
    out.push("wschunks=" + bin.length);
    out.push("wspeak=" + stats(bin).peak);
    out.push("wssrc=" + Object.keys(x.castSrc).sort().join("+"));
    x.castStop("qc");
    out.push("wsstop=" + (sent.indexOf("STOP") >= 0 ? "yes" : "no"));

    // ---------------- the board's secure talk page ----------------
    var y = document.getElementById("talk").contentWindow, g = y.document;
    var said = [], sock = null;
    y.WebSocket = function(u){
      sock = this; var me = this; this.readyState = 1; this.bufferedAmount = 0;
      setTimeout(function(){ if (me.onopen) me.onopen(); }, 20);
    };
    y.WebSocket.prototype.send = function(m){ said.push(m); };
    y.WebSocket.prototype.close = function(){};
    y.navigator.mediaDevices.getUserMedia = async function(){ return tone(y, 440, 0.5); };
    g.getElementById("tPass").value = "secret12";
    await y.castToggle();
    await sleep(900);
    var texts = said.filter(function(m){ return typeof m === "string"; });
    out.push("talkfirst=" + (texts[0] || "none").replace(/ /g, "_"));
    out.push("talksecond=" + (texts[1] || "none").replace(/ /g, "_"));
    out.push("talkchunks=" + said.filter(function(m){ return typeof m !== "string"; }).length);
    // the board refuses the login: the page must say so and stop
    if (sock && sock.onmessage) sock.onmessage({data: "ERR wrong user or password"});
    out.push("talkrefused=" + (!y.castOn && /wrong user/.test(g.getElementById("castStat").textContent)
                               ? "said" : "silent"));
  }catch(err){ out.push("ERR=" + String(err).replace(/[^A-Za-z0-9=]+/g, "_").slice(0, 60)); }
  done(out.join(" "));
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, _main = F.start_hub()
    hub = "/mod?dev=usb%3A" + urllib.parse.quote(fake_serial.PORT)
    direct = "/mod"
    # The talk page is only ever served by the board (over https). Here it is
    # lifted out of its header and served from the Studio folder, so /cast.js
    # and /mice.css resolve to the hub's copies - the same files.
    head = (F.FIRMWARE / "src/web/TalkUI.h").read_text(encoding="utf-8")
    html = head[head.index('R"rawliteral(') + 13:head.index(')rawliteral"')]
    web = F.CODE / "nong" / "main_python_set_nong" / "web"
    talk = web / ("_qctalk_%s.html" % browser._tag())
    talk.write_text(html, encoding="utf-8")
    try:
        browser.raw_page(DRIVER % (hub, direct, "/studio/" + talk.name), base, seconds=40,
                         flags=("--autoplay-policy=no-user-gesture-required",))
    finally:
        talk.unlink(missing_ok=True)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("CM "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                got[k] = v
    if not t.ok(got and "ERR" not in got, "the page reported back",
                "%r" % (got or fake_serial.qc_marks[-3:],)):
        return

    t.eq(got.get("hubstart"), "yes", "through the hub it asks the hub to start first")
    t.ok(int(got.get("hubchunks", 0)) >= 5,
         "and streams chunks while the microphone is on (%s in 1.2 s)" % got.get("hubchunks"))
    t.eq(got.get("hubbytes"), "4096", "each chunk is 2048 16-bit samples")
    t.ok(int(got.get("onepeak", 0)) > 8000, "the microphone is really in them (peak %s)"
         % got.get("onepeak"))
    t.eq(got.get("both"), "mic+pc", "a second source switched on while playing joins the mix")
    t.ok(float(got.get("twofull", 1)) < 0.001,
         "two loud sources summed do not clip (%.2f %% of samples at full scale)"
         % (100 * float(got.get("twofull", 1))),
         "0.9 + 0.9 of full scale used to wrap round and crack; the limiter holds it")
    t.eq(got.get("after"), "pc", "switching the microphone off takes only the microphone out")
    t.eq(got.get("stillsending"), "yes", "and the PC sound keeps playing")
    t.eq(got.get("hubstop"), "yes", "Stop tells the hub")

    t.eq(got.get("wsurl"), "ok", "on the board's own address it opens /ws/audio on the board")
    t.eq(got.get("wsfirst"), "START_22050", "and says the rate before any sound")
    t.ok(int(got.get("wschunks", 0)) >= 5, "then sends PCM over it (%s chunks)" % got.get("wschunks"))
    t.eq(got.get("wssrc"), "mic+song", "a song file and the microphone play at the same time")
    t.ok(int(got.get("wspeak", 0)) > 8000, "and the sound is really in the frames (peak %s)"
         % got.get("wspeak"))
    t.eq(got.get("wsstop"), "yes", "Stop tells the board")

    t.eq(got.get("talkfirst"), "LOGIN_admin_secret12",
         "the secure talk page signs in on the socket first (it has no cookie there)")
    t.eq(got.get("talksecond"), "START_22050", "then asks for the speaker")
    t.ok(int(got.get("talkchunks", 0)) >= 3,
         "and sends the microphone (%s chunks)" % got.get("talkchunks"))
    t.eq(got.get("talkrefused"), "said",
         "a refused login stops it and says why, instead of sending into nothing")

    # ---- the board half of the talk page (read from source) ----------------
    st = (F.FIRMWARE / "src/core/SecureTalk.cpp").read_text(encoding="utf-8")
    t.contains(st, 'if (fd != audioFd) wsSay(req, "ERR log in first");',
               "the board opens its speaker to a signed-in socket only")
    t.contains(st, "} else if (f.type == HTTPD_WS_TYPE_BINARY && fd == audioFd && st) {",
               "and takes sound only from that socket")
    t.contains(st, "if (ESP.getFreeHeap() < MIN_HEAP) {",
               "it refuses to start when memory is short, rather than crash the robot")
    keys = [f.name for f in (F.FIRMWARE / "src").rglob("*")
            if f.is_file() and "PRIVATE KEY" in f.read_text(encoding="utf-8", errors="replace")]
    t.eq(keys, [], "no private key is in the source: each board makes its own")
    # The first TALK ON on the real nong rebooted it (2026-09-28): the
    # certificate code needs more stack than the 8 KB loop task has.
    t.contains(st, 'xTaskCreate(startTask, "talk", TASK_STACK',
               "the certificate and TLS start run in their own task, with room")
