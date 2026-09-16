"""The board refuses to CHANGE anything for a stranger, and still answers questions.

Reproduced on hardware before it was fixed, 2026-08-19, on the nong at
192.168.137.72:

    GET /api/cmd?c=SET%20NAME%20hacked   ->  200, and the board was renamed

Every route on the board answered anyone on the WiFi. The login on the module
page was browser-side only: it hid cards, it never guarded a request. Anyone at
the venue could rename a board, delete its sequences or replace its firmware.

This is a SOURCE check — QC has no ESP32, and qc/lib/fake_wifi.py is a Python
stand-in for the board's HTTP routes, so a C++ gate cannot be executed here.
What it CAN do is hold the design to the three things that make it safe, each
of which is one deletion away from being wrong:

  * the gate reads what a command DOES from the generated table, so a new
    command is protected without anyone remembering to protect it;
  * every route that changes something is gated, and the ones that only report
    are not — the hub's discovery probes /api/status, and gating that would
    hide every board from every hub;
  * a command marked `query` really is read-only, checked against its own help
    text, because a mis-declared flag silently reopens the door. CAM was
    exactly that: query:true, help saying it changes the sensor.
"""
import json
import re
import sys

import qc as F

AREA = "auth"
TITLE = "the board gates what changes, and only what changes"
SLOW = False

sys.path.insert(0, str(F.CODE / "tools"))


def _code(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"//.*", "", s)
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def run(t):
    from registry import strip_jsonc

    portal = _code(F.FIRMWARE / "src/core/WebPortal.cpp")

    # ---- the gate exists, and reads the DATA --------------------------
    t.contains(portal, "allowedCommand",
               "the command route asks whether this command is allowed")
    t.contains(portal, "COMMAND_DOCS",
               "and decides from the generated command table, not a list here")
    t.ok(re.search(r"query\s*\|\|\s*\w+\[i\]\.safety|\.query\b.*\.safety", portal),
         "a command is open only if it reports, or must never be refused",
         "the two flags that make this safe are query and safety")

    # ---- fail CLOSED for anything unknown -----------------------------
    fn = portal[portal.find("bool WebPortal::allowedCommand"):]
    fn = fn[:fn.find("\nString WebPortal::newSession")] or fn[:2000]
    t.contains(fn, "return allowed(req)",
               "a command that is not in the table needs a login",
               )

    # ---- every changing route is gated --------------------------------
    # Read each route's OWN body, not a fixed window: a window long enough to
    # be safe spills into the NEXT route, and a gate deleted from one route
    # then matches the gate in its neighbour. Proven by breaking it.
    def route_body(path):
        i = portal.find('server_.on("%s"' % path)
        if i < 0:
            return ""
        depth, j, started = 0, i, False
        while j < len(portal):
            if portal[j] == "{":
                depth += 1
                started = True
            elif portal[j] == "}":
                depth -= 1
                if started and depth == 0:
                    return portal[i:j + 1]
            j += 1
        return portal[i:]

    for route in ("/api/cmd", "/api/delete", "/api/upload", "/api/ota"):
        body = route_body(route)
        t.ok(body, "%s exists" % route)
        asks = "allowedCommand(req" in body or "allowed(req)" in body
        t.ok(asks, "%s asks whether the caller may do this" % route,
             "it changes something and answered strangers before A1-1")
        t.contains(body, "401",
                   "%s refuses with 401 rather than doing it anyway" % route)

    # An UPLOAD is refused before its FIRST byte lands. The body handler
    # streams chunks to the card while the request is still arriving, so a
    # 401 from the completion handler arrived after the file was already
    # written - /api/ota had exactly this hole until 2026-08-21, and upload
    # kept it one more day.
    #
    # route_body cannot see any of this: it stops at the first callback's
    # closing brace, which for a two-lambda server_.on() is only HALF the
    # route. Match the parentheses instead, so both callbacks are inside.
    def full_route(path):
        i = portal.find('server_.on("%s"' % path)
        if i < 0:
            return ""
        depth, j = 0, portal.find("(", i)
        while j < len(portal):
            if portal[j] == "(":
                depth += 1
            elif portal[j] == ")":
                depth -= 1
                if depth == 0:
                    return portal[i:j + 1]
            j += 1
        return portal[i:]

    up = full_route("/api/upload")
    t.ok(up.count("allowed(req)") >= 2,
         "an upload is refused before its first byte reaches the card",
         "the SD write happens in the body handler, mid-request")

    # ---- the status socket runs no commands ----------------------------
    # Nothing legitimate sends on /ws - the page polls over HTTP where the
    # gate lives, and a socket frame carries no session to check. handle()
    # there was command execution for anyone on the WiFi (A22-1 panel).
    ws = portal[portal.find("ws_.onEvent"):portal.find("server_.addHandler")]
    t.ok(ws and "router_->handle" not in ws,
         "the status socket is push-only",
         "/ws has no login to check, so an arriving frame ran ungated")

    # ---- and the reading routes are NOT ------------------------------
    # Not politeness: the hub finds boards by probing /api/status, so gating it
    # would make every module vanish from every hub on the network.
    for route in ("/api/status", "/api/peers"):
        body = route_body(route)
        t.ok("allowed(req)" not in body,
             "%s stays open, so the hub can still find this board" % route)

    # ---- a login exists, and does not leak which half was wrong -------
    t.contains(portal, '"/api/login"', "there is a way to log in")
    t.contains(portal, "users.verify", "which checks the accounts the board already had")
    login = portal[portal.find('server_.on("/api/login"'):]
    login = login[:1400]
    t.ok(login.count("401") == 1 and "wrong login" in login,
         "a wrong user and a wrong password get the SAME answer",
         "telling a stranger which half they got right is how they learn a "
         "valid user name")

    # ---- a stop is never refused --------------------------------------
    cmds = json.loads(strip_jsonc(
        (F.FIRMWARE / "config/commands.json").read_text(encoding="utf-8")))["commands"]
    stops = [c for c in cmds if c["name"] == "STOP"]
    t.ok(stops, "STOP exists")
    for c in stops:
        t.ok(c.get("safety"),
             "STOP (%s) is declared safety, so it works without a login" % c["scope"],
             "someone watching an arm about to hit a person cannot be asked for "
             "a password first")

    # ---- and no command lies about what it does -----------------------
    # A query flag that is wrong is a hole. CAM carried query:true while its own
    # help said it changes the sensor, which would have left it open to anyone.
    liars = []
    for c in cmds:
        if not c.get("query"):
            continue
        help_txt = (c.get("help") or "").lower()
        if re.search(r"\bchange it\b|\bset\b|\bwrite\b|\bdelete\b", help_txt):
            liars.append("%s: %s" % (c["name"], c.get("help")))
    t.eq(liars, [],
         "no command claims to be read-only while its help says it changes things")

    # ---- these can never be query:true ---------------------------------
    # AUTH is a password ORACLE: marked query:true, /api/cmd would run it
    # for anyone on the WiFi, no login needed - unlimited guessing against
    # the board's own accounts (A22-1 sweep, 2026-08-25). GROUP mutates
    # when given a name, and allowedCommand sees only the verb, so the
    # whole verb has to stay behind the login.
    for name in ("AUTH", "GROUP"):
        open_flag = [c for c in cmds if c["name"] == name and c.get("query")]
        t.ok(not open_flag,
             "%s runs only with a login, never as an open query" % name,
             "query:true would let /api/cmd run it before any login")

    # ---- and the page itself stopped feeding the oracle ----------------
    # doLogin used to try the typed pair with an open AUTH command BEFORE
    # asking for a session - the exact call a stranger would make, shipped as
    # the front door. Direct logins go to /api/login now; only the
    # through-the-hub page still uses AUTH, where holding the cable IS access.
    page = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8",
                                                      errors="replace")
    i = page.find("async function doLogin")
    fn = page[i:page.find("function doLogout", i)] if i >= 0 else ""
    t.ok(i >= 0, "the module page has a login flow")
    t.ok(fn.count("cmd('AUTH") == 1
         and 0 <= fn.find("viaHub()") < fn.find("cmd('AUTH") < fn.find("/api/login"),
         "a direct login asks the board's gate; only the hub path uses AUTH",
         "AUTH tried over /api/cmd from the login form is the oracle again")
