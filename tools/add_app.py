#!/usr/bin/env python3
"""Tell the hub on this PC about an app folder (A51-2): what an app's installer calls.

    python tools/add_app.py "D:/apps/LuckyDraw"          add it to this PC's hub
    python tools/add_app.py "D:/apps/LuckyDraw" --wait   keep trying until the hub runs

The same call as Tools > Add app: POST /api/extensions/add on 127.0.0.1. A
program on this PC needs no hub login (hub_auth NEVER_GATED + start_refused),
a page from another site cannot. No hub running? The app is still installed;
the hub offers it under "found on this PC" the next time it starts, as long as
it sits beside the hub's folder - or run this again.

Standard library only, so an installer can ship this one file next to its app.
"""
import json
import os
import sys
import time
import urllib.request

HUB = os.environ.get("MICE_HUB", "http://127.0.0.1:8642")


def add(folder, hub=HUB, timeout=10):
    req = urllib.request.Request(hub.rstrip("/") + "/api/extensions/add",
                                 data=json.dumps({"folder": folder}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    folder = os.path.abspath(argv[0])
    wait = "--wait" in argv
    while True:
        try:
            got = add(folder)
        except OSError as e:
            if not wait:
                print("no hub answered at %s (%s): the app is installed, add it from "
                      "Tools > Add app when the hub runs" % (HUB, e))
                return 1
            time.sleep(5)
            continue
        if got.get("ok"):
            print("added %s to the hub" % (got.get("app") or {}).get("name", folder))
            return 0
        print("the hub said: %s" % got.get("error"))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
