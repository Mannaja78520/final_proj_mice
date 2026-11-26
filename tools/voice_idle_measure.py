"""Measure what the Voice helper's idle unload frees and what waking it costs.

Run on the PC with the real Voice helper up (default http://127.0.0.1:8767). It is NOT run by QC.
  python tools/voice_idle_measure.py [--helper URL] [--question "สวัสดี"]
Steps: GPU memory used now (nvidia-smi) -> POST /ask (first answer, models warm) time -> POST /unload
-> GPU memory used -> POST /ask again (the wake-up cost) -> GPU memory used. Prints the numbers; nothing
is changed that the next question would not reload by itself. The user must be fine with one slow answer.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, __import__("os").path.dirname(__file__))


def vram_mib():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20).stdout.split()
        return int(float(out[0]))
    except (OSError, ValueError, IndexError):
        return None


def post(url, obj, timeout=300):
    req = urllib.request.Request(url, json.dumps(obj).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    return time.time() - t0, body[:120]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--helper", default="http://127.0.0.1:8767")
    ap.add_argument("--question", default="สวัสดี")
    a = ap.parse_args()
    try:
        import polite
        polite.apply("voice_idle_measure")
    except ImportError:
        pass
    q = {"question": a.question}
    print("GPU memory used now: %s MiB" % vram_mib())
    s1, b1 = post(a.helper + "/ask", q)
    print("first answer with the models warm: %.1f s" % s1)
    post(a.helper + "/unload", {})
    time.sleep(3)
    freed = vram_mib()
    print("after /unload: %s MiB used" % freed)
    s2, b2 = post(a.helper + "/ask", q)
    print("answer after the models were unloaded (wake-up included): %.1f s (+%.1f s)" % (s2, s2 - s1))
    print("after waking: %s MiB used" % vram_mib())


if __name__ == "__main__":
    main()
