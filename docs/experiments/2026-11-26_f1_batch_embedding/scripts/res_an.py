import json, sys, statistics
tag = sys.argv[1]; sf = sys.argv[2]; ef = sys.argv[3]
S = json.load(open(sf)); E = json.load(open(ef))
agg = {}
for sn, m, rd, a, b in E["_windows"]:
    rows = [r for r in S if a + 2 <= r["t"] <= b]
    if not rows: continue
    agg.setdefault(m, []).append({k: statistics.mean(r[k] for r in rows) for k in ("gpu", "vram", "clk", "pw", "srv_cpu", "srv_rss", "ram_avail", "cpu_all")})
out = {m: {k: round(statistics.mean(x[k] for x in v), 1) for k in v[0]} for m, v in agg.items()}
json.dump(out, open(f"out/res_{tag}.json", "w"), indent=1)
for m, v in out.items(): print(m, v)
