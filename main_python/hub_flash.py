"""Flashing a board: over its cable (esptool), over WiFi (OTA), or as commands.

Moved out of main.py on 2026-09-22 (A26-93, see docs/systems/hub-flash.md).
Nothing here changed in behaviour. main.py imports these names back and calls
bind() with itself, so names that still live there (dev_cmd, show,
FIRMWARE_DIR, PORT) are read late - a check that swaps main.dev_cmd reaches
this code too.
"""
import base64
import hashlib
import json
import re
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from hub_usb import _flash_ports, _usb_ident, _usb_touch, usb_close, usb_free

_hub = None                  # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub

#
# The hub already knows which module is on which cable, and since the firmware
# is built per module type there is a right answer to "which binary does this
# board get". So: pick a type, and the hub writes it.
#
# THE CABLE IS THE WHOLE PROBLEM. A COM port belongs to one program at a time,
# and the hub is normally that program — it holds every port open and shares it
# between its pages. esptool needs the port to ITSELF. Every "port is busy"
# failure on the bench was this. So a flash: stops the hub's show player if it
# is driving that port, closes the handle, and marks the port off-limits until
# esptool is finished (see _flash_ports, honoured by _usb_get and the probe).
#
# Where the images come from: `pio run -e mice_<type>` writes them into
# firmware/.pio/build/<env>/. Nothing is downloaded and nothing is bundled yet,
# so a PC that has never built the firmware is told exactly that instead of
# being offered a button that cannot work.
PIO_HOME = Path.home() / ".platformio"
BOOT_APP0 = (PIO_HOME / "packages" / "framework-arduinoespressif32" /
             "tools" / "partitions" / "boot_app0.bin")

# offset -> which file, exactly as PlatformIO's own upload does it
FLASH_PARTS = (("0x1000", "bootloader.bin"), ("0x8000", "partitions.bin"),
               ("0xe000", None), ("0x10000", "firmware.bin"))  # None = boot_app0


_flash_lock = threading.Lock()


def flash_env(module_type):
    return "mice_" + re.sub(r"[^a-z0-9_]", "", (module_type or "").lower())


def flash_image(module_type):
    """What flashing this type would write — and what is missing if it can't."""
    env = flash_env(module_type)
    d = _hub.FIRMWARE_DIR / ".pio" / "build" / env
    parts, missing, built, total = [], [], 0, 0
    for off, name in FLASH_PARTS:
        f = BOOT_APP0 if name is None else (d / name)
        if f.is_file():
            parts.append((off, str(f)))
            total += f.stat().st_size
            built = max(built, f.stat().st_mtime)
        else:
            missing.append(name or "boot_app0.bin")
    # TWO kinds of ready, because the two ways of writing a board need
    # different things. A cable write runs esptool and needs every part - the
    # bootloader and the partition table included. An OTA sends ONE file, the
    # app image, because that is all a running board can accept. A PC that was
    # handed firmware.bin (rather than building it) can do the second and not
    # the first, and that is a normal, useful state - it was reported as
    # "nothing built here" until 2026-08-19.
    app = any(q.endswith("firmware.bin") for _off, q in parts)
    return {"type": module_type, "env": env, "dir": str(d),
            "ready": not missing, "ota_ready": app,
            "missing": missing, "parts": parts,
            "bytes": total, "built_at": int(built)}


def flash_images():
    """Every module type this PC could flash right now.

    The list comes from firmware/config/modules.json — the one file that
    declares what a board can be — plus `blank`, which is the fallback built
    into every firmware rather than a module of its own. Adding a module type
    therefore makes it appear here with nothing to change on this side.
    """
    types = list(_hub.registry.modules()) if _hub.registry else ["nong", "lift"]
    types.append("blank")
    return [{k: v for k, v in im.items() if k != "parts"}
            for im in (flash_image(t) for t in types)]


def send_firmware(to, port, module_type, user, password):
    """Give this PC's firmware to the hub holding the cable, and let it write.

    The image travels; the command does not. This hub does the sending rather
    than the browser because the session cookie is SameSite=Lax: a POST from
    this page straight to another hub carries no cookie and is refused.

    It logs in as the operator each time and keeps nothing. A hub never stores
    another hub's password — the person typing it is the one authorised on
    that machine, and that is the whole point of the gate.
    """
    import base64
    if not to:
        raise ValueError("which PC? name the hub holding the cable")
    im = flash_image(module_type)
    if not im["ready"]:
        raise RuntimeError(
            "no %s firmware on THIS PC to send (missing %s). Build it first: "
            "pio run -e %s" % (module_type, ", ".join(im["missing"]), im["env"]))
    payload = {"port": port, "type": module_type, "from": socket.gethostname(),
               "parts": [{"off": off, "name": Path(p).name,
                          "b64": base64.b64encode(Path(p).read_bytes()).decode()}
                         for off, p in im["parts"]]}

    base = "http://%s:%d" % (to, _hub.PORT)
    cookie = ""
    if user or password:
        req = urllib.request.Request(
            base + "/api/login", method="POST",
            data=json.dumps({"user": user, "password": password}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            answer = json.loads(r.read().decode(errors="replace"))
            if not answer.get("ok"):
                raise RuntimeError("%s refused that login" % to)
            cookie = (r.headers.get("Set-Cookie") or "").split(";")[0]

    req = urllib.request.Request(
        base + "/api/flash/remote", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Cookie": cookie} if cookie else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read().decode(errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(
                "%s wants a login before it will overwrite a board" % to) from e
        # Say what the OTHER PC said. Without this the operator is told the
        # number 400 about a machine they are not sitting at.
        why = ""
        try:
            why = (json.loads(e.read().decode(errors="replace")) or {}).get("error", "")
        except Exception:                     # noqa: BLE001 - a reason is a bonus
            pass
        raise RuntimeError("%s refused it: %s" % (to, why or e.reason)) from e
    out["to"] = to
    out["bytes"] = im["bytes"]
    return out


def esptool_cmd():
    """The command that runs esptool, or None with the reason it cannot.

    Not a pip dependency: the hub stays stdlib-only. PlatformIO already ships
    esptool, so if the firmware can be built on this PC it can also be flashed
    from here. MICE_ESPTOOL overrides it (a full command line), which is also
    how QC drives this path without touching a real board.
    """
    import os
    override = os.environ.get("MICE_ESPTOOL")
    if override:
        import shlex
        # posix=False on Windows, or shlex eats the backslashes in a path and
        # C:\Users\me\esptool.py silently becomes C:Usersmeesptool.py
        parts = shlex.split(override, posix=(os.name != "nt"))
        return [p.strip('"') for p in parts], ""
    esp = PIO_HOME / "packages" / "tool-esptoolpy" / "esptool.py"
    if not esp.is_file():
        return None, ("esptool was not found. It comes with PlatformIO — "
                      "install PlatformIO, or build the firmware once, and it "
                      "will be at %s" % esp)
    # A frozen hub cannot run itself as a python interpreter, so use
    # PlatformIO's own python when there is no real one to hand.
    py = PIO_HOME / "penv" / "Scripts" / "python.exe"
    if not py.is_file():
        py = PIO_HOME / "penv" / "bin" / "python"
    if getattr(sys, "frozen", False):
        if not py.is_file():
            return None, ("no python to run esptool with — PlatformIO's is "
                          "usually at %s" % py)
        return [str(py), str(esp)], ""
    return [str(py if py.is_file() else sys.executable), str(esp)], ""


class Flasher:
    """One flash at a time, on one cable, reported honestly."""

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.port = ""
        self.type = ""
        self.percent = 0
        self.stage = ""
        self.how = ""             # "usb" (esptool) or "wifi" (OTA)
        self.log = []
        self.ok = None            # None = running, True/False = finished
        self.error = ""

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def _claim(self, port, module_type, how, target=None, args=(), stage=""):
        """Take the job and START it, or refuse - ALL UNDER ONE LOCK.

        Every start path used to test running() outside the lock and set the
        fields after it. Two POSTs in that window - a double click, or two
        tabs - both passed the test and both spawned a thread, so two writers
        drove one shared job and each overwrote the other's progress. The GET
        showed whichever wrote last and neither caller was told. Found
        2026-08-21. Starting the thread here closes the same gap that remained
        between claim returning and the thread object being assigned.
        """
        with self.lock:
            if self.running():
                raise RuntimeError("already flashing %s - one board at a time"
                                   % (self.port or self.type))
            self.port, self.type, self.how = port, module_type, how
            self.percent, self.stage, self.log = 0, stage or "starting", []
            self.ok, self.error = None, ""
            if target:
                self.thread = threading.Thread(target=target, args=args,
                                               daemon=True)
                self.thread.start()

    def status(self):
        with self.lock:
            return {"running": self.running(), "port": self.port,
                    "type": self.type, "percent": self.percent,
                    "stage": self.stage, "ok": self.ok, "error": self.error,
                    "how": self.how, "log": self.log[-14:]}

    # ---- over WiFi (OTA) -------------------------------------------------
    #
    # Same job, no cable. The board has two app slots (min_spiffs.csv gives
    # app0 and app1, 1.875 MB each), so the update is written to the one that
    # is NOT running: an update that fails, or a PC that walks away half way,
    # leaves the board booting the firmware it already had.
    #
    # Only firmware.bin travels. The bootloader and the partition table are the
    # parts that would brick a board if they went wrong, they almost never
    # change, and OTA cannot write them anyway — that is the point of OTA.
    def start_ota(self, ip, module_type, user="", password=""):
        im = flash_image(module_type)
        # OTA sends ONE file - the app image - because that is all a running
        # board can take: the bootloader and the partition table are written
        # by esptool over a cable and are not part of an over-the-air update.
        # So asking for all four parts here refused a PC that had exactly what
        # this needs, which is the normal case for a machine that was given the
        # images rather than building them.
        app = [q for off, q in im["parts"] if q.endswith("firmware.bin")]
        if not app:
            raise RuntimeError(
                "no %s app image on this PC. Build it with pio run -e %s, or "
                "copy firmware.bin into %s" % (module_type, im["env"], im["dir"]))
        if not ip:
            raise RuntimeError("which module? this needs its WiFi address")
        self._claim(ip, module_type, "wifi", self._run_ota,
                    (ip, im, user, password))
        return self.status()

    # The board wants a session before it will take firmware, and it is right
    # to: /api/ota replaces the program on a machine anyone on the venue WiFi
    # can reach. Measured on board 42 over real WiFi, 2026-08-21:
    # `401 ERR log in first`. Before the gate moved into the body handler
    # (A18-1) the board wrote the image and refused afterwards, so this was
    # broken the whole time and looked like it worked.

    def _board_session(self, ip, user, password):
        """Log in to a board. -> (cookie, why). One body, shared with dev_cmd."""
        return _hub.board_login(ip, user, password)

    def _run_ota(self, ip, im, user="", password=""):
        import http.client
        try:
            path = [p for off, p in im["parts"] if p.endswith("firmware.bin")][0]
            data = Path(path).read_bytes()
            cookie, why = self._board_session(ip, user, password)
            # An empty reason with no cookie is the ONE case that goes on: a
            # board too old to have a login at all (see _board_session).
            if not cookie and why:
                with self.lock:
                    self.ok, self.stage, self.error = False, "failed", why
                self._say(why)
                return
            self._say("%s %s; sending %s (%.2f MB) over WiFi"
                      % ("logged in to" if cookie else
                         "no login on (old firmware)", ip,
                         Path(path).name, len(data) / 1048576.0))
            b = "----miceota"
            head = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
                    "filename=\"firmware.bin\"\r\nContent-Type: "
                    "application/octet-stream\r\n\r\n" % b).encode()
            tail = ("\r\n--%s--\r\n" % b).encode()
            conn = http.client.HTTPConnection(ip, timeout=90)
            # The board REQUIRES the md5 now: with UPDATE_SIZE_UNKNOWN and
            # nothing registered, its end(true) verified nothing, so a
            # dropped connection booted a half-written image.
            conn.putrequest("POST", "/api/ota?md5=" +
                            hashlib.md5(data).hexdigest())    # noqa: S324
            conn.putheader("Content-Type", "multipart/form-data; boundary=" + b)
            conn.putheader("Content-Length", str(len(head) + len(data) + len(tail)))
            if cookie:
                conn.putheader("Cookie", "%s=%s" % (_hub.BOARD_COOKIE, cookie))
            conn.endheaders()
            conn.send(head)
            with self.lock:
                self.stage = "writing"
            CH = 4096
            for i in range(0, len(data), CH):
                conn.send(data[i:i + CH])
                with self.lock:
                    self.percent = int((i + CH) * 100 / max(1, len(data)))
            conn.send(tail)
            resp = conn.getresponse()
            body = resp.read().decode(errors="replace").strip()
            self._say("%d %s" % (resp.status, body[:200]))
            with self.lock:
                self.ok = (resp.status == 200)
                self.percent = 100 if self.ok else self.percent
                self.stage = "restarting the board" if self.ok else "failed"
                if not self.ok:
                    # the board's own words: it says "the module is moving",
                    # "a sequence is playing" or what the flash write hit
                    self.error = body[:200] or ("the module answered %d" % resp.status)
        except Exception as e:            # noqa: BLE001
            with self.lock:
                self.ok, self.stage = False, "failed"
                self.error = ("%s — is it on WiFi, and does its firmware have "
                              "OTA? (OTA over the cable first, once)" % e)

    # ---- over the COMMAND CHANNEL, whatever that channel is --------------
    #
    # The third way, and the only one that works on a two-wire bus. Asked for
    # 2026-08-20: *make it can flash through all this 3 method too if i need to
    # shieft to stm 32 it cannot use wifi it can use only rs485*.
    #
    # Why the other two cannot do it:
    #   * esptool reaches the ROM bootloader by pulling EN and IO0 with DTR and
    #     RTS. RS485 is two differential wires and has neither, so no amount of
    #     work on the hub side gets there;
    #   * the WiFi updater posts to the board's own web server, which a board
    #     with no radio does not have.
    # Both of those are ways of getting an image IN. This one is the board
    # writing its own spare OTA slot from ordinary command lines, so the link
    # underneath stops mattering — and `dev_cmd` already speaks every one of
    # them, including a module behind another module's hotspot and a module on
    # another PC's cable.
    #
    # It is SLOW: 150 bytes a chunk (see BusUpdate.h — an RS485 line is capped
    # at 250 characters and base64 costs a third), so a 1.3 MB image is around
    # nine thousand round trips. Six minutes on a cable, longer on the bus. That
    # is the price of not having a reset line, and it is paid rarely.
    BUS_CHUNK = 150

    def start_bus(self, dev, module_type):
        im = flash_image(module_type)
        app = [q for off, q in im["parts"] if q.endswith("firmware.bin")]
        if not app:
            raise RuntimeError(
                "no %s app image on this PC. Build it with pio run -e %s, or "
                "copy firmware.bin into %s" % (module_type, im["env"], im["dir"]))
        if not dev:
            raise RuntimeError("which module? this needs its dev address")
        self._claim(dev, module_type, "bus", self._run_bus, (dev, app[0]))
        return self.status()

    def _run_bus(self, dev, path):
        try:
            data = Path(path).read_bytes()
            total = len(data)
            digest = hashlib.md5(data).hexdigest()          # noqa: S324
            self._say("sending %s (%.2f MB) to %s as commands"
                      % (Path(path).name, total / 1048576.0, dev))

            # Ask FIRST whether it fits. The board answers from its real
            # partition table, so "no room" arrives before a single byte is
            # written rather than half way through, when the running firmware
            # is already gone.
            # 30 s, for the same reason FWEND gets 60: this is not a question,
            # it is work. Reserving the slot erases it, and erasing most of two
            # megabytes of flash is seconds, not milliseconds. Timing out here
            # would report a failed update before a single byte was sent —
            # while the board was busy doing exactly what it was asked.
            reply = (_hub.dev_cmd(dev, "FWBEGIN %d %s" % (total, digest),
                             wait=30) or "").strip()
            if not reply.startswith("OK"):
                raise RuntimeError(reply or "the board did not answer FWBEGIN")
            with self.lock:
                self.stage = "writing"

            seq, sent = 0, 0
            while sent < total:
                piece = data[sent:sent + self.BUS_CHUNK]
                # The LENGTH is on the wire because a truncated line is still
                # legal base64. Measured 2026-08-20 on a 1.29 MB image over a
                # cable: one chunk in nine thousand lost 64 characters, decoded
                # cleanly to 102 bytes instead of 150, and nothing noticed until
                # FWEND counted the image 48 bytes short — four minutes gone,
                # with no way to tell which chunk did it.
                line = "FWDATA %d %d %s" % (seq, len(piece),
                                            base64.b64encode(piece).decode())
                # A LOST LINE IS RETRIED, NOT SKIPPED. The board refuses a chunk
                # that is not the one it expects and says which one it wants, so
                # a dropped reply costs a repeat and never a hole in the image.
                # Silently carrying on is how a board ends up booting rubbish.
                for attempt in range(4):
                    try:
                        ans = (_hub.dev_cmd(dev, line) or "").strip()
                    except Exception as e:                    # noqa: BLE001
                        # A LOST REPLY IS THE ORDINARY CASE ON A BUS, and
                        # dev_cmd reports it by raising. Letting that escape
                        # would end the whole update on the first dropped line
                        # — nine thousand chunks means even a rare loss is
                        # near-certain, so retrying has to survive an exception
                        # and not merely an ERR string.
                        ans = "no answer (%s)" % str(e)[:80]
                    if ans.startswith("OK"):
                        break
                    if "expected" in ans:
                        want = re.search(r"expected (\d+)", ans)
                        if want and int(want.group(1)) == seq + 1:
                            break     # it took this one; only the reply was lost
                    # "chunk short" and "not valid base64" both mean the line
                    # was damaged in flight and the board did NOT advance, so
                    # the same chunk goes again — this is the self-healing case
                    # and it must not be mistaken for a hard refusal.
                    if attempt == 3:
                        raise RuntimeError(
                            "chunk %d would not go: %s" % (seq, ans or "no answer"))
                seq += 1
                sent += len(piece)
                # THE BOARD'S OWN RUNNING TOTAL, checked rather than ignored.
                # It is already on the wire in every OK reply, and comparing it
                # turns any remaining drift into an error at the chunk that
                # caused it instead of a mystery at the end of the transfer.
                said = re.match(r"OK \d+ (\d+)", ans)
                if said and int(said.group(1)) != sent:
                    raise RuntimeError(
                        "the board has %s bytes after chunk %d but %d were sent "
                        "— stopping rather than finishing an image that would "
                        "not match" % (said.group(1), seq - 1, sent))
                with self.lock:
                    self.percent = int(sent * 100 / total)

            with self.lock:
                self.stage = "checking the image"
            # FWEND is where a wrong image is caught, while the board is still
            # running firmware that works. Only then does it reboot.
            # 60 s, not the usual 2: the board hashes the whole image before it
            # will boot into it, and reporting a timeout here would mean an
            # operator reflashing a board that had in fact just succeeded.
            reply = (_hub.dev_cmd(dev, "FWEND", wait=60) or "").strip()
            with self.lock:
                self.ok = reply.startswith("OK")
                self.percent = 100 if self.ok else self.percent
                self.stage = "restarting the board" if self.ok else "failed"
                if not self.ok:
                    self.error = reply[:200] or "the board did not answer FWEND"
            self._say(reply[:200])
        except Exception as e:            # noqa: BLE001
            try:
                _hub.dev_cmd(dev, "FWABORT")   # leave it running what it had
            except Exception:             # noqa: BLE001, S110
                pass
            with self.lock:
                self.ok, self.stage = False, "failed"
                self.error = ("%s — the board keeps the firmware it already "
                              "had; nothing was switched over" % e)

    def start(self, port, module_type):
        im = flash_image(module_type)
        if not im["ready"]:
            raise RuntimeError(
                "no %s firmware on this PC (missing %s). Build it first: "
                "pio run -e %s" % (module_type, ", ".join(im["missing"]), im["env"]))
        cmd, why = esptool_cmd()
        if not cmd:
            raise RuntimeError(why)
        if not port:
            raise RuntimeError("which port? pick the cable the board is on")
        self._claim(port, module_type, "usb", self._run, (cmd, im))
        return self.status()

    def start_received(self, port, module_type, parts, who):
        """Flash an image that came from another PC over the network.

        Same writer as a local flash — the only difference is where the bytes
        came from, so the progress, the log and the one-cable-at-a-time rule
        are shared rather than reimplemented. The files land in a temp folder
        that is removed when the write finishes, however it finishes: a failed
        flash must not leave a stale firmware on disk for the next one to pick
        up by mistake.
        """
        import base64
        import tempfile
        cmd, why = esptool_cmd()
        if not cmd:
            raise RuntimeError(why)
        if not port:
            raise RuntimeError("which port? name the cable the board is on")
        if not parts:
            raise RuntimeError("no firmware arrived")
        # The port is about to become an argument to esptool. Nothing that
        # is not a port shape gets that far.
        if not re.fullmatch(r"(COM\d+|/dev/[\w./-]+)", port):
            raise ValueError("%s is not a serial port" % port)
        d = Path(tempfile.mkdtemp(prefix="mice_fw_"))
        got = []
        try:
            for i, p in enumerate(parts):
                # A name is a NAME: no folders, and never empty, or the write
                # lands on the temp folder itself.
                name = Path(str(p.get("name", ""))).name or ("part%d.bin" % i)
                f = d / name
                f.write_bytes(base64.b64decode(p.get("b64", "")))
                # Offsets travel as they are written everywhere else here -
                # 0x1000, not 4096 - so they are read in whatever base they
                # arrive in and handed to esptool in the same form.
                got.append((str(p.get("off", "0")), str(f)))
        except Exception:
            # Nothing has been started yet, so the folder is ours to remove.
            # Leaving it behind on a bad payload is a slow disk leak that only
            # shows up on the PC at the venue.
            shutil.rmtree(d, ignore_errors=True)
            raise
        got.sort(key=lambda pair: int(str(pair[0]), 0))   # by address, not by spelling
        im = {"type": module_type, "parts": got, "ready": True,
              "from": who, "tmp": str(d)}
        try:
            self._claim(port, module_type, "usb", self._run, (cmd, im),
                        stage="receiving from " + who)
        except Exception:
            # Usually "already flashing": the write never started, so nobody
            # owns the folder yet - same rule as the bad-payload path above.
            shutil.rmtree(d, ignore_errors=True)
            raise
        return self.status()

    def _say(self, line):
        with self.lock:
            self.log.append(line)
            m = re.search(r"\((\d+)\s*%\)", line)
            if m:
                self.percent = int(m.group(1))
            low = line.lower()
            for word, stage in (("connecting", "connecting to the board"),
                                ("erasing", "erasing"), ("writing at", "writing"),
                                ("hash of data verified", "verified"),
                                ("hard resetting", "restarting the board")):
                if word in low:
                    self.stage = stage

    def _run(self, cmd, im):
        port = self.port
        try:
            # Give the cable up completely. The hub is the port's owner, so
            # nothing else can do this for us — and esptool cannot share.
            if _hub.show.running():
                try:
                    k, a, b, _p = _hub.parse_dev(_hub.show.dev)
                    if k == "usb" and a == port:
                        _hub.show.stop(freeze=False, why="the board is being flashed")
                except Exception:      # noqa: BLE001
                    pass
            with _flash_lock:
                _flash_ports.add(port)
            # WAIT UNTIL THE CABLE IS REALLY OURS TO GIVE UP. usb_close does
            # not close a port somebody is mid-command on - it puts it back, on
            # purpose - so calling it once and sleeping 300ms was a guess.
            # esptool then met a handle that was still open and died at
            # whatever percent it had reached, leaving the board in the
            # bootloader answering nothing. Measured at the bench 2026-08-20:
            # 21%, "the chip stopped responding".
            deadline = time.time() + 12
            while True:
                usb_close(port)
                _usb_touch.pop(port, None)
                _usb_ident.pop(port, None)   # whatever it was, it is about to change
                if usb_free(port):
                    break
                if time.time() > deadline:
                    raise RuntimeError(
                        "%s is still in use by this hub after 12s - something "
                        "is mid-command on it. Close the module page or Studio "
                        "tab using that cable and try again." % port)
                time.sleep(0.5)
            time.sleep(0.3)                # let Windows actually release the handle

            args = list(cmd) + ["--chip", "esp32", "--port", port,
                                "--baud", "460800", "write_flash", "-z",
                                "--flash_mode", "dio", "--flash_freq", "40m",
                                "--flash_size", "detect"]
            for off, path in im["parts"]:
                args += [off, path]
            self._say("$ esptool " + " ".join(args[2:]))
            import subprocess
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 errors="replace", bufsize=1,
                                 creationflags=_hub.NO_WINDOW)
            for line in p.stdout:
                line = line.rstrip()
                if line:
                    self._say(line)
            code = p.wait()
            with self.lock:
                self.ok = (code == 0)
                self.percent = 100 if self.ok else self.percent
                self.stage = "done" if self.ok else "failed"
                if not self.ok:
                    self.error = self._why_failed()
        except Exception as e:            # noqa: BLE001
            with self.lock:
                self.ok, self.error, self.stage = False, str(e), "failed"
        finally:
            with _flash_lock:
                _flash_ports.discard(port)
            # An image that arrived from another PC lives in a temp folder.
            # Remove it whether the write worked or not: leaving firmware on
            # disk invites the next flash to pick up bytes nobody chose.
            if im.get("tmp"):
                import shutil
                shutil.rmtree(im["tmp"], ignore_errors=True)

    def _why_failed(self):
        """The one line worth reading, in words that say what to do."""
        text = "\n".join(self.log).lower()
        if "failed to connect" in text or "no serial data" in text:
            return ("the board did not answer. Hold its BOOT/IO0 button while "
                    "the flash starts, or check the cable is a data cable.")
        if "access is denied" in text or "could not open" in text or "busy" in text:
            return ("%s is held by another program — close any serial monitor, "
                    "Arduino IDE or Studio 'USB direct' tab, then try again"
                    % self.port)
        for line in reversed(self.log):
            if "error" in line.lower() or "fatal" in line.lower():
                return line.strip()[:200]
        return "esptool failed — see the log"
