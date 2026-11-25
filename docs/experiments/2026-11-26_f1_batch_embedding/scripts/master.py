import subprocess, os, sys, time, json, urllib.request
S = os.path.dirname(os.path.abspath(__file__)); os.chdir(S)
VPY = r"E:\final_proj\mice\Face_Regonize\backend\.venv\Scripts\python.exe"
def run(cmd, log, **kw):
    return subprocess.run(cmd, stdout=open(log, "w"), stderr=subprocess.STDOUT, **kw)
print("A: microbench", flush=True)
run([VPY, "-u", "bench_rec.py", "out/rec.json"], "out/rec.log")
print("A done", os.path.exists("out/rec.json"), flush=True)
env = dict(os.environ, DATABASE_URL=os.path.join(S, "f1", "database", "app.db"), STORAGE_PATH=os.path.join(S, "f1", "storage"),
           F1_MODE_FILE=os.path.join(S, "f1_mode.txt"), RECONIZE_INFERENCE_MODE="dual", PYTHONDONTWRITEBYTECODE="1")
open("f1_mode.txt", "w").write("loop")
srv = subprocess.Popen([VPY, "-m", "uvicorn", "app.main:app", "--port", "8011", "--host", "127.0.0.1"], cwd=os.path.join(S, "f1", "backend"),
                       env=env, stdout=open("out/server.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(120):
        time.sleep(2)
        try:
            h = json.loads(urllib.request.urlopen("http://127.0.0.1:8011/api/health", timeout=3).read())
            if h.get("model_ready"): break
        except Exception: pass
    print("server ready", h.get("inference_mode"), flush=True)
    smp = subprocess.Popen([VPY, "sampler.py", "out/samples.json", str(srv.pid)])
    time.sleep(3)
    print("B: e2e main(orig code) :8000 reference", flush=True)
    run([VPY, "-u", "e2e.py", "8000", "f1_mode_ref.txt", "out/e2e_main8000.json", "20", "1", "loop"], "out/e2e_main8000.log")
    print("C: e2e F1 copy", flush=True)
    run([VPY, "-u", "e2e.py", "8011", "f1_mode.txt", "out/e2e_copy.json", "20", "2", "loop,batch,pad4,pad8"], "out/e2e_copy.log")
    smp.terminate()
finally:
    srv.terminate()
    try: srv.wait(15)
    except Exception: srv.kill()
print("ALL DONE", flush=True)
