# Photobooth Help for Photobooth

## วิธีติดตั้ง

1. ใช้ MiceHub รุ่นที่รองรับ Help ต่อแอป (`/api/help/apps`) และภาพที่ใช้ภาษา/สีของแอปเอง (`nativeVariant`)
2. คัดลอกโฟลเดอร์ `help/` ในแพ็กเกจนี้ไปไว้ที่โฟลเดอร์หลักของ repo Photobooth ผลลัพธ์คือ `Photobooth/help/help.json` เพิ่มเฉพาะโฟลเดอร์ `help/` ไม่แก้โค้ดของแอป
3. ให้ `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` และ `img/` อยู่ใน `help/` เดียวกัน ชื่อรูปต้องตรงกับคู่มือ
4. ใน MiceHub ตรวจว่า Photobooth แสดงในเครื่องมือ แล้วเปิด Help ใหม่ ค้นหา Photobooth ลองสลับภาษาและชุดสีของ Hub

`hub_api_help.py` อ่าน `{โฟลเดอร์แอป}/help` ก่อน ถ้าขาดไฟล์รายการหรือคู่มือภาษาใดภาษาหนึ่ง จะอ่าน `apps/photobooth/help` ของ MiceHub แทน คู่มือมีสี่ภาษา ภาพที่ถ่ายจากข้างในแอปใช้ภาษาอังกฤษของแอปเอง ขั้นตอนของแขกมีทั้งธีม Midnight Blue และ Minimal Light

## Install

1. Use a MiceHub release that serves per-app Help (`/api/help/apps`) and supports fixed app screenshots (`nativeVariant`).
2. Copy this package's `help/` folder to the root of the Photobooth repository. The manifest goes at `Photobooth/help/help.json`. Add only the `help/` folder; change no app code.
3. Keep `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` and `img/` inside that folder. Keep the screenshot filenames.
4. Check that Photobooth appears in MiceHub Tools. Reload Hub Help, find Photobooth and try a different Hub language and theme.

`hub_api_help.py` checks `{app folder}/help` first. If the manifest or a language file is missing, MiceHub uses its own `apps/photobooth/help`. The four translations use screenshots of Photobooth's own English screens; the guest steps are shown in two themes.

## ถ่ายภาพใหม่ / Retake screenshots

- Run Photobooth with demo data and a synthetic camera, plus a demo Hub. From the Mice repo, run `python tools/help_shots.py --app photobooth --base <demo hub URL> --native photobooth=<photobooth URL> --only <key from shots.json> --out _out/help-review` (add `--fake-camera` for camera screens).
- ตรวจทุกภาพกับคำอธิบายก่อนใช้ ใช้ข้อมูลทดสอบและภาพสังเคราะห์เท่านั้น ไม่มีรูปหรือชื่อคนจริง
- Review every image against its step; demo data and synthetic images only. Update `apps/photobooth/help` first, then copy the same files into this package's `help/`. `python qc/run_qc.py --quiet app_help` checks both folders match byte for byte.
