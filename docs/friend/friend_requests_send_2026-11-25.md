# รายการขอเพื่อน (ฉบับสั้นพร้อมส่ง) — 2026-11-25

ฉบับย่อของ `friend_requests_all_2026-11-23.md` ตัดข้อที่เพื่อนทำแล้วออก
เช็คโค้ดเพื่อนแบบอ่านอย่างเดียวเมื่อ 2026-11-25: Face_Regonize `7436718`, All-Jao-Games `7d00404`, Photobooth `d11cffa`
ไม่บังคับทุกข้อ ฝั่งเราใช้ได้อยู่แล้ว ทำแล้วลิงก์แน่นขึ้น  ความลับ (key/secret) อย่าลง git เพราะ repo เราเป็น public

**ขอบคุณที่ทำแล้ว (ตัดออก):** Face tags + นำเข้า Tags + `/api/look/batch` + ขีดจำกัดใน health + threshold ต่อกล้อง (`e998b0e`);
All-Jao ส่ง `alljao:win` + ชื่อผู้เล่น (`146fcbc`); ปุ่ม/โฟลเดอร์ Help ของทั้งสามแอพ

## All-Jao-Games
1. **quiz ส่ง `result.total`** (คะแนนเต็มของรอบ) ใน `alljao:win` — ตอนนี้ยังไม่ส่ง จึงตั้งเกณฑ์ "80%" ไม่ได้ (P1)
2. **วงล้อส่ง `result.noPrize: true`** ที่ช่อง "ลองใหม่" — ตอนนี้ยังไม่มีในโค้ด เราต้องเดาจากคำ (P1)
3. **เกมจับคู่ใส่ `playerName`** ใน record ของ `AllJaoHub.win('memory', ...)` — `matching-game.js:104` ยังไม่มีชื่อ (P1)
4. ช่องชื่อผู้เล่นหน้าวงล้อ/ตู้คีบแสดง `???????????` เปลี่ยนป้ายเป็น «ชื่อผู้เล่น» (P1)
5. รายการเกมเดียวกันทั้งหน้า admin และผู้เล่น (admin 4 เกม ผู้เล่น 3) + `GET /api/games` หรือ `games.json` บอกเกมที่เปิดอยู่ (P2)
6. admin `admin/1234` เช็คในเบราว์เซอร์ ไม่ป้องกันอะไรจริง — ให้ hub เป็น admin เจ้าเดียว หรือยอมรับว่าเกมไม่มี admin (P2)
7. ที่อยู่ hub อ่านจากค่าตั้งได้ ไม่ผูกพอร์ต 8642 และลองที่อยู่ที่สองถ้าไม่ตอบ (G1-G2) (P3)
8. server เปิดเองหลังเปิดเครื่อง (ตอนนี้ hub ต้องสั่งรัน) (P3)

## Face_Regonize
1. **ตั้ง `JWT_SECRET` จริงใน .env และเปลี่ยน admin/admin123** — repo public ค่า default เดาได้ (P1)
2. **`person_id` คงที่** ส่งใน people / history / webhook (ใน `/api/look` มีแล้ว) (P2)
3. **เรียก `yield_to_interactive()` ในงานที่ยังไม่หลีก** (Event Photo, video_devices, kiosk/camera node, enrollment) จะได้ไม่บล็อกงานสดของหุ่น (P2)
4. **รับกล้องเป็นลิงก์ MJPEG** (`http://<hub>:8642/api/dev/cam.stream?dev=<dev>`) ต่อ node — กล้อง USB/ESP32-CAM เปิดได้ทางเดียว ถ้าเปิดซ้ำจะ busy/ภาพดำ (D1, G3) (P2)
5. **มือถือ 390 px พัง**: sidebar กว้าง ~255 px เนื้อหาเหลือ ~135 px ตารางถูกตัด — ให้ยุบ sidebar ต่ำกว่า ~768 px; URL ไม่มีอยู่แสดงหน้าว่าง ให้ใส่หน้า "ไม่พบหน้านี้" (P2)
6. **อ่าน `?lang=th|en|zh|ja`** จาก address แล้วจำไว้ (hub ต่อให้ทุกลิงก์) (P2)
7. สร้าง machine account `robot-hub` (`manage_machine_user.py create`) ตอนนี้เราใช้ role admin (F7) (P2)
8. ย่อรูปใหญ่ตอน decode (`IMREAD_REDUCED_COLOR_2/4`) — เช็คจำนวนหน้าที่เจอเท่าเดิม (P3)
9. `want=persons` ใน `/api/look` ตอบ 422 / `detected_at` ใส่โซนเวลา +07:00 / webhook ตอนจำคนได้ (P3)
10. ถ้าเปิดกล้องเองก่อน ให้เผยเป็นสตรีม MJPEG อ่านอย่างเดียวในเครื่อง (G4) (P3)

## Photobooth
1. **รับ `Authorization: Bearer <โทเค็นบริการ>` ที่ localhost** ที่พอร์ต AdminAuthenticator (ไม่ต้อง cookie/pairing/CSRF) (P1)
2. **หน้าเริ่มใหม่ขึ้น "Kiosk not paired"** (401 `/api/booth/frames`) — ให้หน้าบอกวิธีจับคู่ หรือจับคู่เองที่ localhost (P1)
3. **event ตอนถ่ายเสร็จ** (WS/webhook `session.finished` + session id + วิธีรับภาพที่ผู้ใช้เลือก) ให้หุ่นพูด/แจกของได้ (P2)
4. **เลือกแหล่งกล้องเป็นลิงก์ MJPEG ของ hub** แทนเปิดกล้องเอง (D2) และบอกใน `/api/health` ว่าใช้กล้องตัวไหน (P2)
5. `/api/health` ตอบโดยไม่ต้องล็อกอิน (เช็ค `127.0.0.1:8123` เคยได้ 404) (P2)
6. "วิธีส่งภาพ" (QR/พิมพ์/อีเมล) เป็นรายการตั้งค่าได้ และบอกใน health; ข้อความหน้าแรกแก้จาก admin ได้ (F-4, F-6) (P3)
7. ชื่อคนจาก Reconize ในหน้าถ่ายรูป (ตัวแปลงตั้งค่าได้) (P3)
8. `X-Frame-Options: DENY` → อนุญาต frame-ancestors เฉพาะ hub ถ้าอยากฝังในหน้า hub (`main.py:126`) (P3)
9. endpoint อ่านอย่างเดียวสำหรับ robot (สถิติวันนี้) ไม่ต้อง login admin (P3)

## ทุกแอพ
- อ่าน `?lang=` (th/en/zh/ja) และจำไว้
- เหตุการณ์ส่งมา hub ตามข้อตกลงเดียวกัน (key + `ref` ไม่ซ้ำ + แสดง `message` ตอบ 409 ไม่ใช่บั๊ก) รายละเอียดส่วน A ในฉบับเต็ม
- จะเพิ่มโมเดล/เซสชันบน GPU แจ้งในกลุ่มก่อน (GPU 12 GB ใช้ร่วมกับ Ollama + Voice)
