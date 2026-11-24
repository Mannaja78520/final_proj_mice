# Reconize Help for Face_Regonize

## วิธีติดตั้ง

1. ใช้ MiceHub รุ่นที่รองรับภาพภาษาและสีของแอปใน Help (`nativeVariant`).
2. คัดลอกโฟลเดอร์ `help/` จากแพ็กเกจนี้ไปไว้ที่โฟลเดอร์หลักของ Face_Regonize ระดับเดียวกับ `frontend/` และ `backend/` ผลลัพธ์คือ `Face_Regonize/help/help.json`.
3. ให้ `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` และ `img/` อยู่ใน `help/` เดียวกัน ชื่อรูปต้องตรงกับคู่มือ.
4. ใน MiceHub ตรวจว่า Reconize แสดงในเครื่องมือ แล้วเปิด Help ใหม่ ค้นหา Reconize ลองสลับภาษาและชุดสีของ Hub.

`hub_api_help.py` อ่าน `{โฟลเดอร์แอป}/help` ก่อน ถ้าขาดไฟล์รายการหรือคู่มือภาษาใดภาษาหนึ่ง จะอ่าน `apps/faces/help` ของ MiceHub. คู่มือมีสี่ภาษา ภาพใน Reconize แสดงหน้าตาจริงของแอปและใช้อังกฤษเหมือนตัวแอป.

## Install

1. Use a MiceHub release that supports fixed app screenshots through `nativeVariant`.
2. Copy this package’s `help/` folder to the root of Face_Regonize, beside `frontend/` and `backend/`. The manifest goes at `Face_Regonize/help/help.json`.
3. Keep `th.html`, `en.html`, `zh.html`, `ja.html`, `shots.json` and `img/` inside that folder. Keep the screenshot filenames.
4. Check that Reconize appears in MiceHub Tools. Reload Hub Help, find Reconize and try a different Hub language and theme.

`hub_api_help.py` checks `{partner folder}/help` first. If the manifest or a language file is missing, MiceHub uses its own `apps/faces/help`. The four translations use screenshots of Reconize’s English interface.

## ถ่ายภาพใหม่ / Retake screenshots

- เปิด Reconize ด้วยฐานข้อมูลและบัญชีทดสอบแยกจากงานจริง ลงชื่อเข้าใช้ด้วย Playwright แล้วบันทึกสถานะส่วนตัวด้วย `context.storage_state(path=...)` เก็บไฟล์นี้ไว้นอก Git.
- Run an isolated Reconize demo on loopback with a separate database and demo account. Sign in with Playwright and save private storage state with `context.storage_state(path=...)`. Keep that file out of Git.
- รันคำสั่งจาก repo Mice ใช้ URL ของระบบทดสอบเอง `--only` เลือกภาพตามคีย์ใน `shots.json` และใส่ซ้ำได้ ใช้ `--fake-camera` เมื่อทดสอบกล้อง.
- Run from the Mice repository and substitute your demo URLs and state path. Repeat `--only` for the recipe keys in `shots.json` that you want to retake. Add `--fake-camera` when testing camera screens.

```powershell
python tools/help_shots.py --app faces --base http://127.0.0.1:8642 --native faces=http://127.0.0.1:5173 --state faces=_out/faces-demo-state.json --only reconize-dashboard --out _out/help-review
```

- ภาพที่ขึ้นต้น `reconize-` ถ่ายจากแอป ภาพ `faces-open` ถ่ายจากหน้าเปิดแอปใน Hub ให้เตรียม Hub ทดสอบและตั้ง `HUB_PW` สำหรับภาพนั้น.
- The `reconize-` views come from the app. For the `faces-open` view, point `--base` to an isolated demo Hub and set its demo `HUB_PW`.
- ตรวจทุกภาพและคำอธิบายก่อนนำไปใช้ อย่าใช้รูปคนจริง รายชื่อจริง หรือข้อมูลเข้าสู่ระบบ. อัปเดตที่ `apps/faces/help` ก่อน แล้วคัดลอกไฟล์ชุดเดียวกันมาที่ `help/` ในแพ็กเกจ.
- For the Activities capture, add a dummy activity so Open station is visible.
- ถ้าจะถ่ายหน้า Activities ให้เพิ่มกิจกรรมทดสอบก่อน เพื่อให้เห็น Open station.
- Review each image against its step. Use synthetic images and demo records. Update `apps/faces/help` first and copy the matching files into this package’s `help/`. `python qc/run_qc.py --quiet app_help` checks that both folders match byte for byte.
