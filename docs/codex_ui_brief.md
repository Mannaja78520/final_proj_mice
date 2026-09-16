# Prompt for Codex — take the rainbow off, make the screens cute and easy

Copy everything below the line into Codex. It is written to be pasted whole.

---

You are working in `E:\final_proj\mice\code` — the control software for a robot
rig called Mice: a Python hub (`main_python/`), an ESP32 firmware whose module
website is compiled into it (`firmware/`), a pose editor called Nong Studio
(`nong/main_python_set_nong/`), and a QC suite of 170 checks (`qc/`).

Read `CLAUDE.md` in the repo root before touching anything. It is the standing
agreement for this project and it applies to you exactly as written. The rules
that will bite you fastest are repeated below, but read the file.

## THE JOB

**1. Take the rainbow decoration out, everywhere.**

`shared/web/mice.css` paints a four-colour gradient across the top edge of
every page and a small gradient underline beneath every `h1`:

```css
body{border-top:var(--sp-2) solid transparent;
  border-image:linear-gradient(to right,var(--ty-nong),var(--ty-lift),
    var(--ty-cam),var(--acc)) 1}

h1::after{content:"";display:block;height:3px;width:72px;margin-top:var(--sp-2);
  border-radius:var(--r-pill);
  background:linear-gradient(to right,var(--ty-nong),var(--ty-cam))}
```

The owner's verdict: *it does not help.* Remove both, and any other purely
decorative rainbow you find in the web files. Do NOT touch:

* the per-type colours themselves (`--ty-nong`, `--ty-lift`, `--ty-cam`). They
  carry meaning: a module row is edged in its own type colour and the type is
  also written in words on the badge beside it. Keep that.
* the LED strip's `rainbow` EFFECT (`RGB EFFECT rainbow`, the 🌈 button in
  `main_python/web/rgb.html`). That is a real feature of the light strip, not
  decoration. It stays.

**2. Make the web interface cuter and easier to use than it is now.**

Every screen here is used by DESIGNERS, not programmers. That is a standing
rule in `CLAUDE.md` and `check_designer_first` enforces part of it:

* anything settable is clickable — a value somebody can only change by editing
  a file or typing a URL is a bug;
* plain words on the surface; technical detail (addresses, ids, ports, status
  codes, exception text) hides behind the "Show technical details" switch that
  already exists on every page (`miceAdv`);
* simple on top, complete underneath — the Home / Modules split is the pattern;
* every failure says what to do next, in the place the person is looking.

"Cute" here means warm and calm, not childish: friendlier spacing and rounding,
kinder empty states, clearer grouping, plain encouraging words, restrained use
of the single accent colour. Dark stays the default — a bright screen spills
light into the show area. One accent colour carries interaction; semantic
colours (ok / warn / err) mean state only, never decoration.

The screens, in the order they matter:

| file | what it is |
|---|---|
| `main_python/web/hub.html` | the main screen: modules, tools, settings |
| `firmware/src/web/WebUI.h` | the module page (Move it / Shows & files / Setup) |
| `nong/main_python_set_nong/web/` | Nong Studio: `index.html`, `style.css`, `app.js` |
| `main_python/web/rgb.html` | the light-strip tool |
| `main_python/web/help.html` | the manual |
| `shared/web/mice.css` | the ONE design system every page links |

## RULES YOU MUST FOLLOW (they have each cost real work here)

1. **Work in `code/.staging`, never the main tree.** Promote only with
   `python E:/final_proj/mice/code/promote.py` — always that absolute path. It
   runs the full QC suite and copies back only if every check passes.
2. **Never run `promote.py --init`** while staging holds unpromoted work: it
   refreshes staging *from* main and deletes what you did.
3. **Do not edit `.staging` while a gate is running.** `promote.py` copies what
   is on disk when it finishes, so a file edited mid-run can be promoted
   without any check having read that version.
4. **`shared/web/mice.css` is the only design system.** Every page links it, and
   the ESP32 serves the SAME file from flash (`gen_tables.py` compiles it into
   `web/MiceCss.h`). Change tokens there, not per page. `check_design_system`
   fails if the board and the hub serve different bytes.
5. **`firmware/src/web/WebUI.h` is the MASTER module page and is not compiled.**
   After editing it run `python firmware/tools/gen_tables.py`, which writes
   `firmware/generated/web/ModuleUI.h` — that generated file is what QC reads.
6. **Never delete an id or class a script or a check uses.** Restyle, re-order,
   hide — but keep the hooks. Two examples of what depends on them: the module
   page's cards are shown by `applyTabs()` from `data-tab` + `data-cap`, and
   the QC browser checks look up ids like `#audCard`, `#castBtn`, `#stgState`.
7. **After ANY change to `nong/main_python_set_nong/web/`, run
   `python save_patch.py "<what changed>"` in that folder.** Every change is a
   preserved snapshot there. Do not hand-edit `patches/` or `PATCHES.md`.
8. **Document every feature in `main_python/web/help.html`**, in the same change.
   The `docs` check fails when something exists that the page does not describe.
   If you touch anything commandable, update `firmware/COMMANDS.md` too.
9. **Writing a file from Python on Windows rewrites every line ending.**
   `Path.write_text()` turns `\n` into `\r\n` and a one-line edit then shows up
   as a whole-file change. Use `write_bytes`, or `open(..., newline="")`.
10. **Comments: keep the WHY, cut the story.** About six lines for a block, one
    for a line comment. Say what breaking the line would cost, not what the
    code plainly does.
11. **Nothing hardcoded.** A list belongs in data, not in a source file. If you
    add anything list-shaped, it goes in a config/registry file that somebody
    can edit without opening code.

## VERIFY, EVERY TIME

```
python qc/run_qc.py --quick                      ~90 s, while iterating
python firmware/tools/gen_tables.py              after editing WebUI.h or mice.css
python qc/run_qc.py                              full, drives a real browser (~10 min)
python E:/final_proj/mice/code/promote.py        gate + promote, absolute path
```

The bar to clear: **the full suite green, 4483 assertions or more, 0 failed.**
These checks are the ones your work will meet first — read them before you
design, they encode decisions already taken:

* `check_design_system` — one stylesheet, board and hub byte-identical
* `check_designer_first` — banned programmer words on the surface
  (`qc/data/designer_words.json`)
* `check_responsive` — every page in a real browser at 360 → 1920px, nothing
  scrolls sideways, touch targets ≥ 36px under `pointer:coarse`
* `check_modsite_tabs`, `check_modsite_answers`, `check_hub_answers`,
  `check_studio_notice` — the tabs, and the rule that a control which acts says
  what happened, where the person is standing
* `check_themes` — themes are one block each and all stay readable

**Every fix needs a check, and a check only counts once you have broken the fix
and watched it fail.** The cycle is one command:

```
python tools/sabotage.py --check <name> --spec <spec.json>
```

with a spec of `[{"file": ..., "find": ..., "replace": ..., "why": ...}]`. It
patches, runs the check, and always puts the file back. A sabotage whose text
is not found is an ERROR, not a pass. If a sabotage comes back SILENT, your
check is too loose — tighten it until it bites. That happened four times in the
last two days here, and each time the check was the thing that was wrong.

## THE PLAN

`docs/PLAN.html` is the only record of progress and the owner reads it. Update
it as you go, not at the end:

```
python tools/plan.py add A25-1 "<what the owner asked, in their words>" --status doing
python tools/plan.py doing A25-1
python tools/plan.py running "full QC gate for the new look"
python tools/plan.py done A25-1
python tools/plan.py note A25-1 "<what landed, and the measurement>"
python tools/plan.py running --clear
```

Put the owner's request in first, in their own words, before you start:

> remove the rainbow strip in the web all of it it not help and make the web UI
> more cute and easy to use than this

## CHECKPOINT AS YOU GO — SOMEBODY ELSE MAY HAVE TO FINISH

You may run out of budget mid-task. If that happens the owner will hand the
rest to Claude, and it must be able to pick up without guessing. So:

```
python tools/handover.py save "what I just finished"
```

Run it **before you start**, after each meaningful step, and before you stop.
It snapshots every area through the patchers that already exist (hub + shared
+ QC + tools, Nong Studio's web app, the firmware), and writes
`docs/HANDOVER.md` with: what you last did, the snapshot numbers, what is in
`.staging` and not yet promoted, what the plan still has open, and the commands
to carry on with. `python tools/handover.py show` reads it;
`python tools/handover.py undo` prints how to put any area back.

Nothing is ever overwritten: each area keeps a numbered, append-only history,
and restoring one saves the current version first. Do NOT use `git checkout` to
undo — the real tree carries uncommitted work by design, and that has destroyed
promoted work here before.

Keep `docs/PLAN.html` current with the same discipline (`tools/plan.py`). The
plan says WHAT is left; the handover note says WHERE you stopped.

## DO THE DESIGN YOURSELF

No Gemini, no `agy`, no `tools/ai_panel.py` for this work. The owner asked for
Codex to do all of it. Where the repo's rules say design goes to Gemini Pro,
that is suspended for this task only — you are the designer here. Everything
else in `CLAUDE.md` still applies.

## WHAT DONE LOOKS LIKE

1. No decorative rainbow anywhere in the web files; the type colours still
   carry meaning and the LED rainbow effect still works.
2. The hub, the module page, Studio, the light tool and the help page look like
   one warm, calm, friendly product, and are easier to use than before —
   fewer decisions on screen at once, kinder empty and error states, plain
   words on the surface.
3. `python qc/run_qc.py` green, and a Studio patch snapshot saved.
4. New checks for anything you changed that could silently rot back, each one
   proved by a sabotage that was caught.
5. `docs/PLAN.html` says what you did, and `help.html` describes anything new.
6. Report at the end: what you changed, what you measured, what you did NOT do
   and why. If something in the existing design turns out to be there for a
   reason you cannot see, say so instead of removing it.
