# Mice — read this before doing anything

## There is an active plan. Follow it.

**`docs/PLAN.html`** is the working document for the current refactor. Open it
first, every session. It holds:

* the resume rules (below, in full),
* the **STATE block** — ~40 tasks with `id: status <when> — note`. This is the
  **only** place progress is recorded, and the Progress card at the top of the
  page is rendered from it. Two rules, because the user has to be able to SEE
  that work is happening:
  * **update the plan at every step, not at milestones.** The user asked for
    this directly, 2026-08-18: the page said *nothing in progress* while work
    was happening, so it could not be told from stalled. It is one command:

        python tools/plan.py doing A2-1 A3-1     picked it up
        python tools/plan.py qc A2-1             built, waiting on the gate
        python tools/plan.py done A2-1           landed
        python tools/plan.py running full QC     what is in flight now
        python tools/plan.py running --clear     nothing in flight
        python tools/plan.py show                what the page says

    Run it when you START something, when it goes to the gate, when it lands,
    and whenever a long job begins or ends. It stamps the clock itself, so the
    timestamps cannot drift the way hand-written ones did;
  * mark a task `doing` **when you pick it up**, not only `done` when it lands;
  * stamp the line you touch with the date and time (`2026-08-18 10:44`),
    **read from the machine, never guessed** — `date "+%Y-%m-%d %H:%M"` when you
    pick a task up, and the `when:` line in the patch snapshot you just saved
    when it lands. Stamps written from memory drifted by up to five hours here,
    and two of them were in the future, which makes the whole page untrustworthy.
* **decisions already taken** — do not re-open them and do not ask the user
  again. They are settled and the reasons are written down.
* **verified facts** — assumptions from the original brief that the code
  disproved. Do not rebuild things that do not exist.

Work the tasks in `id` order unless the user says otherwise. Do not ask which
task to do next — read the STATE block and take the first `todo`.

**Keep going by yourself.** The user said so directly, 2026-08-18: they should
not have to say "next" between tasks. Finish one, promote it, mark it, take the
next `todo`, and carry on. Skip anything marked `[hw]` — it needs a real board —
and come back to those when the user says the hardware is on the bench.

Stop only for: a genuinely new decision the plan does not cover (ask once, with
a recommendation), something that would damage hardware or lose saved work, or
the user interrupting. Running out of easy work is NOT a reason to stop: there
are usually thirty tasks a PC can finish.

**More than one thing in progress at a time.** The user asked for this,
2026-08-18: *we can use multi AI to run in progress more than 1 progress, and
then review and edit if wrong, to save time*. So:

* several tasks may be `doing` at once — the Progress card handles it and says
  which ones;
* fan the SLOW parts out in parallel and in the background: model reviews, the
  design of a screen, a long QC run;
* but keep EDITS to `.staging` serialised, one task at a time, unless the tasks
  touch files that do not overlap. Two parallel edits to one file is a lost
  edit, and this session has already lost work to a stray path;
* promote tasks together when they landed together — one QC gate for the batch;
* but NEVER run two things that drive the fake module at once. `run_qc.py`,
  `promote.py` and any throwaway measurement script all report through the same
  fake serial port and the same `qc_marks` list. Running a measurement during a
  promote made `check_responsive` fail with *measurements missing* — its 25
  rows had been displaced by the other script's marks, and its `done` had been
  eaten. That looked exactly like a flake and was not one. One QC-driven
  process at a time; model calls and reading are safe to overlap.

**Every model call starts with `tools/ai_brief.txt`.** The user pays for their
output too, 2026-08-18: *make gemini use less token like claude, we have caveman,
maybe we use too much*. So prepend that file to every `agy` prompt and give a
hard line budget:

    agy -p "$(cat tools/ai_brief.txt)
    <the actual question>
    Answer in at most 25 lines." --mode plan --model <id>

**Design work goes to Gemini Pro, and waits for it.** The user's instruction,
2026-08-19: *when gemini pro hit limit you can check when it will back... don't
stuck with flash model it not good enough and your model make the web not good
like gemini*. So for anything a person LOOKS at — a screen, a palette, a
layout — the model is Pro. If Pro is rate-limited or times out, shorten the
prompt and try again, or come back to it later; do NOT fall back to Flash and
do not design it yourself. Flash stays for trivial lookups and for review
questions where the answer is a fact, not a judgement.

The same session showed why: three areas were finished without asking Pro
anything, and the user's verdict on the result was *why i think it not change
do different*. It was true — the work was structure, and nothing looked any
better for it.

**Gemini 3.1 Pro is the default model.** Checked 2026-08-19: with the brief
above it read a file and answered in two lines in 1m39s. It failed earlier in
this project only on LONG prompts — a 40-line review with six questions timed
out — so the rule is the model stays Pro and the PROMPT stays short:

    --model gemini-3.1-pro-high     default, for anything that matters
    --model gemini-3.7-flash-high   when Pro times out, or for a trivial lookup

If Pro times out, do not retry it with the same prompt: cut the question down
or split it, then retry. A prompt that times out on Pro is usually a prompt
that was asking for four things at once.

Keep the QUESTION short too — name the files and the exact claim, do not paste
code the model can read itself. `--mode plan` makes some models (GPT-OSS) write
a plan artifact instead of answering, so say *answer directly, no plan* when
using them. Gemini 3.1 Pro times out on long review prompts: keep it narrow or
use a Flash model.

**Ask the panel BEFORE acting, not only after.** The user's instruction,
2026-08-19: *use multiple AI to help brainstorm before taking any action*. So
for anything with a design in it — a new screen, a data shape, a protocol, a
decision the plan does not already settle — put the question to the panel
first, read what comes back, and only then write. It costs one command and it
is cheaper than building the wrong thing well.

    python tools/ai_panel.py --ask "<the question>" --dir <file-or-folder> --out <report.md>

**FIVE voices, twice per piece of work.** The user's instruction, 2026-08-19:
*use all to brain strome before code and after finish QC too need to make
sure*. So the panel runs at BOTH ends - once on the design before anything is
written, and once on the finished thing after QC is green, before it is
promoted. The panel is five models from three makers (Gemini Pro, Opus, Sonnet,
Gemini Flash, GPT-OSS) with Gemini Pro as head reviewer.

Two failures that cost real reviews, both silent until 2026-08-19:

* **GPT-OSS had been contributing NOTHING for days.** It errors when an answer
  shape is enforced with a JSON schema, and the report printed `(nothing)`
  beside its name - which reads as *found no problems* and actually meant
  *never ran*. A model that cannot answer as data is now asked again in plain
  prose, and a failure is printed as **FAILED**, never as an empty list.
* **The head reviewer can fail too**, and when it did the whole verdict was
  lost. Another model now judges in its place. The user's rule: *if run of
  token of each use the rest* - one model running out costs one opinion, never
  the review.

`check_panel` holds all of that, so it cannot rot back.

That tool is the standing answer to *do not trust one AI*: it asks several
models the same question in parallel, then hands their answers to a HEAD
reviewer that says which findings are real, which are wrong, and which cannot
be judged from the files. Its own docstring carries the rule that matters —
**the verdict is a shortlist, not a fact.** Every finding is still checked
against the code before anything changes, because this project has had a model
be confidently wrong twice in one day.

It earned itself on its first run: it found `--ty-lift` byte-identical to
`--ok` in all three themes — a lift board's row edged in the colour that means
*fine* — and a theme name hardcoded in the switcher that would have broken the
one promise the theme file makes. Neither was caught by me or by the model that
designed the palette.

**Review every part with several models before promoting it.** Not only when
something fails — the user asked for this as the normal way of working,
2026-08-18: *use multi AI with review each part, we can do like that to make it
more reliable*. Send the SAME question, naming the real files and the exact
claim the change makes, to two or three models at once, in the background, and
ask what is NOT true. Then verify every finding against the code before acting:
a model that is confidently wrong costs more than one that says nothing.

Gemini designs the visible surfaces, Claude builds and verifies the logic, and
now several models review the result. That is three different failure modes
having to line up before something wrong gets through.

**When something fails, ask other models before grinding.** The user's
instruction, 2026-08-18: *use gemini with many model and claude with many model
to check why fail, did theory wrong or not*. A failure usually means the theory
is wrong, and a second model spots that faster than a third attempt does.

    agy models                      what is available today, WITH the exact ids

Two things that cost a review each on 2026-08-19, both silent:

* **`agy` needs `--add-dir`, or it reviews the wrong tree.** Left alone it
  takes the main tree as its workspace and skips dot-directories, so a question
  about unpromoted work is answered about the last PROMOTED version, with
  nothing saying so. It CAN read `.staging` when the directory is named -
  measured 2026-08-19 by asking for a value four minutes old that existed only
  there. `tools/ai_panel.py` does this for you. Pasting the file into the
  prompt is not a way out: a prompt may contain no `"` character, and CSS and
  JS are full of them.
* **The model ids are not what this file used to say.** They are
  `claude-opus-4-6-thinking` and `claude-sonnet-4-6`, not `claude-opus-4.6`.
  A wrong id fails with a list of the right ones, so run `agy models` when in
  doubt.
    agy -p '<question>' --mode plan --model gemini-3.1-pro-high
    agy -p '<question>' --mode plan --model gpt-oss-120b-medium

Available through `agy`: Gemini 3.7/3.6/3.5 Flash (high/medium/low), Gemini 3.1
Pro (high/low), Claude Sonnet 4.6, Claude Opus 4.6, GPT-OSS 120B. Ask two or
three of them the SAME question, with the file contents and the exact failure,
and ask what would make the assumption false. Remember the prompt may contain
no `"` character. Never take any answer on trust — check it against the code,
the way A0-7 turned out (three models could not have saved that one; reading
`RS485Bus::send` did).

**Three tries, then park it.** If a task will not go green, fix and retry — but
after three attempts, set it back to `todo` with a note saying what failed and
what you now suspect, take the next task, and come back to it later. The user's
reason, 2026-08-18: *maybe your theory wrong* — and they are usually right.
A0-7 is the example: it was parked as an RS485 version of the A0-6 logging bug,
and reading the code showed the premise was simply false. Grinding on a wrong
theory costs more than moving on and returning with fresh eyes.

### When to ask, and when not to

**Do NOT ask again about anything already settled.** If it is in the plan's
decisions log, the STATE block, or the verified-facts table, it is decided.
Re-asking wastes the user's time and they have said so directly. Examples of
settled things: restructure aggressively, area by area · QR **and** mDNS, not
one · login required before acting · remote flash sends the image over the
network and confirms, naming the PC · Gemini designs, Claude verifies · keep
both pinout images, chosen by condition · do not merge `SPEED`/`TIME`/`STOP`/
`HOME` across nong and lift.

**DO ask when something is genuinely new** — a choice the plan does not cover,
where two readings would produce materially different work, or where proceeding
on a guess could damage hardware or lose the user's saved work. Ask once, give a
recommendation, and write the answer into the plan's decisions log so the next
session does not ask it again.

The test is simple: *have we decided this already?* If yes, act. If no, and it
matters, ask.

## Hardware first, while the boards are there

**HARDWARE FIRST, WHILE THE BOARDS ARE THERE.** The user's instruction,
2026-08-19: *make the esp32 hardware firmware first, i can use only while in
lab*. The boards are borrowed time; a PC is not. So when hardware is on the
bench, the order changes:

* anything that needs a board, a bus, a servo or a camera goes FIRST, even if
  it is later in the plan's id order;
* PC-only work (screens, themes, checks, docs) waits, because it can be done
  any evening;
* while a board is in hand, MEASURE things that a fake cannot show, and write
  the measurement into the plan — the numbers are the part that cannot be
  recovered later.

That rule has already paid for itself: one hour with a real bus found that the
hub could not see any module with an id above 40, which 2122 passing checks
against a fake had never suggested.

## The rules that have already cost real work

1. **The code is the source of truth**, not the plan, not a comment, not a
   README, and not the user's description. Verify before changing. Five
   assumptions in the original brief turned out to be false.
2. **Work in `code/.staging`, never the main tree.** Promote with
   `python promote.py`, which runs the full QC suite and copies back only if it
   is green.
3. **NEVER run `promote.py --init` while staging holds unpromoted work.** It
   refreshes staging *from* main and deletes it. This destroyed a finished
   feature once already.
4. **Every fix needs a QC check, and the check only counts once you have broken
   the fix and watched it fail.** The assertion helpers take a FIXED number of
   arguments and adding a detail string to the wrong one crashes the check
   rather than failing it: `t.ok(cond, label, detail)` takes a detail,
   `t.eq(got, want, label)` and `t.contains(hay, needle, label)` do NOT.
   Reach for `t.ok` whenever there is something useful to say about a failure. A check that passes before and after guards
   nothing. This has already caught a weak assertion of mine that would have
   shipped as "verified".
5. **Assert on what reached the module** (`fake_serial.wire`), never on what the
   UI says about itself. The UI is always right about itself while the arm sits
   somewhere else.
6. **Files the running system writes to are not source** and must never travel
   with it: `MiceHub.exe`, `promt.md`, `docs/PLAN.html` are in
   `promote.py`'s `SKIP_FILES`. Do not remove them from it.
7. **Talking to Gemini via `agy`: the prompt must contain no `"` character** —
   it truncates there silently and still returns confident nonsense. Ask for
   FIND/REPLACE blocks, never whole files (whole files time out).

## Nothing hardcoded — the user's standing rule

Asked for directly, 2026-08-18, and it applies to Claude AND to Gemini: write
things so they can be changed later without editing code.

* **A list belongs in DATA, not in a source file.** This project already works
  that way — a module type, a servo, a command or a web app is one entry in a
  registry and everything else is generated from it (`check_registries` proves
  it). Anything new follows the same shape.
* **One source, not a copy.** If a fact is needed in two places, one of them
  reads it from the other. `shared/web/mice.css`, `core/PortWrite.h` and the
  generated firmware tables are all the same idea.
* **Per module, per file, per concern.** A new thing should be a new file or a
  new entry, not a new branch inside something long. Where a class makes that
  clearer, use a class; where a small file does, use a small file.
* **Shallow beats clever.** The user asked for *not too many technical depth*:
  no layers that exist only to be layers, no indirection that has to be traced
  through four files to answer what does this do. Plain, obvious, commented.
* The test: **can someone add the next one without opening this file?** If not,
  the list is in the wrong place.

## Division of labour, agreed with the user

**Gemini designs the visible surfaces. Claude builds and verifies the logic.**
Evidence: Gemini's design output was better; it also proposed three CSS changes
that broke the rules they aimed at, and Claude caught two bugs Gemini's own fixes
introduced. Neither is trusted alone — see the multi-model rule in the plan.

## The repeated cycles are commands — use them, do not retype them

Asked for 2026-08-20: *any system or file involving repetitive tasks, convert
them into executable scripts to minimize token usage as much as possible*. Two
cycles were being written out by hand every time, and both are now one command:

    python tools/sabotage.py --check page_version --spec - <<'JSON'
    [{"file": "main_python/main.py", "find": "...", "replace": "",
      "why": "what breaking this would mean"}]
    JSON

    python tools/land.py --done A17-3        quick suite, gate, promote, plan

`sabotage.py` breaks the fix, runs the check, and **always** puts the file back
— including when the check crashes, which a hand-written cycle does not. A
sabotage whose text is not found is an ERROR, never a pass: patching nothing and
watching the check pass reads as *the check is weak* when the truth is *the
sabotage missed*. It earned itself on its first run by catching a weak assertion
of mine — `check_page_version` asserted that the words `myVer === null` appeared,
which survived breaking the line they were on.

`land.py` runs the quick suite first (thirty seconds to learn what the gate takes
five minutes to say), prints the one line worth reading out of three hundred, and
marks tasks done **only** when the gate was green AND it really promoted.

`check_dev_tools` holds both, so they cannot rot.

## Verification, every time

```
python qc/run_qc.py --quick        while iterating (~10 s)
pio run -e mice_nong -e mice_cam -e mice_lift -e mice_blank
python qc/run_qc.py                full, drives a real browser (~8 min)
python E:/final_proj/mice/code/promote.py     ALWAYS by absolute path
```

`promote.py` and `run_qc.py` take the tree from their OWN location, so an
absolute path always works — a bare `python promote.py` depends on the shell's
current directory, and that has silently drifted three times in this project:
once it edited the REAL tree instead of staging, and twice a promote simply did
not run because the shell was still inside `firmware/`.

Rebuild the exe when `main.py` changed:
`python -m PyInstaller --onefile --icon main_python/nong.ico --name MiceHub main_python/main.py`

## Two standing cautions

* **Almost nothing is tested on real hardware.** Every check runs against fakes,
  with two exceptions, both on 2026-08-19 with a nong (id 85) on COM9: A1-1 the
  board's auth gate and A1-2 the shipped password. Those were driven against the
  real board over WiFi, before and after. Everything else is fakes — say so
  plainly rather than reporting a feature as working.
* **`MiceHub.exe` goes stale** whenever `main.py` changes. The user may be
  running yesterday's code without realising.

## The architecture is written down — do not re-derive it

`docs/architecture/` holds `README.md`, `firmware.md`, `hub.md`, `web.md`, each
with `file:line` evidence, produced from three full explorations. Read those
before exploring from scratch; a cold session does not need to repeat the work.

## Sub-project rules still apply

`firmware/CLAUDE.md` and `nong/main_python_set_nong/CLAUDE.md` carry rules for
those folders (COMMANDS.md must stay in sync, patch after every web change,
document every feature in `help.html`). They are not replaced by this file.
