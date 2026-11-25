import os, sys, json, time
import numpy as np, cv2
sys.path.insert(0, r"E:\final_proj\mice\Face_Regonize\backend")
from app.face_recognition import cuda_dlls
cuda_dlls.enable()
import onnxruntime as ort
mp = os.path.expanduser(r"~\.insightface\models\buffalo_l\w600k_r50.onnx")
x = np.random.RandomState(0).randint(0, 255, (8, 112, 112, 3), dtype=np.uint8)
def blob(n): return cv2.dnn.blobFromImages(list(x[:n]), 1/127.5, (112, 112), (127.5,)*3, swapRB=True)
res = {}
for name, opts in (("EXHAUSTIVE (default)", {}), ("HEURISTIC", {"cudnn_conv_algo_search": "HEURISTIC"})):
    t = time.perf_counter(); s = ort.InferenceSession(mp, providers=[("CUDAExecutionProvider", opts)]); load = (time.perf_counter() - t) * 1000
    nm = s.get_inputs()[0].name; r = {"session_load_ms": round(load)}
    for n in (1, 6, 2, 3, 4, 5, 7, 8):
        t = time.perf_counter(); s.run(None, {nm: blob(n)}); r[f"first_call_batch{n}_ms"] = round((time.perf_counter() - t) * 1000)
    # second visit to a known shape right after another shape
    t = time.perf_counter(); s.run(None, {nm: blob(1)}); r["revisit_batch1_after_8_ms"] = round((time.perf_counter() - t) * 1000, 1)
    t = time.perf_counter(); s.run(None, {nm: blob(1)}); r["batch1_again_ms"] = round((time.perf_counter() - t) * 1000, 1)
    res[name] = r; print(name, r, flush=True)
json.dump(res, open("out/cold.json", "w"), indent=1)
