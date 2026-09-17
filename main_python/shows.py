"""SHOWS: saved sequences played one after another.

Asked 2026-09-17: *another tab to mix a lot of sequence ... link the sequence in
series ... like greeting then run the sequence byebye ... mix and match*.

A show is one small JSON file in shows/, listing sequence files by name:

    {"name": "welcome", "loop": false,
     "items": [{"seq": "greeting.yaml", "hold": 500}, {"seq": "byebye.yaml"}]}

The sequences are never copied or changed, so one greeting can sit in many
shows. A person can edit the file by hand; Studio's Shows tab writes the same.
The hub plays a show as one list of steps (ShowPlayer), so it runs over any
link and the robot's own speed cap times the move from one sequence into the next.
"""
import json
import re
import time
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9_\-][A-Za-z0-9 _.\-]{0,79}$")


def _file(name):
    name = str(name or "").strip()
    if name.endswith(".json"):
        name = name[:-5]
    if not NAME.match(name):
        raise ValueError("a show name may use letters, numbers, space, _ - and .")
    return name + ".json"


class Shows:
    """The shows folder: list, load, save, delete, and turn one into steps."""

    def __init__(self, folder: Path, sequences: Path):
        self.folder = Path(folder)
        self.sequences = Path(sequences)

    def names(self):
        if not self.folder.is_dir():
            return []
        return sorted(p.stem for p in self.folder.glob("*.json") if p.is_file())

    def load(self, name):
        f = self.folder / _file(name)
        if not f.is_file():
            raise FileNotFoundError("no show called %s" % name)
        return self.clean(json.loads(f.read_text(encoding="utf-8")))

    @staticmethod
    def clean(show):
        """Only the fields a show has, with sane values - what is saved is what plays."""
        items = []
        for it in (show or {}).get("items") or []:
            seq = str((it or {}).get("seq") or "").strip()
            if seq:
                items.append({"seq": seq, "hold": max(0, int((it or {}).get("hold") or 0))})
        return {"name": str((show or {}).get("name") or "").strip(),
                "loop": bool((show or {}).get("loop")), "items": items}

    def save(self, show):
        show = self.clean(show)
        fname = _file(show["name"])
        self.folder.mkdir(parents=True, exist_ok=True)
        f = self.folder / fname
        existed = f.exists()
        tmp = f.with_suffix(".tmp")
        tmp.write_bytes(json.dumps(show, indent=1).encode("utf-8"))
        tmp.replace(f)
        return fname, existed

    def delete(self, name):
        """Moved into shows/.deleted/, never erased: a mis-click is recoverable."""
        f = self.folder / _file(name)
        if not f.is_file():
            raise FileNotFoundError("no show called %s" % name)
        bin_ = self.folder / ".deleted"
        bin_.mkdir(exist_ok=True)
        dest = bin_ / (time.strftime("%Y%m%d-%H%M%S_") + f.name)
        f.replace(dest)
        return ".deleted/" + dest.name

    def steps(self, show, parse):
        """All the sequences' steps, in order. parse(text) is main.seq_steps.

        A missing or broken sequence stops the whole show with its name: playing
        half a show and skipping the rest silently is worse than not starting.
        """
        show = self.clean(show)
        if not show["items"]:
            raise ValueError("this show has no sequences in it yet")
        out = []
        for n, it in enumerate(show["items"], 1):
            f = self.sequences / it["seq"]
            if "/" in it["seq"] or "\\" in it["seq"] or not f.is_file():
                raise ValueError("step %d: no saved sequence called %s" % (n, it["seq"]))
            try:
                got = parse(f.read_text(encoding="utf-8"))["steps"]
            except ValueError as e:
                raise ValueError("step %d, %s: %s" % (n, it["seq"], e))
            if not got:
                raise ValueError("step %d: %s has no poses" % (n, it["seq"]))
            got = [dict(s) for s in got]
            got[-1]["hold"] = got[-1].get("hold", 0) + it["hold"]   # pause after it
            out += got
        return out
