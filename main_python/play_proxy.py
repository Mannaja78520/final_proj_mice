"""A friend's game that needs its OWN server, shown through the hub (A47-6).

All-Jao-Games moved its state to server.cjs on 2026-11-05 (/api/state/<game>,
/api/versions, /api/gacha/events); a static folder at /play/<id>/ no longer
plays. When a partner's "play" entry in config/partners.json has `proxy` (the
game server's address), the hub forwards to it:

  /play/<id>/<rest>   ->  <proxy>/<rest>, HTML pages get the same inject tag
                          (the win reporter), so the page and its reporter
                          share one origin and no postMessage bridge is needed;
  `proxy_paths`       root-absolute paths the game's own scripts call
                          (server.cjs routes, read from their code 2026-11-05:
                          shared-store.js:16,56, hub-integration.js:23) are
                          forwarded unchanged.

Their server accepts a PUT only when Origin equals http://<Host> (server.cjs:65),
so Host and Origin are rewritten to the game server's own. Their files are
never written. Server-sent events are streamed, not buffered.
"""
import html
import http.client
import json
import time
import urllib.parse

MAX_BODY = 26 * 1024 * 1024        # their server caps a state PUT at 25 MB


def inject(data, pid, play):
    """The win reporter, added just before </body> (never into their files)."""
    if not play.get("inject"):
        return data
    cfg = json.dumps({"partner": pid, "watch": play.get("watch") or []},
                     ensure_ascii=False).replace("</", "<\\/")
    tag = ('<script>window.MICE_PLAY=%s;</script><script src="%s"></script>'
           % (cfg, html.escape(str(play["inject"]), quote=True))).encode("utf-8")
    at = data.lower().rfind(b"</body>")
    return data[:at] + tag + data[at:] if at >= 0 else data + tag


class Games:
    """The proxied games of config/partners.json, re-read at most every `ttl`
    seconds: route() asks on every request, and the file is not worth a read
    each time (the live health probes of read_partners are far worse)."""

    def __init__(self, load, ttl=5.0, clock=time.monotonic):
        self.load, self.ttl, self.clock = load, ttl, clock
        self.at, self.found = -1e9, {}

    def of(self):
        if self.clock() - self.at > self.ttl:
            try:
                every = self.load() or {}
            except Exception:                                # noqa: BLE001
                every = {}
            self.found = {k: v for k, v in every.items() if isinstance(v, dict)
                          and isinstance(v.get("play"), dict) and v["play"].get("proxy")}
            self.at = self.clock()
        return self.found


def target(partners, path):
    """(pid, play, upstream path) when `path` belongs to a proxied game, else None."""
    for pid, entry in (partners or {}).items():
        play = entry.get("play") if isinstance(entry, dict) else None
        if not isinstance(play, dict) or not play.get("proxy"):
            continue
        prefix = "/play/%s/" % pid
        if path.startswith(prefix):
            return pid, play, "/" + path[len(prefix):]
        for p in play.get("proxy_paths") or []:
            if path == p or (p.endswith("/") and path.startswith(p)):
                return pid, play, path
    return None


def forward(h, pid, play, up_path, query, method):
    """Send this request to the game server and its answer back. `h` is the
    hub's request handler (send_bytes, headers, rfile, wfile)."""
    base = urllib.parse.urlsplit(str(play["proxy"]))
    host = base.netloc
    body = None
    if method in ("PUT", "POST"):
        n = int(h.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return h.send_err("too large", 413)
        body = h.rfile.read(n) if n else b""
        h._body_read = True
    headers = {"Host": host}
    for k in ("Content-Type", "Accept"):
        if h.headers.get(k):
            headers[k] = h.headers[k]
    if h.headers.get("Origin"):
        headers["Origin"] = base.scheme + "://" + host
    conn = http.client.HTTPConnection(base.hostname, base.port or 80, timeout=30)
    try:
        conn.request(method, up_path + ("?" + query if query else ""), body, headers)
        resp = conn.getresponse()
    except OSError as e:
        conn.close()
        return h.send_err("the game server (%s) does not answer: %s" % (host, e), 502)
    ctype = resp.getheader("Content-Type") or "application/octet-stream"
    try:
        if ctype.startswith("text/event-stream"):
            h.send_response(resp.status)
            h.send_header("Content-Type", ctype)
            h.send_header("Cache-Control", "no-cache")
            h.send_header("Connection", "close")
            h.end_headers()
            h.close_connection = True
            while True:
                line = resp.readline()
                if not line:
                    break
                h.wfile.write(line)
                h.wfile.flush()
            return None
        data = resp.read()
        if "text/html" in ctype:
            data = inject(data, pid, play)
        return h.send_bytes(data, ctype, resp.status)
    except (OSError, http.client.HTTPException):
        h.close_connection = True      # the reader went away, or the stream broke
        return None
    finally:
        conn.close()
