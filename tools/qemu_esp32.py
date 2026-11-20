"""Install Espressif's QEMU (the ESP32 emulator) for qc/checks/check_qemu_firmware.

    python tools/qemu_esp32.py install     download into .local/qemu (gitignored)
    python tools/qemu_esp32.py where       print the QEMU that QC will use

Needs no admin rights. Linux also needs `libslirp0` (apt install libslirp0);
the Windows build ships its own DLLs. The release is pinned so a QC run never
changes under us. Nothing here touches a board.
"""
import os
import platform
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "qc" / "lib"))
import qemu_board  # noqa: E402

TAG = "esp-develop-9.2.2-20250817"
BASE = "https://github.com/espressif/qemu/releases/download/" + TAG + "/"
# (os, arch) -> asset. Checked 2026-11-20 for linux x86_64; Windows name follows the same scheme.
ASSETS = {
    ("Linux", "x86_64"): "qemu-xtensa-softmmu-esp_develop_9.2.2_20250817-x86_64-linux-gnu.tar.xz",
    ("Windows", "AMD64"): "qemu-xtensa-softmmu-esp_develop_9.2.2_20250817-x86_64-w64-mingw32.tar.xz",
}
DEST = ROOT / ".local" / "qemu"


def install():
    name = ASSETS.get((platform.system(), platform.machine()))
    if not name:
        sys.exit("no QEMU build listed for %s/%s - set MICE_QEMU to your own" %
                 (platform.system(), platform.machine()))
    DEST.mkdir(parents=True, exist_ok=True)
    archive = DEST / name
    print("downloading", name)
    urllib.request.urlretrieve(BASE + name, archive)
    if name.endswith(".zip"):
        zipfile.ZipFile(archive).extractall(DEST)
    else:
        with tarfile.open(archive) as t:
            t.extractall(DEST)
    archive.unlink()
    print("installed:", qemu_board.find_qemu() or "NOT FOUND - look inside " + str(DEST))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "where"
    if cmd == "install":
        install()
    else:
        print(qemu_board.find_qemu() or "not installed (python tools/qemu_esp32.py install)")
