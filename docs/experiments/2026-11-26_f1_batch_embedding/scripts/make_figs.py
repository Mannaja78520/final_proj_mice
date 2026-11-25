import json, statistics, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Leelawadee UI", "Tahoma", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
OUT = sys.argv[1]
BLUE, GREEN, RED, GREY, AMB = "#4f81bd", "#9bbb59", "#c0504d", "#8c8c8c", "#e69f00"
r1 = json.load(open("out/rec.json")); r2 = json.load(open("out/rec2.json"))
e1 = json.load(open("out/e2e_copy.json")); e2 = json.load(open("out/e2e_copy2.json"))
# ---- fig 1: shape switch cost
d = r1["ORT default (EXHAUSTIVE)"]
labels = ["ทุกเฟรม 1 หน้า", "ทุกเฟรม 6 หน้า", "สลับ 1↔2 หน้า", "สลับ 1↔6 หน้า"]
keys = ["always 1", "always 6", "alt 1/2", "alt 1/6"]
vals = [d[k]["median"] for k in keys]
fig, ax = plt.subplots(figsize=(8, 4.3))
bars = ax.bar(labels, vals, color=[GREEN, GREEN, RED, RED])
for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center")
ax.set_ylabel("ms ต่อการเรียกโมเดลจำหน้า 1 ครั้ง")
ax.set_title("RTX 5070 Ti: ขนาด batch เปลี่ยนทีไร โมเดลช้าลง ~27 ms ทุกครั้ง", fontsize=11)
ax.set_ylim(0, max(vals) * 1.15)
fig.tight_layout(); fig.savefig(f"{OUT}/2026-11-26_f1_shape_switch.png", dpi=130); plt.close(fig)
# ---- fig 2: per-frame embedding cost
pats = ["robot 1,1,1,2,1,1,1,3,1", "event crowd (Poisson mean 3, 1-8)", "uniform random 1-8", "fixed 6", "fixed 1"]
plab = ["หุ่นยนต์\n(1,1,1,2,1,1,1,3,1)", "งานคนเยอะ\n(เฉลี่ย 3 หน้า)", "สุ่ม 1-8 หน้า", "6 หน้าคงที่", "1 หน้าคงที่"]
ms = list(r2["robot 1,1,1,2,1,1,1,3,1"].keys())
mlab = {"loop (today)": "วนทีละหน้า (โค้ดปัจจุบัน)", "F1 batch of n": "F1 batch n หน้า", "pad to 8": "batch คงที่ 8 (เติมให้ครบ)",
        "pad to 4/8": "batch คงที่ 4/8", ms[-1]: "hybrid: ≤2 หน้าวน, ≥3 ใช้ batch 8 อีก session"}
cols = [GREY, RED, AMB, "#f2c85b", GREEN]
fig, ax = plt.subplots(figsize=(10, 4.8))
w = 0.16
for j, m in enumerate(ms):
    ax.bar([i + (j - 2) * w for i in range(len(pats))], [r2[p][m]["mean"] for p in pats], w, label=mlab.get(m, m), color=cols[j])
ax.set_xticks(range(len(pats))); ax.set_xticklabels(plab)
ax.set_ylabel("ms ต่อเฟรม (เฉลี่ย, เฉพาะขั้น embedding)")
ax.set_title("เวลา embedding ต่อเฟรม ตามรูปแบบจำนวนหน้า (RTX 5070 Ti)", fontsize=11)
ax.legend(fontsize=8, loc="upper left"); fig.tight_layout(); fig.savefig(f"{OUT}/2026-11-26_f1_per_frame_embed.png", dpi=130); plt.close(fig)
# ---- fig 3: e2e /api/look latency
def agg(e, sn, m, k): 
    rs = e.get(sn, {}).get(m)
    return statistics.mean(r[k] for r in rs) if rs else None
scen = [("fixed 6 faces", "6 หน้าคงที่"), ("robot stream 1,1,1,2,1,0,1,1,3,1", "หุ่นยนต์\n(0-3 หน้า)"), ("mix 0/1/6", "สลับ 0/1/6"), ("crowd random 1-6", "งานคนเยอะ\n(สุ่ม 1-6)")]
modes = [("loop", "วนทีละหน้า (ปัจจุบัน)", GREY), ("batch", "F1 batch n หน้า", RED), ("pad8", "batch คงที่ 8", AMB), ("pad4", "batch คงที่ 4/8", "#f2c85b"), ("hybrid", "hybrid (2 session)", GREEN)]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), sharey=False)
for ax, k, t in zip(axs, ["p50", "p95"], ["median (p50)", "p95"]):
    w = 0.16
    for j, (m, ml, c) in enumerate(modes):
        xs, ys = [], []
        for i, (sn, sl) in enumerate(scen):
            v = agg(e2, sn, m, k) if sn in e2 and m in e2.get(sn, {}) else agg(e1, sn, m, k)
            if v is not None: xs.append(i + (j - 2) * w); ys.append(v)
        ax.bar(xs, ys, w, label=ml, color=c)
    ax.set_xticks(range(len(scen))); ax.set_xticklabels([s[1] for s in scen], fontsize=9)
    ax.set_title(f"/api/look ตั้งแต่ส่งจนได้คำตอบ: {t}", fontsize=10); ax.set_ylabel("ms")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=5, fontsize=9, frameon=False)
fig.suptitle("วัดจริงทั้งระบบ (hub + voice ทำงานอยู่, 10 ครั้ง/วินาที, RTX 5070 Ti)", fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(f"{OUT}/2026-11-26_f1_e2e_latency.png", dpi=130); plt.close(fig)
# ---- fig 4: resources
res = json.load(open("out/res_p2.json"))
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8))
for ax, (k, t, u) in zip(axs, [("gpu", "GPU ใช้งานเฉลี่ย", "%"), ("srv_cpu", "CPU ของ face server", "% ของ 1 คอร์"), ("srv_rss", "RAM ของ face server", "MiB")]):
    ms_ = [m for m, _, _ in modes if m in res]
    bars = ax.bar(range(len(ms_)), [res[m][k] for m in ms_], color=[c for m, _, c in modes if m in res])
    for b, m in zip(bars, ms_): ax.text(b.get_x() + b.get_width() / 2, res[m][k], f"{res[m][k]:.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(ms_))); ax.set_xticklabels([{"loop": "วนทีละหน้า", "batch": "F1", "pad4": "คงที่ 4/8", "pad8": "คงที่ 8", "hybrid": "hybrid"}[m] for m in ms_], fontsize=9)
    ax.set_title(t, fontsize=10); ax.set_ylabel(u); ax.set_ylim(0, max(res[m][k] for m in ms_) * 1.18)
fig.suptitle("ทรัพยากรขณะวัด 4 สถานการณ์ x 2 รอบ (10 ครั้ง/วินาที)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/2026-11-26_f1_resources.png", dpi=130); plt.close(fig)
print("figs ok")
