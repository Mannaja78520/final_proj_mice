# Handover

Written by `tools/handover.py`. Read this first if you are picking up work somebody else started.

**When:** 2026-09-08 22:23  
**Last step:** A25 landed: rainbow guarded, shortcuts tab named

**Source saved:** `E:\final_proj\mice\code`

## Snapshots taken

* **hub, shared web, QC and tools** - patch 0029: `E:\final_proj\mice\code\patches_code\0029_a25-landed-rainbow-guarded-shortcuts-tab-named`
* **Nong Studio web app** - patch 0081: `E:\final_proj\mice\code\nong\main_python_set_nong\patches\0081_a25-landed-rainbow-guarded-shortcuts-tab-named`
* **firmware and the module page** - patch 0052: `E:\final_proj\mice\code\firmware\patches\0052_a25-landed-rainbow-guarded-shortcuts-tab-named`

Each area keeps its own numbered history and can be put back on its own: `--list` to see them, `--restore <n>` to go back. Nothing here reverts anything by itself.

## What is in .staging but not promoted

* changed in staging: PATCHES.md
* changed in staging: firmware/PATCHES.md
* changed in staging: nong/main_python_set_nong/PATCHES.md

## What the plan still has open

* A24-41 [todo] 2026-09-08 13:01  hw=lift board + PCM5102A + TPA3118 + the 12V speaker  — user 2026-09-08: add to the plan to 

## How to carry on

```
python qc/run_qc.py --quick                    ~90 s, is it green now
python firmware/tools/gen_tables.py            after editing WebUI.h or mice.css
python qc/run_qc.py                            full, real browser
python E:/final_proj/mice/code/promote.py      gate + promote, absolute path
python tools/plan.py show                      what the plan says
python tools/handover.py save "<next step>"     checkpoint again
```

Work in `code/.staging`, never the real tree. Read `CLAUDE.md` first - it is the standing agreement, and every rule in it was paid for.
