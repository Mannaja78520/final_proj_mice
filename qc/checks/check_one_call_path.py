"""Talking to a module goes down ONE path, whichever address you use.

There were three ways to say "send this command to that module":

  * `/api/dev/cmd?dev=wifi:IP` - the current one, which also understands
    `usb:COM`, a module behind a peer, and `hub:IP/...` for a cable on another
    PC;
  * `/api/robot/cmd?ip=IP` - the older spelling, still used by Nong Studio;
  * `/api/usb/cmd?port=COM` - the cable spelling, used so a module website and
    Studio can share one cable.

Three implementations of one call, and they had ALREADY drifted: only
`/api/robot/cmd` guarded against two show clocks on one robot, the other
`/api/robot/*` calls did not, and neither of the older two could reach a module
through another hub or behind a peer - which the dev path has done since A2-4.
So a feature added to the modern path silently did not exist on the two older
addresses that real programs were using.

They are shims now. What this checks is that they STAY shims: the failure being
prevented is somebody fixing a bug on one address and leaving the other two
wrong, which is what happened last time and is invisible until the day somebody
uses the other spelling.
"""
import re

import qc as F

AREA = "hub"
TITLE = "one code path for talking to a module, three ways to address it"


def run(t):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")

    # ---- there is one implementation --------------------------------
    t.contains(src, "def dev_route(self",
               "the one call lives in its own method")
    t.contains(src, 'return self.dev_route(method, path[len("/api/dev/"):], q)',
               "/api/dev/* is a call to it")

    # ---- and the older spellings go through it ----------------------
    robot = src[src.find('if path.startswith("/api/robot/")'):]
    robot = robot[:robot.find('if path == "/api/robot/upload"')]
    t.contains(robot, "self.dev_route(",
               "/api/robot/* hands the call to the same method")
    t.contains(robot, '"wifi:" + ip',
               "having turned its ip into a dev address")
    t.ok("robot_get(ip," not in robot,
         "and does not talk to the board itself any more",
         "that was the second implementation: %s"
         % re.findall(r"robot_get\([^)]*\)", robot))

    usb = src[src.find('if path == "/api/usb/cmd"'):]
    usb = usb[:usb.find('if path == "/api/usb/close"')]
    t.contains(usb, "self.dev_route(",
               "/api/usb/cmd hands the call over too")
    t.contains(usb, '"usb:" + port',
             "having turned its port into a dev address")
    t.ok("usb_cmd(port," not in usb,
         "and does not send the command itself",
         "that was the third implementation")

    # ---- the guard that had drifted now covers all three ------------
    # check_takeover is what stops two show clocks driving one robot. It used
    # to be called by /api/robot/cmd and /api/usb/cmd but not by the other
    # /api/robot/* calls; now there is one place it can live.
    dev = src[src.find("def dev_route(self"):]
    dev = dev[:dev.find("\n    def ", 10)]
    t.contains(dev, "check_takeover",
               "the shared path guards against two show clocks")
    t.ok(robot.count("check_takeover") == 0 and usb.count("check_takeover") == 0,
         "and the shims do not each guard separately",
         "a guard in three places is three places to forget it")

    # ---- an unknown call is refused, not forwarded ------------------
    t.contains(robot, "unknown robot call",
               "an address that is not one of the five is refused")
    t.ok('"cmd", "status", "files", "download", "delete"' in robot,
         "and the five are named",
         "forwarding anything at all would turn a typo into a call to the "
         "board with a path nobody meant")
