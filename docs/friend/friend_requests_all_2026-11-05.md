# ขอเพื่อนทั้งหมดในฉบับเดียว + ข้อตกลงกลางระหว่าง hub กับทุกแอพ — 2026-11-05

ส่งทีเดียวในกลุ่ม ใช้ได้กับ 3 แอพ: **All-Jao-Games**, **Face_Regonize (Reconize)**, **Photobooth**
อ่านโค้ดของเพื่อนแบบอ่านอย่างเดียว ไม่แก้ ไม่คัดลอก ฝั่งเราทำเสร็จและใช้ได้โดยไม่ต้องรอข้อไหน
ทุกข้อทำให้ลิงก์แน่นขึ้น ไม่บังคับ เรียงตามความสำคัญ **P1 ทำก่อน / P2 ควรมี / P3 ไว้ทีหลัง**

> ที่ยังไม่ได้เช็ค: commit ล่าสุดของเพื่อน (เราเช็คจากคลาวด์ไม่ได้) ข้อไหนเพื่อนทำไปแล้ว ข้ามได้เลย
> โค้ดที่อ้างถึง: Face_Regonize e8d4a22, Photobooth 858f0b6, All-Jao-Games f9e8ff4

---

## ส่วน A — ข้อตกลงกลาง hub ↔ แอพ (ใช้เหมือนกันทุกแอพ)

เดิมข้อตกลงนี้ (เกม → ตู้กาชา `POST /api/gacha/game`) ใช้กับเกมอย่างเดียว ตอนนี้ขยายให้ **ทุกแอพใช้รูปแบบเดียวกัน**
ทั้งขาไป (แอพเรียก hub) และขากลับ (hub เรียกแอพ) hub อยู่ที่ `http://<เครื่อง PC>:8642` ส่ง/รับ JSON ทั้งหมด

### A1. ใช้กับอะไรได้บ้าง

| ทิศทาง | ตัวอย่าง | มีแล้วฝั่งเรา |
|---|---|---|
| แอพ → hub: "มีเหตุการณ์เกิดขึ้น" | เกมแจ้งว่ามีคนชนะ, Photobooth แจ้งถ่ายรูปเสร็จ, Face แจ้งจำคนได้ | `POST /api/gacha/game` ใช้ได้แล้ว (เกมเท่านั้น) |
| แอพ → hub: "ขอให้ทำ" | ขอให้ตู้ปล่อยของ, ขอให้หุ่นพูด | `/api/gacha/dispense`, `/api/gacha/can`, `/api/speak` |
| hub → แอพ: "ถามข้อมูล/สั่งงาน" | ถามว่าใครอยู่หน้ากล้อง, ดูสถานะ, เข้าหน้า admin | มีแล้วกับ Face (`/api/look`, `/api/node/{id}/present`) |
| hub → แอพ: webhook | ตู้หมด/ปล่อยแล้ว บอกให้แอพรู้ | `gacha.dispensed` `gacha.out` `gacha.empty` ฯลฯ (แอพส่ง URL มาให้เรา) |

### A2. ขาไป: แอพเรียก hub

```
POST http://<hub>:8642/api/gacha/game          (เส้นทางอื่นของ hub ใช้หัวข้อ/ตอบแบบเดียวกัน)
Header: X-Mice-Key: <กุญแจ>        หรือ  Authorization: Bearer <โทเค็นที่ hub ออกให้> (ดู A4)
Content-Type: application/json
{"game": "quiz", "result": "5", "person": "สมชาย", "ref": "<id ไม่ซ้ำของเหตุการณ์นี้>"}
```
- `ref` **บังคับในทางปฏิบัติ**: ส่งซ้ำ `ref` เดิมให้ผลครั้งเดียว (hub จำ `game:ref` ไว้ — `main_python/gacha.py:686-690`) ลองใหม่ตอนเน็ตหลุดได้ปลอดภัย
- `person` เว้นว่างได้ ถ้าส่ง `"@face"` hub ใช้คนที่กล้องเห็นตอนนั้น
- กุญแจ (X-Mice-Key) สร้างเองในหน้า Prize machines ▸ Other PCs and forms ต่อหนึ่งแอพหนึ่งกุญแจ ลบทิ้งได้ทันที
- หน้าเว็บที่ hub เสิร์ฟเอง (`/play/<แอพ>/`) ไม่ต้องใช้กุญแจ (hub เช็คว่า Origin คือ hub เอง — `main_python/hub_auth.py:237`)

### A3. คำตอบ (รูปเดียวกันทุกเส้นทาง)

| กรณี | HTTP | body |
|---|---|---|
| สำเร็จ | 200 | `{"ok": true, "machine": "g2", "message": "ตู้ 1 หมดแล้ว เชิญรับพวงกุญแจที่ตู้ 2 ข้างประตู"}` |
| ไม่มีรางวัลสำหรับผลนี้ (แพ้) **ไม่ใช่ error** | 200 | `{"ok": false, "reason": "no prize for this result"}` |
| ติดกติกา (ครบสิทธิ์/งานปิด/ของหมด) | 409 | `{"ok": false, "reason": "person limit reached" \| "event closed" \| ..., "message": "..."}` |
| ไม่มีกุญแจ/ผิด | 401 | `{"ok": false, "error": "..."}` |
- ทุกคำตอบมี `message` เป็นภาษาคน เอาไปโชว์บนจอของแอพได้เลย ไม่ต้องแปลเอง
- `reason` เป็นรหัสคงที่ให้โปรแกรมเช็ค (ห้ามแอพเอาไปโชว์คนใช้)
- แอพ**ห้ามถือว่า 409 คือบั๊ก** แค่แสดง `message` แล้วเล่นต่อ

### A4. Auth เดียวกันทุกที่ (ต่อกับแผน admin เดิม)

หลักการ: **หน้า login ของ hub เป็นประตูหน้า** แอพเพื่อนไม่ต้องมีรหัสผ่านที่เดาได้ และไม่ต้องเก็บรหัสผ่านของ hub

1. **แอพ → hub**: ใช้ `X-Mice-Key` (มีแล้ว) ต่อแอพ
2. **hub → แอพ**: ส่ง `Authorization: Bearer <โทเค็น>` ที่ hub ออกให้ รูปแบบเดียวกันทุกแอพ:
   `mice1.<payload base64url>.<ลายเซ็น HMAC-SHA256 base64url>`
   payload = `{"iss":"mice-hub","app":"photobooth","scope":"admin","iat":1730800000,"exp":1730800300}` (อายุสั้น ~5 นาที)
   ตรวจฝั่งแอพ: คำนวณ HMAC ของ payload ด้วยค่า `MICE_HUB_SECRET` ใน .env ของแอพ (สุ่มยาว ≥32 ตัวอักษร, hub กับแอพถือค่าเดียวกัน) เทียบแบบ constant-time เช็ค `exp`, `app` ตรงชื่อตัวเอง แล้วยอมรับ
   ตัวอย่างตรวจ Python (ประมาณ 10 บรรทัด ไม่ต้องลงไลบรารี):
   ```python
   import hmac, hashlib, base64, json, time, os
   def hub_token_ok(tok, app):
       try: tag, p, sig = tok.split(".")
       except ValueError: return False
       want = hmac.new(os.environ["MICE_HUB_SECRET"].encode(), p.encode(), hashlib.sha256).digest()
       if tag != "mice1" or not hmac.compare_digest(base64.urlsafe_b64decode(sig + "=="), want): return False
       d = json.loads(base64.urlsafe_b64decode(p + "=="))
       return d.get("app") == app and d.get("exp", 0) > time.time()
   ```
3. **ของที่ไม่เปลี่ยน**: ถ้าแอพมี login ของตัวเองอยู่แล้วและใช้ได้ (เช่น Face_Regonize รับ Bearer JWT อยู่แล้ว — `auth.py:48`, `deps.py:52-61`) **ไม่ต้องทำอะไรเพิ่ม** เราใช้ของเดิมต่อ โทเค็น `mice1` เป็นทางเลือกสำหรับแอพที่ยังไม่มี
4. **ขอบเขต**: โทเค็น/กุญแจที่ hub ออกให้แอพ ใช้ได้แค่เส้นทางที่ระบุ (`scope`) ไม่ใช่สิทธิ์ admin ของ hub ทั้งหมด
5. ความลับทั้งหมด (`MICE_HUB_SECRET`, กุญแจ) เก็บใน `.env` / ไฟล์ที่ git ไม่ติดตาม ห้าม commit (repo ของเรา public)

ฝั่งเราทำเอง (ไม่ต้องรอ): ชนิด login `jwt` (มีแล้ว) + `bearer`/`mice1` ใน `config/partners.json`, secret ต่อแอพในไฟล์ local ที่ git ไม่ติดตาม,
hub โชว์ปุ่ม admin ของแอพเฉพาะแอดมินของ hub

### A5. Webhook (hub → แอพ)
แอพส่ง URL มา เราตั้งใน `webhooks.<kind>` แล้ว `POST` JSON `{type, machine, item, person, app, seq, stock, result, reason, message, event, time}`
`type` = `gacha.dispensed | gacha.jam | gacha.empty | gacha.out | gacha.low | gacha.refused`
ส่งพร้อม `Authorization: Bearer mice1...` (A4) ให้แอพเช็คว่ามาจาก hub จริง ตอบ 2xx ภายใน 5 วิ ไม่เช่นนั้นเราทิ้ง ไม่ retry รัว

### A6. ข้อตกลงที่ทุกแอพถือเหมือนกัน
- เวลาเป็น ISO-8601 พร้อมโซนเวลา (เช่น `2026-11-05T16:30:00+07:00`)
- ชื่อคน: ถ้ามี `person_id` คงที่ ใช้ id นำชื่อ (ชื่อเทียบแบบไม่สนตัวพิมพ์เล็กใหญ่)
- เปลี่ยนรูปแบบ key/ฟิลด์ที่เราอ่านอยู่ → แจ้งในกลุ่มก่อน (ลิงก์จะหลุดเงียบๆ)

---

## ส่วน B — รายการขอแยกตามแอพ (รวมจากทุกแหล่ง ตัดที่ซ้ำและที่เสร็จแล้ว)

### B1. All-Jao-Games (เกม)

ตอนนี้ hub เปิดโฟลเดอร์เกมที่ `/play/all-jao/` แล้วแปะสคริปต์เราอ่านผลจาก localStorage
(`all-jao-games.wheel.v2` logs, `.claw.v1` logs, `.quiz.v1` players, ข้อความ "จับคู่ครบทุกคู่แล้ว") — `wheel script.js:8 + wheel-state.js:28`, `claw-game.js:8,308`, `quiz-game.js:8,138`, `matching-game.js:84,94` ถ้าเปลี่ยนชื่อ key ลิงก์หลุด

| # | ขอ | ทำไม | อ้างอิง | ระดับ |
|---|---|---|---|---|
| 1 | **ยิง event ตอนมีคนชนะ ทุกเกม** `window.dispatchEvent(new CustomEvent("alljao:win", {detail:{game, result, player, id}}))` โดย `game` = wheel/claw/quiz/memory และ `id` = id เดียวกับ record ใน logs | ไม่ต้องพึ่งรูปข้อมูลใน localStorage ที่เปลี่ยนเมื่อไหร่ก็ได้ เรารับ event นี้ไว้แล้ว (`config/partners.json` all-jao `play.watch`) | `docs/gacha/friend_requests.md` ข้อ 1 | **P1** |
| 2 | **ช่องใส่ชื่อผู้เล่นในวงล้อกับตู้คีบ** (ตอนนี้มีแค่ quiz) | นับสิทธิ์ต่อคนถูกคน ถ้าไม่มีเราใช้คนที่กล้องเห็นแทน (`@face`) ซึ่งอาจผิดคน | quiz-game.js:138 มีให้ดู | P2 |
| 3 | **เกมจับคู่เก็บผลชนะเป็น record** (เหมือน quiz players) | ตอนนี้เราต้องอ่านข้อความบนจอ ซึ่งเปลี่ยนคำก็พัง | matching-game.js:84,94 | P2 |
| 4 | **admin ของเกม**: ตอนนี้ `admin/1234` เช็คในเบราว์เซอร์ ไม่ได้ป้องกันอะไรจริง → ให้รับ admin flag จากหน้าที่ hub เสิร์ฟ (`/play/all-jao/`) หรือยอมรับว่าเกมไม่มี admin จริง | admin เป็นของ hub เจ้าเดียว | script.js:143-152 | P2 |
| 5 | **(ไม่ต้องทำก็ได้)** ถ้าเปิดเกมบนเครื่องอื่นแล้วอยากให้ตู้ปล่อยของ ให้เรียก A2 ตรงๆ ด้วยกุญแจ | เล่นบนเครื่องอื่นได้โดยไม่ต้องผ่าน `/play/` | ส่วน A | P3 |
| 6 | **(ไม่ต้องทำก็ได้)** ส่ง URL webhook มาถ้าอยากรู้ว่าของหมด (`gacha.out`, `gacha.dispensed`) | เกมเลิกสุ่มรางวัลที่หมดแล้ว | ส่วน A5 | P3 |

### B2. Face_Regonize (Reconize)

ที่เพื่อนทำแล้ว ขอบคุณ (ตัดออกจากรายการ): `GET /api/node/{id}/present`, `call_as`, `title`, `language` ต่อคน,
โมเดลรู้จำหน้าแบบ dual/CUDA รับหลายงานพร้อมกัน (ข้อขอ 2026-10-19 — 4 แหล่งพร้อมกัน 32/32)

| # | ขอ | ทำไม | อ้างอิง | ระดับ |
|---|---|---|---|---|
| 1 | **ตั้ง `JWT_SECRET` จริงใน .env และเปลี่ยน admin/admin123 เดิม** | ค่า default เดาได้ และโค้ดใน repo เป็นสาธารณะ ใครก็ปลอม token ได้ (เป็นข้อเดียวที่เรื่อง admin ต้องการจาก Face) | `config.py:104` (JWT_SECRET), `config.py:108-109` (admin) | **P1** |
| 2 | **แท็กกลุ่มต่อคน** (`vip`, `staff`, `guest`) ใน `GET /api/people`, `/api/look`, history เช่น `"tags": ["vip"]` | ทำกติกา "vip ได้ของ 3 ครั้ง" และให้ Voice ทักต่างกันตามกลุ่ม โดยไม่พิมพ์ชื่อทีละคน | `docs/gacha/friend_requests.md` Face ข้อ 1 | P1 |
| 3 | **นำเข้าแท็กจาก Google Sheet/Excel** คอลัมน์ `Tags` (คั่นด้วย ,) แบบเดียวกับ Name/Photo | ไม่ต้องกรอกแท็กมือทีละคน | เดียวกับ 2 | P2 |
| 4 | **`person_id` คงที่ส่งมาทุกที่** (people, look, history, webhook) | ชื่ออาจสะกดต่างกัน id คงที่ปลอดภัยกว่า | เดียวกับ 2 | P2 |
| 5 | **`Retry-After` เป็นวินาทีจริง** ไม่ใช่ 0 ตลอด | วัดจริง 2026-10-15 `/api/look` โดน 429 ติดกันเกิน 1 นาที แล้ว header บอกให้ลองใหม่ทันที | `services/look_service.py:50-63,112` | P2 |
| 6 | **`/api/health` บอกสถานะงาน**: `{"status":"ok","busy_with":"event_photo","live_queue":2,"device":"cuda"}` + เวลารอเฉลี่ยของ `/api/look` | ฝั่งเราบอกคนใช้ไม่ได้ว่ารอเพราะอะไร และวัดว่าแก้แล้วดีขึ้นจริง | ตอนนี้ตอบแค่ `{"status":"ok"}` | P2 |
| 7 | **ให้งานที่ยังไม่หลีก `/api/look` เรียก `yield_to_interactive()` ด้วย**: Event Photo, `video_devices.py:50/87/111`, kiosk/camera node (`api/recognition.py:208` รอ lock ไม่จำกัด), enrollment/import, `photo_processing_service.py:1255` | งานสดของหุ่นจะไม่ถูกบล็อก (ถ้าข้อ dual-model ที่ทำไปแล้วครอบคลุมอยู่แล้ว ข้ามได้) | `event_photo_detection_service.py:108` | P3 |
| 8 | **ทำ embedding แบบ batch** แทนวนทีละหน้า | วัด 8 หน้า 39.5 → 11.7 ms (เร็วขึ้น 3.4 เท่า) ช่วยรูปหมู่ ความแม่นเท่าเดิม | `engine.py:460-461` | P3 |
| 9 | **ย่อรูป ~12 MP ตอน decode** ด้วย `cv2.IMREAD_REDUCED_COLOR_2/4`, ย่อด้วย `INTER_LINEAR` | decode 33 → 17/12 ms; ย่อ 4.4 → 0.7 ms **เช็คก่อน**: จำนวนหน้าที่เจอต้องเท่าเดิมกับชุดรูปทดสอบของเพื่อน | ผลวัดใน `face_perf_2026-11-05` (PC ของเรา) | P3 |
| 10 | **ย้าย .onnx ที่ไม่ใช้ออกจาก `buffalo_l`** (insightface สร้าง session ทั้ง 5 ไฟล์แล้วทิ้ง 3) | เปิดโปรแกรมเร็วขึ้น เท่านั้น | เดียวกับ 8 | P3 |
| 11 | **`want=persons` ใน `/api/look` ตอบ 422** → ทำให้ใช้ได้ | ไว้ใช้เมื่อเราต้องการข้อมูลรายคนในคำขอเดียว | `api/look.py:41` | P3 |
| 12 | **`detected_at` ใน history ใส่โซนเวลา** (+07:00) | ตรงกับ A6 | `models/models.py:74,124` | P3 |
| 13 | **webhook ตอนจำคนได้** `POST <url ของเรา>` `{"name","person_id","node_id","tags","time"}` พร้อม Bearer ตาม A4 | ตอนนี้เราถามซ้ำเป็นระยะ | `docs/gacha/friend_requests.md` Face ข้อ 4 | P3 |

**ไม่ต้องทำ (เราลองแล้ว ไม่ช่วย):** KV cache (ไม่ใช่ LLM), FP16 (12.08 vs 11.97 ms), det_size 640 (ช้าลง หน้า 62→66), det_size 160 (พลาดหน้า),
ตัวเลือก ORT, ปิด TF32 (34.5 ms ช้าลงมาก), INT8/buffalo_s (แม่นลด) — ความเร็วตอนนี้ ~12 ms/รูป VRAM ~0.56 GB เร็วพออยู่แล้ว ข้อ 8-10 เป็นของแถม

### B3. Photobooth

| # | ขอ | ทำไม | อ้างอิง | ระดับ |
|---|---|---|---|---|
| 1 | **ตัวตรวจสิทธิ์ตัวที่สองที่พอร์ต AdminAuthenticator ที่มีอยู่**: รับ `Authorization: Bearer <โทเค็นบริการ>` จาก env เฉพาะ localhost ไม่ต้องใช้ cookie/pairing/CSRF (ใช้โทเค็น `mice1` ตาม A4 ได้เลย) | ตอนนี้ hub login แทนไม่ได้ (ต้อง cookie + จับคู่อุปกรณ์ + CSRF, รหัสผ่านตั้งได้ทาง CLI เท่านั้น) | `admin_gate.py:38-49`, `52-69`, `cli.py:318` | **P1** |
| 2 | **ให้หน้าถ่ายรูปเอาชื่อจาก Reconize ได้** (ตัวแปลงชื่อที่ตั้งค่าได้) | ตอนนี้ไม่มี adapter รับชื่อคน ตู้ถ่ายรูปไม่รู้ว่าใครยืนอยู่ | handoff `face-photobooth-pc.md:109` | P2 |
| 3 | **รับภาพจากสตรีมที่ hub แชร์** ไม่ใช่แค่เลขกล้อง physical | กล้องตัวเดียวใช้ได้หลายแอพ ไม่ต้องแย่งกล้อง | handoff `face-photobooth-pc.md:110` | P2 |
| 4 | **(ถ้าจะใช้โมเดลหน้า)** เรียก `/api/look` ของ Face แบบเดียวกับเรา: 1 คำขอต่อกล้อง ไม่เกิน 4 ภาพ/วิ ส่ง `source` เป็นชื่อกล้อง JPEG ≤ 2 MiB | จะได้ไม่แย่งคิวกับหุ่น | `docs/friend/` ข้อ B2 | P3 |
| 5 | **ตรวจ `http://127.0.0.1:8123/api/health`**: ตอนนี้ 404 ทั้งที่ process ฟังพอร์ตอยู่ ยืนยันว่าบริการ delivery ทำงานหรือเปล่า | ไม่แน่ใจว่าฟังก์ชันส่งงานใช้ได้ | handoff `face-photobooth-pc.md:121` | P3 |
| 6 | ส่ง `X-Frame-Options: DENY` อยู่ → hub เปิดได้แค่แท็บใหม่ (ถ้าอยากฝังในหน้า hub ให้อนุญาต frame-ancestors เฉพาะ hub) | ฝั่งเราไม่บังคับ แค่แจ้ง | `backend/src/photobooth/main.py:126` | P3 |

---

## ส่วน C — สรุปสั้นสำหรับแปะกลุ่ม (ถ้าอ่านแค่นี้)

ทำ 4 ข้อนี้ก่อน ที่เหลือทำเมื่อว่าง:
1. **All-Jao**: ยิง `alljao:win` ตอนมีคนชนะทุกเกม (B1-1)
2. **Face_Regonize**: ตั้ง `JWT_SECRET` จริง + เปลี่ยน admin/admin123 (B2-1) และใส่ `tags` ต่อคน (B2-2)
3. **Photobooth**: รับ Bearer service token ที่ localhost (B3-1)
4. ทุกคน: ถ้าจะส่งเหตุการณ์มา hub ใช้ข้อตกลงส่วน A เดียวกัน (key + `ref` ไม่ซ้ำ)

ทุกแอพ: ความลับ (secret/key) อย่าลง git — repo ของเรา public

## ที่มาของรายการ (เพื่อตรวจ)
`docs/gacha/friend_requests.md` (2026-10-22), `docs/friend_requests_admin_2026-11-04.md` (PR #122), `docs/friend/face_regonize_perf_2026-11-05.md` (PR #125),
`friend_api/ขอเพื่อนแก้_2026-10-19.md`, `friend_api/gacha_requests_2026-10-22.md`, `handoff/tasks/face-photobooth-pc.md`, `handoff/tasks/friend-face-server.md`
เอกสารเดิมยังเก็บไว้เป็นหลักฐาน ฉบับนี้แทนที่ในการส่งให้เพื่อน
