"""The hub's routes for the prize dispensers (A47-2). The brain is gacha.py.

    GET  /api/gacha                 machines (live), items, event, rules source, counts
    POST /api/gacha/config          {machines?, items?, event?, rules?, webhooks?, ...}   (login)
    POST /api/gacha/dispense        {item, person, app, machine, force, wait}
                                    (login, or a program on this PC - hub_auth.LOCAL_OK)
                                    person "@face" = whoever the face app sees nearest now
    POST /api/gacha/can             {item, person} -> may they, how many left    (same gate)
    POST /api/gacha/event           {name?, open?, reset?} to every machine   (login)
    POST /api/gacha/machine         {machine, cmd} one board command, logged   (login)
    GET  /api/gacha/rules           the rules (people's names: login)
    POST /api/gacha/rules           {items, people} save locally              (login)
    POST /api/gacha/rules/pull      read the Google Sheet tabs into the local rules (login)
    POST /api/gacha/rules/push      send the local rules to the sheet's script (login)
    GET  /api/gacha/log             the dispense log, newest last (?limit=, &csv=1)  (login)
    GET  /api/gacha/stats           counts per item / machine / person / app (login)

Force (admin's extra prize) needs a logged-in person, never a local program:
it skips the limits, so a program must not be able to hand out the whole box.
"""
import csv
import io
import json
import os
import sys
from pathlib import Path

import gacha as gm

NOT_MINE = object()
_hub = None
_gacha = None


def bind(hub):
    global _hub
    _hub = hub


def cfg_path():
    if os.environ.get("MICE_GACHA_CONFIG"):
        return Path(os.environ["MICE_GACHA_CONFIG"])
    p = Path(_hub.asset("config", "gacha.json"))
    bundled = getattr(sys, "_MEIPASS", "")
    if bundled and Path(bundled) in p.parents:
        # the exe's bundled copy vanishes on exit: keep changes beside the exe
        p = Path(_hub.HERE) / "config" / "gacha.json"
    return p


def data_dir():
    return Path(os.environ.get("MICE_GACHA_DATA") or (Path(_hub.DATA) / ".local" / "gacha"))


def find_dev(name):
    """A machine's board by its module name, over its fastest live route."""
    if not name:
        return None
    for m in _hub.hub_modules.modules_here():
        if str(m.get("name") or "").lower() == str(name).lower() and m.get("best"):
            return m["best"]
    return None


def gacha():
    global _gacha
    if _gacha is None or _gacha.cfg_path != cfg_path():
        _gacha = gm.Gacha(cfg_path(), data_dir(), send=_hub.dev_cmd, find_dev=find_dev)
    return _gacha


def face_now():
    """The person the face app sees nearest right now, or ''."""
    try:
        got, code = _hub.hub_api_faces.ask("GET", what="/present?seconds=10")
    except Exception:                                        # noqa: BLE001
        return ""
    people = (got or {}).get("people") or []
    return (people[0].get("name") or "") if code == 200 and people else ""


class GachaRoutes:
    def _gacha_body(self):
        try:
            d = json.loads(self.body().decode() or "{}")
        except ValueError:
            return None
        return d if isinstance(d, dict) else None

    def api_gacha(self, method, path, q):
        if not path.startswith("/api/gacha"):
            return NOT_MINE
        g = gacha()
        if path == "/api/gacha" and method == "GET":
            c = g.cfg()
            return self.send_json({"ok": True, "event": c["event"], "items": c["items"],
                                   "machines": g.machines_view(),
                                   "rules": {k: v for k, v in c["rules"].items()
                                             if k != "sheet_write_url"},
                                   "webhooks": {k: len(v or []) for k, v in c["webhooks"].items()},
                                   "messages": c.get("messages") or {},
                                   "low_stock": c.get("low_stock")})
        if path == "/api/gacha/stats":
            return self.send_json({"ok": True, "stats": g.stats(), "hooks": g.hook_log[-20:]})
        if path == "/api/gacha/log":
            rows = g.log_rows(limit=int((q.get("limit") or ["200"])[0] or 0))
            if (q.get("csv") or [""])[0]:
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=gm.LOG_FIELDS, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
                return self.send_bytes(buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
            return self.send_json({"ok": True, "rows": rows})
        if path == "/api/gacha/rules" and method == "GET":
            r = g.rules()
            return self.send_json({"ok": True, "rules": r, "csv": gm.rules_to_csv(r),
                                   "webhooks": g.cfg().get("webhooks") or {},
                                   "sheet_write_url": g.cfg()["rules"].get("sheet_write_url", "")})
        if method != "POST":
            return self.send_err("POST only here", 405)
        d = self._gacha_body()
        if d is None:
            return self.send_err("that request was not readable")
        who = self.logged_in_user() if self.logged_in() else ""
        if path == "/api/gacha/config":
            ok, why = g.save_cfg(d)
            return self.send_json({"ok": ok, "error": why}, 200 if ok else 400)
        if path in ("/api/gacha/dispense", "/api/gacha/can"):
            person = str(d.get("person") or "")
            if person == "@face":
                person = face_now()
            force = bool(d.get("force"))
            if force and not who:
                return self.send_json({"ok": False, "need_login": True,
                                       "error": "only a logged-in admin may give one anyway"}, 401)
            if path == "/api/gacha/can":
                ok, why, detail = g.check(str(d.get("item") or ""), person, force)
                return self.send_json(dict(detail, ok=ok, reason=why, person=person))
            got = g.dispense(item=str(d.get("item") or ""), person=person,
                             app=str(d.get("app") or ("hub" if who else "program")),
                             machine=d.get("machine") or None, force=force,
                             by=who or "program", wait=bool(d.get("wait")))
            return self.send_json(got, 200 if got.get("ok") else 409)
        if path == "/api/gacha/event":
            sent = g.set_event(name=d.get("name"), open_=d.get("open"),
                               reset=bool(d.get("reset")))
            return self.send_json({"ok": True, "sent": sent, "event": g.cfg()["event"]})
        if path == "/api/gacha/machine":
            m = g.machine(d.get("machine"))
            cmd = str(d.get("cmd") or "").strip()
            if not m or not cmd:
                return self.send_err("which machine, and what to tell it")
            try:
                reply = g.ask(m, cmd)
            except Exception as e:                           # noqa: BLE001
                reply = "ERR %s" % e
            g.log_event({"kind": "machine", "machine": m["id"], "by": who,
                         "reason": cmd, "result": reply})
            return self.send_json({"ok": reply.startswith("OK") or reply.startswith("{"),
                                   "reply": reply})
        if path == "/api/gacha/rules":
            ok, why = g.save_rules(d.get("rules") if "rules" in d else d)
            return self.send_json({"ok": ok, "error": why}, 200 if ok else 400)
        if path == "/api/gacha/rules/pull":
            ok, why, rules = g.pull_rules()
            return self.send_json({"ok": ok, "error": why, "rules": rules}, 200 if ok else 502)
        if path == "/api/gacha/rules/push":
            ok, why = g.push_rules()
            return self.send_json({"ok": ok, "error": why}, 200 if ok else 502)
        return self.send_err("no such address: " + path, 404)
