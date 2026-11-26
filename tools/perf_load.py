"""Drive the Mice apps together and time each one: alone, then all at once.

Companion of perf_profile.py (which samples RAM/VRAM/CPU while this runs).
Workloads are data in config/perf_load.json: add one = add a row. Read-only
against the apps: face /api/look keeps nothing, voice /ask is a text question,
camera stream only reads bytes.

  python tools/perf_load.py --seconds 20 --out .local/perf/load.json
Prints per workload: calls, median ms, p95 ms, errors, for "alone" and "together".
"""
import argparse
import json
import statistics
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "config" / "perf_load.json"


def _token(cfg):
    login = ROOT / "main_python" / "faces_login.json"
    if not login.is_file():
        login = ROOT / "main_python" / "faces_login.default.json"
    creds = json.loads(login.read_text(encoding="utf-8")).get("reconize") or {}
    req = urllib.request.Request(cfg["face_api"] + "/api/auth/login", data=json.dumps(creds).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())["access_token"]


def w_face(cfg, ctx):
    img = Path(cfg["face_image"]).read_bytes()
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"a.jpg\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n").encode() + img + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(cfg["face_api"] + "/api/look", data=body, headers={
        "Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + ctx["token"]})
    urllib.request.urlopen(req, timeout=30).read()


def w_voice(cfg, ctx):
    q = ctx["questions"][ctx["i"] % len(ctx["questions"])]
    ctx["i"] += 1
    req = urllib.request.Request(cfg["voice"] + "/ask", data=json.dumps({"text": q}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()


def w_llm(cfg, ctx):
    body = {"model": cfg["llm_model"], "stream": False, "keep_alive": "1h",
            "messages": [{"role": "user", "content": "ตอบสั้นๆ: ตู้มหัสจรรย์คืออะไร"}],
            "options": {"num_predict": 40}}
    req = urllib.request.Request(cfg["llm"] + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=120).read()


def w_camera(cfg, ctx):
    """One frame time from the hub's shared MJPEG: read until a JPEG end marker."""
    if "cam" not in ctx:
        ctx["cam"] = urllib.request.urlopen(cfg["hub"] + "/api/dev/cam.stream?dev=" + urllib.parse.quote(cfg["camera_dev"]), timeout=20)
        ctx["buf"] = b""
    while b"\xff\xd9" not in ctx["buf"]:
        ctx["buf"] += ctx["cam"].read(4096)
    ctx["buf"] = ctx["buf"].split(b"\xff\xd9", 1)[1]


def w_stt(cfg, ctx):
    clips = ctx.setdefault("clips", sorted((ROOT / cfg["stt_clips"]).glob("*.wav"))[:6])
    clip = clips[ctx["i"] % len(clips)]
    ctx["i"] += 1
    req = urllib.request.Request(cfg["voice"] + "/transcribe?lang=th", data=clip.read_bytes(),
                                 headers={"Content-Type": "audio/wav"})
    urllib.request.urlopen(req, timeout=120).read()


def w_helper(cfg, ctx):
    """Background-class work: the helper translates a visitor's words to English
    (POST /translate with no target), which runs the local model under the
    scheduler's `helper` class - the kind of job a live question must overtake."""
    texts = cfg.get("helper_texts") or ["ตู้นี้ทำอะไรได้บ้าง ราคาเท่าไหร่"]
    ctx["j"] = ctx.get("j", 0) + 1
    req = urllib.request.Request(cfg["voice"] + "/translate", data=json.dumps(
        {"text": texts[ctx["j"] % len(texts)]}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=120).read()


WORK = {"stt": w_stt, "face": w_face, "voice": w_voice, "llm": w_llm, "camera": w_camera, "helper": w_helper}


def run(names, cfg, seconds, rates=None, helpers=0):
    """`helpers` extra threads of the background `helper` workload run beside `names`."""
    rates = rates or {}
    names = list(names) + (["helper"] if helpers else [])
    ctx_all = {"token": _token(cfg) if "face" in names else "", "questions": cfg["questions"], "i": 0}
    res = {n: {"ms": [], "err": 0} for n in names}
    end = time.time() + seconds

    def loop(n):
        ctx = dict(ctx_all)
        gap = 1.0 / rates[n] if rates.get(n) else 0.0   # 0 = as fast as it answers
        while time.time() < end:
            t = time.time()
            try:
                WORK[n](cfg, ctx)
                res[n]["ms"].append((time.time() - t) * 1000)
            except Exception:
                res[n]["err"] += 1
                time.sleep(0.5)
            time.sleep(max(0.0, gap - (time.time() - t)))
    ts = [threading.Thread(target=loop, args=(n,)) for n in names]
    ts += [threading.Thread(target=loop, args=("helper",)) for _ in range(max(0, helpers - 1))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return res


def summary(res):
    out = {}
    for n, r in res.items():
        v = sorted(r["ms"])
        out[n] = {"calls": len(v), "med_ms": round(statistics.median(v), 1) if v else None,
                  "p95_ms": round(v[int(len(v) * 0.95) - 1], 1) if len(v) > 1 else None,
                  "p99_ms": round(v[min(len(v) - 1, int(len(v) * 0.99))], 1) if len(v) > 1 else None, "err": r["err"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=20)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--helpers", type=int, default=0,
                    help="N threads of background helper translations beside the live workloads "
                         "(together phase only); reports their calls = background throughput")
    ap.add_argument("--together-only", action="store_true", help="skip the one-by-one phase")
    ap.add_argument("--real", action="store_true",
                    help="cap each workload at config ratesHz (a show day, not a stress test)")
    a = ap.parse_args()
    cfg = json.loads(CONF.read_text(encoding="utf-8"))
    names = [n for n in cfg["workloads"] if not a.only or n in a.only.split(",")]
    report = {}
    for n in ([] if a.together_only else names):
        report["alone_" + n] = summary(run([n], cfg, a.seconds, cfg.get("ratesHz") if a.real else None))
        print("alone", n, report["alone_" + n][n], flush=True)
    report["together"] = summary(run(names, cfg, a.seconds, cfg.get("ratesHz") if a.real else None, a.helpers))
    for n, s in report["together"].items():
        print("together", n, s, flush=True)
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
