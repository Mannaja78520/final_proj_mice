"""One revisioned, atomic machine-local store; only the Hub writes it."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading


class StaleSettings(ValueError):
    pass


class ResourceSettings:
    def __init__(self, path, defaults, validate):
        self.path, self.defaults, self.validate = Path(path), dict(defaults), validate
        self.lock = threading.RLock()

    def read(self):
        with self.lock:
            try:
                raw = self.path.read_bytes()
            except FileNotFoundError:
                return {"revision": "default", "settings": dict(self.defaults), "warning": ""}
            except OSError:
                return {"revision": "unreadable", "settings": dict(self.defaults),
                        "warning": "อ่านค่าประสิทธิภาพไม่ได้ กำลังใช้ค่าเริ่มต้น"}
            revision = hashlib.sha256(raw).hexdigest()
            try:
                data = json.loads(raw)
                if data.get("version") != 1:
                    raise ValueError("Unsupported settings")
                settings = self.validate(data["settings"])
                return {"revision": revision, "settings": settings, "warning": ""}
            except (ValueError, TypeError, KeyError, AttributeError):
                return {"revision": revision, "settings": dict(self.defaults),
                        "warning": "ค่าประสิทธิภาพเดิมอ่านไม่ได้ กำลังใช้ค่าเริ่มต้นและยังเก็บไฟล์เดิมไว้"}

    def save(self, settings, revision):
        settings = self.validate(settings)
        with self.lock:
            current = self.read()
            if not isinstance(revision, str) or revision != current["revision"]:
                raise StaleSettings("ค่าถูกเปลี่ยนจากอีกหน้าหนึ่งแล้ว โหลดใหม่ก่อนบันทึก")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=".resources-", delete=False) as f:
                    temp = Path(f.name)
                    f.write(json.dumps({"version": 1, "settings": settings}, ensure_ascii=False).encode("utf-8"))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, self.path)
            finally:
                if temp is not None and temp.exists():
                    temp.unlink()
            return self.read()
