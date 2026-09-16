import json
import re

new_sources = [
  {
    "key": "incropera",
    "number": 81,
    "author": "F. P. Incropera, D. P. DeWitt, T. L. Bergman, and A. S. Lavine",
    "title": "Fundamentals of Heat and Mass Transfer",
    "year": "2006",
    "kind": "Book",
    "url": "https://www.wiley.com/",
    "locator": "6th Edition, Wiley. ISBN 978-0471457282",
    "scope": "Conduction, convection, and lumped capacitance thermal modeling for servo heat dissipation.",
    "access": "Official book / print",
    "doi": "",
    "accessed": "2026-09-11"
  },
  {
    "key": "meriam",
    "number": 82,
    "author": "J. L. Meriam and L. G. Kraige",
    "title": "Engineering Mechanics: Statics",
    "year": "2012",
    "kind": "Book",
    "url": "https://www.wiley.com/",
    "locator": "7th Edition, Wiley. ISBN 978-0470614730",
    "scope": "Force and moment equilibrium calculations for static joints.",
    "access": "Official book / print",
    "doi": "",
    "accessed": "2026-09-11"
  },
  {
    "key": "hughes",
    "number": 83,
    "author": "Austin Hughes and Bill Drury",
    "title": "Electric Motors and Drives: Fundamentals, Types and Applications",
    "year": "2013",
    "kind": "Book",
    "url": "https://www.sciencedirect.com/book/9780080983325/electric-motors-and-drives",
    "locator": "4th Edition, Newnes.",
    "scope": "DC servo motor characteristics, torque production, and thermal limits.",
    "access": "Publisher page",
    "doi": "10.1016/C2011-0-07555-5",
    "accessed": "2026-09-11"
  },
  {
    "key": "krishnan",
    "number": 84,
    "author": "R. Krishnan",
    "title": "Electric Motor Drives: Modeling, Analysis, and Control",
    "year": "2001",
    "kind": "Book",
    "url": "https://www.pearson.com/",
    "locator": "Prentice Hall. ISBN 978-0130910141",
    "scope": "Electromechanical equations for DC servo motors, back-EMF, and dynamic responses.",
    "access": "Official book / print",
    "doi": "",
    "accessed": "2026-09-11"
  }
]

# 1. Update ref_sources.js
with open('docs/ref_sources.js', 'r', encoding='utf-8') as f:
    src_content = f.read()

if '\"key\": \"incropera\"' not in src_content and 'key: "incropera"' not in src_content:
    src_content = src_content.replace('  }\n];', '  },\n' + ',\n'.join(['  ' + json.dumps(s, indent=4).replace('\\n', '\n') for s in new_sources]) + '\n];')
    
    # Fix quotes for new sources to match check_ref regex rules just in case
    for key in ['key', 'number', 'author', 'title', 'year', 'kind', 'url', 'locator', 'scope', 'access', 'doi', 'accessed']:
        src_content = src_content.replace(f'    \"{key}\":', f'    {key}:')
    
    with open('docs/ref_sources.js', 'w', encoding='utf-8') as f:
        f.write(src_content)
    print('Updated docs/ref_sources.js')

# 2. Add new topics to ref_data.js
new_topics = [
  {
    "id": "thermodynamics-motor",
    "group": "Embedded hardware",
    "name": "Heat Transfer (Motor Thermal Model)",
    "where": [],
    "eq": "q = hA(T_s - T_\\infty)\\n\\Delta T = P_{loss} R_{th}",
    "why": "Calculates heat dissipation and temperature rise in servo motors to prevent overheating during continuous operation under load.",
    "watch": "Assumes lumped capacitance model; actual heat transfer relies heavily on ambient airflow and chassis conductivity.",
    "sources": ["incropera", "hughes", "krishnan", "esp32", "servo-lib"],
    "name_th": "การถ่ายเทความร้อน (แบบจำลองทางความร้อนของมอเตอร์)",
    "why_th": "คำนวณการกระจายความร้อนและอุณหภูมิที่เพิ่มขึ้นในเซอร์โวมอเตอร์เพื่อป้องกันความร้อนสูงเกินไประหว่างการทำงานต่อเนื่อง",
    "status": "background",
    "provenance": "Thermal limits for servo sizing",
    "units": "q: W, h: W/m²·K, T: K, R_th: K/W",
    "reviewed": "2026-09-11"
  },
  {
    "id": "statics-joints",
    "group": "Nong — the humanoid",
    "name": "Static Mechanics (Holding Torque)",
    "where": [],
    "eq": "\\Sigma F = 0\\n\\Sigma M = 0\\n\\tau_{hold} = J^T(q) F_{tip} + g(q)",
    "why": "Equilibrium equations for static mechanics. Used to calculate the holding torque required by servos to counteract gravity and payload forces at rest.",
    "watch": "Friction and gear back-drivability offer some passive holding, but worst-case calculations must assume the servo provides full torque.",
    "sources": ["meriam", "hibbeler", "craig", "spong", "siciliano"],
    "name_th": "กลศาสตร์สถิต (แรงบิดต้านทานเพื่อรักษาสมดุล)",
    "why_th": "สมการสมดุลสถิต ใช้สำหรับคำนวณแรงบิดที่เซอร์โวต้องใช้ในการยึดตำแหน่งเพื่อต้านแรงโน้มถ่วงและน้ำหนักบรรทุก",
    "status": "background",
    "provenance": "Payload and holding torque sizing",
    "units": "F: N, M: N·m, τ: N·m",
    "reviewed": "2026-09-11"
  },
  {
    "id": "servo-motor-model",
    "group": "Embedded hardware",
    "name": "DC Servo Motor Electromechanics",
    "where": [],
    "eq": "V = I R + L \\frac{dI}{dt} + K_e \\omega\\n\\tau_m = K_t I",
    "why": "Fundamental equations for DC servo motors linking electrical inputs (voltage, current) to mechanical outputs (torque, speed). Back-EMF restricts top speed.",
    "watch": "Torque is strictly proportional to current, but voltage limits restrict how fast the required current can be reached due to motor inductance.",
    "sources": ["krishnan", "hughes", "feedback", "franklin", "servo-lib"],
    "name_th": "กลศาสตร์ไฟฟ้าของเซอร์โวมอเตอร์กระแสตรง",
    "why_th": "สมการพื้นฐานสำหรับเซอร์โวมอเตอร์กระแสตรง เชื่อมโยงตัวแปรทางไฟฟ้า (แรงดัน กระแส) กับทางกล (แรงบิด ความเร็ว)",
    "status": "background",
    "provenance": "Electrical models for motor speed and torque",
    "units": "V: V, I: A, R: Ω, L: H, K_e: V·s/rad, τ_m: N·m",
    "reviewed": "2026-09-11"
  }
]

with open('docs/ref_data.js', 'r', encoding='utf-8') as f:
    data_content = f.read()

for t in new_topics:
    if f'"{t["id"]}"' not in data_content and f'{t["id"]}' not in data_content:
        # dump json without double-escaping newlines and quotes on keys
        t_str = "  {\n"
        for k, v in t.items():
            if k == "sources":
                t_str += f"    {k}: [\n      " + ",\n      ".join([f'"{s}"' for s in v]) + "\n    ],\n"
            elif k == "where":
                t_str += f"    {k}: [],\n"
            else:
                t_str += f"    {k}: \"{v}\",\n"
        t_str = t_str.rstrip(",\n") + "\n  },\n"
        
        # inject to the beginning
        data_content = data_content.replace('window.REF = [\n', 'window.REF = [\n' + t_str)

with open('docs/ref_data.js', 'w', encoding='utf-8') as f:
    f.write(data_content)
print('Updated docs/ref_data.js with new mechanics/servo topics.')

