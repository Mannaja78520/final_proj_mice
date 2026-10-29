#!/usr/bin/env python3
"""Forwarder for run_qc.py to support `python code/qc/run.py` invocation."""
import subprocess
import sys
from pathlib import Path

qc_script = Path(__file__).resolve().parent / "run_qc.py"
res = subprocess.run([sys.executable, str(qc_script)] + sys.argv[1:])
sys.exit(res.returncode)
