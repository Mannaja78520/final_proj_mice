"""End-to-end /api/look on the F1 copy server, interleaved modes. Needs: server on PORT, mode file."""
import sys, json, time, statistics, urllib.request, uuid, threading
import numpy as np, cv2
PORT = int(sys.argv[1]); MODEFILE = sys.argv[2]; OUT = sys.argv[3]
SECS = float(sys.argv[4]) if len(sys.argv) > 4 else 25
ROUNDS = int(sys.argv[5]) if len(sys.argv) > 5 else 2
MODES = sys.argv[6].split(",") if len(sys.argv) > 6 else ["loop", "batch", "pad4", "pad8"]
BASE = f"http://127.0.0.1:{PORT}"
sys.path.insert(0, r"E:\final_proj\mice\Face_Regonize\backend")
img = cv2.imread(r"E:\final_proj\mice\Face_Regonize\backend\.venv\Lib\site-packages\insightface\data\images\t1.jpg")
creds = json.load(open(r"E:\final_proj\mice\mice_system\main_python\faces_login.default.json"))["reconize"]
tok = json.loads(urllib.request.urlopen(urllib.request.Request(BASE + "/api/auth/login", data=json.dumps(creds).encode(), headers={"Content-Type": "application/json"}), timeout=15).read())["access_token"]

def post(data):
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="a.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + data + f"\r\n--{b}--\r\n".encode()
    r = urllib.request.Request(BASE + "/api/look", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + tok})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())

# build frames with k visible faces by greying the others (using the server to find boxes)
full = cv2.imencode(".jpg", img)[1].tobytes()
r = post(full); H, W = r["image"]["h"], r["image"]["w"]
boxes = sorted([f["box"] for f in r["faces"]], key=lambda b: b[0])
print("faces in t1 via server:", len(boxes), flush=True)
def frame_k(k):
    im = img.copy()
    for i, b in enumerate(boxes):
        if i >= k:
            x1, y1, x2, y2 = int(b[0]*W)-12, int(b[1]*H)-12, int(b[2]*W)+12, int(b[3]*H)+12
            im[max(y1,0):y2, max(x1,0):x2] = 127
    return cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()
frames = {k: frame_k(k) for k in range(0, len(boxes) + 1)}
actual = {k: len(post(frames[k])["faces"]) for k in frames}
print("face count per frame variant (asked->found):", actual, flush=True)
SC = {
    "fixed 6 faces": [6],
    "robot stream 1,1,1,2,1,0,1,1,3,1": [1, 1, 1, 2, 1, 0, 1, 1, 3, 1],
    "mix 0/1/6": [0, 1, 6],
    "crowd random 1-6": __import__("random").Random(5).choices([1, 2, 3, 4, 5, 6], weights=[2, 3, 3, 2, 1, 1], k=60),
}
def run(seq, secs, rate=10.0):
    lat, per = [], {}
    t_end = time.perf_counter() + secs; nxt = time.perf_counter(); i = 0; err = 0; srv = []
    while time.perf_counter() < t_end:
        now = time.perf_counter()
        if now < nxt: time.sleep(nxt - now)
        k = seq[i % len(seq)]; i += 1
        t = time.perf_counter()
        try:
            rr = post(frames[k]); dt = (time.perf_counter() - t) * 1000
            lat.append(dt); per.setdefault(actual[k], []).append(dt); srv.append(rr["took_ms"])
        except Exception as e:
            err += 1
        nxt = max(nxt + 1.0 / rate, time.perf_counter() - 0.0)  # one in flight; skip catch-up
        nxt = max(nxt, t + 1.0 / rate)
    lat.sort()
    return {"n": len(lat), "err": err, "p50": round(statistics.median(lat), 1), "p95": round(lat[int(len(lat) * .95)], 1),
            "mean": round(statistics.mean(lat), 1), "server_p50": round(statistics.median(srv), 1), "req_per_s": round(len(lat) / secs, 2),
            "per_faces": {str(n): {"p50": round(statistics.median(v), 1), "p95": round(sorted(v)[int(len(v) * .95)], 1)} for n, v in sorted(per.items())}}
res = {}
wins = []
def setmode(m): open(MODEFILE, "w").write(m); time.sleep(0.2)
# warmup every mode a bit
for m in MODES:
    setmode(m); run(SC["robot stream 1,1,1,2,1,0,1,1,3,1"], 6)
for rd in range(ROUNDS):
    for sn, seq in SC.items():
        for m in (MODES if rd % 2 == 0 else MODES[::-1]):
            setmode(m)
            t0w = time.time(); r = run(seq, SECS); wins.append([sn, m, rd, t0w, time.time()])
            res.setdefault(sn, {}).setdefault(m, []).append(r)
            print(f"round{rd} {sn} | {m}: p50 {r['p50']} p95 {r['p95']} rps {r['req_per_s']} srv {r['server_p50']}", flush=True)
res['_windows'] = wins
json.dump(res, open(OUT, "w"), indent=1)
print("DONE", flush=True)
