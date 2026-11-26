import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Leelawadee UI", "Tahoma", "DejaVu Sans"]
OUT = sys.argv[1]
r3 = json.load(open("out/rec3.json")); r4 = json.load(open("out/rec4.json"))
GREY, RED, AMB, GREEN, BLUE, TEAL = "#8c8c8c", "#c0504d", "#e69f00", "#9bbb59", "#4f81bd", "#2a9d8f"
pats = ["robot 1,1,1,2,1,1,1,3,1", "event crowd (Poisson mean 3, 1-8)", "uniform random 1-8", "fixed 6"]
plab = ["หุ่นยนต์\n(1,1,1,2,1,1,1,3,1)", "งานคนเยอะ\n(เฉลี่ย 3 หน้า)", "สุ่ม 1-8 หน้า", "6 หน้าคงที่"]
sets = [("loop (today)", r3, "วนทีละหน้า (ปัจจุบัน)", GREY), ("hybrid (merged)", r3, "hybrid (merge แล้ว, +0.3 GB)", AMB),
        ("graph buckets 1/2/8, max_workspace=0", r4, "bucket 1/2/8 + CUDA graph (+1.3 GB)", BLUE),
        ("graph buckets 1/2/4/8, max_workspace=0", r4, "bucket 1/2/4/8 + CUDA graph (+1.85 GB)", TEAL)]
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
for ax, k, t in zip(axs, ["mean", "p95"], ["เฉลี่ยต่อเฟรม", "p95 ต่อเฟรม"]):
    w = 0.2
    for j, (m, src, lab, c) in enumerate(sets):
        ax.bar([i + (j - 1.5) * w for i in range(len(pats))], [src[p][m][k] for p in pats], w, label=lab, color=c)
    ax.set_xticks(range(len(pats))); ax.set_xticklabels(plab, fontsize=9); ax.set_ylabel("ms (เฉพาะขั้น embedding)"); ax.set_title(t, fontsize=10)
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=4, fontsize=9, frameon=False)
fig.suptitle("รอบ 1-2: embedding ต่อเฟรม RTX 5070 Ti (ข้อมูลดิบ rec3.json / rec4.json)", fontsize=11)
fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(f"{OUT}/2026-11-26_f1_round2_embed.png", dpi=130); plt.close(fig)
# vram
names = ["hybrid\n(+1 session)", "bucket 1/8\n+graph", "bucket 1/2/8\n+graph", "bucket 1/4/8\n+graph", "bucket 1/2/4/8\n+graph"]
vals = [r4["vram_MiB"]["hybrid default workspace (+1 session)"], r4["vram_MiB"]["graph buckets 1/8, max_workspace=0 (2 sessions)"], r4["vram_MiB"]["graph buckets 1/2/8, max_workspace=0 (3 sessions)"],
        r4["vram_MiB"]["graph buckets 1/4/8, max_workspace=0 (3 sessions)"], r4["vram_MiB"]["graph buckets 1/2/4/8, max_workspace=0 (4 sessions)"]]
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(names, vals, color=[AMB, BLUE, BLUE, BLUE, TEAL])
for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v + 20, f"{v}", ha="center")
ax.set_ylabel("VRAM ที่เพิ่ม (MiB) นอกเหนือจาก session ปัจจุบัน"); ax.set_title("ราคาของแต่ละทางเลือกเป็น VRAM (ว่างรวมเหลือ ~3 GB ตอนรันทุกแอป)", fontsize=10)
ax.axhline(3000, color=RED, ls="--", lw=1); ax.text(0.02, 3030, "VRAM ว่างทั้งเครื่อง ~3 GB", color=RED, fontsize=8)
ax.set_ylim(0, 3300); fig.tight_layout(); fig.savefig(f"{OUT}/2026-11-26_f1_round2_vram.png", dpi=130); plt.close(fig)
print("ok")
