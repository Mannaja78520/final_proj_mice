# สิ่งที่ต้องขอจากแอปของเพื่อน — อัปเดต 2026-11-05

อ่านโค้ดแบบอ่านอย่างเดียว + รันสคริปต์ของเพื่อนเท่านั้น (ไม่แก้โฟลเดอร์เพื่อน)
เวอร์ชันที่ตรวจ: All-Jao-Games `f9e8ff4` (2026-09-08), Face_Regonize `e8d4a22` (2026-10-20),
Photobooth `858f0b6` (2026-10-04) — ทั้งสามตัวตรงกับ GitHub ล่าสุด (`git ls-remote`, 2026-11-05)
ตัวเลขวัดบน PC (RTX 5070 Ti 12 GB) ไฟล์ผล: `.local/face_load_2026-11-05/` (ไม่อยู่ใน git)

รายการเดิม: `docs/gacha/friend_requests.md` (2026-10-22) — ดูคอลัมน์ "สถานะ" ด้านล่าง

## Face_Regonize (จำหน้า, พอร์ต 8000)

ที่เราใช้อยู่: `POST /api/look`, `GET /api/node/{id}/present`, `GET /api/history?after_seq=`,
`WS /api/node/events-feed`, `GET /api/health`, `GET /api/reports/dashboard`, `call_as` `title` `language`

ที่วัดได้ (2026-11-05, ใช้งานจริงพร้อม Typhoon + whisper):
- `/api/look` 640px: 6 กล้อง x 4 ภาพ/วิ ผ่านหมด p95 ~200 ms ไม่มี 429
- 8 กล้อง x 4 ภาพ/วิ: เกินกำลัง ได้ ~21 ภาพ/วิ รวม, p95 ~580 ms, มี 429 ทุกกล้อง, ช่องว่างนานสุด 4.3 วิ
- endpoint อ่านอื่นๆ เร็ว: history 36-81 ms, present 10 ms, health 40 ms
- แอปใช้ VRAM ~1.3 GB ตอนว่าง (โหมด dual)

| # | ขอ | สถานะ | หลักฐาน |
| --- | --- | --- | --- |
| F1 | กลุ่ม/แท็กต่อคน (`vip`, `staff`) ใน `GET /api/people` และผลรู้จำ | ยังไม่ทำ | ตาราง `person` ไม่มีคอลัมน์ tags; `GET /api/people` คืน 18 ฟิลด์ ไม่มี tags |
| F2 | นำเข้าแท็กจาก Sheet/Excel คอลัมน์ `Tags` | ยังไม่ทำ | ขึ้นกับ F1 |
| F3 | `person_id` คงที่ทุกที่ | ทำแล้ว | `/api/look` ส่ง `person_id`, `participant_id` |
| F4 | webhook ตอนจำคนได้ | ยังไม่ทำ (มี WS events-feed แทน ใช้ได้) | ไม่มี route webhook ใน `backend/app/api/` |
| F5 (ใหม่) | บอกขีดจำกัด `/api/look` ใน `/api/health` เช่น `max_live_fps` หรือคิวต่อ source เพื่อให้เราลดภาพ/วิเองก่อนโดน 429 | ใหม่ | 8 กล้องได้ 429 (ไฟล์ r3_8streams_voice.json) |
| F6 (ใหม่) | ปรับ batch หลายภาพใน `/api/look` ครั้งเดียว (หลายกล้องต่อ request) จะลดคิว | ใหม่ | ตอนนี้ 1 JPEG ต่อ request (docs/robot-integration-api.md:66) |
| F7 (ใหม่) | ช่วยสร้าง machine account ให้เรา (`python scripts/manage_machine_user.py create --username robot-hub`) | ใหม่ | ตอนนี้ไฟล์ล็อกอินของเรา `main_python/faces_login.json` เป็น role `admin` (GET /api/auth/me) — ควรใช้ machine แทน (ฝั่งเราต้องเปลี่ยนด้วย) |
| F8 (ใหม่) | ปรับ threshold ได้ต่อกล้อง (CCTV ไกล ภาพเล็ก) | ใหม่ | `face_match_threshold` 0.45 ค่าเดียวทั้งระบบ (`GET /api/settings`) |

ฝั่งเราเอง (ไม่ใช่ของเพื่อน): ถ้าตัวเฝ้าดูใบหน้า `apps/faces` (พอร์ต 8769) ไม่ได้รัน ทุกคำถาม Voice ช้า
2.5-3 วิ เพราะรอ timeout ฝั่งเรา (history ของเพื่อนเองตอบใน 81 ms)

## All-Jao-Games (เกม, พอร์ต 8080)

ที่เราใช้อยู่: hub เปิดโฟลเดอร์เกมที่ `/play/all-jao/` แล้วอ่านผลชนะจาก localStorage
(`config/partners.json` play.watch)

| # | ขอ | สถานะ | หลักฐาน |
| --- | --- | --- | --- |
| G1 | `window.dispatchEvent(new CustomEvent("alljao:win", ...))` ทุกเกม (สำคัญสุด) | ยังไม่ทำ | ค้นทั้งโฟลเดอร์ไม่เจอ `alljao:win` หรือ `CustomEvent(`; commit ล่าสุด 2026-09-08 |
| G2 | ช่องใส่ชื่อผู้เล่นในวงล้อและตู้คีบ | ยังไม่ทำ | มีชื่อเฉพาะ quiz (`quiz-game.js`) |
| G3 | เกมจับคู่เก็บผลชนะเป็น record | ยังไม่ทำ | `matching-game.js:8` มี key `all-jao-games.memory.v1` แต่เราอ่านผลจากข้อความบนจอ "ครบทุกคู่" |
| G4 | เรียก `POST /api/gacha/game` ตรง (ไม่บังคับ) | ยังไม่ทำ | — |
| G5 | รับ webhook ของหมด `gacha.out` | ยังไม่ทำ | — |
| G6 (ใหม่) | อย่าเปลี่ยนชื่อ localStorage key (`*.v1`, `wheel.v2`) โดยไม่บอก | ข้อตกลง | ลิงก์ของเราผูกกับชื่อ key เหล่านี้ |

## Photobooth (ตู้ถ่ายรูป, พอร์ต 8121)

ที่เราใช้อยู่: `GET /api/health` (เช็คว่าเปิด) และเปิดหน้า `/booth` `/admin` ในแท็บใหม่
รันผ่านสคริปต์ของเพื่อน `scripts/stop-main.ps1` แล้ว `scripts/run-main.ps1` (ติดตั้งที่ `C:\Photobooth\Main\app`)

| # | ขอ | สถานะ | หลักฐาน |
| --- | --- | --- | --- |
| P1 (ใหม่) | ยอมให้ hub ของเราฝังหน้า booth ใน iframe (`Content-Security-Policy: frame-ancestors http://127.0.0.1:8642`) | ยังเป็น DENY | `backend/src/photobooth/main.py:126` `X-Frame-Options: DENY` |
| P2 (ใหม่) | event ตอนถ่ายเสร็จ (เช่น WS หรือ webhook `session.finished` พร้อม session id) ให้หุ่นพูด/แจกของได้ | ไม่มี | มีแค่ route `POST /{session_id}/finish` ของ booth sessions (ต้องเป็นเครื่องที่จับคู่แล้ว `require_device`) ไม่มี webhook หรือ WS ให้คนนอกฟัง |
| P3 (ใหม่) | บอกใน `/api/health` ว่ากำลังใช้กล้องตัวไหน (booth ใช้กล้องผ่านเบราว์เซอร์ `getUserMedia`) | ไม่มี | ถ้าใช้กล้องตัวเดียวกับระบบจำหน้า จะชนกัน เปิดพร้อมกันไม่ได้ |
| P4 (ใหม่) | ขอ endpoint อ่านอย่างเดียวสำหรับ robot (สถิติวันนี้ เช่น จำนวนรูป) ที่ไม่ต้องล็อกอิน admin | ไม่มี | router activity (`/activity`, `/history`, `/statistics`) ต้อง `require_device` + `require_admin` (`modules/activity/api.py:41`) |
