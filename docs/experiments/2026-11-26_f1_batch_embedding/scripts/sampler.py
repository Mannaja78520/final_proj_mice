import sys, time, json, subprocess, psutil
out, pid = sys.argv[1], int(sys.argv[2])
p = psutil.Process(pid); known = {}
def cpu_of():
    tot = 0.0; rss = 0.0
    for q in [p] + p.children(recursive=True):
        if q.pid not in known:
            known[q.pid] = q; q.cpu_percent(None); continue
        try:
            tot += known[q.pid].cpu_percent(None); rss += known[q.pid].memory_info().rss / 2**20
        except Exception: pass
    return tot, rss
cpu_of()
rows = []
end = time.time() + 3600
while time.time() < end:
    time.sleep(1.0)
    try:
        g = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,clocks.sm,power.draw", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip().split(",")
        cpu, rss = cpu_of()
        vm = psutil.virtual_memory()
        rows.append({"t": time.time(), "gpu": float(g[0]), "vram": float(g[1]), "clk": float(g[2]), "pw": float(g[3]), "srv_cpu": cpu, "srv_rss": rss, "ram_avail": vm.available / 2**20, "cpu_all": psutil.cpu_percent(None)})
        if len(rows) % 5 == 0: json.dump(rows, open(out, "w"))
    except Exception:
        pass
