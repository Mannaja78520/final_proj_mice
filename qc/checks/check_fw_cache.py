"""Firmware build-artifact cache: a hit only for the same inputs, never a bad copy.

User 2026-11-25: the firmware changed once, yet every gate rebuilt it (414-474 s
on a fresh tree). qc/lib/fw_cache.py keeps green builds outside the repo, keyed
on inputs + toolchain + env. This check proves the rules on fake artifacts, with
no compiler: same key hits, any changed input / toolchain / env misses, a
corrupted or truncated entry is a miss (so it is rebuilt), and
MICE_QC_REBUILD=1 forces a miss.
"""
import os
import tempfile
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "the firmware artifact cache hits only for identical inputs and rejects corrupt entries"


def run(t):
    import fw_cache
    d = Path(tempfile.mkdtemp(prefix="qc_fwc_"))
    root, build = d / "cache", d / "build"
    (build / "mice_nong").mkdir(parents=True)
    for name, data in (("firmware.bin", b"F" * 5000), ("bootloader.bin", b"B" * 100),
                       ("partitions.bin", b"P" * 50), ("firmware.elf", b"E" * 300)):
        (build / "mice_nong" / name).write_bytes(data)
    out = "Flash: [====      ]  41.0% (used 1 bytes)"

    c = fw_cache.ArtifactCache("inputsA", "toolsA", build, root)
    t.ok(c.restore("mice_nong") is None, "nothing cached yet is a miss")
    t.ok(c.store("mice_nong", out), "a green build is stored")
    shutil_rm(build / "mice_nong")
    got = c.restore("mice_nong")
    t.ok(got == out, "the same key restores the pio output", repr(got))
    t.ok((build / "mice_nong" / "firmware.bin").read_bytes() == b"F" * 5000
         and (build / "mice_nong" / "bootloader.bin").is_file(),
         "and the binaries are back in the build dir")

    t.ok(fw_cache.ArtifactCache("inputsB", "toolsA", build, root).restore("mice_nong") is None,
         "a changed firmware input is a miss")
    t.ok(fw_cache.ArtifactCache("inputsA", "toolsB", build, root).restore("mice_nong") is None,
         "a changed toolchain version is a miss")
    t.ok(c.restore("mice_lift") is None, "another environment is a miss")

    os.environ["MICE_QC_REBUILD"] = "1"
    try:
        t.ok(c.restore("mice_nong") is None, "MICE_QC_REBUILD=1 forces a real build")
    finally:
        del os.environ["MICE_QC_REBUILD"]

    entry = root / c.key("mice_nong")
    # corrupt one byte (same size): the hash catches it
    blob = bytearray((entry / "firmware.bin").read_bytes())
    blob[10] ^= 0xFF
    (entry / "firmware.bin").write_bytes(bytes(blob))
    t.ok(c.restore("mice_nong") is None, "a flipped byte in the cached binary is a miss")
    c.store("mice_nong", out)
    t.ok(c.restore("mice_nong") == out, "rebuilding rewrites a good entry")
    (entry / "firmware.bin").write_bytes(b"F" * 10)
    t.ok(c.restore("mice_nong") is None, "a truncated cached binary is a miss")

    shutil_rm(build / "mice_nong" / "firmware.bin", file=True)
    t.ok(not c.store("mice_nong", out), "a build with no firmware.bin is never stored")

    src = (F.QC / "checks" / "check_build_split.py").read_text(encoding="utf-8")
    t.ok("cache hit" in src and "cache miss" in src and "not t.failed" in src,
         "check_build_split prints hit/miss and stores only after its assertions held")


def shutil_rm(p, file=False):
    import shutil
    if file:
        Path(p).unlink(missing_ok=True)
    else:
        shutil.rmtree(p, ignore_errors=True)
