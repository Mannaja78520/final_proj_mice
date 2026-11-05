# สิ่งที่อยากขอจากแอพของเพื่อน (ตู้กาชาปอง + Voice) — อัปเดต 2026-10-22

ฝั่งเรา (Mice) ทำเสร็จแล้วและใช้ได้โดยไม่ต้องรอข้อไหนเลย (ทดสอบกับตู้จำลอง)
ทุกข้อด้านล่างทำให้ลิงก์แน่นขึ้น ไม่มีข้อไหนบังคับ เรียงตามความสำคัญ
อ่านจากโค้ดของเพื่อนแบบอ่านอย่างเดียว: All-Jao-Games (main) และ Face_Regonize e8d4a22

hub ของเราอยู่ที่ `http://<เครื่อง PC>:8642` ส่ง JSON ทั้งหมด

## All-Jao-Games (เกม)

ตอนนี้: hub เปิดโฟลเดอร์เกมของเพื่อนที่ `/play/all-jao/` แล้วแปะสคริปต์ของเราตอนส่งหน้าเว็บ
(ไม่แก้ไฟล์ของเพื่อน) สคริปต์อ่านผลชนะจาก localStorage (`all-jao-games.wheel.v2` logs,
`all-jao-games.claw.v1` logs, `all-jao-games.quiz.v1` players) และข้อความ
"จับคู่ครบทุกคู่แล้ว" ของเกมจับคู่ ถ้าเพื่อนเปลี่ยนชื่อ key หรือรูปข้อมูลพวกนี้ ลิงก์จะหลุด

1. **ยิง event ตอนมีคนชนะ ทุกเกม (สำคัญสุด)** จะได้ไม่ต้องพึ่งรูปข้อมูลใน localStorage
   ```js
   window.dispatchEvent(new CustomEvent("alljao:win", {detail: {
     game: "wheel",          // wheel | claw | quiz | memory
     result: "ตุ๊กตาหมี",      // ชื่อรางวัลที่ได้ / คะแนน quiz / "won"
     player: "สมชาย",        // ชื่อผู้เล่น ถ้ามี (ไม่มีก็เว้นว่าง)
     id: "<id ของ record นี้>" // ใช้ id เดียวกับที่เก็บใน logs เพื่อไม่ให้แจกซ้ำ
   }}));
   ```
   ฝั่งเรารับ event นี้ไว้แล้ว (`config/partners.json` all-jao play.watch)
2. **ช่องใส่ชื่อผู้เล่นในวงล้อและตู้คีบ** (ตอนนี้มีแค่ quiz) จะได้นับสิทธิ์ต่อคนได้ถูกคน
   ถ้าไม่มี เราใช้คนที่กล้องเห็นตอนนั้นแทน
3. **เกมจับคู่ให้เก็บผลชนะเป็น record** (เหมือน quiz players) ไม่ใช่แค่ข้อความบนจอ
4. **ถ้าจะเรียกเราเองตรงๆ (ไม่ต้องทำก็ได้)**: เปิดเกมบนเครื่องอื่นแล้วอยากให้ตู้ปล่อยของ
   ```
   POST http://<hub>:8642/api/gacha/game
   Header: X-Mice-Key: <กุญแจที่สร้างในหน้า Prize machines ▸ Other PCs and forms>
   {"game": "quiz", "result": "5", "person": "สมชาย", "ref": "<id ไม่ซ้ำของรอบนี้>"}
   ตอบ: {"ok": true, "machine": "g2", "message": "ตู้ 1 หมดแล้ว เชิญรับพวงกุญแจที่ตู้ 2 ข้างประตู"}
        {"ok": false, "reason": "person limit reached" | "event closed" | ..., "message": "..."}
   ```
   เอา `message` ไปโชว์บนจอเกมได้เลย บอกว่าไปรับที่ตู้ไหน
5. **ถ้าอยากรู้ว่าของหมด** ให้ส่ง URL มา เราจะยิง webhook `gacha.out` (ชนิดนั้นหมดทุกตู้)
   และ `gacha.dispensed` (ปล่อยแล้ว) ให้ เกมจะได้เลิกสุ่มรางวัลที่หมดแล้ว

## Face_Regonize

ที่เพื่อนทำแล้ว ขอบคุณ: `GET /api/node/{id}/present`, `call_as`, `title`, `language` ต่อคน

1. **กลุ่ม/แท็กต่อคน** เช่น `vip`, `staff`, `guest` ในข้อมูลคน และส่งออกมาใน
   `GET /api/people` กับผลรู้จำ (`/api/look`, history) เช่น `"tags": ["vip"]`
   ใช้ทำกติกา "vip ได้ของ 3 ครั้ง" โดยไม่ต้องพิมพ์ชื่อทีละคน และให้ Voice ทักทายต่างกันตามกลุ่ม
2. **นำเข้าแท็กจาก Google Sheet/Excel** คอลัมน์ `Tags` (คั่นด้วย ,) ตอน import คนเข้า
   แบบเดียวกับคอลัมน์ Name/Photo ที่มีอยู่
3. **ชื่อสะกดเหมือนกันทุกที่** กติกาของเราจับคู่ด้วยชื่อตามที่แอพเพื่อนส่งมา (ไม่สนตัวพิมพ์เล็กใหญ่)
   ถ้ามี `person_id` คงที่ส่งมาด้วยทุกที่ จะดีกว่าชื่อ
4. **(ไม่ด่วน) webhook ตอนจำคนได้** `POST <url ของเรา>` `{"name", "person_id", "node_id", "tags", "time"}`
   ตอนนี้เราถามซ้ำเป็นระยะแทน

## อัปเดต 2026-11-05 — รับ G1-G6 แล้ว + สัญญา G4 (ร่างจากฝั่งเรา)

ฝั่งเรารับ `alljao:win` รูปแบบใหม่ (`playerName`, `result.label` / `result.score`) แล้ว
และส่ง `gacha.out` ไป `POST /api/gacha/webhook` พร้อม Bearer token (token อยู่ใน env
`GACHA_WEBHOOK_TOKEN` หรือไฟล์ `.local/gacha/game_webhook_token.txt` ฝั่งเรา ไม่อยู่ใน git)
ตั้งใน `config/gacha.json`: `"webhooks": {"out": [{"url": "http://<เครื่องเกม>:4173/api/gacha/webhook", "format": "alljao"}]}`

**G4 สัญญา `POST /api/gacha/game` (ถ้าเพื่อนอยากให้เกมเรียก hub ตรง ไม่บังคับ)**
- Request: `POST http://<hub>:8642/api/gacha/game` JSON
  `{"game":"quiz","result":"8","person":"<playerName>","ref":"<detail.id>"}`
- Auth: header `X-Mice-Key: <กุญแจที่สร้างในหน้า Prize machines ▸ Other PCs and forms>`
  (เก็บเป็น env/ไฟล์ฝั่งเซิร์ฟเวอร์ของเกม ห้ามใส่ในหน้าเว็บหรือ git)
- Idempotency: `ref` ซ้ำ (ต่อ game) = ตอบ `{"ok":true,"repeat":true}` ไม่แจกซ้ำ จึง retry ได้เมื่อ timeout
  ใช้ `detail.id` เป็น `ref`
- Response 200: `{"ok":true,"machine":"g2","message":"..."}` แจกแล้ว (แสดง `message` บอกที่รับ)
  `{"ok":false,"reason":"no prize for this result"}` ไม่ถึงเกณฑ์ (ไม่ใช่ error)
  409 `{"ok":false,"reason":"person limit reached"|"event closed"|"out of stock"|...,"message":"..."}`
  401 key ผิด; ไม่ต้อง retry เมื่อ 4xx
- เกณฑ์ชนะ (เช่น quiz คะแนนขั้นต่ำ) ตั้งฝั่ง hub ไม่ใช่ฝั่งเกม

**ขอเพิ่มใน `alljao:win` (ไม่บังคับ แต่ทำให้ฝั่งเราไม่ต้องตั้งค่าเอง)**:
- quiz: `result.total` = คะแนนเต็มของรอบนั้น (จำนวนข้อ) เพื่อให้เพิ่มข้อได้โดยฝั่งเราไม่ต้องแก้ เกณฑ์ตั้งเป็น "80%" ได้
- วงล้อ: `result.noPrize: true` ที่ช่อง "ลองใหม่"/ไม่ได้ของ (ตอนนี้เราข้ามจากคำใน `games_skip`)

**ที่ยังขอเพิ่ม (ไม่บังคับ)**: ใน `gacha.out` webhook ให้เกมรับ field เสริม `item` (ชนิดที่หมด) และ
`machines` จะได้เลิกสุ่มรางวัลชนิดนั้นตรงตัว (ตอนนี้เรายิงเพิ่มให้ ถ้า server ปฏิเสธ field แปลกให้บอก);
และให้มี `gacha.dispensed` ด้วย ถ้าอยากโชว์ตู้ที่ปล่อยของ

## ฝั่งเราเตรียมไว้แล้ว (ไม่ต้องทำอะไร)

- กติกาแจกของต่องาน/ต่อคน/คนพิเศษ ตั้งในหน้า Prize machines หรือดึงจาก Google Sheet
  (ตัวอย่าง `docs/gacha/items.sample.csv`, `people.sample.csv`)
- Voice: คำตอบแบบไหนให้ของอะไร (ต่องานได้), เก็บว่าคนถามเรื่องอะไร + กราฟ + CSV
- รายละเอียด API ทั้งหมด: `docs/gacha/README.md`
