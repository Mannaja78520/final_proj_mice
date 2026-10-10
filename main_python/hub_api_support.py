"""The hub's routes for self-update, the diagnostics text and problem reports.

Moved out of main.py's Handler.api() on 2026-09-22 (A26-93). Handler inherits
SupportRoutes, and api() asks it before carrying on down its own chain. Names
that live in main.py are read late through _hub, so a check that swaps
main.<name> reaches this code too.
"""
import json
import socket
import threading
import time
import uuid

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class SupportRoutes:
    def api_support(self, method, path, q):
        if path == "/api/app/version":
            me = _hub.app_here()
            if not me:
                return self.send_json({"ok": True, "sha": "", "bytes": 0,
                                       "why": "this hub runs from source, so "
                                              "it has no app to hand out"})
            exe, size, sha = me
            return self.send_json({"ok": True, "sha": sha, "bytes": size,
                                   "when": time.strftime(
                                       "%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime(exe.stat().st_mtime)),
                                   "host": socket.gethostname()})
        if path == "/api/app":
            # A browser cannot reach that PC's serial ports at any address, so
            # the PC has to run something that can. This is it.
            me = _hub.app_here()
            if not me:
                return self.send_err("this hub runs from source - there is no "
                                     "built app to download", 404)
            exe, _size, _sha = me
            return self.send_bytes(
                exe.read_bytes(), "application/octet-stream",
                headers=(("Content-Disposition",
                          "attachment; filename=MiceHub.exe"),))
        if path == "/api/selfupdate":
            # METHOD FIRST. A plain `if path ==` that answers the GET makes the
            # POST below unreachable, so the button would report state and
            # never update.
            if method == "POST":
                ok, msg = _hub.do_update()
                return self.send_json({"ok": ok, "message": msg})
            return self.send_json(_hub.update_state())
        if path == "/api/diag":
            # PLAIN TEXT, not JSON: a person pastes this into a message, and
            # they should be able to read what they are handing over before
            # they send it. Open like the rest of reading - and it carries no
            # password, which check_diagnostics enforces rather than trusts.
            return self.send_bytes(_hub.diagnostics().encode("utf-8"),
                                   "text/plain; charset=utf-8")
        if path == "/api/report" and method == "POST":
            # A REPORT anyone can send — no login, no password, stored machine-local.
            # The page sends: text, page, module, build, time, attachDiag (bool).
            # We add: client IP, user agent, and if attachDiag, the diagnostics text.
            # Saved as one JSON file per report under HERE/reports/ (never promoted).
            # json/uuid come from the module imports - a local import here made
            # the names local to this WHOLE router function, and every endpoint
            # that reads them earlier (pairing, saves, OTA, play) died with
            # UnboundLocalError. 33 red checks from two lines.
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 1048576:
                    # This endpoint is deliberately open, so the cap is not
                    # optional: a lying Content-Length must not become RAM.
                    # Same rudeness rule as drain() - past the cap, drop the
                    # connection instead of reading it.
                    self.close_connection = True
                    self._body_read = True
                    return self.send_json({"ok": False,
                                           "error": "that report is too big"})
                raw = self.body().decode("utf-8") or "{}"
                data = json.loads(raw)
            except Exception:
                return self.send_json({"ok": False, "error": "bad json"})
            text = (data.get("text") or "").strip()[:4000]
            if not text:
                return self.send_json({"ok": False, "error": "empty"})
            page = str(data.get("page") or "")[:60]
            module = str(data.get("module") or "")[:60]
            build = str(data.get("build") or "")[:80]
            # The visitor's clock lands in a FILENAME below, so it is stripped
            # to plain characters first - an unfiltered ..\..\ wrote the
            # report wherever it pointed on this PC (A22-1 panel, 2026-08-25).
            t = "".join(ch for ch in str(data.get("time") or "")
                        if ch.isalnum() or ch in "-T:.Z ")[:40]
            attach = bool(data.get("attachDiag"))
            # Build the report record
            report = {
                "id": uuid.uuid4().hex[:12],
                "time": t or time.strftime("%Y-%m-%dT%H:%M:%S"),
                "text": text,
                "page": page,
                "module": module,
                "build": build,
                "attachDiag": attach,
                "client": self.client_address[0] if self.client_address else "",
                "ua": self.headers.get("User-Agent", "")[:200],
            }
            if attach:
                try:
                    report["diag"] = _hub.diagnostics()
                except Exception:
                    report["diag"] = "diagnostics unavailable"
            # Write to HERE/reports/ (not SKIP_FILES - those are for promote.py)
            # but a sibling of the hub: machine-local, never in source.
            rep_dir = _hub.HERE / "reports"
            rep_dir.mkdir(exist_ok=True)
            fname = rep_dir / (report["time"].replace(":", "-") + "_" + report["id"] + ".json")
            try:
                _hub.write_atomic(fname, json.dumps(report, ensure_ascii=False, indent=2))
            except Exception as e:
                return self.send_json({"ok": False, "error": "write failed: " + str(e)})
            # English lands in the file later; the visitor's own words are
            # already saved, so nothing waits on the model here.
            threading.Thread(target=_hub._translate_report_later,
                             args=(fname, text), daemon=True).start()
            return self.send_json({"ok": True, "id": report["id"]})
        if path == "/api/reports" and method == "GET":
            # LIST reports for the complaints screen — no login, anyone can see.
            # Returns: [ {id, time, text, text_en, page, module, build, status, ...} ]
            # text_en was translated ONCE when the report was filed (see
            # _translate_report_later); empty means no translation yet and the
            # pages fall back to the original words. No model call here - a
            # list refresh must be instant even with the helper switched off.
            rep_dir = _hub.HERE / "reports"
            if not rep_dir.is_dir():
                return self.send_json({"ok": True, "reports": []})
            out = []
            # Read under the SAME lock the writers hold: on Windows an open
            # read handle makes the writers' os.replace fail, so an unlocked
            # list refresh could eat a just-finished translation.
            with _hub._reports_lock:
                for f in sorted(rep_dir.glob("*.json"), reverse=True):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        continue          # a corrupt sibling, not ours
                    # Never send diag in the list - only the summary fields.
                    # A closed report keeps its file so the next person finds it.
                    out.append({
                        "id": data.get("id"),
                        "time": data.get("time"),
                        "text": data.get("text") or "",
                        "text_en": data.get("text_en") or "",
                        "page": data.get("page"),
                        "module": data.get("module"),
                        "build": data.get("build"),
                        "status": data.get("status", "open"),
                        "client": data.get("client", ""),
                    })
            return self.send_json({"ok": True, "reports": out})
        if path == "/api/reports" and method == "POST":
            # UPDATE a report status: {id: "...", status: "fixed" | "not-a-problem"}
            # No login — the point is a designer can close it from the screen.
            import json as _json
            try:
                raw = self.body(1048576).decode("utf-8") or "{}"
                data = _json.loads(raw)
            except Exception:
                return self.send_json({"ok": False, "error": "bad json"})
            rid = (data.get("id") or "").strip()
            status = (data.get("status") or "").strip()
            if not rid or status not in ("fixed", "not-a-problem", "open"):
                return self.send_json({"ok": False, "error": "bad payload"})
            rep_dir = _hub.HERE / "reports"
            if not rep_dir.is_dir():
                return self.send_json({"ok": False, "error": "not found"})
            for f in rep_dir.glob("*.json"):
                try:
                    # Read under the SAME lock as the writer: a copy taken
                    # outside it can put back a version without the other's
                    # change (the translation vanishing again).
                    with _hub._reports_lock:
                        try:
                            j = _json.loads(f.read_text(encoding="utf-8"))
                        except Exception:
                            continue            # a corrupt sibling, not ours
                        if j.get("id") != rid:
                            continue
                        j["status"] = status
                        _hub.write_atomic(f, _json.dumps(j, ensure_ascii=False, indent=2))
                except Exception as e:
                    return self.send_json(
                        {"ok": False, "error": "could not save: %s" % e})
                return self.send_json({"ok": True})
                return self.send_json({"ok": True})
            return self.send_json({"ok": False, "error": "not found"})

        return NOT_MINE
