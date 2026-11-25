import os, sys, json, glob
import numpy as np, cv2
sys.path.insert(0, r"E:\final_proj\mice\Face_Regonize\backend")
from app.face_recognition import cuda_dlls
cuda_dlls.enable()
import onnxruntime as ort
from insightface.app import FaceAnalysis
from insightface.utils import face_align
d = r"E:\final_proj\mice\Face_Regonize\backend\.venv\Lib\site-packages\insightface\data\images"
fa = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider"], allowed_modules=["detection"]); fa.prepare(ctx_id=0, det_size=(320, 320))
mp = os.path.expanduser(r"~\.insightface\models\buffalo_l\w600k_r50.onnx")
s = ort.InferenceSession(mp, providers=["CUDAExecutionProvider"]); nm = s.get_inputs()[0].name
def emb(crops, pad=None):
    n = len(crops); c = list(crops)
    if pad and n < pad: c += [c[-1]] * (pad - n)
    out = []
    for i in range(0, len(c), 8 if pad else len(c)):
        ch = c[i:i+8] if pad else c
        out.append(s.run(None, {nm: cv2.dnn.blobFromImages(ch, 1/127.5, (112,112), (127.5,)*3, swapRB=True)})[0])
    return np.concatenate(out)[:n]
rows = []
for f in sorted(glob.glob(d + "/*.jpg")):
    im = cv2.imread(f)
    b, k = fa.det_model.detect(im, max_num=0, metric="default")
    if len(b) == 0: continue
    cr = [face_align.norm_crop(im, landmark=k[i], image_size=112) for i in range(len(b))]
    loop = np.concatenate([emb([c]) for c in cr])
    for name, e in (("batch", emb(cr)), ("pad8", emb(cr, 8))):
        a = loop / np.linalg.norm(loop, axis=1, keepdims=True); bb = e / np.linalg.norm(e, axis=1, keepdims=True)
        cos = (a * bb).sum(1)
        rows.append((os.path.basename(f), name, len(cr), float(cos.min()), float(np.abs(a - bb).max())))
for name in ("batch", "pad8"):
    r = [x for x in rows if x[1] == name]
    print(name, "images", len(r), "faces", sum(x[2] for x in r), "min cos", min(x[3] for x in r), "max abs diff", max(x[4] for x in r))
