# Codex, Antigravity and Claude: shared working agreement

This is the coordination procedure for this Mice workspace. It extends
AGENTS.md and CLAUDE.md. The current user request determines task scope.
It does not start model calls, share chat histories, or enforce filesystem
permissions. Each assistant must read it and follow it. Existing sessions
must be told to reload it; creating this file does not notify them.

## Read before writing

1. Read AGENTS.md, CLAUDE.md and the newest entries of docs/BRIDGE.md.
2. Read only the relevant tasks in the real docs/PLAN.html. Use tools/plan.py
   with an explicit --page for changes; do not edit generated plan_state.js.
3. Identify yourself by assistant and unique session, for example
   codex-20260911-review. Record the absolute working tree and exact files.
4. Claim the files in BRIDGE before editing. Include generators, generated
   outputs and tests that your commands write, not just hand-edited files.
   Directory claims overlap every file beneath that directory.

All coordination uses the real root E:/final_proj/mice/code, even when source
work is in a staging copy. BRIDGE is the append-only ownership and handoff
log; PLAN remains the only task progress record. HANDOVER is a checkpoint,
not proof of present ownership. Old timestamps do not release a claim.

## Serialize claims and shared bookkeeping

Use E:/final_proj/mice/code/.staging-coordination.lock as a SHORT mutex for
BRIDGE appends and tools/plan.py calls. It is a directory; the .staging prefix
keeps it out of source promotion and Git through existing rules.

- Acquire by creating the directory exclusively, without -Force. In
  PowerShell: New-Item -ItemType Directory -Path
  'E:/final_proj/mice/code/.staging-coordination.lock' -ErrorAction Stop.
  Run that as one command. If it fails, do not perform dependent writes.
- Write owner.txt inside it with your session and the machine timestamp.
  Re-read BRIDGE AFTER acquiring the mutex. If an overlapping claim exists,
  append a request, release the mutex, and do independent work, unless the
  user explicitly transferred the stopped owner's task as described below.
  Record that authority and the exact transferred claims before editing.
- Append your CLAIM or RELEASE, or run the required plan update while holding
  the mutex. Preserve existing bytes, UTF-8 and line endings. Do not rewrite
  another assistant's entry. Re-read after each write to confirm it landed.
- Remove only your own owner.txt and then the empty lock directory in a
  finally block. Check the owner session before release. Never recursively
  delete it, clear someone else's lock, or reclaim it on age alone.

Keep this mutex only for seconds of bookkeeping. Do not hold it while
researching, editing, reviewing or running QC. File ownership persists in
BRIDGE after releasing the mutex. If a session crashes with the mutex held,
confirm it has stopped and resolve its ownership before clearing the lock.
Until resolved, reading and work on already-owned independent files can
continue. All assistants must adopt this protocol for it to prevent races.

## Parallel work and exclusive resources

- Different claimed files may be worked on concurrently. Review another
  assistant's stable snapshot without editing its files. Save feedback in
  your own claimed report and let the owner apply it, or accept a handoff.
- The existing shared .staging has ONE editing owner at a time. Other code
  writers need separately established staging copies and disjoint claims.
  Do not initialize or refresh someone else's staging. A Git worktree alone
  does not include this project's uncommitted work; do not use HEAD as an
  assumed complete baseline. This setup creates no new working copies.
- Only one process may own the shared QC/fake-module/hardware resources.
  Claim QC in BRIDGE, verify no driver is active, and freeze its entire input
  tree until it finishes. Other agents may read or work outside that tree;
  avoid heavy GPU, network and model-download work during timing gates.
- Promotion, shared checkpoint/history writes, dependency/environment
  changes, generated shared files, service restarts and hardware access need
  exclusive claims too. Do not stop another session's processes.
- Integration needs a separate claim. Before promotion, reconcile current
  main and staging changes and freeze every path the promotion will write.
  Preserve the instruction changes and all concurrent reference work.
  Follow the existing review and QC workflow; no blanket promotion of
  unrelated work. Release QC/integration claims after the process ends.

## Handoff and token limits

Append a compact block to BRIDGE under the mutex:

    ### <machine timestamp + timezone> — <assistant/session>
    Event: CLAIM | REQUEST | HANDOFF | RELEASE
    Task: <existing plan ID>
    Tree: <absolute path>
    Files/resources: <exact paths, outputs, environment, QC if applicable>
    Evidence: <commands, actual results, stable snapshot/hash if relevant>
    Next: <recipient and next step; unresolved issues>

HANDOFF must explicitly state which claims are released; the recipient then
records its own CLAIM before editing. An explicit user-authorized takeover
of a stopped owner is also allowed under the provider-limit procedure below.
A plan status of done or a silent
terminal is not a handoff. Before a token limit, record changed files,
unfinished work, tests and the next command. A failed model review is not
approval. Do not repeat an unchanged failed request in a loop: record the
error, change the diagnostic approach, or leave a bounded handoff.

Use Caveman full, plain-speak and token-thrift: concise conversation, complete
implementation and evidence. One owner builds; another reviews when required
by the existing workflow. Do not create extra paid review panels merely to
coordinate three already-running assistants.

## Current reference handoff

The user reports Antigravity is editing the reference library. Reserve
docs/ref.html, docs/ref_data.js, docs/ref_sources.js and reference generator
scripts for Antigravity until an explicit release. Claude's current source
ownership has not been confirmed; do not infer it from old task timestamps.

Codex task A21-12 is to review and add references AFTER that release. Keep
Thai and English explanations. Verify original sources, DOI/title/year,
formula assumptions and code mappings; separate implemented behavior from
related literature and proposed experiments. A linked paper or passing
syntax check alone does not establish a thesis claim. Preserve Antigravity's
work, record corrections, deduplicate sources and verify the rendered page.

## Prompt for an already-running assistant

```text
Read AGENTS.md, CLAUDE.md, docs/COORDINATION.md and the newest docs/BRIDGE.md
entries in E:/final_proj/mice/code before your next edit. Identify your
assistant/session and claim your exact files and resources using the shared
mutex. Preserve other assistants' changes. Work only on your assigned task;
one owner per file, one owner for shared staging, one QC driver at a time.
Use Caveman full, plain-speak and token-thrift. Update the real plan with
tools/plan.py. Before stopping, record evidence and explicitly release your
claims. Antigravity owns references until handoff; Codex reviews and adds
references afterward under A21-12. Confirm what you own before continuing.
```

Instruction entry points, checked 2026-09-11: Codex reads
[AGENTS.md](https://developers.openai.com/codex/guides/agents-md); Claude uses
[CLAUDE.md and imports](https://code.claude.com/docs/en/memory); Antigravity
supports [workspace rules](https://www.antigravity.google/docs/rules-workflows/)
under .agents/rules. Confirm the shared rule is Always On in Antigravity's
Rules panel. Live adoption by Claude and Antigravity must be acknowledged;
it has not been verified by Codex.

## Provider limits and continuing in another session

### Mandatory consultation when the user asks

User instruction, 2026-09-15: when told to ask Codex, the current assistant
must make the request before another patch or QC restart. "I solved it",
"one final attempt", assumed startup cost, and a handoff prompt for the user
are not substitutes for calling the available Codex CLI or agent tool.

1. Acknowledge the request and send a narrow question with tools/ai_brief.txt,
   the exact working tree, relevant files, decisive failure and a line budget.
   Use gpt-6-astra with high effort. A supported agent tool may be used instead
   of the CLI; identify it and label same-provider review honestly.
2. Record the actual invocation, requested/observed model if known, and the
   completed response or exact failure in BRIDGE. Save a review artifact under
   a claimed path. Never report consultation as complete while it is pending.
3. Evaluate the response against code and evidence. Send a bounded follow-up
   when a finding is unclear or contradicted; then apply and verify the fix.
4. If the call fails, diagnose the error. Follow Codex-first fallback routing
   below and tell the user what happened. A timeout is not a quota limit.
   Never silently skip the consultation or claim a failed call approved work.
5. Announce every QC restart and its reason. Report measured progress and
   actual exit status; do not promise a clean result or invent finish times.

These instructions require observable behavior, but cannot force a model to
obey. Existing Gemini/Antigravity sessions must reload GEMINI.md and the
Always On shared-coordination rule. A successful tool response, not an
assurance in chat, is evidence that the requested consultation happened.

User instruction, 2026-09-14: Codex helps first when a problem occurs. Use
Gemini or another available provider only when Codex is limited/unavailable.
Claude reaching a limit does not require waiting: Codex takes over the current
assigned task. These instructions apply to Claude, Gemini/Antigravity and
ChatGPT/Codex in new prompts as well as existing sessions. This newer routing
rule takes precedence over older fixed builder roles and mandatory five-model
panels in CLAUDE.md. Preserve required checks and independent review.

- Keep the actual host identity. Never pass --host claude from a Codex host
  just to force routing. The installed claudex-loop runner may require the
  other provider; report that mismatch and use a fresh Codex review under
  this user-authorized routing exception. Label same-provider review honestly.
- Read the installed claudex-loop SKILL.md and runtime reference before CLI
  calls. Locate the current executable and check its version; extension
  directories change. Use an absolute --cli path when supported. Do not
  assume a remembered extension version, PATH or UI login proves CLI access.
- Request gpt-6-astra with high effort for Codex help, as the user specified.
  Prepend tools/ai_brief.txt and give a narrow question, exact tree/files and
  a line budget. Never send the whole chat or credential files.
- Record attempted provider, requested model/effort, observed model if known,
  result path, actual error and reset time if reported. A timeout is not proof
  of a quota limit. Retry only after changing a diagnosed cause or narrowing
  the question; no repeated blind requests. Announce any fallback.
- If Codex cannot continue, use an available Gemini reviewer through the
  existing ai_panel.py/agy workflow. Discover current model IDs; do not invent
  them. A failed or empty review is never approval. If every provider is
  unavailable, preserve work and leave the next diagnostic step in BRIDGE.

Checkpoint after each meaningful change, before long checks, and before a
limit when possible. PLAN records status; append-only BRIDGE records transfer:

    Task: <page + ID and current user objective>
    Tree: <absolute source tree; main versus staging explicitly>
    Files/resources: <claims, changed paths, generated outputs>
    Evidence: <actual commands, exit results, review path, hashes where useful>
    In flight: <PID, command, log path; or none>
    Remaining: <failures, unverified behavior, required review/gate>
    Next: <one exact command or bounded action, and recipient>
    Release: <exact claims released; never imply a running QC is released>

The incoming assistant reads current files, latest relevant BRIDGE entries
and PLAN, checks active processes, then claims the transferred paths under
the mutex. A user-authorized takeover after a limit can transfer the stopped
assistant's task; record that authority. Do not stop unrelated sessions or
infer their release from age. Finish or identify any still-running gate before
editing its tree. Reconcile newer edits instead of restoring an old snapshot.
If a hard limit prevented a checkpoint, reconstruct from disk and process/log
evidence; mark missing evidence unknown. Never promote from a stale green run.

### Paste into Claude, Gemini or ChatGPT/Codex

```text
Continue the current handed-off task in E:/final_proj/mice/code. Read
AGENTS.md, CLAUDE.md, docs/COORDINATION.md and latest relevant docs/BRIDGE.md
entries, then the named task in the real plan (robot/system page explicitly).
Use the latest handoff's tree, files, evidence and next action; verify them
against disk and active processes. Claim released/user-transferred paths under
the shared mutex before edits. Preserve unrelated work and staging. Codex
helps first on problems; only if Codex is limited/unavailable use Gemini or
another available provider. Keep the real host identity and record failures,
fallbacks and review evidence. Continue through required verification. Before
stopping, update PLAN and append a compact BRIDGE handoff with the exact next
step, in-flight processes and explicit claim releases. Do not restart unrelated
todo tasks. Use Caveman full, plain-speak and token-thrift.
```

These files share project state, not private chat histories. An assistant
without filesystem access must be given the latest handoff text. Existing
sessions must reload these rules; this does not automatically launch or notify
another provider, bypass account limits, or prove that it adopted the rules.
