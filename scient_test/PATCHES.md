# Test plan patches

Every change to the test files is saved here as a numbered patch, so a result sheet can always be matched back to the exact version of the test that produced it. Old patches are never removed — restore any of them with `python save_patch.py --restore <n>`.

Recorded data in `results/` is never patched: that is measurement, not source.

| # | when | change | files |
|---|---|---|---|
| 0001 | 2026-07-26 00:04 | initial test plan: nong (10 IV) + lift (11 IV) modules, rs485/wifi/usb as separate per-module transport tests, results CSVs, bench.py | 9 |
| 0002 | 2026-07-26 00:54 | add testapp.py measuring app (ms timing the eye cannot do) + simulator + who-measures-what docs | 11 |
