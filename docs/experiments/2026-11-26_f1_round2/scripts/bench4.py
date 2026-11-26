"""Round 1: is there anything better than the hybrid? recognition model only, per-frame embedding cost."""
import os, sys, json, time, random, statistics, subprocess, math
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
def blob(imgs): return cv2.dnn.blobFromImages(imgs, 1/127.5, (112, 112), (127.5,)*3, swapRB=True)
BUCKETS = (1, 2, 4, 8)
import onnx
_m = onnx.load(mp)
for _o in _m.graph.output:
    _d = _o.type.tensor_type.shape.dim[0]; _d.ClearField("dim_value"); _d.dim_param = "N"   # the file declares output batch = 1; widen so a bound buffer of N passes
MP_FIXED = _m.SerializeToString()
def plain(opts=None, fixed=False): return ort.InferenceSession(MP_FIXED if fixed else mp, providers=[("CUDAExecutionProvider", dict(opts or {}))])
class Plain:
    def __init__(s, opts=None): s.s = plain(opts); s.n = s.s.get_inputs()[0].name
    def run(s, imgs): return s.s.run(None, {s.n: blob(imgs)})[0]
class IOB:
    """fixed-shape session with preallocated device buffers; optional CUDA graph"""
    def __init__(s, bsz, graph, opts=None):
        o = dict(opts or {}); 
        if graph: o["enable_cuda_graph"] = "1"
        s.s = plain(o, fixed=True); s.bsz = bsz
        s.n = s.s.get_inputs()[0].name; s.o = s.s.get_outputs()[0].name
        s.x = ort.OrtValue.ortvalue_from_numpy(np.zeros((bsz, 3, 112, 112), np.float32), "cuda", 0)
        s.y = ort.OrtValue.ortvalue_from_numpy(np.zeros((bsz, 512), np.float32), "cuda", 0)
        s.io = s.s.io_binding(); s.io.bind_ortvalue_input(s.n, s.x); s.io.bind_ortvalue_output(s.o, s.y)
        for _ in range(3): s.s.run_with_iobinding(s.io)
    def run(s, imgs):
        s.x.update_inplace(blob(imgs)); s.s.run_with_iobinding(s.io); return s.y.numpy()
def pad(imgs, to): return imgs + [imgs[-1]] * (to - len(imgs))
def bucket(n): return next(b for b in BUCKETS if n <= b)
import gc
res = {"vram_MiB": {}, "accuracy_vs_loop": {}}
def chunks(imgs): return [imgs[i:i + 8] for i in range(0, len(imgs), 8)]
rng = random.Random(11)
def pois(l):
    L, p, kk = math.exp(-l), 1.0, 0
    while True:
        p *= rng.random()
        if p <= L: return kk
        kk += 1
PAT = {"robot 1,1,1,2,1,1,1,3,1": [1, 1, 1, 2, 1, 1, 1, 3, 1], "event crowd (Poisson mean 3, 1-8)": [min(max(pois(3), 1), 8) for _ in range(400)],
       "uniform random 1-8": [rng.randint(1, 8) for _ in range(400)], "fixed 6": [6], "fixed 1": [1], "fixed 2": [2]}
ARENA = {"arena_extend_strategy": "kSameAsRequested"}
def group(gname, make, methods_of):
    v0 = vram(); S = make(); used = vram() - v0; res["vram_MiB"][gname] = used
    M = methods_of(S)
    ref = None
    for mn, f in M.items():
        for pn, seq in PAT.items():
            for n in set(seq): f(c8[:n])
            for i in range(40): f(c8[:seq[i % len(seq)]])
            lat = []
            for i in range(600):
                n = seq[i % len(seq)]; im = c8[:n]
                t = time.perf_counter(); f(im); lat.append((time.perf_counter() - t) * 1000)
            ls = sorted(lat)
            res.setdefault(pn, {})[mn] = {"mean": round(statistics.mean(lat), 2), "p50": round(statistics.median(lat), 2), "p95": round(ls[int(len(ls) * .95)], 2), "p99": round(ls[int(len(ls) * .99)], 2), "max": round(ls[-1], 1)}
            print(pn, "|", mn, res[pn][mn], flush=True)
        worst, md = 1.0, 0.0
        for n in range(1, 9):
            e = f(c8[:n]); r = REF[n]; a = r / np.linalg.norm(r, axis=1, keepdims=True); b2 = e / np.linalg.norm(e, axis=1, keepdims=True)
            worst = min(worst, float((a * b2).sum(1).min())); md = max(md, float(np.abs(a - b2).max()))
        res["accuracy_vs_loop"][mn] = {"min_cos": round(worst, 7), "max_abs_diff": md}
    print(gname, "VRAM", used, flush=True)
    del S, M; gc.collect(); time.sleep(1)
base = Plain(); REF = {n: np.concatenate([base.run([c]) for c in c8[:n]]) for n in range(1, 9)}
def loop_f(s1): return lambda imgs: np.concatenate([s1.run([i]) for i in imgs])
def pad(imgs, to): return imgs + [imgs[-1]] * (to - len(imgs))
def bucket(n): return next(b for b in BUCKETS if n <= b)
WS0 = {"cudnn_conv_use_max_workspace": "0"}
def mkb(bs, graph, opts): return {b: IOB(b, graph, opts) for b in bs}
def bkn(S, key, bsz):
    bsz = tuple(sorted(bsz))
    def bucket2(n): return next(b for b in bsz if n <= b)
    return lambda imgs: np.concatenate([S[key][bucket2(len(c))].run(pad(c, bucket2(len(c))))[:len(c)] for c in chunks(imgs)])
group("loop baseline", lambda: {"s1": base}, lambda S: {"loop (today)": loop_f(S["s1"])})
def hyb(S):
    def f(imgs):
        if len(imgs) <= 2: return loop_f(S["s1"])(imgs)
        return np.concatenate([S["s8"].run(pad(c, 8))[:len(c)] for c in chunks(imgs)])
    return {"hybrid, default workspace": f}
group("hybrid default workspace (+1 session)", lambda: {"s1": base, "s8": Plain()}, hyb)
group("hybrid, max_workspace=0 (+1 session)", lambda: {"s1": Plain(WS0), "s8": Plain(WS0)}, lambda S: {k.replace("default workspace", "max_workspace=0"): v for k, v in hyb(S).items()})
for bs in ((1, 2, 4, 8), (1, 4, 8), (1, 2, 8), (1, 8)):
    nm = "graph buckets %s, max_workspace=0" % "/".join(map(str, bs))
    group(nm + " (%d sessions)" % len(bs), (lambda bs=bs: {"b": mkb(bs, True, WS0)}), (lambda S, bs=bs, nm=nm: {nm: bkn(S, "b", bs)}))
nm = "graph buckets 1/2/4/8, default workspace"
group(nm + " (4 sessions)", lambda: {"b": mkb((1, 2, 4, 8), True, {})}, lambda S: {nm: bkn(S, "b", (1, 2, 4, 8))})
res["gpu"] = os.popen("nvidia-smi --query-gpu=name,driver_version --format=csv,noheader").read().strip(); res["ort"] = ort.__version__
json.dump(res, open("out/rec4.json", "w"), indent=1); print("DONE", flush=True)
