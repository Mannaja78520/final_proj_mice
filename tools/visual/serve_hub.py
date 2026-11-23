"""Boot the QC hub (fake module on COM99) and keep it up for the screenshot tool.

Prints the base URL on the first line. Throwaway password/ext files, same as QC.
"""
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "qc"))
sys.path.insert(0, str(ROOT / "qc" / "lib"))
import qc as F  # noqa: E402

base, _main = F.start_hub()
print(base, flush=True)
while True:
    time.sleep(3600)
