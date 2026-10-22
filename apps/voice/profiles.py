"""Local character folders. Defaults are a snapshot; every edit belongs to a copy."""
import base64
from contextlib import nullcontext
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path
import registry


class ProfileError(ValueError):
    pass


def guarded(method):
    """A switch cannot split a request between two characters."""
    def call(handler, *args, **kwargs):
        with getattr(handler.brain, "profile_lock", nullcontext()):
            store = getattr(handler.brain, "profiles", None)
            if store:
                try:
                    store.bind(handler.brain)
                except (OSError, ValueError) as exc:
                    return handler._json({"ok": False, "error": str(exc)}, 409)
            return method(handler, *args, **kwargs)
    return call


class Profiles:
    def __init__(self, root, config, faq, styles):
        spec = registry.load(Path(__file__).resolve().parents[2] / "config" / "voice_profiles.json")
        self.FILES, self.KINDS = spec["files"], spec["assets"]
        self.MAX_ASSET = spec["maxAssetBytes"]
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        default = self.folder("default")
        if not default.exists():
            # Publish the complete snapshot once; a failed seed never becomes default.
            temp = Path(tempfile.mkdtemp(prefix=".seed-", dir=self.root))
            try:
                sources = dict(zip(self.FILES, (config, faq, styles)))
                sources["gestures.json"] = Path(__file__).resolve().parents[2] / spec["gestureFile"]
                for name in self.FILES:
                    source = Path(sources[name])
                    data = registry.load(source) if source.is_file() else {}
                    if name == "voice.json":
                        data.pop("googleApiKey", None)
                    self.write(temp / name, data)
                for kind in self.KINDS:
                    (temp / kind).mkdir()
                sequences = Path(__file__).resolve().parents[2] / spec["sequenceFolder"]
                answers = registry.load(temp / "qa_data.json")
                for item in answers.get("faqs", []):
                    for move in [item, *(item.get("moves") or [])]:
                        name = move.get("move")
                        if not name or str(name).startswith("@profile/"):
                            continue
                        try:
                            self.name(name)
                        except ProfileError:
                            continue
                        source = sequences / name
                        if source.is_file() and not source.is_symlink() and source.resolve().is_relative_to(sequences.resolve()):
                            shutil.copyfile(source, temp / "motions" / name)
                            move["move"] = "@profile/" + name
                self.write(temp / "qa_data.json", answers)
                temp.rename(default)
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
        # Older characters predate the gesture store. Add only the missing file;
        # their settings, answers and original default snapshot stay intact.
        gesture_source = Path(__file__).resolve().parents[2] / spec["gestureFile"]
        gesture_seed = registry.load(gesture_source) if gesture_source.is_file() else {}
        for folder in self.root.iterdir():
            if folder.name.startswith(".") or not folder.is_dir():
                continue
            target = self.confined(self.folder(folder.name) / "gestures.json")
            if not target.exists():
                self.write(target, gesture_seed)
        if not (self.root / "active.json").exists():
            if not self.folder("current").exists():
                self.create("current", "default")
            self.write(self.root / "active.json", {"name": "current"})

    @staticmethod
    def name(value):
        name = str(value or "")
        if (not name or len(name) > 80 or name != name.strip() or name.endswith(".")
                or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.startswith(".")
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", name)):
            raise ProfileError("Use a name without slashes or reserved file characters.")
        return name

    def confined(self, path):
        path = Path(path)
        if not path.resolve().is_relative_to(self.root):
            raise ProfileError("That file is outside this character's folder.")
        # Junctions inside a profile could alias default or another character.
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ProfileError("Linked folders and files cannot be used for characters.")
        return path

    def folder(self, name):
        return self.confined(self.root / self.name(name))

    @staticmethod
    def write(path, data):
        fd, temp = tempfile.mkstemp(prefix=".save-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=1)
                stream.write("\n")
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    @property
    def active(self):
        return self.name(json.loads(self.confined(self.root / "active.json").read_text(encoding="utf-8"))["name"])

    def file(self, name):
        return self.confined(self.folder(self.active) / name)

    def revision(self):
        h = hashlib.sha256(self.active.encode("utf-8"))
        for name in self.FILES:
            h.update(self.file(name).read_bytes())
        return h.hexdigest()

    def check(self, request, writable=True):
        if writable and self.active.lower() == "default":
            raise ProfileError("Default is kept safe. Make a named copy before saving.")
        if request.get("revision") != self.revision():
            raise ProfileError("This character changed elsewhere. Reload it before saving.")

    def bind(self, brain):
        config, faq, styles = (self.file(name) for name in self.FILES[:3])
        for path in (config, faq, styles):
            if not path.is_file():
                raise ProfileError("This character is missing a settings file.")
        if brain.cfg_path != config:
            brain.cfg_path, brain.faq_path = config, faq
            brain._cfg_mtime = None
            brain._styles = None
        brain.styles_path = styles
        # Derived audio is kept out of the immutable default snapshot, too.
        brain.cache_dir = self.confined(self.root / ".cache" / self.active)
        brain.cache_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name, source):
        name = self.name(name)
        dest, origin = self.folder(name), self.folder(source)
        if name.lower() == "default" or dest.exists():
            raise ProfileError("That character already exists. Choose another name.")
        if not origin.is_dir():
            raise ProfileError("The character to copy is missing.")
        for path in origin.rglob("*"):
            self.confined(path)
        temp = Path(tempfile.mkdtemp(prefix=".copy-", dir=self.root))
        try:
            shutil.copytree(origin, temp, dirs_exist_ok=True)
            temp.rename(dest)
        finally:
            if temp.exists():
                shutil.rmtree(temp)
        return name

    def select(self, name):
        folder = self.folder(name)
        for file in self.FILES:
            json.loads(self.confined(folder / file).read_text(encoding="utf-8"))
        self.write(self.root / "active.json", {"name": name})

    def view(self):
        names = sorted(p.name for p in self.root.iterdir()
                       if not p.name.startswith(".") and p.is_dir()
                       and not p.is_symlink() and not p.is_junction())
        assets = {}
        for kind, endings in self.KINDS.items():
            folder = self.confined(self.folder(self.active) / kind)
            assets[kind] = sorted(p.name for p in folder.iterdir()
                                  if p.suffix.lower() in endings and p.is_file()
                                  and not p.is_symlink()) if folder.exists() else []
        return {"active": self.active, "names": names, "folder": str(self.folder(self.active)), "revision": self.revision(),
                "readOnly": self.active.lower() == "default", "assets": assets}

    def asset(self, profile, kind, name):
        if kind not in self.KINDS:
            raise ProfileError("Choose sound or a robot move.")
        name = self.name(name)
        if Path(name).suffix.lower() not in self.KINDS[kind]:
            raise ProfileError("That file type cannot be used here.")
        return self.confined(self.folder(profile) / kind / name)

    def upload(self, request):
        self.check(request)
        path = self.asset(self.active, request.get("kind"), request.get("name"))
        try:
            body = base64.b64decode(request.get("data") or "", validate=True)
        except (ValueError, TypeError):
            raise ProfileError("That file could not be read.") from None
        if not body or len(body) > self.MAX_ASSET:
            raise ProfileError("Choose a file smaller than 2 MB.")
        if path.exists():
            raise ProfileError("That file already exists. Rename the new file first.")
        if request.get("kind") == "motions":
            body.decode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(body)
        return path.name
