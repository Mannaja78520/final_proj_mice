"""The hub's routes for the show clock, live audio, saved shows and stop-all.

Moved out of main.py's Handler.api() on 2026-09-22 (A26-93). Handler inherits
PlayRoutes, and api() asks it before carrying on down its own chain. Names
that live in main.py are read late through _hub, so a check that swaps
main.<name> reaches this code too.
"""
import json
import threading
import time
import urllib.request

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class PlayRoutes:
    def api_play(self, method, path, q):
        # ---- the hub as the show clock (see ShowPlayer) ----
        # POST /api/play   {dev, steps:[{pose[10], t, hold}], loop, name, from_ms}
        # GET  /api/play   where the show is right now
        # POST /api/play/stop
        if path == "/api/play" and method == "POST":
            try:
                d = json.loads(self.body().decode())
                return self.send_json(_hub.show.start(
                    d["dev"], d["steps"], d.get("loop"), d.get("name", ""),
                    d.get("from_ms", 0), bool(d.get("watch"))))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/play":
            return self.send_json(_hub.show.status())
        # ---- live audio to a module's speaker (A24-32) ----
        # POST /api/stream/start  {dev|ip, port, rate, file}
        # POST /api/stream/feed   raw 16-bit mono PCM, from the browser capture
        # POST /api/stream/stop   |  GET /api/stream  where it is up to
        if path == "/api/stream/start" and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
                dev = str(d.get("dev") or "")
                ip = str(d.get("ip") or "")
                if dev and not ip:
                    kind, addr, _bus, _peer = _hub.parse_dev(dev)
                    if kind != "wifi":
                        return self.send_err(
                            "live audio goes over WiFi - open this module over "
                            "WiFi, or give its address", 501)
                    ip = addr.split(":")[0]
                port = int(d.get("port") or _hub.stream_audio.DEF_PORT)
                rate = int(d.get("rate") or _hub.stream_audio.DEF_RATE)
                # The BOARD is told first: it must be listening before the
                # first datagram, or the start of the sound is simply gone.
                said = _hub.dev_cmd(dev or ("wifi:" + ip),
                               "STREAM ON %d %d" % (port, rate))
                if not said.startswith("OK"):
                    return self.send_err("the board refused the stream: " + said)
                st = _hub.streamer.start(ip, port, rate, str(d.get("name") or "live"))
                if d.get("file"):
                    pcm = _hub.stream_audio.wav_pcm(_hub.SEQUENCES.parent / "music"
                                               / _hub.safe_name(str(d["file"])), rate)
                    threading.Thread(target=_hub.streamer.feed_all, args=(pcm,),
                                     daemon=True).start()
                return self.send_json({"ok": True, "board": said, **st})
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/stream/feed" and method == "POST":
            took = _hub.streamer.feed(self.body())
            return self.send_json({"ok": True, "took": took,
                                   "queued": _hub.streamer.q.qsize()})
        if path == "/api/stream/stop" and method == "POST":
            st = _hub.streamer.stop()
            try:
                if st.get("ip"):
                    _hub.dev_cmd("wifi:" + st["ip"], "STREAM OFF")
            except Exception as e:            # noqa: BLE001
                st["error"] = str(e)
            return self.send_json({"ok": True, **st})
        if path == "/api/stream":
            return self.send_json({"ok": True, **_hub.streamer.status()})

        if path == "/api/stream/voice" and method == "POST":
            try:
                data = json.loads(self.body().decode())
                text = data.get("text")
                dev = data.get("dev")
                req = urllib.request.Request("http://127.0.0.1:8767/say", data=json.dumps({"text": text, "lang": ""}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    wav_bytes = r.read()
                import io, wave
                with wave.open(io.BytesIO(wav_bytes)) as w:
                    pcm = w.readframes(w.getnframes())
                    rate = w.getframerate()
                kind, addr, _, _ = _hub.parse_dev(dev)
                ip = addr.split(":")[0]
                _hub.dev_cmd(dev, "STREAM ON %d %d" % (_hub.stream_audio.DEF_PORT, rate))
                _hub.streamer.start(ip, _hub.stream_audio.DEF_PORT, rate, "voice")
                threading.Thread(target=_hub.streamer.feed_all, args=(pcm,), daemon=True).start()
                return self.send_json({"ok": True})
            except Exception as e:
                return self.send_err(str(e))

        # ---- shows: saved sequences in series (shows.py) ----
        if path == "/api/shows":
            return self.send_json({"ok": True, "shows": _hub.SHOWS.names()})
        if path == "/api/show":
            try:
                return self.send_json({"ok": True, "show": _hub.SHOWS.load((q.get("name") or [""])[0])})
            except (ValueError, FileNotFoundError) as e:
                return self.send_err(e, 404)
        # GET is "the saved show called X"; POST (below) is the draft being
        # edited. Without the method test this branch also swallowed the POST
        # and answered about a show with no name.
        if path == "/api/show/steps" and method != "POST":
            # THE SAME LIST THE ROBOT WILL RUN. Studio draws a show on its own
            # timeline from this, rather than re-implementing the chaining and
            # the repeats in JavaScript - two copies of that rule would drift,
            # and then the editor would show a run the robot does not perform
            # (A31-3). `marks` says where each pass starts, for the labels.
            try:
                marks = []
                steps = _hub.SHOWS.steps(_hub.SHOWS.load((q.get("name") or [""])[0]),
                                         _hub.seq_steps, marks)
                return self.send_json({"ok": True, "steps": steps, "marks": marks})
            except (ValueError, FileNotFoundError) as e:
                return self.send_err(e, 404)
        if path in ("/api/show/save", "/api/show/delete", "/api/show/play",
                    "/api/show/steps") and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
                if path == "/api/show/steps":
                    # the DRAFT being edited, not a saved file: the Shows tab
                    # redraws the timeline as sequences are added and repeats
                    # are typed, before anything is saved.
                    marks = []
                    steps = _hub.SHOWS.steps(_hub.SHOWS.clean(d.get("show") or {}),
                                             _hub.seq_steps, marks)
                    return self.send_json({"ok": True, "steps": steps, "marks": marks})
                if path == "/api/show/save":
                    fname, existed = _hub.SHOWS.save(d.get("show") or {})
                    return self.send_json({"ok": True, "file": fname, "replaced": existed})
                if path == "/api/show/delete":
                    return self.send_json({"ok": True, "kept": _hub.SHOWS.delete(d.get("name"))})
                sh = _hub.SHOWS.load(d.get("name")) if d.get("name") and not d.get("show") \
                    else _hub.SHOWS.clean(d.get("show"))
                steps = _hub.SHOWS.steps(sh, _hub.seq_steps)
                return self.send_json(_hub.show.start(d["dev"], steps, sh["loop"],
                                                 sh["name"] or "show"))
            except (ValueError, FileNotFoundError, KeyError) as e:
                return self.send_err(e)

        if path == "/api/play/beat" and method == "POST":
            # Can only keep a show alive or let it run alone - never start one -
            # so it needs no login, like stop (A26-46).
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                d = {}
            return self.send_json(_hub.show.beat(bool(d.get("leaving"))))
        if path == "/api/play/stop":
            return self.send_json(_hub.show.stop())

        if path == "/api/stopall" and method == "POST":
            # EVERYTHING, AT ONCE. The show clock first, because it is what
            # keeps sending new positions - stopping the boards while the clock
            # runs means the next tick starts them moving again. Then every
            # board the hub can reach, each one told directly rather than by
            # broadcast: a broadcast reaches whatever is listening, and the
            # answer to "did it stop?" has to be per board or it is not an
            # answer.
            #
            # It never asks first. A stop that needs confirming is a stop that
            # arrives after the thing you were trying to prevent.
            stopped, failed, slow = [], [], []
            try:
                _hub.show.stop(freeze=False, why="somebody pressed stop")
            except Exception:                              # noqa: BLE001
                pass
            mods = [m for m in _hub.modules_here() if m.get("routes")]

            # ONE THREAD PER BOARD, ALL AT ONCE. Stopping them in a row meant
            # each stop queued behind whatever that cable was already doing -
            # a flash holds its port lock for up to 30s (FWEND) - so the last
            # board waited for every board before it (A22-1 panel, 2026-08-25).
            def _stop_one(m, out):
                who = ("#%s %s" % (m.get("id"), m.get("name") or "")).strip()
                # The first route that answers is enough - the board is one
                # board however many ways in it has.
                for r in m.get("routes") or []:
                    try:
                        _hub.dev_cmd(r.get("dev"), "MOVE STOP")
                        out.append((who, True))
                        return
                    except Exception:                      # noqa: BLE001
                        continue
                out.append((who, False))

            # `got` must exist BEFORE the comprehension runs - a tuple
            # assignment evaluates the whole right side first, and the
            # threads' args referenced it while it was still unborn.
            got = []
            threads = [
                threading.Thread(target=_stop_one, args=(m, got), daemon=True)
                for m in mods]
            for th in threads:
                th.start()
            deadline = time.time() + _hub.PEER_WAIT + 2
            for th in threads:
                th.join(max(0.1, deadline - time.time()))
            for who, done in got:
                (stopped if done else failed).append(who)
            said = {w for w, _d in got}
            slow = [(" #%s %s" % (m.get("id"), m.get("name") or "")).strip()
                    for m in mods
                    if ("#%s %s" % (m.get("id"), m.get("name") or "")).strip()
                    not in said]
            return self.send_json({"ok": not failed, "stopped": stopped,
                                   "failed": failed, "slow": slow})

        return NOT_MINE
