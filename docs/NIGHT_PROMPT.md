# The prompt to paste tonight (2026-09-18, from the dorm)

Copy everything between the lines into Claude Code, then go to sleep.

---

Work all night by yourself, no questions. Read CLAUDE.md and docs/PLAN.html
first, then docs/BRIDGE.md from the bottom for what session
claude:09180022-caee did tonight (commits c13026e, 7662ddb, ddf22c1).

Own your work: `python tools/plan.py session claude`, then mark every task
`doing` when you pick it up and `done` when it lands, with `--agent`.

Do these, in this order:

1. The dead sessions left tasks half-finished with no handoff. Check each
   against the code, then either finish it or set it back to `todo` with a
   note saying what is really there:
   claude:09171324-229c -> A26-31, A26-32, A26-33, A26-34, A26-40
   claude:09171741-5585 -> A26-42, A26-45, A26-46
   Older, no owner -> A26-5, A26-7, A26-8, A26-14, A21-12, A21-17
2. Then take the first `todo` in id order and keep going. Skip anything
   marked `[hw]`: the boards are not on the bench.
3. Voice answer quality (A26-68 left this open): the local model writes weak
   Thai - it mixes ครับ and ค่ะ, cuts replies off, and sometimes answers in
   the wrong language on very short questions. Fix what can be fixed in the
   prompt and in the saved answers (apps/voice/qa_data.json), and add saved
   answers for the questions a visitor really asks. Never let the model
   invent a fact; that rule is already in all four prompts, keep it.

Rules that are not negotiable:
* every fix gets a QC check, and the check only counts once you have broken
  the fix with `python tools/sabotage.py` and watched it fail. Thai text in a
  sabotage must go in a UTF-8 spec FILE, not a heredoc - it arrives mangled;
* `python qc/run_qc.py --quick` must be green before you commit;
* commit in small batches with a real message; main holds other sessions'
  uncommitted work, so stage only the files you touched, never `git add -A`;
* write what you did to docs/BRIDGE.md as you go, so the morning makes sense;
* do not ask me anything - if a decision is genuinely new, pick the safer
  option, write it in the plan, and carry on.

In the morning, leave one short summary at the top of your last message: what
landed, what is still broken, and what needs me.

---
