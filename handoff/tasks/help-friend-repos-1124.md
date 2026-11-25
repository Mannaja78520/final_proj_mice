# help-friend-repos-1124 — Put Help + a main-page Help button into Face_Regonize and Photobooth
Owner: codex:11240915-1a99
Branch: claude/project-thread-181856 (mice repo); friend repos: add-mice-help
Plan: none (user ask 2026-11-24)
Updated: 2026-11-24T09:58+07:00
Last commit: Face 7436718 on origin/add-mice-help, Photobooth d11cffa local, Mice docs 18fed68 in PR #248, Mice checkpoint 0a5a135 before this one

## User orders (Thai, 2026-11-24)
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA3Q6QC2jUpeSUV6Yw8pqH9TK: "put facereg and photobooth into the friend's git now; the game: let me look first for a moment"
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA32W8jHrzFH9jPqiqEZXH89j: "also put it on the main page in the facereg and photobooth apps, easy to click"
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA3G1GZftdzWidxFYUeavAdkg: "let GPT do all of it, you are out of quota"
Standing PC approvals: cmsg_01R7BbYxaTb3Yv9YS3gQaaA39kL7igdPaE1F66ZxWq6meq, cmsg_01R7BbYxaTb3Yv9YS3gQaaA3GFKFwe31L9cSDhiS4Mbs2z.

## THIS IS THE USER'S OWN EXCEPTION to "never edit friend repos", for Face_Regonize and Photobooth ONLY
Allowed: ADD the help/ folder and ONE minimal Help button on each app's main page. Nothing else in their code.
NOT allowed: All-Jao-Games (HOLD, user wants to look first: do not touch, do not push). Their main branch, force-push, merging.

## Work (per repo; use a clean clone/worktree under E:\work, never their working tree if it has uncommitted changes)
1. Read-only first: git status, branch, remote, last commit. Back up (note commit + copy under mice_system\.local\backup).
2. New branch `add-mice-help` from the repo's default branch.
3. Copy docs/friend/reconize_help_package/help and docs/friend/photobooth_help_package/help from Mice main (#245, #247) to each repo root. Commit "Add MICE Help package (help/)".
4. Main-page Help button: read their frontend, reuse their own button style/classes, no new dependencies.
   Reconize: dashboard header (and login page if simple). Photobooth: organizer/admin main page and, only if it
   does not disturb the guest flow, a small Help on the start screen. Must work STANDALONE (no MiceHub): serve/link their
   own help/ files (least invasive way that works in their server); optionally also offer MiceHub http://127.0.0.1:8642/help#faces
   (#photobooth) when reachable. Record the choice. Commit "Add Help button to main page".
5. Test: the app still starts, the button opens the help and its images show; screenshot each main page with the button
   (light/dark if themed); LOOK at every screenshot. Gemini 4 may review (leads only).
6. Push: `git push -u origin add-mice-help` (no force). If refused / credentials needed, STOP and write exactly why here.
7. Also update docs/friend/friend_requests_all_2026-11-23.md in mice_system (our repo, new branch from main, draft PR,
   merge per standing approval cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv when green). Include branch status, commit IDs, merge ownership, and Hub discovery.
8. Update this file after EVERY step and push WIP to Mice claude/project-thread-181856. Keep keys, passwords and real data out of Git.

## Doing now
Stopped at two external blockers. Published Face branch and Mice handoff branch are verified. Mice docs are in draft PR #248.

## Done
- Face base e998b0e and package 3ea59d1. Photobooth base 858f0b6 and package ee9e201. SHA-256 matched all 31 and 37 original files to source. Backed up both bases and the inherited Face diff in mice_system/.local/backup/help-friend-repos-1124.
- Registered A58-24 in the real system plan. Both Vite builds passed. Photobooth lint and 397 frontend tests passed (tests ran before the import-path-only correction).
- Edge passed with both actual clone servers and temporary databases. Face Login and dashboard, plus Photobooth organizer, opened own-origin Help. Each app loaded 18 images in every locale. Dev and production rendered identical pages in all 4 locales. Inspected all 10 screenshots in E:/work/help_friend_repos_1124/.local/friend-help-evidence.
- Committed the exact tested Help paths in Face 7436718 and Photobooth d11cffa. Only inherited .vite5180.log remains untracked in Face.
- Face branch pushed and ls-remote verified 7436718baa5055e778eeded3fdbfc6ecfa8d5a7c.
- Updated the Mice friend request in .local/mice-friend-doc with actual branch status, commit IDs, standalone links and the Hub help/help.json lookup.
- Mice full QC interrupted after detecting A59-2 had claimed the shared driver first. Stopped only our run, released our claim, and restored 8 transient generated files in our isolated docs worktree. No full-QC result.
- Opened Mice draft PR #248 from 18fed68. Direct Hub lookup with test partner paths discovered both packages and resolved 18 images in each locale.

## Next
With explicit user authorization, push Photobooth add-mice-help at d11cffa and update draft PR #248 status. With explicit A59-2 QC release, claim the driver, run python qc/run_qc.py --quiet --done-file qc/friend-status-done.json in .local/mice-friend-doc, and merge PR #248 only after green full QC.

## Blocked
Photobooth push was not executed. Automatic approval review rejected publishing friend source changes to ChocolateOwO without explicit trusted user authorization. Requested specific authorization for add-mice-help at d11cffa. Mice full QC is waiting for A59-2 to release the shared driver.

## Facts found
- Both backends serve built frontend/dist. Both Vite configs register a plugin that renders root help fragments into /help/index.html and three other locale pages and resolves their images. Source fragments stay byte-identical for Hub.
- Standalone browser test used 18084 and 18085, dev Help used 15184 and 15185. Deferred Photobooth guest-screen button to keep guest flow intact.

## File status

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| Mice: handoff/tasks/help-friend-repos-1124.md | Track scope, verification and publication | In progress | git diff --check | this checkpoint |
| Face: frontend/src/components/Layout.tsx | Standalone Help in dashboard header | Committed | Build + Edge on isolated app | 7436718 |
| Face: frontend/src/pages/Login.tsx | Standalone Help on login | Committed | Build + Edge on isolated app | 7436718 |
| Face: .vite5180.log | Inherited test output, preserve outside commit | Existing | not run | uncommitted |
| Face: frontend/vite.config.ts | Register bundled Help plugin | Committed | Build + Edge on isolated app | 7436718 |
| Face: frontend/vite.help.ts | Serve guide in dev and emit guide with screenshots in build | Committed | Build + Edge on isolated app | 7436718 |
| Photobooth: frontend/vite.config.ts | Register bundled Help plugin | Committed | Build + Edge on isolated app | d11cffa |
| Photobooth: frontend/vite.help.ts | Serve guide in dev and emit guide with screenshots in build | Committed | Build + Edge on isolated app | d11cffa |
| Photobooth: frontend/src/features/admin/components/AdminLayout.tsx | Standalone Help in organizer navigation | Committed | Build + Edge on isolated app | d11cffa |
| Mice: docs/friend/friend_requests_all_2026-11-23.md | Record Face published, Photobooth pending and Hub discovery | Draft PR #248 | Diff check and test-partner Hub lookup pass; full QC pending | 18fed68 |
| Face: help/standalone.html | Locale navigation and standalone app links | Committed | Build + Edge on isolated app | 7436718 |
| Photobooth: help/standalone.html | Locale navigation and standalone app links | Committed | Build + Edge on isolated app | d11cffa |
| Mice: docs/system_integral.html | A58-24 live plan row, mirrored from task workspace | Live state | plan.py show | uncommitted |
| Mice: docs/system_integral_state.js | Generated system plan state | Live state | plan.py show | uncommitted |
| Mice: docs/BRIDGE.md | Shared claim, QC release and handoff under mutex | Released | Real plan A58-24 handed off | uncommitted |
| Face: help/en.html | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/help.json | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-dark-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-activities.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-attendees.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-cctv.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-connect.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-dashboard.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-event-photos.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-history.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-import.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-login.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-pdpa.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-people.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-privacy.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-recognition.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-reports.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-settings.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-uploads.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/en-light-reconize-video.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/ja-dark-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/ja-light-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/th-dark-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/th-light-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/zh-dark-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/img/zh-light-faces-open.webp | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/ja.html | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/shots.json | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/th.html | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Face: help/zh.html | Bundled guide or image | Committed | SHA-256 matches source | 3ea59d1 |
| Photobooth: help/en.html | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/help.json | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-capture.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-choose.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-decorate.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-delivery.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-review.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-booth-start.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-dark-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-activity.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-capture.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-choose.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-decorate.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-delivery.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-editor.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-frames.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-history.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-profiles.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-retention.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-review.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-sign-in.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-start.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-statistics.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-system.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-test.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-booth-unpaired.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/en-light-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/ja-dark-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/ja-light-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/th-dark-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/th-light-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/zh-dark-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/img/zh-light-photobooth-open.webp | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/ja.html | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/shots.json | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/th.html | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |
| Photobooth: help/zh.html | Bundled guide or image | Committed | SHA-256 matches source | ee9e201 |

## Result
- Face_Regonize: push สาขา add-mice-help แล้ว (คู่มือ 3ea59d1, ปุ่ม 7436718) หน้า Dashboard และ Login เปิดคู่มือได้
- Photobooth: ปุ่ม Help หน้า Organizer ผ่านแล้ว (คู่มือ ee9e201, ปุ่ม d11cffa) รออนุญาตให้ push
- ตรวจภาพทั้ง 10 ภาพที่ E:/work/help_friend_repos_1124/.local/friend-help-evidence แล้ว เอกสาร Mice อยู่ใน draft PR #248 รอ full QC
- ตำแหน่งปุ่ม: Face Layout.tsx:94 และ Login.tsx:55, Photobooth AdminLayout.tsx:65. ทดสอบบนพอร์ตแยกและปิดครบแล้ว งานอยู่ในสอง repo ที่ระบุและเอกสาร Mice
