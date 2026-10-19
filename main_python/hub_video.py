"""Videos from a link for Studio's Moves from a video page (A44-8).

User 2026-10-19: a YouTube link, a Google Drive link or another link should
work like a picked file. A browser cannot read the picture of a video another
site plays (it is locked to that site), so the hub fetches the video onto this
PC and serves it from its own address, where Studio may read every frame.

One fetch: a share link (Drive, Dropbox) becomes its download address
(config/video_links.json `shares`); an address that answers with a video is
saved as it comes; anything else is a page, handed to yt-dlp. What went wrong
is said in plain words (`say`), with the program's own line kept for the
technical view. Files live in the PC's temp folder, never in the repo, and
only the newest `keep` stay.
"""
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
         ".mkv": "video/x-matroska", ".mov": "video/quicktime", ".ogv": "video/ogg",
         ".mp3": "audio/mpeg"}
EXT_OF = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
          "video/x-matroska": ".mkv", "video/ogg": ".ogv"}


def _sniff(head):
    """The file's own first bytes: mp4/mov carry `ftyp`, webm/mkv the EBML mark.
    A Drive or Dropbox answer says application/octet-stream whatever it holds."""
    if head[4:8] == b"ftyp":
        return ".mp4"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    return ""


class Links:
    def __init__(self, cfg_path, folder=None):
        self.cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        self.dir = Path(folder or Path(tempfile.gettempdir()) / "mice_video")
        self.jobs = {}
        self.lock = threading.Lock()
        self._ytdlp = None          # the command that answered, once found
        # QC swaps this: the yt-dlp step without the internet
        self.run_ytdlp = self._run_ytdlp

    # ---- words ---------------------------------------------------------
    def say(self, tech):
        low = str(tech).lower()
        for s in self.cfg["say"]:
            if any(h in low for h in s["has"]):
                return s["say"]
        return "This link could not be read. The technical view has what the site answered."

    def _fail(self, job, words, tech=""):
        job.update(state="failed", error=words, tech=str(tech)[-600:])

    # ---- jobs ----------------------------------------------------------
    def start(self, url):
        """A new fetch, or the finished one for the same link."""
        url = (url or "").strip()
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return None, "That is not a web link. Paste one that starts with https://"
        with self.lock:
            for jid, j in self.jobs.items():
                if j["url"] == url and j["state"] in ("working", "done") and \
                        (j["state"] == "working" or Path(j["file"]).is_file()):
                    return jid, ""
            jid = secrets.token_hex(8)
            self.jobs[jid] = {"url": url, "state": "working", "pct": 0, "title": "",
                              "file": "", "error": "", "tech": "", "how": "",
                              "started": time.time(), "stop": False, "proc": None}
        threading.Thread(target=self._fetch, args=(jid,), daemon=True).start()
        return jid, ""

    def status(self, jid):
        j = self.jobs.get(jid)
        if not j:
            return None
        out = {k: j[k] for k in ("state", "pct", "title", "error", "tech", "how")}
        f = Path(j["file"]) if j["state"] == "done" else None
        out["size"] = f.stat().st_size if f and f.is_file() else 0
        return out

    def cancel(self, jid):
        j = self.jobs.get(jid)
        if not j or j["state"] != "working":
            return False
        j["stop"] = True
        if j["proc"]:
            try:
                j["proc"].kill()
            except OSError:
                pass
        return True

    def path_of(self, jid, kind=""):
        j = self.jobs.get(jid)
        if not j or j["state"] != "done":
            return None
        f = j.get("sound") if kind == "sound" else j["file"]
        return Path(f) if f and Path(f).is_file() else None

    def _new_file(self, jid, ext):
        self.dir.mkdir(parents=True, exist_ok=True)
        keep = int(self.cfg.get("keep") or 6)
        old = sorted((f for f in self.dir.iterdir() if f.is_file()),
                     key=lambda f: f.stat().st_mtime, reverse=True)
        # only a fetch still running is spared; a done one is fetched again if asked
        busy = {Path(j["file"]).name for j in self.jobs.values()
                if j["file"] and j["state"] == "working"}
        for f in old[keep * 2:]:          # a video and its sound count as one
            if f.name not in busy:
                try:
                    f.unlink()
                except OSError:
                    pass
        return self.dir / (jid + ext)

    # ---- one fetch -----------------------------------------------------
    def _fetch(self, jid):
        j = self.jobs[jid]
        try:
            direct, share = j["url"], None
            for s in self.cfg["shares"]:
                m = re.search(s["match"], direct)
                if m:              # the share page's address -> its download address
                    share, direct = s, m.expand(s["direct"])
                    break
            j["how"] = share["label"] if share else ""
            got = self._plain(jid, direct, share)
            if got == "page" and not j["stop"]:
                j["how"] = j["how"] or "yt-dlp"
                self.run_ytdlp(jid)
        except Exception as e:                        # noqa: BLE001 - said, never thrown
            self._fail(j, self.say(e), "%s: %s" % (type(e).__name__, e))
        if j["stop"] and j["state"] == "working":
            self._fail(j, "Stopped.")
        j["proc"] = None

    def _plain(self, jid, url, share):
        """Save it if the address answers with a video; "page" if it is a page."""
        j = self.jobs[jid]
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            r = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            if share:
                return self._fail(j, share["html"], "HTTP %s" % e.code)
            return "page"        # a site that refuses plain readers may still let yt-dlp in
        except (urllib.error.URLError, OSError) as e:
            return self._fail(j, self.say(e), str(e))
        with r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            head = r.read(16)
            ext = EXT_OF.get(ctype) or _sniff(head)
            if not ext:
                if share:
                    return self._fail(j, share["html"], "the link answered " + (ctype or "no type"))
                if ctype.startswith("audio/"):
                    return self._fail(j, "This link is sound only. Moves need a video of a person.", ctype)
                return "page"
            name = re.findall(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', r.headers.get("Content-Disposition") or "")
            j["title"] = urllib.parse.unquote(name[0]) if name else \
                urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name) or "video"
            total = int(r.headers.get("Content-Length") or 0)
            cap = int(self.cfg.get("maxMB") or 800) << 20
            if total > cap:
                return self._fail(j, self.say("too big"), "%d MB" % (total >> 20))
            dest = self._new_file(jid, ext)
            part = dest.with_name(dest.name + ".part")
            n = len(head)
            with open(part, "wb") as f:
                f.write(head)
                while not j["stop"]:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    n += len(chunk)
                    if n > cap:
                        f.close()
                        part.unlink()
                        return self._fail(j, self.say("too big"), "over %d MB" % (cap >> 20))
                    f.write(chunk)
                    if total:
                        j["pct"] = round(100 * n / total)
            if j["stop"]:
                part.unlink()
                return None
            part.replace(dest)
            j.update(file=str(dest), pct=100, state="done")
        return None

    # ---- yt-dlp ----------------------------------------------------------
    def ytdlp(self):
        """The yt-dlp command that answers on this PC, or None."""
        if self._ytdlp:
            return self._ytdlp
        py = "" if getattr(sys, "frozen", False) else sys.executable
        for cmd in self.cfg["ytdlp"]["run"]:
            cmd = [py if a == "{python}" else a for a in cmd]
            if not cmd[0] or not shutil.which(cmd[0]):
                continue
            try:
                r = subprocess.run(cmd + ["--version"], capture_output=True, text=True,
                                   timeout=30, creationflags=NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if r.returncode == 0 and r.stdout.strip():
                self._ytdlp = [shutil.which(cmd[0])] + cmd[1:]
                return self._ytdlp
        return None

    def ffmpeg(self):
        cmd = list(self.cfg.get("ffmpeg") or ["ffmpeg"])
        found = shutil.which(cmd[0])
        return [found] + cmd[1:] if found else None

    def _run_ytdlp(self, jid):
        j = self.jobs[jid]
        cmd = self.ytdlp()
        if not cmd:
            return self._fail(j, "This PC cannot read links from video sites yet: yt-dlp is not "
                                 "installed. On the PC run:  " + self.cfg["ytdlp"]["install"],
                              "no yt-dlp on PATH")
        y = self.cfg["ytdlp"]
        ff = self.ffmpeg()
        h = str(int(self.cfg.get("height") or 720))
        fmt = (y["merge"] if ff else y["single"]).replace("{h}", h)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._new_file(jid, "")
        args = cmd + ["--no-playlist", "--no-mtime", "--newline", "--progress",
                      "-f", fmt, "--max-filesize", "%dM" % int(self.cfg.get("maxMB") or 800),
                      "-o", str(self.dir / (jid + ".%(ext)s")),
                      "--no-simulate",
                      "--print", "before_dl:MICETITLE %(title)s",
                      "--print", "after_move:MICEFILE %(filepath)s",
                      "--progress-template", "download:MICEPCT %(progress._percent_str)s"]
        if ff:
            args += ["--merge-output-format", "mp4", "--ffmpeg-location", ff[0]]
        for rt in y.get("jsRuntimes") or []:
            if shutil.which(rt):
                args += ["--js-runtimes", rt]
        args += list(y.get("args") or [])
        args.append(j["url"])
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             creationflags=NO_WINDOW)
        j["proc"] = p
        timer = threading.Timer(60 * int(self.cfg.get("minutes") or 15), p.kill)
        timer.start()
        lines, path = [], ""
        try:
            for line in p.stdout:
                line = line.strip()
                if line.startswith("MICEPCT"):
                    m = re.search(r"([\d.]+)%", line)
                    if m:
                        j["pct"] = min(99, round(float(m.group(1))))
                elif line.startswith("MICETITLE "):
                    j["title"] = line[10:]
                elif line.startswith("MICEFILE "):
                    path = line[9:]
                elif line:
                    lines.append(line)
            p.wait()
        finally:
            timer.cancel()
        if j["stop"]:
            return None
        errs = [x for x in lines if x.startswith("ERROR")] or lines[-3:]
        if p.returncode != 0 or not path or not Path(path).is_file():
            tech = " | ".join(errs) or "yt-dlp stopped (%s)" % p.returncode
            return self._fail(j, self.say(tech), tech)
        j.update(file=path, pct=100, state="done")
        return None

    # ---- a picked file, and the sound for the robot ------------------------
    def put(self, read, n, name):
        """A video picked in the browser, kept here so its sound can be made."""
        cap = int(self.cfg.get("maxMB") or 800) << 20
        if n > cap:
            raise ValueError(self.say("too big"))
        ext = Path(name or "").suffix.lower()
        jid = secrets.token_hex(8)
        dest = self._new_file(jid, ext if ext in TYPES else ".mp4")
        left = n
        with open(dest, "wb") as f:
            while left > 0:
                chunk = read(min(left, 1 << 16))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        with self.lock:
            self.jobs[jid] = {"url": "", "state": "done", "pct": 100, "title": name or "video",
                              "file": str(dest), "error": "", "tech": "", "how": "file",
                              "started": time.time(), "stop": False, "proc": None}
        return jid

    def sound(self, jid, start, end):
        """(mp3 path, words): the part of the video the moves were made from,
        so the robot's music starts with the first move."""
        src = self.path_of(jid)
        if not src:
            return None, "That video is no longer on this PC. Fetch or pick it again."
        ff = self.ffmpeg()
        if not ff:
            return None, ("This PC cannot take the sound out of a video yet: ffmpeg is not "
                          "installed. On the PC run:  winget install ffmpeg")
        out = src.with_name("%s_%d_%d.mp3" % (jid, round(start * 10), round(end * 10)))
        if not out.is_file():
            cut = ["-ss", "%.2f" % max(0.0, start)] + (["-to", "%.2f" % end] if end > start else [])
            r = subprocess.run(ff + ["-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
                               + cut + ["-vn", "-ac", "2", "-ar", "44100", "-b:a", "128k", str(out)],
                               capture_output=True, text=True, timeout=300,
                               creationflags=NO_WINDOW)
            if r.returncode != 0 or not out.is_file():
                return None, "The sound could not be taken out of this video (it may have none)."
        self.jobs[jid]["sound"] = str(out)
        return out, ""


def send_file(h, f, ctype):
    """A video to the browser, with Range: seeking a <video> asks for a part of
    the file, and an answer without 206 leaves it unable to jump at all."""
    size = f.stat().st_size
    start, end, code = 0, size - 1, 200
    m = re.match(r"bytes=(\d*)-(\d*)$", (h.headers.get("Range") or "").strip())
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            start = int(m.group(1))
            end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
        else:
            start = max(0, size - int(m.group(2)))
        if start > end or start >= size:
            h.send_response(416)
            h.send_header("Content-Range", "bytes */%d" % size)
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        code = 206
    h.send_response(code)
    h.send_header("Content-Type", ctype)
    h.send_header("Accept-Ranges", "bytes")
    h.send_header("Content-Length", str(end - start + 1))
    if code == 206:
        h.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    if h.command == "HEAD":
        return
    with open(f, "rb") as fh:
        fh.seek(start)
        left = end - start + 1
        try:
            while left > 0:
                chunk = fh.read(min(left, 1 << 16))
                if not chunk:
                    break
                h.wfile.write(chunk)
                left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            h.close_connection = True   # the player jumped elsewhere mid-part
