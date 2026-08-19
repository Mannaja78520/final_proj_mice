# -*- mode: python ; coding: utf-8 -*-
"""MiceHub as ONE file: no folders to copy, no Python to install.

Asked for on 2026-08-19, about the second PC at a venue: *if other pc don't
have python html css node or other thing what should we do*. The answer is that
it should need none of them, and until now the exe was only half of that - the
code was frozen but every page, stylesheet and registry still had to travel
beside it in the right folders.

What is bundled here is exactly what the hub READS and never writes. Anything
written at runtime - the password hash, known hubs, Studio's projects, the
firmware images - is deliberately absent, because PyInstaller unpacks a
one-file build into a temporary folder that is deleted on exit. A saved project
in there would vanish when the app closed, which is a far worse bug than a
missing file.

Build:  python -m PyInstaller --clean MiceHub.spec
"""
from pathlib import Path

ROOT = Path(SPECPATH)                                    # noqa: F821 - code/

datas = [
    (str(ROOT / "main_python" / "web"), "main_python/web"),
    (str(ROOT / "shared" / "web"), "shared/web"),
    (str(ROOT / "nong" / "main_python_set_nong" / "web"),
     "nong/main_python_set_nong/web"),
    # The registries, and the reader that turns them into lists. A module type
    # or a servo is one entry in these files, so they are not optional extras.
    (str(ROOT / "tools" / "registry.py"), "tools"),
    (str(ROOT / "firmware" / "config"), "firmware/config"),
    # The web apps themselves. Missed on the first build, and the exe started
    # perfectly and served an EMPTY app list - the registry loaded, found no
    # folder, and reported nothing wrong. Only running the exe on its own
    # showed it, which is why check_onefile derives this list from the
    # registry rather than trusting anyone to remember.
    (str(ROOT / "apps"), "apps"),
    # Served to a module's own page when it is reached over WiFi.
    (str(ROOT / "firmware" / "src" / "web" / "WebUI.h"), "firmware/src/web"),
]

a = Analysis(                                            # noqa: F821
    [str(ROOT / "main_python" / "main.py")],
    pathex=[str(ROOT / "main_python")],
    binaries=[],
    datas=datas,
    hiddenimports=["hub_auth", "discovery", "mdns", "qr"],
    excludes=["tkinter", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)                                        # noqa: F821

exe = EXE(                                               # noqa: F821
    pyz, a.scripts, a.binaries, a.datas, [],
    name="MiceHub",
    console=True,
    icon=str(ROOT / "main_python" / "nong.ico"),
    upx=False,
    disable_windowed_traceback=False,
)
