#!/usr/bin/env python3
"""Nong Studio standalone launcher (compatibility stub).

The server moved to code/main_python/main.py — the Mice hub, THE main
program: it discovers every module on the network and serves Nong Studio
as one of its functions at /studio/. Running this file still works: it
simply starts the hub.
"""
import runpy
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent.parent / "main_python" / "main.py"
runpy.run_path(str(HUB), run_name="__main__")
