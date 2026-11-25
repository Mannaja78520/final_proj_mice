"""Each check process writes into its own copy of projects / sequences / shows.

2026-11-26: about 35 checks save into the studio data folders under fixed names
(qc_video_page, qc_welcome, dummy_<date>.yaml ...). Run a check twice at once and
the copies overwrote each other (3 copies of check_video_page: 1 passed); nine
checks failed that way. qc.isolate_data now gives every hub its own copy. This
proves it: the hub's folders are NOT the tree's, they start with what the tree
ships, and a save through the hub's API never reaches the tree.
"""
import json
from pathlib import Path

import fake_serial
import qc as F

AREA = "tooling"
TITLE = "a hub's saved projects and sequences land in this check's own copy, not in the tree"


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    real = F.STUDIO
    box = main._qc_data_box
    t.ok(Path(main.PROJECTS) == box / "projects" and Path(main.PROJECTS) != real / "projects",
         "the hub's projects folder is its own copy", str(main.PROJECTS))
    t.ok(Path(main.SEQUENCES) == box / "sequences" and Path(main.SHOWS.folder) == box / "shows",
         "and so are sequences and shows")
    shipped = sorted(p.name for p in (real / "projects").glob("*.json"))[:3]
    t.ok(all((Path(main.PROJECTS) / n).is_file() for n in shipped),
         "the copy starts with what the tree ships", repr(shipped))
    name = "qc_isolation_probe"
    # save through the hub's own file writer, the same call the API uses
    main.write_atomic(Path(main.PROJECTS) / (name + ".json"), json.dumps({"qc": 1}))
    t.ok((Path(main.PROJECTS) / (name + ".json")).is_file(), "a save lands in the copy")
    t.ok(not (real / "projects" / (name + ".json")).exists(),
         "and never in the tree's own projects folder",
         "two overlapping runs would overwrite each other's files")
    t.ok(F.isolate_data(main) == box, "asking again keeps the same copy (one per process)")
