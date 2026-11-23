"""One app by itself: `MiceHub.exe --alone voice` (user 2026-11-23).

*Every app must work alone, not through the hub, with nearly the same
functions - and when the hub or other apps are running, they join up.*

WHAT "ALONE" IS. The same program (one code base, so a fix is made once),
started for ONE app: its own port from the app's app.json (`alonePort`), its
page at "/", and nothing else started that the app does not need - no
network-wide hunt for hubs, no name on port 80, no friend programs resumed.
It does not look for a hub and does not need one: whatever the app needs
(the voice helper, a board scan for the prize machine) it starts by itself,
exactly as the hub would. Opening a SECOND app's page here gives a plain
page that points to where that app is running (found through peers.py) or
says how to start it - never a half-working copy.

WHAT "TOGETHER" IS. Every process, alone or the full hub, writes itself into
the peers folder (peers.py) and reads it. The full hub lists the alone apps
at /api/peers, so its Tools page can link them; an alone app finds a
neighbour by what it can DO (`caps` in app.json: "prize", "speak", "camera"),
not by who it is.

An app with `needs` (Reconize, Photobooth) is a friend's program: it runs by
itself from its own folder, and this module says so instead of faking it.
"""
import html

import peers

# Written once, so every page of this mode says the same thing.
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title><link rel="stylesheet" href="/mice.css"></head>
<body><main class="wrap" style="max-width:34rem;margin:3rem auto;padding:0 1rem">
<h1>%(title)s</h1>%(more)s<script src="/mice.js"></script></main></body></html>"""

# The words are fixed texts so the language packs (shared/web/lang) can turn them.
NOT_HERE = "This app is not open in this window."
RUNNING = "It is already open in its own window on this PC."
OPEN_IT = "Open it"
HOW = "Open the full MICE program to use every app together, or start this app by itself."


def arg(argv, name):
    """Value of `--name <v>` or `--name=<v>`, else ""."""
    for i, a in enumerate(argv):
        if a == "--" + name and i + 1 < len(argv):
            return argv[i + 1].strip()
        if a.startswith("--" + name + "="):
            return a[len(name) + 3:].strip()
    return ""


class AloneMode:
    """The one app this process serves, and how it joins its neighbours."""

    def __init__(self, app, port):
        self.app = app              # a registry entry (tools/registry.py)
        self.port = int(port)

    @classmethod
    def from_args(cls, argv, find_app):
        """-> AloneMode, or None when --alone was not given. A bad name or an
        app that is not ours raises SystemExit with the plain reason."""
        want = arg(argv, "alone")
        if not want:
            return None
        app = find_app(want)
        if not app:
            raise SystemExit("no app called %r" % want)
        if app.get("needs"):
            raise SystemExit(
                "%s is a friend's program: it runs by itself from its own folder "
                "(no hub needed). Start it there; the hub only links to it." % app["name"])
        port = arg(argv, "port") or app.get("alonePort") or 0
        try:
            port = int(port)
        except ValueError:
            raise SystemExit("--port must be a number") from None
        if not 1024 <= port <= 65535:
            raise SystemExit("%s has no port of its own yet (alonePort in its app.json)"
                             % app["name"])
        return cls(app, port)

    # -------------------------------------------------------- what is open
    def other_app_page(self, path, all_apps):
        """The app whose page `path` is (its /app/<id>/ or its historic url like
        /studio/), when that app is not this one: else None."""
        for a in all_apps:
            base = a["path"].rstrip("/")
            if a["id"] != self.app["id"] and (path == base or path.startswith(base + "/")):
                return a
        return None

    def landing_for(self, other):
        """(html, status) for a page of an app that is not this one."""
        found = peers.peers(app=other["id"], skip_port=self.port)
        if found:
            more = "<p>%s</p>%s" % (RUNNING, "".join(
                '<p><a class="btn" href="%s">%s</a></p>' % (
                    html.escape(p["url"].rstrip("/") + other["path"]), OPEN_IT)
                for p in found))
        else:
            more = ("<p>%s</p><p class=\"tech\"><code>MiceHub.exe --alone %s</code></p>"
                    % (NOT_HERE + " " + HOW, html.escape(other["id"])))
        return PAGE % {"title": html.escape(other["name"]), "more": more}, 200

    # ------------------------------------------------------ the neighbours
    def announce(self):
        return peers.announce(self.app["id"], self.port, self.app.get("caps") or [],
                              name=self.app["name"], alone=True)

    def withdraw(self):
        peers.withdraw(self.app["id"], self.port)
