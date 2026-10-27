"""The index the user opens: every result table, video and training round.

Reads only what run.py saved (summary.json, training.json), so it can be
rebuilt any time with `--report`. Writes index.html (Thai, opens straight
from the folder), results.json (everything) and results.md (the tables).
"""
import html
import json
from pathlib import Path

# (key in score, Thai label, how to judge: "low" / "abs" / "one", format)
METRICS = [
    ("boneMusicDeg", "ผิดจากท่าคน ตามเวลาเพลงจริง (°)", "low", "%.1f"),
    ("boneShapeDeg", "ผิดจากรูปท่า ไม่นับเวลา (°)", "low", "%.1f"),
    ("waistErrDeg", "เอวผิด (°)", "low", "%.1f"),
    ("shrugErrDeg", "ไหล่ยักผิด (°)", "low", "%.1f"),
    ("driftMedianS", "ช้ากว่าเพลง มัธยฐาน (วินาที)", "abs", "%.1f"),
    ("lengthRatio", "ความยาวท่า ÷ ความยาวเพลง", "one", "%.2f"),
    ("jerkRms", "ความกระตุก jerk RMS (°/s³)", "low", "%.0f"),
    ("peakDps", "ความเร็วสูงสุดของข้อ (°/s)", "info", "%.0f"),
    ("studioFlaggedS", "เวลาที่ใกล้ชนเกินระยะเผื่อ ตัวตรวจ Studio (วินาที)", "low", "%.1f"),
    ("collisionFramesApprox", "เฟรมใกล้ชน (ตัววัดประมาณ)", "low", "%d"),
    ("minGapMmApprox", "ระยะห่างน้อยสุด ประมาณ (mm)", "high", "%.1f"),
    ("limitFramesPct", "เวลาที่ข้อชนลิมิต (%)", "low", "%.1f"),
    ("computeS", "เวลาคำนวณ/เทรน (วินาที)", "low", "%.0f"),
]


def _value(c, key):
    s = c["score"]
    if key == "studioFlaggedS":
        return s.get("studio", {}).get("flaggedS")
    if key == "computeS":
        return s.get("computeS", s.get("trainS"))
    return s.get(key)


def _best(values, how):
    vals = [v for v in values if v is not None]
    if not vals or how == "info":
        return None
    if how == "low":
        return min(vals)
    if how == "high":
        return max(vals)
    if how == "abs":
        return min(vals, key=abs)
    return min(vals, key=lambda v: abs(v - 1))


class Report:
    def __init__(self, out, cfg, publish_to=None):
        """publish_to: a repo file that gets the tables only (no private data:
        angles, seconds and settings), so the numbers are kept in git too."""
        self.out, self.cfg, self.publish_to = Path(out), cfg, publish_to

    def cases(self):
        found = []
        for p in sorted(self.out.glob("*/*/summary.json")):
            s = json.loads(p.read_text(encoding="utf-8"))
            s["folder"] = p.parent
            t = p.parent / self.cfg["rl"]["id"] / "training.json"
            s["training"] = json.loads(t.read_text(encoding="utf-8")) if t.exists() else None
            found.append(s)
        return found

    def size_gb(self):
        return sum(f.stat().st_size for f in self.out.rglob("*") if f.is_file()) / 1e9

    def write(self):
        cases = self.cases()
        rel = lambda p: Path(p).relative_to(self.out).as_posix()
        md, body = [], []
        for case in cases:
            names = [c["id"] for c in case["contenders"]]
            head = f"{case['dance']} · {case['scenario']['label']} (เพลง {case['songS']:.0f} วินาที)"
            md += [f"## {head}", "", "| ตัววัด | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
            rows = []
            for key, label, how, fmt in METRICS:
                vals = [_value(c, key) for c in case["contenders"]]
                best = _best(vals, how)
                cells = []
                for v in vals:
                    text = "-" if v is None else fmt % v
                    cells.append(f"**{text}**" if v is not None and v == best else text)
                md.append(f"| {label} | " + " | ".join(cells) + " |")
                rows.append("<tr><th>%s</th>%s</tr>" % (html.escape(label), "".join(
                    "<td class=%s>%s</td>" % ("best" if c.startswith("**") else "", html.escape(c.strip("*"))) for c in cells)))
            md.append("")
            folder = case["folder"]
            vids = [("comparison.mp4", "วิดีโอเทียบ (ทุกแบบ หลายมุม + เพลง)"), ("rl_progress.mp4", "RL ทีละรอบการเทรน (ต่อกัน)")]
            links = "".join(f'<p><b>{t}</b><br><video controls preload="none" src="{rel(folder / v)}"></video></p>'
                            for v, t in vids if (folder / v).exists())
            tr = case["training"]
            rounds = ""
            if tr:
                rid = self.cfg["rl"]["id"]
                rounds = "<h4>RL ทีละรอบ · %s · รวม %.0f วินาที (%.1f นาที)</h4><table><tr><th>รอบ</th><th>เทรนรอบนี้ (วิ)</th><th>เทรนสะสม (วิ)</th><th>ผิดตามเวลาเพลง (°)</th><th>ผิดรูปท่า (°)</th><th>jerk</th><th>คลิป</th></tr>" % (
                    html.escape(str(tr.get("gpu"))), tr["totalTrainS"], tr["totalTrainS"] / 60)
                for r in tr["rounds"]:
                    clip = folder / rid / ("round_%02d" % r["round"]) / "clip.mp4"
                    rounds += "<tr><td>%d</td><td>%.0f</td><td>%.0f</td><td>%.1f</td><td>%.1f</td><td>%.0f</td><td>%s</td></tr>" % (
                        r["round"], r["trainS"], r["totalTrainS"], r.get("boneMusicDeg", float("nan")),
                        r.get("boneShapeDeg", float("nan")), r.get("jerkRms", float("nan")),
                        f'<a href="{rel(clip)}">ดู</a>' if clip.exists() else "-")
                rounds += "</table>"
            body.append("<section><h2>%s</h2><table><tr><th>ตัววัด</th>%s</tr>%s</table>%s%s</section>" % (
                html.escape(head), "".join("<th>%s</th>" % html.escape(c["label"]) for c in case["contenders"]),
                "".join(rows), links, rounds))
        size = self.size_gb()
        text = "# RL vs planner\n\n" + "\n".join(md)
        (self.out / "results.md").write_text(text, encoding="utf-8")
        if self.publish_to and cases:
            rec = cases[-1].get("record") or {}
            stamp = "\n".join(["", "## Run record", "",
                               f"- commit {rec.get('gitCommit')} (dirty: {rec.get('gitDirty')}), {rec.get('startedUtc')}",
                               f"- {rec.get('gpu')} · torch {rec.get('torch')} · CUDA {rec.get('cuda')} · {rec.get('os')}",
                               "- every run's full record: .local/rl_compare/experiments.jsonl on the PC", ""])
            Path(self.publish_to).parent.mkdir(parents=True, exist_ok=True)
            Path(self.publish_to).write_text(text + stamp, encoding="utf-8")
        (self.out / "results.json").write_text(json.dumps([{k: v for k, v in c.items() if k != "folder"} for c in cases],
                                                          indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        page = PAGE.replace("{{BODY}}", "\n".join(body) or "<p>ยังไม่มีผล</p>").replace(
            "{{SIZE}}", "%.2f GB (งบ %s GB)" % (size, self.cfg["video"]["budgetGB"]))
        (self.out / "index.html").write_text(page, encoding="utf-8")
        if size > self.cfg["video"]["budgetGB"]:
            print(f"WARNING: results take {size:.1f} GB, over the {self.cfg['video']['budgetGB']} GB budget", flush=True)


PAGE = """<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RL vs planner</title>
<style>
:root{--bg:#f6f4f0;--fg:#1d1b18;--dim:#6b655c;--line:#ddd6cc;--best:#d9f2dc}
@media (prefers-color-scheme:dark){:root{--bg:#171513;--fg:#eee9e2;--dim:#a39b90;--line:#3a352f;--best:#1f4a27}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 Tahoma,"Leelawadee UI",sans-serif;margin:0 auto;max-width:1200px;padding:16px}
table{border-collapse:collapse;width:100%;margin:8px 0 16px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
td.best{background:var(--best);font-weight:bold}video{width:100%;max-width:960px}section{margin-bottom:40px}
.note{color:var(--dim)}h2{margin-top:32px}
</style></head><body>
<h1>RL เทียบกับระบบท่าเต้นที่ใช้อยู่ (planner)</h1>
<p class="note">ทุกแบบใช้ท่าคนชุดเดียวกัน (cheer v2), ริก 10 ข้อของ Studio, servo model เดียวกัน และกติกาความเร็วเดียวกันในแต่ละสถานการณ์.
ช่องสีเขียว = ดีที่สุดในแถวนั้น. "ตามเวลาเพลงจริง" = เทียบท่าหุ่นกับท่าคนในวินาทีเดียวกันของเพลงต้นฉบับ;
"ไม่นับเวลา" = จับคู่เวลาให้ดีที่สุดก่อนแล้วค่อยวัดรูปท่า (แบบเดียวกับคะแนน 7.5° ของ Studio).
ใกล้ชนวัดด้วยตัวตรวจของ Studio เองบนการเคลื่อนที่จริงของ servo. ยังไม่ได้ทดสอบกับหุ่นจริง.</p>
<p class="note">พื้นที่ที่ใช้: {{SIZE}}</p>
{{BODY}}
</body></html>"""
