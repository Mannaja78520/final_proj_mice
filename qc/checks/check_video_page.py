"""The Video page: a link plays like a file, and the robot moves beside it (A44-8).

User 2026-10-19: an app of its own for moves from a video - the person with
their music, the skeleton found on them, and the robot moving, side by side
and in step - that also takes YouTube, Google Drive and other links, and whose
settings are used in Nong Studio. Built as Studio's Video tab: the same time
bar, the same project file.

The hub half (hub_video.py), with no internet: a local server stands in for
the web.
* fetching a link needs a login (it writes to this PC on someone's say-so);
* a link that answers with a video is saved as it is; one that answers with a
  page goes to yt-dlp (swapped here for a recorder); a share link (Drive,
  Dropbox) becomes its download address, and a share that answers with a page
  says how to share it, in words - never handed to yt-dlp;
* with no yt-dlp on the PC the answer names the command that installs it;
* the video is served with Range (206): a <video> cannot seek without it;
* the sound of the part the moves were made from becomes an mp3 (ffmpeg).

The page half, in a real browser:
* the Video tab puts the person, the 3D robot and the choices side by side;
* a link is fetched through the hub and the player can seek in it;
* at each moment of the video the robot takes the made moves' pose for that
  moment (eased like the firmware), and the skeleton its frame;
* Play plays the video WITH its sound, and the robot moves along;
* closing the page gives the editor back the pose it had;
* the video's sound reaches the ROBOT'S CARD and is the first move's music;
* the choices are saved in the project file and come back when it is opened.
"""
import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the Video page fetches links and plays the person beside the robot"
SLOW = True

DRIVER = """
const wait = ms => new Promise(r => setTimeout(r, ms));
function rep(k, v){ qcMark("VP~" + k + "=" + String(v).replace(/~/g, "_")); }
async function until(f, ms){ const t = performance.now();
  while (!f()) { if (performance.now() - t > ms) return false; await wait(100); } return true; }
function ink(){ const c = document.getElementById("vidOverlay");
  if (!c.width || !c.height) return 0;
  const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) n += d[i] > 0; return n; }
async function at(s){ const v = document.getElementById("vidPlayer");
  await new Promise(r => { v.onseeked = r; v.currentTime = s; setTimeout(r, 4000); });
  await wait(250); }
async function run(){
  const ready = await until(() => typeof vidPage === "function" && typeof haveRobot === "function"
                                   && haveRobot() && typeof elbowBalls !== "undefined", 25000);
  if (!ready) { rep("ERR", "the app or the robot link never came up"); return; }
  const p0 = pose.slice();
  showTab("video");
  await wait(400);
  rep("card", document.getElementById("vidCard").offsetParent !== null);
  // measured in frames of a laptop's and a phone's width: media queries answer
  // to the frame (as check_studio_layout does)
  for (const [w, h, tag] of [[1280, 800, "wide"], [390, 800, "phone"]]) {
    const f = document.createElement("iframe");
    f.width = w; f.height = h; f.src = "/studio/";
    document.body.appendChild(f);
    await until(() => f.contentWindow && typeof f.contentWindow.vidPage === "function"
                      && f.contentDocument.getElementById("vidStage"), 20000);
    await wait(500);
    f.contentWindow.showTab("video");
    await wait(400);
    const R = id => f.contentDocument.getElementById(id).getBoundingClientRect();
    const st = R("vidStage"), vp = R("viewport"), sd = R("side");
    rep(tag + "W", Math.round(st.width) + "/" + Math.round(vp.width));
    rep(tag + "By", tag === "wide" ? st.right <= vp.left + 2 && vp.right <= sd.left + 2
                                   : st.bottom <= vp.top + 2 && vp.bottom <= sd.top + 2);
    f.remove();
  }
  // a link, through the hub
  document.getElementById("vidLink").value = LINK;
  await vidFetch();
  const v = document.getElementById("vidPlayer");
  await until(() => v.readyState >= 1, 10000);
  rep("src", /\\/api\\/video\\/file\\?id=/.test(v.src)); rep("dur", (v.duration || 0).toFixed(1));
  rep("to", document.getElementById("vidTo").value);
  await at(3.0);
  rep("seek", v.currentTime.toFixed(1));
  // what Make moves leaves behind: frames (with the picture's points) and moves
  const A = RIG.neutral.map((x, i) => clampJ(i, x)), B = A.slice();
  B[0] = clampJ(0, A[0] + 40);
  const P = []; for (let i = 0; i < 33; i++) P.push({x: 0.3 + (i % 2) * 0.4, y: 0.15 + i * 0.02, v: 1});
  vidFrames = []; for (let i = 0; i <= 40; i++) vidFrames.push({t: i / 10, w: null, p: i < 20 ? null : P});
  vidMade = {keys: [{pose: A, t: 1000, hold: 0}, {pose: B, t: 2000, hold: 0, tset: true}],
             start: 0, videoMs: 2000, handMiss: [0, 0], kept: 2, partial: 0};
  document.getElementById("vidFrom").value = "0";
  await at(1.0);
  rep("mid", (pose[0] - (A[0] + B[0]) / 2).toFixed(2)); rep("inkEarly", ink());
  await at(2.5);
  rep("end", (pose[0] - B[0]).toFixed(2)); rep("inkLate", ink());
  document.getElementById("vidSkel").checked = false; vidLastMs = -1; await wait(250);
  rep("inkOff", ink());
  document.getElementById("vidSkel").checked = true;
  // play: the video with its sound, the robot along with it
  await at(0.0);
  vidPlayBoth();
  await wait(1300);
  rep("plays", !v.paused); rep("playSaid", document.getElementById("vidStat").textContent.slice(0, 100)); rep("sound", !v.muted); rep("moved", (pose[0] - A[0]).toFixed(1));
  v.pause();
  // closing the page gives the editor back its pose
  showTab("pose");
  rep("back", JSON.stringify(pose) === JSON.stringify(p0)); rep("pageOff", !document.body.classList.contains("vidpage"));
  // on the time bar, then the sound onto the robot's card as the first move's music
  showTab("video");
  window.askUnsaved = async () => true;
  await vidUse("replace");
  rep("onBar", keys.length); rep("soundBox", !document.getElementById("vidSoundBox").hidden);
  await vidSound();
  rep("cue", cueTrack(keys[0]) || "none");
  rep("stat", document.getElementById("vidStat").textContent.slice(0, 120));
  // the choices ride in the project file
  document.getElementById("vidMirror").checked = true;
  document.getElementById("vidDetail").value = "close";
  document.getElementById("vidFrom").value = "0.5";
  setWorkName("qc_video_page");
  rep("saved", await saveProject());
  document.getElementById("vidMirror").checked = false;
  document.getElementById("vidDetail").value = "smooth";
  document.getElementById("vidLink").value = "";
  window.confirm = () => false;
  await loadProject("qc_video_page.json");
  rep("mirrorBack", document.getElementById("vidMirror").checked);
  rep("detailBack", document.getElementById("vidDetail").value);
  rep("linkBack", document.getElementById("vidLink").value === LINK);
}
window.addEventListener("load", function(){
  run().catch(e => rep("ERR", String(e && e.stack || e).slice(0, 200))).then(() => qcMark("VP~done"));
});
"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _serve(folder):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                          functools.partial(_Quiet, directory=str(folder)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d/" % srv.server_port


def _wait(links, jid, seconds=30):
    end = time.time() + seconds
    while links.status(jid)["state"] == "working" and time.time() < end:
        time.sleep(0.1)
    return links.status(jid)


def _req(url, data=None, headers=None):
    req = F._with_cookie(urllib.request.Request(url, data=data, headers=headers or {},
                                                method="POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def run(t):
    ff = shutil.which("ffmpeg")
    if not ff:
        t.give_up("ffmpeg not found - it makes the test clip (and the robot's mp3)")
    tmp = Path(tempfile.mkdtemp(prefix="qc_video_page_"))
    web = tmp / "web"
    web.mkdir()
    # VP8 + Vorbis: every browser build plays it (headless Chromium has no H.264)
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "4",
                    "-c:v", "libvpx", "-b:v", "200k", "-c:a", "libvorbis", "-shortest",
                    str(web / "clip.webm")], check=True, timeout=120)
    (web / "page.html").write_text("<html><body>a page, not a video</body></html>")
    clip = (web / "clip.webm").read_bytes()
    srv, local = _serve(web)
    base, main = F.start_hub()
    import hub_api_studio
    import hub_video
    cfg_path = F.CODE / "config" / "video_links.json"
    links = hub_video.Links(cfg_path, tmp / "cache")
    hub_api_studio.LINKS = links
    try:
        _hub_half(t, base, local, links, clip, cfg_path, tmp)
        _page_half(t, base, local + "clip.webm", links, main)
    finally:
        hub_api_studio.LINKS = None
        srv.shutdown()
        for f in (main.PROJECTS / "qc_video_page.json", main.PROJECTS / "qc_video_page.json.bak"):
            f.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)


def _hub_half(t, base, local, links, clip, cfg_path, tmp):
    import hub_video
    body = json.dumps({"url": local + "clip.webm"}).encode()
    F.logout_qc()
    code, _, _ = _req(base + "/api/video/fetch", body, {"Content-Type": "application/json"})
    t.ok(code == 401, "fetching a link needs a login", code)
    F.login(base)
    code, _, raw = _req(base + "/api/video/fetch", body, {"Content-Type": "application/json"})
    got = json.loads(raw or b"{}")
    if not t.ok(code == 200 and got.get("id"), "a link starts a fetch", raw[:200]):
        return
    st = _wait(links, got["id"])
    t.ok(st["state"] == "done" and st["size"] == len(clip),
         "a link that answers with a video is saved as it is", st)
    jid = got["id"]
    code, _, raw = _req(base + "/api/video/fetch?id=" + jid)
    t.ok(code == 200 and json.loads(raw)["state"] == "done", "the page can ask how far it got", raw[:200])
    code, h, raw = _req(base + "/api/video/file?id=" + jid, headers={"Range": "bytes=100-199"})
    t.ok(code == 206 and raw == clip[100:200] and
         h.get("Content-Range") == "bytes 100-199/%d" % len(clip),
         "the video is served by parts (206), so the player can seek", (code, h.get("Content-Range")))
    code, h, raw = _req(base + "/api/video/file?id=" + jid)
    t.ok(code == 200 and raw == clip and h.get("Accept-Ranges") == "bytes",
         "and whole, saying it takes parts", (code, h.get("Accept-Ranges")))
    code, _, raw = _req(base + "/api/video/fetch", json.dumps({"url": "ftp://x/y"}).encode(),
                        {"Content-Type": "application/json"})
    t.ok(code == 400 and b"https://" in raw, "a non-web link is refused in words", raw[:200])

    # a page goes to yt-dlp; with none on the PC the answer names the fix
    asked = []
    links.run_ytdlp = lambda j: (asked.append(j), links._fail(links.jobs[j], "recorded"))
    j, _ = links.start(local + "page.html")
    st = _wait(links, j)
    t.ok(asked == [j] and st["how"] == "yt-dlp", "a link that answers with a page goes to yt-dlp", st)
    links.run_ytdlp = links._run_ytdlp
    if links.ytdlp():
        # the real yt-dlp on a page that carries a video (its generic reader)
        (tmp / "web" / "show.html").write_text(
            '<html><head><title>Dance</title></head><body><video src="clip.webm"></video></body></html>')
        st = _wait(links, links.start(local + "show.html")[0], 120)
        t.ok(st["state"] == "done" and st["size"] == len(clip) and st["title"].startswith("Dance"),
             "yt-dlp on this PC fetches the video a page carries", st)
    else:
        print("   (no yt-dlp on this PC: its real run is not tried)")
    none = hub_video.Links(cfg_path, tmp / "cache")
    none.cfg["ytdlp"]["run"] = [["no-such-yt-dlp-qc"]]
    st = _wait(none, none.start(local + "page.html")[0])
    t.ok(st["state"] == "failed" and "yt-dlp is not installed" in st["error"]
         and none.cfg["ytdlp"]["install"] in st["error"],
         "with no yt-dlp on this PC the answer names the command that installs it", st)

    # share links: the real patterns, then a stand-in share on the local server
    import re
    shares = {s["id"]: s for s in links.cfg["shares"]}
    m = re.search(shares["drive"]["match"], "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view?usp=sharing")
    t.ok(m and "id=1AbCdEfGhIjKlMnOp" in m.expand(shares["drive"]["direct"]),
         "a Google Drive share link becomes its download address", m and m.expand(shares["drive"]["direct"]))
    m = re.search(shares["dropbox"]["match"], "https://www.dropbox.com/scl/fi/ab/x.mp4?rlkey=k&dl=0")
    t.ok(m and m.expand(shares["dropbox"]["direct"]).endswith("rlkey=k&dl=1"),
         "a Dropbox share link becomes its download address", m and m.expand(shares["dropbox"]["direct"]))
    fake = hub_video.Links(cfg_path, tmp / "cache")
    fake.cfg["shares"] = [{"id": "qc", "label": "QC share", "match": re.escape(local) + r"share/([\w.]+)",
                           "direct": local + r"\1", "html": "SHARE IT WITH ANYONE"}]
    fake.run_ytdlp = lambda j: fake._fail(fake.jobs[j], "went to yt-dlp")
    st = _wait(fake, fake.start(local + "share/clip.webm")[0])
    t.ok(st["state"] == "done" and st["how"] == "QC share", "a share link is fetched from its download address", st)
    st = _wait(fake, fake.start(local + "share/page.html")[0])
    t.ok(st["error"] == "SHARE IT WITH ANYONE",
         "a share that is not open to anyone says how to share it, not yt-dlp", st)
    t.ok("needs a login" in links.say("ERROR: [youtube] abc: Private video. Sign in if you've been granted access")
         and "could not be read" in links.say("ERROR: something new"),
         "what went wrong is said in words, a new error included")

    # the sound of the part the moves were made from
    code, _, raw = _req(base + "/api/video/sound", json.dumps({"id": jid, "from": 1, "to": 3}).encode(),
                        {"Content-Type": "application/json"})
    code2, h, mp3 = _req(base + "/api/video/file?kind=sound&id=" + jid)
    t.ok(code == 200 and code2 == 200 and h.get("Content-Type") == "audio/mpeg"
         and (mp3[:3] == b"ID3" or mp3[:2] in (b"\xff\xfb", b"\xff\xf3")) and 8000 < len(mp3) < 80000,
         "the video's sound from 1 s to 3 s becomes an mp3", (code, code2, len(mp3)))
    code, _, raw = _req(base + "/api/video/put?name=mine.webm", clip,
                        {"Content-Type": "application/octet-stream"})
    pid = json.loads(raw or b"{}").get("id", "")
    code2, _, back = _req(base + "/api/video/file?id=" + pid)
    t.ok(code == 200 and back == clip, "a picked file is kept on the hub for its sound", (code, code2))


def _page_half(t, base, link, links, main):
    if not browser.available():
        t.give_up("headless Edge not found - the page half needs a real browser")
    fake_serial.reset()
    drv = "const LINK = %s;\n" % json.dumps(link) + DRIVER
    # no user here to tap Play: a sound may start without one
    browser.page(drv, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT),
                 seconds=90, flags=("--autoplay-policy=no-user-gesture-required",))
    marks = [m[3:] for m in fake_serial.qc_marks if m.startswith("VP~") and "=" in m]
    v = dict(m.split("=", 1) for m in marks)
    print("   page:", v)
    if not t.ok("ERR" not in v and "linkBack" in v, "the page driver ran to the end", v.get("ERR", v)):
        return
    sw, vw = (int(x) for x in v["wideW"].split("/"))
    t.ok(v["wideBy"] == "true" and sw > 300 and vw > 300,
         "at 1280 px the person, the 3D robot and the choices are side by side (%d px, %d px)"
         % (sw, vw), v)
    t.ok(v["phoneBy"] == "true", "on a phone the person is above the robot, the choices below", v)
    t.ok(v["card"] == "true", "the Video tab shows its choices", v)
    t.ok(v["src"] == "true" and abs(float(v["dur"]) - 4) < 0.3 and abs(float(v["to"]) - 4) < 0.3,
         "a link plays from the hub like a picked file (%s s)" % v["dur"], v)
    t.ok(abs(float(v["seek"]) - 3.0) < 0.2, "and the player can jump into it (%s s)" % v["seek"], v)
    t.ok(abs(float(v["mid"])) < 0.5, "half way through a move the robot is half way, eased "
         "like the firmware (%s deg off)" % v["mid"], v)
    t.ok(abs(float(v["end"])) < 0.5, "after the move it holds the move's pose", v)
    t.ok(int(v["inkEarly"]) == 0 and int(v["inkLate"]) > 50,
         "the skeleton is the one found at that moment, none where none was found", v)
    t.ok(int(v["inkOff"]) == 0, "and Skeleton off hides it", v)
    t.ok(v["plays"] == "true" and v["sound"] == "true" and abs(float(v["moved"])) > 2,
         "Play plays the video with its sound and the robot moves along (%s deg)" % v["moved"], v)
    t.ok(v["back"] == "true" and v["pageOff"] == "true", "closing the page gives the editor its pose back", v)
    t.ok(v["onBar"] == "2" and v["soundBox"] == "true", "the moves go on the time bar", v)
    music = [f["n"] for f in fake_serial.SD_DIRS.get("/music", [])]
    t.ok(v["cue"] != "none" and v["cue"] in music,
         "the video's sound reaches the robot's card and is the first move's music (%s)" % v["cue"],
         {"cue": v["cue"], "card": music, "said": v.get("stat")})
    proj = main.PROJECTS / "qc_video_page.json"
    saved = json.loads(proj.read_text(encoding="utf-8")).get("video") if proj.is_file() else None
    t.ok(saved and saved["src"]["url"] == link and saved["mirror"] is True
         and saved["detail"] == "close" and saved["from"] == 0.5,
         "the video and its choices are saved in the project file", saved)
    t.ok(v["mirrorBack"] == "true" and v["detailBack"] == "close" and v["linkBack"] == "true",
         "and come back when the project is opened", v)
