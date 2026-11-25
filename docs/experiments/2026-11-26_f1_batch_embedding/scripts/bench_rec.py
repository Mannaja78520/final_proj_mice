import os, sys, json, time, random, statistics
import numpy as np, cv2
sys.path.insert(0, r"E:\final_proj\mice\Face_Regonize\backend")
from app.face_recognition import cuda_dlls  # friend's DLL loader (read only)
cuda_dlls.enable()
import onnxruntime as ort
from insightface.app import FaceAnalysis
from insightface.utils import face_align
OUT = sys.argv[1] if len(sys.argv) > 1 else "out/rec.json"
img = cv2.imread(r"E:\final_proj\mice\Face_Regonize\backend\.venv\Lib\site-packages\insightface\data\images\t1.jpg")
fa = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider"], allowed_modules=["detection"])
fa.prepare(ctx_id=0, det_size=(320, 320))
b, k = fa.det_model.detect(img, max_num=0, metric="default")
crops = [face_align.norm_crop(img, landmark=k[i], image_size=112) for i in range(len(b))]
print("faces in t1:", len(crops), flush=True)
crops8 = (crops * 2)[:8]
mp = os.path.expanduser(r"~\.insightface\models\buffalo_l\w600k_r50.onnx")

def blob(n):
    return cv2.dnn.blobFromImages(crops8[:n] if n <= 8 else (crops8 * 4)[:n], 1/127.5, (112, 112), (127.5,)*3, swapRB=True)

def mk(opts):
    so = ort.SessionOptions()
    s = ort.InferenceSession(mp, so, providers=[("CUDAExecutionProvider", dict(opts))], )
    assert s.get_providers()[0] == "CUDAExecutionProvider"
    return s

def run_pattern(sess, sizes, n_calls=240, warm=30, pad=None):
    name = sess.get_inputs()[0].name
    lat = {}
    seq = [sizes[i % len(sizes)] for i in range(n_calls + warm)]
    for i, n in enumerate(seq):
        tgt = pad(n) if pad else n
        t = time.perf_counter()
        x = blob(tgt)
        sess.run(None, {name: x})
        dt = (time.perf_counter() - t) * 1000
        if i >= warm:
            lat.setdefault(n, []).append(dt)
    allv = [v for l in lat.values() for v in l]
    return {"per_size_median": {str(n): round(statistics.median(v), 1) for n, v in sorted(lat.items())},
            "median": round(statistics.median(allv), 1),
            "p95": round(sorted(allv)[int(len(allv) * .95)], 1),
            "total_per_call_mean": round(statistics.mean(allv), 1)}

ROBOT = [1, 1, 1, 2, 1, 1, 1, 3, 1]          # faces per frame, 0-face frames skipped (no embedding call)
patterns = {
    "always 1": [1], "always 2": [2], "always 6": [6], "always 8": [8],
    "alt 1/6": [1, 6], "alt 1/2": [1, 2],
    "robot 1,1,1,2,1,1,1,3,1": ROBOT,
    "random 1-8": [random.Random(7).randint(1, 8) for _ in range(64)],
}
cfgs = {
    "ORT default (EXHAUSTIVE)": {},
    "algo_search=HEURISTIC": {"cudnn_conv_algo_search": "HEURISTIC"},
    "algo_search=DEFAULT": {"cudnn_conv_algo_search": "DEFAULT"},
}
res = {}
for cn, co in cfgs.items():
    sess = mk(co)
    res[cn] = {}
    for pn, p in patterns.items():
        res[cn][pn] = run_pattern(sess, p)
        print(cn, "|", pn, res[cn][pn]["median"], res[cn][pn]["p95"], flush=True)
    del sess
# fix candidates on default session: pad to constant batch
sess = mk({})
res["FIX pad"] = {}
for padname, padf in {"pad to 8 always": lambda n: 8, "pad to 4 (<=4) else 8": lambda n: 4 if n <= 4 else 8}.items():
    res["FIX pad"][padname] = {}
    for pn in ["robot 1,1,1,2,1,1,1,3,1", "alt 1/6", "random 1-8", "always 1", "always 6"]:
        res["FIX pad"][padname][pn] = run_pattern(sess, patterns[pn], pad=padf)
        print("PAD", padname, "|", pn, res["FIX pad"][padname][pn]["median"], res["FIX pad"][padname][pn]["p95"], flush=True)
# two sessions: batch-1 session + batch-N session (never switch shape inside one session)
s1, sN = mk({}), mk({})
def two_sess(n_calls=240, warm=30, sizes=ROBOT):
    n1 = s1.get_inputs()[0].name; lat = []
    for i in range(n_calls + warm):
        n = sizes[i % len(sizes)]
        t = time.perf_counter()
        if n == 1:
            s1.run(None, {n1: blob(1)})
        else:
            sN.run(None, {n1: blob(8)})   # sN always sees batch 8 (padded)
        dt = (time.perf_counter() - t) * 1000
        if i >= warm: lat.append(dt)
    return {"median": round(statistics.median(lat), 1), "p95": round(sorted(lat)[int(len(lat) * .95)], 1), "mean": round(statistics.mean(lat), 1)}
res["FIX two sessions (bs1 + padded bs8)"] = {"robot": two_sess()}
print("TWO", res["FIX two sessions (bs1 + padded bs8)"], flush=True)
# baseline equivalent: loop of batch-1 calls (what the friend's engine does now), per frame total
def loop_frame(sess, sizes=ROBOT, n_calls=240, warm=30):
    n1 = sess.get_inputs()[0].name; lat = []
    for i in range(n_calls + warm):
        n = sizes[i % len(sizes)]
        t = time.perf_counter()
        for _ in range(n):
            sess.run(None, {n1: blob(1)})
        dt = (time.perf_counter() - t) * 1000
        if i >= warm: lat.append(dt)
    return {"median": round(statistics.median(lat), 1), "p95": round(sorted(lat)[int(len(lat) * .95)], 1), "mean": round(statistics.mean(lat), 1)}
res["per-frame embed time, robot stream"] = {
    "loop of bs1 (friend's engine today)": loop_frame(mk({})),
    "F1 one batch of n": run_pattern(mk({}), ROBOT),
    "padded to 8": run_pattern(mk({}), ROBOT, pad=lambda n: 8),
    "padded 4/8": run_pattern(mk({}), ROBOT, pad=lambda n: 4 if n <= 4 else 8),
}
res["gpu"] = os.popen("nvidia-smi --query-gpu=name,driver_version,clocks.sm,utilization.gpu --format=csv,noheader").read().strip()
res["ort"] = ort.__version__
json.dump(res, open(OUT, "w"), indent=1)
print("DONE", flush=True)
