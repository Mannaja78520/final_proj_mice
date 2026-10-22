# Every remaining gachapon/voice link (games, outside apps, voice questions, friend list)

Owner: claude:10qzvx
Updated: 2026-10-22 18:50Z
Branch: claude/project-thread-10qzvx
Last commit: (none yet)
Plan: A47-6 game link, A47-7 app keys, A47-8 voice questions, A47-9 friend list

## Goal
User 2026-10-22 18:33Z: "ทำ app อย่างอื่นที่ต้องการที่เกี่ยวข้องทั้งหมดและไม่ได้ทำทั้งหมดเลย"
(build every related app/link from the gachapon ask that is not built yet);
18:34Z "ไม่ใช่แค่ gacha พวก voice ก็ทำต่อให้ครบ" (finish voice too);
18:35Z "ถ้ามีอะไรจะขอจากแอพเพื่อนก็บอกมา" (list what the friend's apps should add,
the user sends it). If usage runs out, ChatGPT/Codex continues from this file.
Base already merged: PR #57 firmware, PR #58 hub app /app/gacha/ + Voice Questions tab
(see handoff/tasks/gachapon.md, docs/gacha/README.md).

Gaps found by reading the code 2026-10-22:
1. A47-6 The friend's All-Jao-Games (static folder, `python -m http.server 8080`) keeps
   wins only in its own localStorage (`all-jao-games.wheel.v2` logs, `.claw.v1` logs,
   `.quiz.v1` players with name+score) and the memory game only shows a status text
   (`#memory-status-text` "เก่งมาก! จับคู่ครบทุกคู่แล้ว"). Nothing reaches the hub.
   Plan: the hub serves their folder READ-ONLY at /play/all-jao/ and adds one
   <script> (apps/all-jao/link.js) to index.html as it is sent (their files are never
   changed). The script watches localStorage writes / the status text per watcher in
   config/gacha.json "games" and POSTs /api/gacha/game {game, result, person}.
   The hub maps game+result -> kind (rules list in config) and dispenses.
   Note: a new origin = their settings saved at :8080 do not carry over (say so in Help).
2. A47-7 Other PCs need a hub login today. Add app keys (.local/gacha/keys.json, never
   git), header X-Mice-Key or "key" in the JSON; page: make / remove a key.
3. A47-8 Voice Questions tab: topics are only editable in the file; add an editor,
   a "make a saved answer" button on the asked-most list, and `when.event` on voice
   prize rules.
4. A47-9 docs/gacha/friend_requests.md + Thai list in the thread.

## Facts found
- All-Jao-Games is a static folder (python -m http.server 8080); wins only in its localStorage:
  wheel script.js:8 key all-jao-games.wheel.v2, record wheel-state.js:28 {id, prizeId, label};
  claw claw-game.js:8,308 same ledger; quiz quiz-game.js:8,138 players {id, name, score};
  memory matching-game.js:84,94 only #memory-status-text. No fetch/postMessage anywhere.
- Face_Regonize e8d4a22: GET /api/node/{id}/present exists (nodes.py:68,397); person has
  call_as/title/language (models.py:39-46), no tags/groups; import picks Name/Photo columns.
- Hub gate: main.route uses hub_auth.gated + local_ok/from_program_here, now also key_ok +
  app_key_name and page_here_ok + page_here. Help page is built from main_python/web/help/parts/.

## Doing now
Quick QC (`python qc/run_qc.py --quiet --quick`), then full QC, then PR from
claude/project-thread-10qzvx to main and merge when green.

## Done
- plan rows A47-6..9 added.
- A47-6 built: main.py serve_play (/play/<pid>/, read-only, injects partners.json play.inject +
  watch), apps/all-jao/link.js, partners.json all-jao "play" (watch list read from their code),
  gacha.py game_win (dedupe by ref) + "games" rules + busy_wait_s (a turning machine is waited
  for, not "out everywhere"), /api/gacha/game (login | program here | key | hub page on this PC:
  main.page_here, hub_auth.PAGE_HERE_OK), Prize machines page "Games that give a prize",
  All-Jao page plays /play/all-jao/.
- A47-7 built: app keys .local/gacha/keys.json, hub_auth.KEY_OK, X-Mice-Key or ?key=,
  /api/gacha/keys, page card "Other PCs and forms". Keys never force.
- A47-8 part: voice prize rule when.event (voice_prizes.prize_for), Event column on the page.
- A47-8 done: /api/questions/topics (GET, POST login; patterns must compile), Voice > Questions:
  Topics editor, "Asked often, no saved answer yet" + "Make an answer" (opens Answers with the
  question filled in). voice_prizes.save_topics, stats "unsaved".
- A47-6 browser proof: qc/checks/check_game_prize.py (fake game in an iframe at /play/games/:
  storage record, alljao:win event, memory text; 3 sabotages caught). link.js also listens to
  the event "alljao:win" asked of the friend.
- A47-9 docs: docs/gacha/README.md (keys, curl + Apps Script examples, games), Help parts
  (main_python/web/help/parts/gacha.html, all-jao.html -> tools/build_web.py), Thai friend list
  docs/gacha/friend_requests.md (+ copy /mnt/project-files/friend_api/gacha_requests_2026-10-22.md),
  docs/systems.json app-gacha + systems build.
- stats per hour + chart on Prize machines. check_gacha 39 asserts, 7 sabotages caught.

## Next
1. Full QC green (cloud: pip install pyserial psutil platformio; cd firmware && pio run -e mice_nong;
   git fetch origin app:refs/remotes/origin/app). Known flakes pass alone (see HANDOFF/memory).
2. PR to main, merge, `python tools/plan.py done A47-9`, delete this file in the merging PR.
3. On the PC after merge (Remote Control session): rebuild MiceHub.exe with the spec, open
   /app/all-jao/ and play a wheel spin with a rule on Prize machines > Games, see the toast.
   Their own :8080 settings do not carry over to /play/all-jao/ (new origin).
4. Still open elsewhere (not this task): A47-5 bench (handoff/tasks/gachapon.md), voice keys,
   person tests: all need the user or hardware.

## Blocked
- nothing (no hardware needed; tested against fakes only).
