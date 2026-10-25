"""Resource settings API and public browser-only bootstrap."""
import json
import os
import threading
from urllib.parse import urlsplit

from resource_policy import ResourcePolicy
from resource_settings import StaleSettings

NOT_MINE = object()
_hub = None
_policy = None
_policy_lock = threading.Lock()


def bind(hub):
    global _hub, _policy
    _hub, _policy = hub, None


def policy():
    global _policy
    with _policy_lock:
        if _policy is None:
            _policy = ResourcePolicy(_hub.asset("config", "resource_policy.json"),
                                     _hub.DATA / ".local" / "resource_settings.json")
        return _policy


def child_environment():
    return {**os.environ, "MICE_RESOURCE_SETTINGS": str(_hub.DATA / ".local" / "resource_settings.json"),
            "MICE_RESOURCE_REGISTRY": str(_hub.asset("config", "resource_policy.json"))}


def browser_bootstrap():
    # Only registry presets: never reveal Hub inventory, selections or paths.
    try:
        data = json.dumps(policy().client_data(), ensure_ascii=True)
        source = (_hub.SHARED_WEB / "resources.js").read_bytes()
        return (";window.MiceResourceRegistry=" + data + ";\n").encode() + source + b"\n;\n"
    except (OSError, ValueError, TypeError, KeyError):
        return b""  # Theme/login and Studio's existing fallback still load.


class ResourceRoutes:
    def api_resources(self, method, path, q):
        if path != "/api/resources":
            return NOT_MINE
        if not self.logged_in():
            return self.send_err("log in first", 401)
        try:
            manager = policy()
            if method == "POST":
                origin = self.headers.get("Origin")
                if origin and (urlsplit(origin).scheme not in ("http", "https") or
                               urlsplit(origin).netloc.lower() != self.headers.get("Host", "").lower()):
                    return self.send_err("save from this hub's page", 403)
                length = int(self.headers.get("Content-Length") or 0)
                if not 0 < length <= 8192:
                    return self.send_err("settings are too large or empty", 413)
                data = json.loads(self.body().decode("utf-8"))
                if not isinstance(data, dict) or set(data) != {"settings", "revision"}:
                    raise ValueError("ส่งค่าประสิทธิภาพพร้อมรุ่นข้อมูลก่อนบันทึก")
                manager.store.save(data["settings"], data["revision"])
            elif method != "GET":
                return self.send_err("GET or POST only", 405)
            return self.send_bytes(json.dumps(manager.status(), ensure_ascii=False).encode(),
                                   "application/json; charset=utf-8", headers=[("Cache-Control", "no-store")])
        except StaleSettings as exc:
            return self.send_err(str(exc), 409)
        except (ValueError, TypeError, KeyError) as exc:
            return self.send_err(str(exc), 400)
        except OSError:
            return self.send_err("บันทึกค่าประสิทธิภาพไม่ได้ ค่าก่อนหน้ายังอยู่ ลองตรวจสิทธิ์การเขียนแล้วบันทึกอีกครั้ง", 503)
