# Mice — read this before doing anything

Short on purpose (user 2026-09-24: weekly limit hit fast; this file is sent on
every turn). The long version with every incident story: `git show b89e7fa:CLAUDE.md`.
Detailed agent procedure: `docs/COORDINATION.md` — read it only when coordinating
or handing off.

## Find the subsystem first

`python tools/systems.py which <file>`, then read that ONE header in
`docs/systems/`. Stay in that system's files; the header lists its checks.
New file or system: add it to `docs/systems.json`, then `python tools/systems.py build`.

## The plan: docs/PLAN.html

* The STATE block is the only progress record. Update it at every step:

      python tools/plan.py session claude      once; then --agent or MICE_AGENT
      python tools/plan.py add <id> "<text>"   check the id is free first
      python tools/plan.py doing <id>          picked up
      python tools/plan.py qc <id>             waiting on the gate
      python tools/plan.py done <id>           landed
      python tools/plan.py running <text> | --clear
      python tools/plan.py handoff <id> "<next step>"   before a limit or stop

* Anything the user asks for goes into the STATE block the moment it is
  asked, in their own words, before the work starts.
* Timestamps come from the clock (plan.py stamps them). Never write one by hand.
* Decisions log and verified facts in the plan are settled. Do not re-ask.
* Work tasks in id order. Take the first `todo`; do not ask what next. Keep
  going without the user saying "next". Skip `[hw]` tasks unless boards are on
  the bench — then hardware tasks go FIRST, and write measurements into the plan.
* Stop only for: a new decision the plan does not cover (ask once, with a
  recommendation, then log it), risk to hardware or saved work, or the user.
* Three failed tries: set the task back to `todo` with a note on the suspected
  wrong theory, take the next one.

## Token budget (user 2026-09-24)

* Full QC, gates, promote and land go to the `qc-runner` agent (Sonnet): the
  long output stays out of the main session. It only reports; it never fixes.
* Quick suite and single checks run in the main session with `2>&1 | tail -8`.
  An agent run costs ~57k tokens of fixed overhead (measured 2026-09-24).
* A qc-runner verdict ("real bug", "flake") is a lead. Opus checks it before fixing.
* One task, or one batch landed together, per session. Then the user runs
  `/clear`; the plan and handoff notes carry the state.
* Search before reading, read line ranges, never re-read what is in context.

## Parallel work

* Several tasks may be `doing` at once. Model reviews and design questions can
  run in the background.
* Edits to `.staging` stay serial unless the files do not overlap.
* Only ONE QC-driven process at a time (`run_qc.py`, `promote.py`, measurement
  scripts share the fake serial port and `qc_marks`). Check `plan.py show` for
  `RUNNING:` first.
* Nothing heavy (GPU model, big download) while a gate runs: load-induced false
  failures cost a 7-minute gate each.
* Do not edit `.staging` while a gate runs: promote copies what is on disk at the end.
* Python on Windows: `write_text()` turns LF into CRLF. Use `write_bytes`,
  `open(..., newline="")` or the Edit tool.

## Other models

* Codex helps first; Gemini and others are fallback (docs/COORDINATION.md).
* Gemini: always `--model gemini-3.8-flash-high` (user 2026-09-17: no Pro).
* Every `agy` prompt starts with `tools/ai_brief.txt` and a line budget:
  `agy -p "$(cat tools/ai_brief.txt) <question> Answer in at most 25 lines." --mode plan --model <id>`
* `agy` prompt: no `"` character (truncates silently). Pass `--add-dir` for
  `.staging` or it reviews the promoted tree. Ask for FIND/REPLACE, not whole files.
  `agy models` lists exact ids.
* Design questions (screens, data shapes, protocols): ask the panel before
  writing and again after QC is green:
  `python tools/ai_panel.py --ask "<q>" --dir <path> --out <report.md>`
* Every model finding is a shortlist, not a fact. Verify against the code.
* On a failure, ask another model whether the theory is wrong before grinding.

## Rules that already cost real work

1. The code is the source of truth — not the plan, a comment, or the user's description.
2. Work in `code/.staging`. Promote with `python E:/final_proj/mice/code/promote.py`
   (runs full QC, copies back only when green). Always the absolute path.
3. NEVER run `promote.py --init` while staging holds unpromoted work.
4. Every fix needs a QC check, proven by breaking the fix:
   `python tools/sabotage.py --check <name> --spec -` (always restores the file).
   `t.ok(cond, label, detail)` takes a detail; `t.eq` and `t.contains` do NOT.
5. Assert on what reached the module (`fake_serial.wire`), not on what the UI says.
6. `MiceHub.exe`, `promt.md`, `docs/PLAN.html` are in `promote.py` SKIP_FILES. Keep them there.
7. Finish with `python tools/land.py --done <ids>`: quick suite, gate, promote, plan.

## Code style

* Comments keep the WHY: measurement + date, the reason, the hidden trap.
  About 6 lines per block, 1 per line comment. Long stories go in the QC
  check docstring.
* Nothing hardcoded: a list lives in DATA (registries), one source not copies,
  a new thing is a new file or entry. Test: can someone add the next one
  without opening this file?
* Shallow beats clever. No layers that exist only to be layers.
* Every formula has an entry in `docs/ref_data.js` (`check_ref` enforces it).
* Replies to the user: short, except warnings, destructive steps, and "why".

## Every screen is for a designer, not a programmer

On every page the hub serves: anything settable is clickable; plain words on
the surface; technical detail (addresses, ids, ports, errors, status codes)
behind the technical switch; simple on top, complete underneath (Home /
Modules). `check_designer_first` holds it; banned words are in
`qc/data/designer_words.json`.

Gemini designs visible surfaces; Claude builds and verifies logic.

## Verification

```
python qc/run_qc.py --quick        while iterating (~10 s)
pio run -e mice_nong -e mice_cam -e mice_lift -e mice_blank
python qc/run_qc.py                full, real browser (~8 min)
python E:/final_proj/mice/code/promote.py
```

Rebuild the exe when `main_python/` or `config/` changed:
`python -m PyInstaller --clean MiceHub.spec` — always the spec. A bare script
build ships an exe with no pages and overwrites the spec.

## Cautions

* Almost nothing is tested on real hardware. Only A1-1 and A1-2 (nong id 85,
  2026-08-19). Say "tested against fakes" plainly.
* `MiceHub.exe` goes stale whenever hub code changes.
* Architecture is in `docs/architecture/` (with file:line evidence). Read it
  before exploring from scratch.
* `firmware/CLAUDE.md` and `nong/main_python_set_nong/CLAUDE.md` still apply.
