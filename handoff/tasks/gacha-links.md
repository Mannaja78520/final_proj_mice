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

## Doing now
A47-9 docs: docs/gacha/README.md (games, keys, examples), docs/gacha/friend_requests.md
(gacha + voice), Help page section, project file friend_api/ copy; then full QC + PR.

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
- stats per hour + chart on Prize machines. check_gacha 39 asserts, 7 sabotages caught.

## Next
1. A47-9 docs + README + Help (see Doing now).
2. A47-8 voice, A47-9 docs, full QC, PR, merge.

## Blocked
- nothing (no hardware needed; tested against fakes only).
