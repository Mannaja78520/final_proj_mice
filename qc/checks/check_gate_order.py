"""The firmware build runs before the checks that read its images.

A26-83, 2026-09-21: the first full gate on every fresh staging tree failed
check_flash, check_ota and check_ota_only ("this PC has a full nong image to
work from"), and the second gate on the same tree passed. check_build_split
builds the images, and it is a SOLO check - and SOLO checks ran AFTER the
parallel pools, so on a tree with no firmware/.pio yet the image readers ran
first and found nothing. Five gates were lost to it in one day.
"""
import qc as F

AREA = "tooling"
TITLE = "the firmware build runs before the checks that read its images"


def run(t):
    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")
    t.ok('RUN_FIRST = {"check_build_split"}' in src,
         "check_build_split is marked to run first")
    first = src.find("for f, mod in first:")
    pools = src.find("pools, futs, by_path = [], [], {}")
    t.ok(0 < first < pools,
         "and it runs before the parallel pools start",
         "first at %d, pools at %d" % (first, pools))
