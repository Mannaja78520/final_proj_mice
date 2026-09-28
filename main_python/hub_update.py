"""Self-update from the app branch, and the diagnostics text for support.

Moved out of main.py on 2026-09-23 (A26-93). Nothing here changed in
behaviour. main.py imports these names back and calls bind() with itself;
names that live there, and names QC swaps on main, are read late as _hub.
"""
from pathlib import Path
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


# Where the built hub is published. The `app` branch holds MiceHub.exe and
# nothing else; there are no GitHub releases, so this asks the branch.
APP_REPO = "Mannaja78520/final_proj_mice"
APP_BRANCH = "app"
APP_API = "https://api.github.com/repos/%s/commits/%s" % (APP_REPO, APP_BRANCH)
APP_RAW = "https://raw.githubusercontent.com/%s/%s/MiceHub.exe" % (APP_REPO, APP_BRANCH)


def _my_sha_file():
    """Beside the exe, so it travels with the thing it describes."""
    return Path(sys.executable).parent / "MiceHub.sha"


def update_state():
    """What is running, what is offered, and whether it may be replaced now."""
    frozen = getattr(sys, "frozen", False)
    mine = ""
    f = _my_sha_file()
    if f.is_file():
        mine = f.read_text(encoding="utf-8", errors="replace").strip()[:40]

    out = {"ok": True, "frozen": frozen, "running": mine, "offered": "",
           "when": "", "message": "", "can": False, "why": ""}
    # OLDER THAN THE SOURCE BESIDE IT is a different question from *is there a
    # newer build on GitHub*, and it is the one that bit on 2026-08-21. It is
    # answered on every branch below, including the busy ones, because a hub
    # that refuses to update right now still needs to say what it is running.
    st = _hub.build_stamp.state()
    out.update({"stale": st["stale"], "staleWhy": _hub.build_stamp.why(st),
                "rebuild": _hub.build_stamp.REBUILD, "built": st["built"],
                "changed": st["changed"]})
    if not frozen:
        out["why"] = ("this is main.py, not the built app - update it with git "
                      "pull, which also brings the firmware and the checks")
        return out
    # BUSY MEANS NO. Replacing the program mid-flash leaves a board half
    # written, and mid-show stops the installation in front of an audience.
    if _hub.flasher.running():
        out["why"] = "a board is being flashed - wait for it to finish"
        return out
    if _hub.show.running():
        out["why"] = "a show is playing - stop it first"
        return out
    try:
        req = urllib.request.Request(APP_API, headers={"Accept":
                                     "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode(errors="replace"))
        out["offered"] = (d.get("sha") or "")[:40]
        out["when"] = ((d.get("commit") or {}).get("committer") or {}).get("date", "")
        out["message"] = ((d.get("commit") or {}).get("message") or "").split("\n")[0][:90]
        out["can"] = bool(out["offered"]) and out["offered"] != mine
        if not out["can"] and out["offered"]:
            out["why"] = "this is already the newest build"
    except Exception as e:                                    # noqa: BLE001
        # No internet is the NORMAL case at a venue, so it is a plain answer
        # and not an error page.
        out["why"] = "cannot reach GitHub (%s)" % str(e)[:60]

    # THE HUB NEXT DOOR. On show day there is no internet, and the newest build
    # a PC can reach is the one on the desk beside it, not GitHub.
    near = hub_offers()
    if near and near.get("sha") and near["sha"] != mine:
        newer = (not out["offered"]) or (near.get("when", "") > out.get("when", ""))
        if newer:
            out.update({"offered": near["sha"], "when": near.get("when", ""),
                        "message": "from %s on this network" % near["host"],
                        "from": "http://%s:%d/api/app" % (near["ip"], _hub.PORT),
                        "can": True, "why": ""})
    return out


def app_here():
    """This hub's own program, if it is a built one. (path, bytes, sha) or None.

    A browser can never reach another PC's serial ports, at any address - so the
    only way that PC drives its own cables is to run this program. At a venue
    there is usually no internet, which makes the hub on the next desk the
    nearest place to get it.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable)
    if not exe.is_file():
        return None
    sha = ""
    f = _my_sha_file()
    if f.is_file():
        sha = f.read_text(encoding="utf-8", errors="replace").strip()[:40]
    return exe, exe.stat().st_size, sha


def hub_offers():
    """The newest build any OTHER hub on this network is running.

    Asked 2026-08-21. GitHub is the right source when there is internet and the
    wrong one when there is not - which is the show-day case. A hub on the same
    switch is reachable either way.
    """
    best = None
    for h in _hub.scan_hubs(False):
        ip = h.get("ip")
        if not ip or _hub.is_self(ip):
            continue
        try:
            with urllib.request.urlopen(
                    "http://%s:%d/api/app/version" % (ip, _hub.PORT), timeout=5) as r:
                d = json.loads(r.read().decode(errors="replace"))
        except Exception:                                     # noqa: BLE001
            continue                  # a closed laptop is normal, not an error
        if not d.get("sha") or not d.get("bytes"):
            continue
        d["ip"] = ip
        d["host"] = h.get("host") or ip
        if not best or (d.get("when") or "") > (best.get("when") or ""):
            best = d
    return best


def do_update():
    """Fetch the published exe and put it in place. Returns (ok, message)."""
    st = update_state()
    if not st["can"]:
        return False, st["why"] or "nothing to update"
    # Whatever update_state chose: GitHub, or the hub on the next desk.
    where = st.get("from") or APP_RAW
    try:
        with urllib.request.urlopen(where, timeout=180) as r:
            blob = r.read()
    except Exception as e:                                    # noqa: BLE001
        return False, "download failed: %s" % str(e)[:90]
    # A truncated download that overwrote the app would leave nothing to run.
    if len(blob) < 2_000_000 or blob[:2] != b"MZ":
        return False, ("that download is not a Windows program (%d bytes) - "
                       "nothing was replaced" % len(blob))
    exe = Path(sys.executable)
    old = exe.with_name("MiceHub.old.exe")
    try:
        old.unlink(missing_ok=True)
        # Windows will not overwrite a RUNNING exe, but it will rename one.
        # The old file stays as the way back if the new one will not start.
        exe.rename(old)
        exe.write_bytes(blob)
        _my_sha_file().write_text(st["offered"], encoding="utf-8")
    except OSError as e:
        return False, "could not replace the program: %s" % str(e)[:90]
    return True, ("updated to %s - close this window and start MiceHub.exe "
                  "again. The previous version is MiceHub.old.exe"
                  % st["offered"][:12])


# The line the bundle splits on: everything above it is for the person
# reading, everything below is for support. The page and the check split on
# this exact string - changing it here changes all three or nothing.
DIAG_TECH_MARK = "--- technical detail below, for support ---"


def diagnostics() -> str:
    """Everything anyone asks for first, as one block of plain text.

    "It does not work" is never enough to act on. The answer is always the same
    four questions - which PC, what does it see, what firmware is on the
    boards, and what can this machine even do - and getting them out of
    somebody over chat takes half an hour. This is one button instead.

    TWO HALVES, asked 2026-08-22 (A21-5): IN PLAIN WORDS first - what is
    connected, what needs attention, each with its fix, NO ids, ports or
    addresses - then DIAG_TECH_MARK, then the technical bundle below it,
    which stays complete because support needs every id. The page shows the
    plain half and hides the rest behind the technical switch.

    PLAIN TEXT, NOT JSON. It gets pasted into a message by a person, and JSON
    pasted into a chat window is a wall nobody reads.

    NOTHING SECRET, EVER. This is written to be shared, so a password in it is
    a password published. The hub keeps one in plain text beside itself
    (hub_password.txt), a module's WiFi credentials come back in some status
    replies, and the AP password is derived from the group name. None of them
    belong here, and check_diagnostics exists to keep it that way - a bundle
    that leaks is worse than no bundle, because the leak travels further than
    the problem it was meant to solve.
    """
    import platform                                          # noqa: PLC0415

    def line(k, v):
        return "%-14s %s" % (k, v)

    def pline(k, v):
        return "  %-11s %s" % (k, v)

    def disp_name(m):
        # probe_module defaults an unnamed WiFi module's name to its IP;
        # an address in the plain half breaks the no-addresses promise.
        # search, not fullmatch: a name like 192.168.4.21:8642 or a forwarded
        # hub: prefix still carries an address and must be stripped too
        nm = m.get("name") or ""
        if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", nm):
            nm = ""
        return nm or ("unnamed %s robot" % (m.get("type") or "?"))

    # Gather once; the plain half and the technical half read the SAME data.
    _st = _hub.build_stamp.state()
    esp_cmd, esp_why = _hub.esptool_cmd()
    images = _hub.flash_images()
    ports = _hub.serial_ports()
    mods = _hub.modules_here()

    # ASK THE BOARD which firmware it runs. The module list is built from
    # PING, which answers id, name and type and nothing else - so `fw` is
    # simply not in it. One extra command per board, on an explicit button
    # press, with a short wait: a board that has gone quiet says so and does
    # not hold up the rest.
    def ask_fw(m):
        dev = (m.get("routes") or [{}])[0].get("dev")
        if not dev:
            return "?"
        try:
            info = _hub.dev_cmd(dev, "INFO", wait=2.0) or ""
            got = json.loads(info[info.find("{"):info.rfind("}") + 1])
            return got.get("fw") or "?"
        except Exception as e:                                # noqa: BLE001
            return "no answer (%s)" % str(e)[:40]

    fws = {m.get("id"): ask_fw(m) for m in mods}

    # ---- the plain half -------------------------------------------------
    plain = ["IN PLAIN WORDS", ""]
    if mods:
        names = ", ".join(disp_name(m) for m in mods)
        plain.append(pline("robots", "%d connected - %s"
                           % (len(mods), names)))
    else:
        plain.append(pline("robots", "none found - are they powered, "
                                     "and on this WiFi?"))

    worry = []
    if _st["built"] and _st["stale"]:
        worry.append("this hub program is older than the files beside it - "
                     "run the updater or get the newest MiceHub.exe")
    if not esp_cmd:
        worry.append("the flashing tool is missing - boards can still be used, "
                     "but new firmware cannot be installed until it is set up")
    for im in images:
        if not im.get("ready") and not im.get("ota_ready"):
            worry.append("no %s firmware is built on this PC yet - build it "
                         "before trying to flash a %s board"
                         % (im.get("type"), im.get("type")))
    if not ports:
        worry.append("no cable is plugged into this PC - boards on a wire "
                     "will not appear until one is")
    for m in mods:
        who = disp_name(m)
        if m.get("stale"):
            worry.append("%s is answering slowly - it may be busy or going "
                         "offline" % who)
        elif str(fws.get(m.get("id"))).startswith("no answer"):
            worry.append("%s did not answer when asked about itself - "
                         "check its power" % who)
    if worry:
        plain.append("")
        plain.append(pline("needs attention:", ""))
        plain.extend("  - " + w for w in worry)
    else:
        plain.append(pline("all good:", "nothing needs attention right now."))

    # ---- the technical half, exactly as it has always been --------------
    out = ["mice diagnostics  " + time.strftime("%Y-%m-%d %H:%M:%S"),
           "=" * 58]
    out += plain
    out += ["", DIAG_TECH_MARK, "", "THIS PC"]
    out.append(line("host", socket.gethostname()))
    out.append(line("os", "%s %s" % (platform.system(), platform.release())))
    out.append(line("python", platform.python_version()))
    out.append(line("hub at", "%s:%d" % (_hub.lan_ip(), _hub.PORT)))
    out.append(line("web build", str(_hub.web_version())))
    out.append(line("frozen", "yes (MiceHub.exe)" if getattr(sys, "frozen", False)
                    else "no (running main.py)"))
    # The first question after any strange report: is this even today's build?
    if _st["built"]:
        out.append(line("exe built", "%s%s" % (
            _st["built"], "  STALE - %s" % _hub.build_stamp.why(_st)
            if _st["stale"] else "  (matches the source beside it)")))
    out.append(line("esptool", "yes" if esp_cmd else "NO - %s"
                    % (esp_why or "not found")))

    out += ["", "FIRMWARE BUILT ON THIS PC"]
    for im in images:
        state = "ready" if im.get("ready") else (
            "app only (WiFi/bus, not cable)" if im.get("ota_ready") else "NOT BUILT")
        out.append(line("  " + str(im.get("type")), "%s  %s" % (
            state, ("%.2f MB" % (im["bytes"] / 1048576.0)) if im.get("bytes") else "")))

    out += ["", "SERIAL PORTS"]
    if not ports:
        out.append("  none")
    for p in ports:
        out.append(line("  " + str(p.get("port")), "%s%s" % (
            p.get("desc") or "?", "  (bluetooth)" if p.get("bt") else "")))

    out += ["", "MODULES FOUND"]
    if not mods:
        out.append("  none - are they powered, and on this WiFi?")
    for m in mods:
        ways = ", ".join("%s%s" % (r.get("kind"),
                                   (" " + str(r.get("port"))) if r.get("port") else "")
                         for r in m.get("routes", []))
        out.append(line("  #%s" % m.get("id"), "%s  type=%s  fw=%s  via %s%s" % (
            m.get("name") or "?", m.get("type") or "?",
            fws.get(m.get("id"), "?"), ways,
            "  [LATE]" if m.get("stale") else "")))

    out += ["", "(no passwords are included in this text)"]
    return chr(10).join(out)
