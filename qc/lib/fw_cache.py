"""Firmware build-artifact cache for QC: build once, reuse while nothing changed.

A fresh worktree or staging tree has no firmware/.pio, so every full gate used
to compile five environments (414-474 s measured 2026-11-25) for firmware that
had not changed. This cache lives OUTSIDE the repo (~/.platformio/
qc_artifact_cache/<key>/) and is keyed per environment on:

  * every firmware/config/shared-web input the build reads (the caller's hash,
    check_build_split._inputs_key: firmware sources, platformio.ini, config,
    the generator, the shared stylesheet),
  * the PlatformIO version and the version of every installed platform and
    package (a toolchain or framework upgrade changes the binary),
  * the environment name.

A hit copies the binaries into firmware/.pio/build/<env>/ and the check still
runs EVERY assertion on them. An entry is only written after the check's own
assertions passed (`store`), and every restore re-verifies size and sha256, so a
corrupt or truncated entry is a miss and is rebuilt, never trusted.
Force a real build: `run_qc.py --rebuild-firmware` or MICE_QC_REBUILD=1.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path.home() / ".platformio" / "qc_artifact_cache"
PIO_HOME = Path.home() / ".platformio"
# what the checks read from a build dir: images (flash, OTA, QEMU) and the elf
ARTIFACTS = ("firmware.bin", "bootloader.bin", "partitions.bin", "firmware.elf")


def forced():
    return os.environ.get("MICE_QC_REBUILD", "") not in ("", "0")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def toolchain_key(pio):
    """Hash of the PlatformIO version + every installed platform/package version."""
    h = hashlib.sha256()
    try:
        r = subprocess.run([str(pio), "--version"], capture_output=True, text=True, timeout=60)
        h.update((r.stdout or "").strip().encode())
    except (OSError, subprocess.SubprocessError):
        h.update(b"pio?")
    for sub, meta in (("platforms", "platform.json"), ("packages", "package.json")):
        for d in sorted((PIO_HOME / sub).glob("*")):
            ver = ""
            try:
                ver = str(json.loads((d / meta).read_text(encoding="utf-8")).get("version", ""))
            except (OSError, ValueError):
                pass
            h.update(("%s/%s=%s;" % (sub, d.name, ver)).encode())
    return h.hexdigest()


class ArtifactCache:
    def __init__(self, inputs_key, toolchain, build_root, root=ROOT):
        self.inputs, self.toolchain = inputs_key, toolchain
        self.build_root = Path(build_root)          # firmware/.pio/build
        self.root = Path(root)

    def key(self, env):
        h = hashlib.sha256()
        for part in (self.inputs, self.toolchain, env):
            h.update(part.encode() + b"\0")
        return h.hexdigest()

    def _dir(self, env):
        return self.root / self.key(env)

    def restore(self, env):
        """Copy a verified entry into the build dir. Returns the pio output text,
        or None on a miss (absent, forced, or failing its size/hash check)."""
        if forced():
            return None
        d = self._dir(env)
        try:
            man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        files = man.get("files") or {}
        if "firmware.bin" not in files:
            return None
        for name, meta in files.items():
            p = d / name
            if not p.is_file() or p.stat().st_size != meta["size"] or _sha(p) != meta["sha256"]:
                return None
        dest = self.build_root / env
        dest.mkdir(parents=True, exist_ok=True)
        for name in files:
            shutil.copy2(d / name, dest / name)
        return man.get("out", "")

    def store(self, env, out):
        """Record the build in the build dir as a green entry (atomic rename)."""
        src = self.build_root / env
        files = {}
        tmp = self.root / (self.key(env) + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        for name in ARTIFACTS:
            p = src / name
            if p.is_file():
                shutil.copy2(p, tmp / name)
                files[name] = {"size": p.stat().st_size, "sha256": _sha(tmp / name)}
        if "firmware.bin" not in files:
            shutil.rmtree(tmp, ignore_errors=True)
            return False
        (tmp / "manifest.json").write_text(json.dumps({"env": env, "files": files, "out": out}),
                                           encoding="utf-8")
        final = self._dir(env)
        shutil.rmtree(final, ignore_errors=True)
        os.replace(str(tmp), str(final))
        return True
