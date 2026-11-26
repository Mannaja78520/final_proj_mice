import json, statistics as st, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Leelawadee UI", "Tahoma", "DejaVu Sans"]
OUT = sys.argv[1]
d = json.load(open("out/e2e_load.json")); res = json.load(open("out/res_p3.json"))
GREY, AMB, TEAL = "#8c8c8c", "#e69f00", "#2a9d8f"
modes = [("loop", "วนทีละหน้า (ปัจจุบัน)", GREY), ("hybrid", "hybrid (merge แล้ว)", AMB), ("bucketgraph", "bucket 1/2/4/8 + CUDA graph", TEAL)]
agg = {}
for sn, v in d.items():
    if sn == "_windows": continue
    load = sn.split(" | ")[1]
    for m, rs in v.items():
        for r in rs:
            agg.setdefault((load, m), []).append(r)
fig, axs = plt.subplots(1, 3, figsize=(14, 4.6))
for ax, (k, t) in zip(axs, [("p50", "median (p50)"), ("p95", "p95 (ค่ากลางของ 4 ช่อง)"), ("p99", "p99 (เฉลี่ย 4 ช่อง)")]):
    w = 0.25
    for j, (m, lab, c) in enumerate(modes):
        vals = []
        for load in ("real", "stress"):
            xs = [r[k] for r in agg[(load, m)]]
            vals.append(st.median(xs) if k == "p95" else st.mean(xs))
        bars = ax.bar([0 + (j - 1) * w, 1 + (j - 1) * w], vals, w, label=lab, color=c)
        for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["โหลดใช้งานจริง\n(STT 0.5/วิ + ถาม 0.5/วิ + กล้อง)", "โหลดสูงสุด\n(ยิงไม่พัก)"], fontsize=9)
    ax.set_title(f"/api/look {t}", fontsize=10); ax.set_ylabel("ms")
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, frameon=False)
fig.suptitle("ทุกแอปรันพร้อมกัน: voice STT + ถามตอบ + กล้อง hub + face (10 ครั้ง/วิ) RTX 5070 Ti", fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(f"{OUT}/2026-11-26_f1_round3_load_latency.png", dpi=130); plt.close(fig)
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8))
for ax, (k, t, u) in zip(axs, [("gpu", "GPU ใช้งานเฉลี่ย", "%"), ("srv_cpu", "CPU ของ face server", "% ของ 1 คอร์"), ("ram_avail", "RAM ว่างของเครื่อง", "MiB")]):
    ms = [m for m, _, _ in modes]
    bars = ax.bar(range(3), [res[m][k] for m in ms], color=[c for _, _, c in modes])
    for b, m in zip(bars, ms): ax.text(b.get_x() + b.get_width() / 2, res[m][k], f"{res[m][k]:.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(3)); ax.set_xticklabels(["วนทีละหน้า", "hybrid", "bucket+graph"], fontsize=9); ax.set_title(t, fontsize=10); ax.set_ylabel(u); ax.set_ylim(0, max(res[m][k] for m in ms) * 1.18)
fig.suptitle("ทรัพยากรขณะทุกแอปรันพร้อมกัน (เฉลี่ยทุกช่อง)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/2026-11-26_f1_round3_resources.png", dpi=130); plt.close(fig)
print("ok")
