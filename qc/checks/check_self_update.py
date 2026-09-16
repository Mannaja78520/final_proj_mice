"""The hub can replace itself, and refuses to at the wrong moment.

Asked 2026-08-19: *click to update when a new one is uploaded to git*.

There are no GitHub releases for this project - the `app` branch holds
`MiceHub.exe` and nothing else - so it asks that branch. Documenting what
exists beats documenting what the plan assumed.

The refusals are the feature. An update that goes ahead at the wrong moment is
worse than one that never runs:

  * **not while a board is being flashed.** Replacing the program mid-write
    leaves a board half written and nothing driving the rest of it;
  * **not while a show is playing.** That stops the installation in front of an
    audience;
  * **not when running from source.** `git pull` brings the firmware and the
    checks too; swapping an exe that is not there would do nothing;
  * **not when GitHub cannot be reached.** No internet is the NORMAL case at a
    venue, so it is a plain sentence, not an error page;
  * **and never a truncated download.** A short read that overwrote the program
    would leave nothing to start. The bytes are checked before anything is
    replaced, and the previous version is kept as the way back.
"""
import json
import re

import qc as F

AREA = "hub"
TITLE = "the hub can update itself, and refuses while it is busy"


def run(t):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    auth = (F.HUB / "hub_auth.py").read_text(encoding="utf-8")

    # ---- it asks the branch that really publishes the app ------------
    t.contains(src, "APP_BRANCH", "the branch it fetches from is named once")
    t.ok("/releases" not in src.split("def diagnostics")[0],
         "and it does not ask for a GitHub release",
         "there is none - the app branch is where MiceHub.exe is published, "
         "and a release URL would 404 forever")

    st = src[src.find("def update_state():"):]
    st = st[:st.find("\ndef ", 1)]

    # ---- the refusals ------------------------------------------------
    for guard, why in (("flasher.running()", "a board is being flashed"),
                       ("show.running()", "a show is playing"),
                       ('getattr(sys, "frozen", False)', "running from source")):
        t.contains(st, guard, "it checks: %s" % why)
    i_busy = min(st.find("flasher.running()"), st.find("show.running()"))
    i_net = st.find("urllib.request.urlopen")
    t.ok(0 < i_busy < i_net,
         "and checks them BEFORE asking the network",
         "asking GitHub first wastes ten seconds at a venue with no internet "
         "to answer a question whose answer was already no")
    t.contains(st, "cannot reach GitHub",
               "no internet is answered plainly, not as an error")

    # ---- a bad download never replaces the program -------------------
    do = src[src.find("def do_update():"):]
    do = do[:do.find("\ndef ", 1)]
    t.contains(do, 'blob[:2] != b"MZ"',
               "the download is checked to be a Windows program")
    i_check = do.find('b"MZ"')
    i_write = do.find("exe.rename(old)")
    t.ok(0 < i_check < i_write,
         "before anything is moved or written",
         "a truncated read that overwrote the program would leave nothing to "
         "start, on the machine that runs the installation")
    t.contains(do, "MiceHub.old.exe",
               "and the previous version is kept as the way back")
    t.contains(do, "exe.rename",
               "the running exe is RENAMED, not overwritten",
               )
    t.ok("write_bytes(blob)" in do,
         "then the new one is written in its place",
         "Windows refuses to overwrite a running program but allows renaming "
         "it, which is the only reason this can work at all")

    # ---- replacing the program needs a login -------------------------
    t.contains(auth, '"/api/selfupdate"',
               "replacing the hub is behind the login")
    m = re.search(r"GATED_POST = \{([^}]*)\}", auth, re.S)
    t.ok(m and "selfupdate" in m.group(1),
         "as a POST, so READING what is offered stays open",
         "reading a version is as harmless as reading the module list; "
         "replacing the program is the most destructive thing it can do, on a "
         "network several people share")

    # ---- the route answers, and the method decides -------------------
    route = src[src.find('if path == "/api/selfupdate":'):]
    route = route[:route.find("\n        if path ==", 1)]
    i_m = route.find('method == "POST"')
    i_get = route.find("update_state()")
    t.ok(0 < i_m < i_get,
         "the POST is handled before the GET answer returns",
         "a plain `if path ==` that answers the GET first makes the POST "
         "unreachable, so the button reports state and never updates")

    fake = __import__("fake_serial")
    fake.reset()
    base, _m = F.start_hub()
    code, body = F.get(base + "/api/selfupdate")
    t.eq(code, 200, "the state endpoint answers")
    d = json.loads(body)
    for k in ("frozen", "running", "offered", "can", "why"):
        t.ok(k in d, "it reports %s" % k)
    # QC runs from source, so this is the branch under test here.
    t.eq(d["can"], False, "and refuses to update a source checkout")
    t.contains(d["why"], "git pull",
               "saying what to do instead")

    # ---- two presses, never one --------------------------------------
    fn = hub[hub.find("async function checkUpdate()"):]
    fn = fn[:fn.find("\n// ---- the diagnostics")]
    t.contains(fn, "/api/selfupdate",
               "the page asks what is offered")
    t.contains(fn, "method: 'POST'",
               "and replaces only on a second, separate press")
    i_ask = fn.find("fetch('/api/selfupdate')")
    i_do = fn.find("method: 'POST'")
    t.ok(0 < i_ask < i_do,
         "checking comes first and is harmless",
         "one button that both checks and replaces would swap the program "
         "somebody is using, from a press that looked like a question")
    t.contains(fn, "danger",
               "and the replace button looks like what it does")
