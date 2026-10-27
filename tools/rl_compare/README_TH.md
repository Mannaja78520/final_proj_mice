# RL เทียบกับ planner (การทดลองแยก ไม่แตะระบบท่าเต้นหลัก)

เครื่องมือนี้เอาท่าคนชุดเดียวกัน (cheer v2) มาให้สองแบบทำ แล้ววัดผลด้วยเกณฑ์เดียวกัน

- **planner**: ระบบที่ Studio ใช้อยู่ (IK, ตรวจชน, RRT อ้อม) รันด้วยโค้ด Studio ตัวจริงผ่าน Node
  มีสองแบบ คือรักษารูปท่าแต่ช้ากว่าเพลง (แบบที่ใช้ทำ v2) และรักษาจังหวะเพลงแต่ตัดท่าให้สั้นลง
- **RL**: นโยบายที่เรียนเลียนแบบท่าคนด้วย PPO บน GPU ใช้ริก 10 ข้อของ Studio, servo model และกติกาความเร็วเดียวกัน

ทุกแบบถูกวัดบนการเคลื่อนที่จริงของ servo (มี lag และเพดานความเร็ว) ส่วนการชนใช้ตัวตรวจของ Studio เอง
ผลทั้งหมดยังไม่ได้ทดสอบกับหุ่นจริง

## รันเอง (ไม่ต้องใช้ AI)

ดับเบิลคลิก `tools\rl_compare\run_compare.bat` หรือพิมพ์ใน PowerShell ที่โฟลเดอร์ `code`:

```
python -m tools.rl_compare.run                  ทุกเพลง ทุกสถานการณ์ (เทรนใหม่เฉพาะที่ยังไม่มีผล)
python -m tools.rl_compare.run --fresh          เทรน RL ใหม่ทั้งหมด (หลังเปลี่ยนค่าตั้ง)
python -m tools.rl_compare.run --dance come_and_cheer_left_v2 --scenario firmware
python -m tools.rl_compare.run --quick          ทดสอบสั้นมาก ว่าทุกขั้นทำงาน
python -m tools.rl_compare.run --no-video       เอาแค่ตัวเลข ไม่ทำวิดีโอ
python -m tools.rl_compare.run --report         สร้างหน้าสรุปใหม่จากผลที่มีอยู่
```

ครั้งแรกต้องติดตั้ง: `pip install torch --index-url https://download.pytorch.org/whl/cu128`
และ `pip install opencv-python pillow numpy` (ต้องมี `node` และ `ffmpeg` ในเครื่อง ซึ่งมีอยู่แล้ว)

## ผลอยู่ที่ไหน

`code\.local\rl_compare\index.html` เปิดด้วยเบราว์เซอร์ได้เลย มีตารางผล วิดีโอ และตารางทีละรอบ
(ไม่ขึ้น git, งบรวมไม่เกิน 20 GB)

- `<เพลง>\<สถานการณ์>\comparison.mp4` วิดีโอเทียบ: คนต้นฉบับ + ทุกแบบ 2 มุม + เพลง
  เส้นม่วงบนแขนหุ่น = ท่าที่คนทำจริง ห่างมาก = ผิดมาก, `late` = หุ่นช้ากว่าเพลงกี่วินาที
- `rl_progress.mp4` คลิป RL ต่อกันทีละรอบการเทรน ดูว่าเก่งขึ้นอย่างไร
- `rl\round_XX\` ของแต่ละรอบ: `clip.mp4`, `policy.pt`, `motion.npz`, `round.json` (เวลาเทรน คะแนน)
- `results.md`, `results.json` ตัวเลขทั้งหมด

## ปรับค่าได้ที่ `config/rl_compare.json`

| ค่า | ความหมาย |
| --- | --- |
| `data.dances` | เพลงที่จะเทียบ (ชื่อไฟล์ `<ชื่อ>_analysis.json` ใน `.local/cheer_rig_1027`) |
| `scenarios[].safeDps` | เพดานความเร็วของบอร์ด 60 = เฟิร์มแวร์ตอนนี้, `null` = ใช้แค่ลิมิตของ servo |
| `metrics.collisionMm` | ระยะที่นับว่าชน `null` = ใช้ค่าเดียวกับ Studio (`safe_path.json` clearMm 5 mm + rig extraClearanceMm) ใส่ตัวเลขเพื่อลองค่าอื่นเฉพาะการทดลองนี้ |
| `servo.lagMs` | servo ตามคำสั่งช้ากี่ ms (ค่าเดา จนกว่าจะวัดในแล็บ) |
| `rl.rounds`, `rl.updatesPerRound` | เทรนนานแค่ไหน (1 รอบ = 1 คลิป) |
| `rl.envs` | หุ่นจำลองพร้อมกันบน GPU (มาก = เร็วขึ้น แต่ใช้หน่วยความจำ GPU มากขึ้น) |
| `rl.reward.*` | น้ำหนักรางวัล: `bone` ตามท่าคน, `body` เอว/ไหล่, `smooth` ความนุ่ม, `near` ห่างจากการชน, `limit` ไม่ชนลิมิตข้อ |
| `video.angles` | มุมกล้อง (yaw/pitch องศา) |
| `video.roundClipS` | คลิปต่อรอบยาวกี่วินาที |

เปลี่ยนค่าแล้วรัน `--fresh` เพื่อเทรนใหม่ (ถ้าไม่ใส่ จะใช้ผลเดิมที่เทรนไว้แล้ว)
