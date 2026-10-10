"""The hub's routes for the rig's voice: speakers, the speaking queue, silence.

System A4-3..A4-5. The queue itself is hub_speak.py; this only reads the
request and hands it over. Names that live in main.py are read late through
_hub, so a check that swaps main.<name> reaches this code too.

    GET  /api/speakers        every speaker, ready or not, and why
    POST /api/speakers        {default, voices: {id: voice}}          (login)
    GET  /api/speak           what is being said and what waits       (login)
    POST /api/speak           {text, to, voice, lang, whenBusy, take, move, module}
                              (login, or a program on this PC - hub_auth.LOCAL_OK)
    POST /api/speak/stop      quiet now, never gated
"""
import json

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class SpeakRoutes:
    def api_speak(self, method, path, q):
        speak = _hub.hub_speak
        if path == "/api/speakers":
            if method == "POST":
                try:
                    d = json.loads(self.body().decode() or "{}")
                except ValueError:
                    return self.send_err("that request was not readable")
                ok, why = speak.save_speakers(d if isinstance(d, dict) else {})
                if not ok:
                    return self.send_err(why)
            cfg, why = speak.read_speakers()
            return self.send_json({"ok": True, "default": cfg.get("default") or "pc",
                                   "speakers": speak.speaker_list(cfg),
                                   "error": why})
        if path == "/api/speak/stop" and method == "POST":
            boards = speak.off_all(speak.SPEECH.silence(), wait=3.0)
            return self.send_json({"ok": True, "silenced": boards})
        if path == "/api/speak":
            if method != "POST":
                return self.send_json(speak.SPEECH.status())
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                return self.send_err("that request was not readable")
            who = self.logged_in_user() if self.logged_in() else "a program on this PC"
            got = speak.SPEECH.submit(d, who=who)
            return self.send_json(got, 200 if got.get("ok") else 400)
        return NOT_MINE
