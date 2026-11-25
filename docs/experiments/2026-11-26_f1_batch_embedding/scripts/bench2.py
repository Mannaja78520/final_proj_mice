import os, sys, json, time, random, statistics, subprocess
import numpy as np, cv2
sys.path.insert(0, r"E:\final_proj\mice\Face_Regonize\backend")
from app.face_recognition import cuda_dlls
cuda_dlls.enable()
import onnxruntime as ort
from insightface.app import FaceAnalysis
from insightface.utils import face_align
img = cv2.imread(r"E:\final_proj\mice\Face_Regonize\backend\.venv\Lib\site-packages\insightface\data\images\t1.jpg")
fa = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider"], allowed_modules=["detection"]); fa.prepare(ctx_id=0, det_size=(320, 320))
b, k = fa.det_model.detect(img, max_num=0, metric="default")
crops = [face_align.norm_crop(img, landmark=k[i], image_size=112) for i in range(len(b))]
c8 = (crops * 2)[:8]
mp = os.path.expanduser(r"~\.insightface\models\buffalo_l\w600k_r50.onnx")
def vram(): return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip())
def blob(n): return cv2.dnn.blobFromImages(c8[:n], 1/127.5, (112, 112), (127.5,)*3, swapRB=True)
def mk(): return ort.InferenceSession(mp, providers=["CUDAExecutionProvider"])
v0 = vram(); s1 = mk(); v1 = vram(); s8 = mk(); v2 = vram()
nm = s1.get_inputs()[0].name
def m_loop(n):
    for _ in range(n): s1.run(None, {nm: blob(1)})
def m_batch(n): s1.run(None, {nm: blob(n)})
def m_pad8(n): s1.run(None, {nm: blob(8)})
def m_pad48(n): s1.run(None, {nm: blob(4 if n <= 4 else 8)})
def m_hybrid(n):
    if n <= 2: m_loop(n)
    else: s8.run(None, {nm: blob(8)})
def m_hybrid_fresh(n): pass
METHODS = {"loop (today)": m_loop, "F1 batch of n": m_batch, "pad to 8": m_pad8, "pad to 4/8": m_pad48, "hybrid: 1-2 faces loop, 3+ padded-8 2nd session": m_hybrid}
rng = random.Random(11)
def pois(l):
    import math
    L, p, kk = math.exp(-l), 1.0, 0
    while True:
        p *= rng.random()
        if p <= L: return kk
        kk += 1
PAT = {
    "robot 1,1,1,2,1,1,1,3,1": [1, 1, 1, 2, 1, 1, 1, 3, 1],
    "uniform random 1-8": [rng.randint(1, 8) for _ in range(400)],
    "event crowd (Poisson mean 3, 1-8)": [min(max(pois(3), 1), 8) for _ in range(400)],
    "fixed 6": [6], "fixed 1": [1],
}
res = {"vram_extra_session_MiB": v2 - v1, "vram_first_session_MiB": v1 - v0}
for pn, seq in PAT.items():
    res[pn] = {}
    for mn, f in METHODS.items():
        for n in set(seq): f(n)          # touch every shape once
        for i in range(30): f(seq[i % len(seq)])
        lat = []
        for i in range(360):
            n = seq[i % len(seq)]
            t = time.perf_counter(); f(n); lat.append((time.perf_counter() - t) * 1000)
        lat_s = sorted(lat)
        res[pn][mn] = {"mean": round(statistics.mean(lat), 2), "p50": round(statistics.median(lat), 2), "p95": round(lat_s[int(len(lat) * .95)], 2), "max": round(lat_s[-1], 1)}
        print(pn, "|", mn, res[pn][mn], flush=True)
json.dump(res, open("out/rec2.json", "w"), indent=1)
print("DONE")
