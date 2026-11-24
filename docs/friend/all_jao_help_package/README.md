# All-Jao Games Help for All-Jao-Games

## วิธีติดตั้ง

1. ใช้ MiceHub รุ่นที่รองรับ Help ต่อแอป (`/api/help/apps`) และภาพที่ใช้ภาษา/สีของแอปเอง (`nativeVariant`)
2. คัดลอกโฟลเดอร์ `help/` ในแพ็กเกจนี้ไปไว้ที่โฟลเดอร์หลักของ All-Jao-Games ระดับเดียวกับ `server.cjs` ผลลัพธ์คือ `All-Jao-Games/help/help.json` อย่าแก้ไฟล์เกมอื่น
3. ให้ `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` และ `img/` อยู่ใน `help/` เดียวกัน ชื่อรูปต้องตรงกับคู่มือ
4. ใน MiceHub ตรวจว่า All-Jao Games แสดงในเครื่องมือ แล้วเปิด Help ใหม่ ค้นหา All-Jao ลองสลับภาษาและชุดสีของ Hub

`hub_api_help.py` อ่าน `{โฟลเดอร์แอป}/help` ก่อน ถ้าขาดไฟล์รายการหรือคู่มือภาษาใดภาษาหนึ่ง จะอ่าน `apps/all-jao/help` ของ MiceHub แทน คู่มือมีสี่ภาษา ภาพภายในเกมเป็นหน้าจอจริงของเกม ซึ่งใช้ภาษาไทยและสีของเกมเอง

## Install

1. Use a MiceHub release that serves per-app Help (`/api/help/apps`) and supports fixed app screenshots (`nativeVariant`).
2. Copy this package's `help/` folder to the root of All-Jao-Games, beside `server.cjs`. The manifest goes at `All-Jao-Games/help/help.json`. Change no other game file.
3. Keep `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` and `img/` inside that folder. Keep the screenshot filenames.
4. Check that All-Jao Games appears in MiceHub Tools. Reload Hub Help, find All-Jao and try a different Hub language and theme.

`hub_api_help.py` checks `{app folder}/help` first. If the manifest or a language file is missing, MiceHub uses its own `apps/all-jao/help`. The four translations use screenshots of the game's own (Thai) screens.

## ถ่ายภาพใหม่ / Retake screenshots

- Run the game's own server on loopback (`node server.cjs`, port 4173) with demo data, and a demo Hub. From the Mice repo:

```powershell
python tools/help_shots.py --app all-jao --base http://127.0.0.1:8642 --only all-jao-games-box --out _out/help-review
```

- ตรวจทุกภาพกับคำอธิบายก่อนใช้ ใช้ข้อมูลทดสอบเท่านั้น ไม่มีรายชื่อหรือข้อมูลจริง
- Review every image against its step; demo data only. Update `apps/all-jao/help` first, then copy the same files into this package's `help/`. `python qc/run_qc.py --quiet app_help` checks both folders match byte for byte.
