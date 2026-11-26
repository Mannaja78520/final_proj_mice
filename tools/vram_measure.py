"""Measure the GPU-memory planner on the real PC: calibrate, card sizes, spill / swap / hybrid.

    python tools/vram_measure.py calibrate      service times alone on GPU and CPU, swap cost, VRAM per model, Spark speech
    python tools/vram_measure.py caps           card sizes 2, 4, 6, 8, 10, 12 GB and the whole card, 2 runs each
    python tools/vram_measure.py strategies     swap and hybrid at 2, 4, 6 GB (spill = the `caps` runs)
    python tools/vram_measure.py all            all of the above        (smoke = a 10-minute dry run)
    python tools/vram_measure.py reduced        NO stop of the real Voice: the side Voice gets a 2.0 and 2.5 GB budget
                                                (MICE_VRAM_VOICE_BUDGET_MIB) while the real Voice holds the card;
                                                calibration at those sizes, spill / swap / hybrid, 2 runs each

What it does, and what it touches:
  * Holds the PC-wide QC lock (qc/lib/runlock.py) for the whole session, so no QC runs under the numbers.
  * Stops the REAL Voice (the process listening on 8767) so its models do not count as "other programs"
    on the simulated card, and ALWAYS starts it again with the same command at the end (finally).
    The hub, the face app and the camera stay up and are loaded by the runs, as at the booth.
  * Runs a side hub (8650, nothing reaches real boards, names or peers) and a side Voice (8768) from THIS tree.
    `MICE_VRAM_CAP_MIB` pretends the smaller card: every program's real use counts as used, so the
    room the Voice has is cap minus what the others hold (printed per run).
  * Results: .local/perf/vram_<date>/ (calibration.json, one folder per setting with perf*.json and info.json).
Windows only (it makes its speech clips with System.Speech and uses nvidia-smi).
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qc" / "lib"))
VOICE = "http://127.0.0.1:8768"
NOWIN = 0x08000000
DETACHED = 0x00000008
OUT = ROOT / ".local" / "perf" / ("vram_" + time.strftime("%Y-%m-%d"))
CLIP_DIR = ROOT / ".local" / "perf" / "clips"
SPARK_ROOTS = []                                  # more places to look for .local/tts_spark (set from the real Voice's tree)


def say(*a):
    msg = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(msg, flush=True)
    with open(OUT / "session.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def used_mib():
    out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], text=True)
    u, t = [int(x) for x in out.strip().split(",")]
    return u, t


def procs(match, avoid=()):
    import psutil
    for p in psutil.process_iter(["pid", "cmdline"]):
        c = " ".join(p.info["cmdline"] or [])
        if match in c and not any(a in c for a in avoid):
            yield p


def kill(match, avoid=()):
    import psutil
    for p in list(procs(match, avoid)):
        try:
            for ch in p.children(recursive=True):
                ch.kill()
            p.kill()
        except psutil.Error:
            pass
    time.sleep(2)


def listener(port):
    """The process listening on a local port, or None."""
    import psutil
    for c in psutil.net_connections(kind="tcp"):
        if c.status == "LISTEN" and c.laddr.port == port and c.pid:
            return psutil.Process(c.pid)
    return None


def http(path, body=None, ctype="application/json", timeout=240, base=VOICE):
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": ctype} if body is not None else {})
    t = time.time()
    d = urllib.request.urlopen(req, timeout=timeout).read()
    return (time.time() - t) * 1000, d


def health(base=VOICE):
    return json.loads(http("/health", timeout=20, base=base)[1])


def make_clips():
    """Three short sentences spoken by Windows, 16 kHz mono: the hearing workload."""
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    if len(list(CLIP_DIR.glob("*.wav"))) >= 3:
        return
    ps = ("Add-Type -AssemblyName System.Speech; $sp=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,"
          "[System.Speech.AudioFormat.AudioChannel]::Mono); $i=0; "
          "foreach($t in 'Hello, what can this machine do for me today','How much does it cost to play one round','Please tell me where the nearest toilet is')"
          "{$i++; $sp.SetOutputToWaveFile('%s\\c'+$i+'.wav',$f); $sp.Speak($t); $sp.SetOutputToNull()}" % str(CLIP_DIR).replace("/", "\\"))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def side_hub_main(port):
    """The branch hub on a side port with everything that could reach the rest of the PC turned off."""
    import webbrowser
    sys.path.insert(0, str(ROOT / "main_python"))
    sys.argv = [sys.argv[0]]
    webbrowser.open = lambda *a, **k: False
    import main

    class NoName:
        def __init__(self, *a, **k):
            self.name, self.error = "side-hub.local", "side hub: no name"

        def taken(self):
            return None

        def start(self):
            return False

        def stop(self):
            pass

    main.mdns.Responder = NoName
    main.start_short_name = lambda: False
    for fn in ("announce", "withdraw", "release_all"):
        setattr(main.peers, fn, lambda *a, **k: None)
    main.scan_modules = lambda *a, **k: None          # would open the real boards' serial ports
    main.route_probe_loop = lambda *a, **k: None
    main.PORT = port
    main.main()


def start_hub():
    if list(procs("vram_measure.py side-hub")):
        return
    lg = open(OUT / "side_hub.log", "ab")
    subprocess.Popen([sys.executable, "-u", str(ROOT / "tools" / "vram_measure.py"), "side-hub", "8650"], cwd=str(ROOT),
                     stdout=lg, stderr=lg, creationflags=NOWIN)
    time.sleep(6)


def start_voice(env=None, tag="voice"):
    kill("service.py --port 8768")
    e = dict(os.environ)
    for k in ("MICE_VRAM_CAP_MIB", "MICE_VRAM_STRATEGY", "MICE_LEARNED_VRAM"):
        e.pop(k, None)
    e.update({k: str(v) for k, v in (env or {}).items() if v is not None})
    lg = open(OUT / ("%s.log" % tag), "ab")
    subprocess.Popen([sys.executable, "-u", str(ROOT / "apps/voice/service.py"), "--port", "8768"], cwd=str(ROOT), env=e,
                     stdout=lg, stderr=lg, creationflags=NOWIN)
    t0, last, same = time.time(), None, 0
    while time.time() - t0 < 300:
        try:
            h = health()
            parts = h["parts"]
            sig = (parts["llm"], parts["stt"], json.dumps({k: v["device"] for k, v in ((h.get("vram") or {}).get("models") or {}).items()}, sort_keys=True))
            sig = sig + (round(used_mib()[0] / 50),)           # a model that is loading moves the card's memory
            if time.time() - t0 > 40:
                same = same + 1 if sig == last else 0
                if same >= 4:                               # nothing changed for about 12 s: the preload is over
                    return h
            last = sig
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("the side Voice was not ready in 300 s")


def clips():
    return sorted(CLIP_DIR.glob("*.wav"))


def warm():
    for _ in range(2):
        http("/translate", json.dumps({"text": "สวัสดีครับ วันนี้มีกิจกรรมอะไรบ้าง"}).encode())
        http("/transcribe?lang=th", clips()[0].read_bytes(), "audio/wav")


def med(xs):
    xs = [x for x in xs if x == x]
    return round(statistics.median(xs), 1) if xs else None


def times(fn, n):
    out = []
    for _ in range(n):
        try:
            out.append(fn())
        except Exception as e:                        # noqa: BLE001
            out.append(float("nan"))
            say("  call error:", e)
    return out


def devices(h):
    loaded = (h.get("resources") or {}).get("loaded") or {}
    return {k: v.get("actualDevice") or v.get("device") for k, v in loaded.items()}


def service_times(label, n=6):
    r = {"stt_ms": times(lambda: http("/transcribe?lang=th", clips()[0].read_bytes(), "audio/wav")[0], n),
         "helper_ms": times(lambda: http("/translate", json.dumps({"text": "ตู้นี้ทำอะไรได้บ้าง ราคาเท่าไหร่ ห้องน้ำอยู่ไหน"}).encode())[0], n),
         "ask_faq_ms": times(lambda: http("/ask", json.dumps({"text": "สวัสดี"}).encode())[0], n),
         "ask_free_ms": times(lambda: http("/ask", json.dumps({"text": "ช่วยแต่งกลอนสั้นๆ เกี่ยวกับหุ่นยนต์ให้หน่อย"}).encode(), timeout=120)[0], 3)}
    for k in list(r):
        r[k + "_median"] = med(r[k])
    say(label, {k: v for k, v in r.items() if k.endswith("_median")})
    return r


def spark_times(device, n=3):
    """Spark Thai speech with feeling, alone, on `device`: start the server, time the line, read its VRAM."""
    rt = next((r for r in (ROOT / ".local" / "tts_spark", *SPARK_ROOTS) if (r / "venv" / "Scripts" / "python.exe").exists()), ROOT / ".local" / "tts_spark")
    py = rt / "venv" / "Scripts" / "python.exe"
    if not py.exists():
        say("Spark speech is not installed here: not measured")
        return None
    kill("tts_spark/server.py --port 8780")
    before = used_mib()[0]
    env = dict(os.environ, HF_HOME=str(rt / "hf"))
    lg = open(OUT / ("spark_%s.log" % device), "ab")
    t0 = time.time()
    subprocess.Popen([str(py), "-u", str(ROOT / "apps/voice/tts_spark/server.py"), "--port", "8780", "--checkpoint", "raw", "--device", device, "--runtime", str(rt)],
                     cwd=str(ROOT), env=env, stdout=lg, stderr=lg, creationflags=NOWIN)
    ready = None
    while time.time() - t0 < 240:
        try:
            if json.loads(http("/health", base="http://127.0.0.1:8780", timeout=3)[1]).get("ok"):
                ready = time.time() - t0
                break
        except Exception:
            time.sleep(3)
    if ready is None:
        say("Spark server on", device, "did not come up in 240 s")
        kill("tts_spark/server.py --port 8780")
        return {"device": device, "error": "not ready in 240 s"}
    after = used_mib()[0]
    body = json.dumps({"text": "สวัสดีครับ ยินดีต้อนรับสู่ตู้มหัสจรรย์ วันนี้มีอะไรให้ช่วยไหมครับ", "emotion": "neutral"}).encode()
    ms = times(lambda: http("/speak", body, base="http://127.0.0.1:8780", timeout=180)[0], n + 1)
    res = {"device": device, "loadSeconds": round(ready, 1), "vramDeltaMiB": after - before, "line_ms": ms, "line_ms_median_warm": med(ms[1:])}
    say("Spark on", device, res)
    kill("tts_spark/server.py --port 8780")
    return res


def calibrate(quick=False):
    n = 3 if quick else 6
    res = {"date": time.strftime("%Y-%m-%d %H:%M")}
    learned = OUT / "learned_calib.json"
    if learned.exists():
        learned.unlink()
    res["usedBeforeVoiceMiB"], res["totalMiB"] = used_mib()
    say("the others hold", res["usedBeforeVoiceMiB"], "MiB of", res["totalMiB"], "(no Voice running)")
    h = start_voice({"MICE_LEARNED_VRAM": learned}, "calib_gpu")
    res["usedAfterPreloadMiB"] = used_mib()[0]
    res["gpuDevices"], res["llmDevice"], res["vram"] = devices(h), h.get("llmDevice"), h.get("vram")
    say("GPU run: devices", res["gpuDevices"], "| used", res["usedAfterPreloadMiB"])
    warm()
    res["gpu"] = service_times("GPU alone", n)
    http("/unload", b"{}")                            # the swap: everything out, the first call loads its model again
    time.sleep(2)
    res["usedAfterUnloadMiB"] = used_mib()[0]
    res["swap_stt_cold_ms"] = http("/transcribe?lang=th", clips()[0].read_bytes(), "audio/wav")[0]
    res["usedAfterSttReloadMiB"] = used_mib()[0]
    res["swap_helper_cold_ms"] = http("/translate", json.dumps({"text": "สวัสดีครับ"}).encode())[0]
    res["usedAfterLlmReloadMiB"] = used_mib()[0]
    res["learnedMiB"] = json.loads(learned.read_text(encoding="utf-8")) if learned.exists() else {}
    say("swap: stt cold", round(res["swap_stt_cold_ms"]), "ms, helper cold", round(res["swap_helper_cold_ms"]), "ms; learned sizes", res["learnedMiB"])
    h = start_voice({"MICE_VRAM_CAP_MIB": 1, "MICE_LEARNED_VRAM": learned}, "calib_cpu")
    res["cpuDevices"] = devices(h)
    say("CPU run: devices", res["cpuDevices"])
    warm()
    res["cpu"] = service_times("CPU alone", n)
    kill("service.py --port 8768")
    if not quick:
        res["spark"] = [spark_times("cuda"), spark_times("cpu")]
    (OUT / "calibration.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def reduced_calibrate(budgets):
    """Service times and swap cost, from two short side-Voice runs that fit in the room the real Voice leaves.
    Swap mode is used on purpose for the GPU run: the model that is asked for takes the card alone, so each
    model is timed alone on the GPU and its real VRAM is the nvidia-smi step when it loads."""
    res = {"date": time.strftime("%Y-%m-%d %H:%M"),
           "note": "REDUCED: the real Voice kept running; GPU times from the side Voice in swap mode with a %d MiB budget" % max(budgets)}
    res["usedBeforeMiB"], res["totalMiB"] = used_mib()
    stt_body, ask_free = clips()[0].read_bytes(), json.dumps({"text": "ช่วยแต่งกลอนสั้นๆ เกี่ยวกับหุ่นยนต์ให้หน่อย"}).encode()
    helper_body = json.dumps({"text": "ตู้นี้ทำอะไรได้บ้าง ราคาเท่าไหร่ ห้องน้ำอยู่ไหน"}).encode()
    # GPU: everything out, then one model at a time asked for -> it gets the card
    h = start_voice({"MICE_VRAM_VOICE_BUDGET_MIB": max(budgets), "MICE_VRAM_STRATEGY": "swap"}, "calib_gpu")
    gpu = {"budgetMiB": max(budgets), "strategy": "swap"}
    http("/unload", b"{}")
    time.sleep(3)
    u0 = used_mib()[0]
    gpu["swap_stt_cold_ms"] = http("/transcribe?lang=th", stt_body, "audio/wav")[0]
    u1 = used_mib()[0]
    gpu["devices_after_stt"] = devices(health())
    gpu["stt_ms"] = times(lambda: http("/transcribe?lang=th", stt_body, "audio/wav")[0], 6)
    gpu["hearing_vram_MiB"] = u1 - u0
    http("/unload", b"{}")
    time.sleep(3)
    u2 = used_mib()[0]
    gpu["swap_helper_cold_ms"] = http("/translate", helper_body)[0]
    u3 = used_mib()[0]
    gpu["devices_after_helper"] = devices(health())
    gpu["llmDevice"] = health().get("llmDevice")
    gpu["helper_ms"] = times(lambda: http("/translate", helper_body)[0], 6)
    gpu["ask_free_ms"] = times(lambda: http("/ask", ask_free, timeout=120)[0], 3)
    gpu["llm_vram_MiB"] = u3 - u2
    for k in ("stt_ms", "helper_ms", "ask_free_ms"):
        gpu[k + "_median"] = med(gpu[k])
    say("GPU alone:", {k: v for k, v in gpu.items() if k.endswith("_median") or "cold" in k or "vram" in k}, gpu["devices_after_stt"], gpu["devices_after_helper"])
    res["gpu"] = gpu
    kill("service.py --port 8768")
    # CPU: a budget of nothing
    h = start_voice({"MICE_VRAM_VOICE_BUDGET_MIB": 300}, "calib_cpu")
    warm()
    cpu = service_times("CPU alone", 6)
    cpu["devices"] = devices(health())
    res["cpu"] = cpu
    kill("service.py --port 8768")
    res["spark"] = [spark_times("cpu")]
    (OUT / "calibration_reduced.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def perf(tag, seconds, runs, helpers=4):
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    for i in range(1, runs + 1):
        cmd = [sys.executable, "tools/perf_load.py", "--seconds", str(seconds), "--real", "--together-only", "--only", "face,voice,stt,camera",
               "--helpers", str(helpers), "--out", str(d / ("perf%d.json" % i))]
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        say("  run", i, [l for l in r.stdout.splitlines() if "together" in l and ("voice" in l or "stt" in l or "helper" in l)])


def one_setting(tag, env, seconds, runs):
    learned, work = OUT / "learned_calib.json", OUT / ("learned_%s.json" % tag)
    if learned.exists():
        shutil.copy(learned, work)
    h = start_voice(dict(env or {}, MICE_LEARNED_VRAM=work), tag)
    warm()
    h = health()
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=True)
    info = {"env": {k: str(v) for k, v in (env or {}).items()}, "devices": devices(h), "llmDevice": h.get("llmDevice"),
            "vram": h.get("vram"), "usedMiB": used_mib()[0]}
    say(tag, "devices", info["devices"], "| used", info["usedMiB"], "| lastDecision", (info["vram"] or {}).get("lastDecision"))
    perf(tag, seconds, runs)
    h2 = health()
    info["devicesAfter"], info["vramAfter"] = devices(h2), h2.get("vram")
    info["scheduler"] = (h2.get("scheduler") or {}).get("classes")
    (d / "info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    kill("service.py --port 8768")


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if phase == "side-hub":
        return side_hub_main(int(sys.argv[2]))
    OUT.mkdir(parents=True, exist_ok=True)
    make_clips()
    quick = phase == "smoke"
    seconds, runs = (15, 1) if quick else (60, 2)
    from runlock import RunLock
    lock = RunLock(say=lambda m: print(m, flush=True))
    lock.acquire()
    reduced = phase == "reduced"                         # the real Voice stays up: nothing of it is stopped or restarted
    real = None if reduced else listener(8767)
    real_cmd, real_cwd = (real.cmdline(), real.cwd()) if real else (None, None)
    real_root = Path(real_cmd[-1]).parents[2] if real_cmd and real_cmd[-1].endswith("service.py") else None
    if real_root:
        SPARK_ROOTS.append(real_root / ".local" / "tts_spark")
    if reduced and listener(8767):
        SPARK_ROOTS.append(Path(listener(8767).cmdline()[-1]).parents[2] / ".local" / "tts_spark")
    cfg_sched, cfg_perf = ROOT / "config/scheduler.json", ROOT / "config/perf_load.json"
    profiles = ROOT / "config" / "voice_profiles"
    if reduced and not profiles.exists() and listener(8767):
        real_root = Path(listener(8767).cmdline()[-1]).parents[2]
    if real_root and not profiles.exists() and (real_root / "config" / "voice_profiles").exists():
        shutil.copytree(real_root / "config" / "voice_profiles", profiles)
    cfg_sched.write_text(cfg_sched.read_text(encoding="utf-8").replace("http://127.0.0.1:8642", "http://127.0.0.1:8650"), encoding="utf-8")
    pl = cfg_perf.read_text(encoding="utf-8").replace('"http://127.0.0.1:8767"', '"http://127.0.0.1:8768"')
    cfg_perf.write_text(pl.replace('"apps/voice/tts_cache"', json.dumps(str(CLIP_DIR).replace("\\", "/"))), encoding="utf-8")
    try:
        say("== phase", phase, "| real Voice:", real_cmd)
        if real:
            say("stopping the real Voice", real.pid)
            real.kill()
            time.sleep(4)
        start_hub()
        if reduced:
            used, total = used_mib()
            budgets = [b for b in (2048, 2560) if b + 700 <= total - used]      # CUDA context needs about 0.4 GB on top
            say("free on the real card:", total - used, "MiB; budgets that fit:", budgets)
            reduced_calibrate(budgets)
            for b in budgets:
                for strat in ("spill", "swap", "hybrid"):
                    one_setting("%s_budget%d" % (strat, b), {"MICE_VRAM_VOICE_BUDGET_MIB": b, "MICE_VRAM_STRATEGY": strat}, seconds, runs)
        if phase in ("smoke", "calibrate", "all"):
            calibrate(quick)
        if phase == "smoke":
            one_setting("smoke_cap4096", {"MICE_VRAM_CAP_MIB": 4096}, seconds, runs)
            one_setting("smoke_swap4096", {"MICE_VRAM_CAP_MIB": 4096, "MICE_VRAM_STRATEGY": "swap"}, seconds, runs)
            one_setting("smoke_hybrid4096", {"MICE_VRAM_CAP_MIB": 4096, "MICE_VRAM_STRATEGY": "hybrid"}, seconds, runs)
        if phase in ("caps", "all"):
            for cap in (2048, 4096, 6144, 8192, 10240, 12288, None):
                one_setting("cap_%s" % (cap or "uncapped"), {"MICE_VRAM_CAP_MIB": cap}, seconds, runs)
        if phase in ("strategies", "all"):
            for cap in (2048, 4096, 6144):
                for strat in ("swap", "hybrid"):
                    one_setting("%s_%s" % (strat, cap), {"MICE_VRAM_CAP_MIB": cap, "MICE_VRAM_STRATEGY": strat}, seconds, runs)
    finally:
        kill("service.py --port 8768")
        kill("vram_measure.py side-hub")
        subprocess.run(["git", "checkout", "--", "config/scheduler.json", "config/perf_load.json"], cwd=str(ROOT))
        shutil.rmtree(profiles, ignore_errors=True)
        if real_cmd:
            lg = open(OUT / "real_voice.log", "ab")
            subprocess.Popen(real_cmd, cwd=real_cwd, stdout=lg, stderr=lg, creationflags=NOWIN | DETACHED)
            say("real Voice started again:", real_cmd)
            t0 = time.time()
            while time.time() - t0 < 240:
                try:
                    h = health("http://127.0.0.1:8767")
                    if "loaded" in h["parts"]["stt"]:
                        say("the real Voice is back; devices", devices(h))
                        break
                except Exception:
                    pass
                time.sleep(4)
        lock.release()


if __name__ == "__main__":
    main()
