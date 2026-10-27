"""Side-by-side videos with the song: the dancer, then every contender from
several angles, each robot drawn with the dancer's own bone directions as a
faint ghost on its arms (the gap between them IS the tracking error).

Drawn from the same TorchRig the scores use (Studio's tree, waist yaw put
back for the picture), painter-sorted, so what is seen is what was scored.
Frames go straight into ffmpeg (H.264 + the song cut from the source video).
"""
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch

FONTS = ["C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/LeelawUI.ttf",
         "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
BG, PANEL, GRID, TEXT, DIM = (24, 20, 17), (38, 32, 28), (70, 60, 52), (240, 236, 230), (170, 160, 150)
GHOST = (200, 120, 255)


def font(size):
    from PIL import ImageFont
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def put_text(img, xy, text, size, color=TEXT):
    """Thai-capable text (PIL) onto a BGR image region, in place."""
    from PIL import Image, ImageDraw
    f = font(size)
    x, y = xy
    box = f.getbbox(text)
    w, h = box[2] + 4, box[3] + 6
    w, h = min(w, img.shape[1] - x), min(h, img.shape[0] - y)
    if w <= 0 or h <= 0:
        return
    region = Image.fromarray(img[y:y + h, x:x + w][:, :, ::-1].copy())
    ImageDraw.Draw(region).text((0, 0), text, font=f, fill=tuple(int(c) for c in color[::-1]))
    img[y:y + h, x:x + w] = np.asarray(region)[:, :, ::-1]


class RobotPainter:
    """Every frame's 3D shapes at once, then drawn per camera angle."""

    def __init__(self, kin, rig):
        self.kin, self.rig = kin, rig
        d = rig["dims"]
        self.H = d["torsoH"]
        self.len = {"L": (d["upperLenL"], d["foreLenL"]), "R": (d["upperLenR"], d["foreLenR"])}
        self.sense8 = kin.sense[8].item()
        self.zero8 = kin.zero[8].item()

    def frames(self, q):
        """q (F,10) -> dict of numpy arrays (F, ..., 3) in the world frame (waist put back)."""
        with torch.no_grad():
            pts = self.kin.points(torch.as_tensor(q, dtype=self.kin.dtype))
            out = {k: v.cpu().numpy() for k, v in pts.items() if not k.startswith("q")}
            for s in ("L", "R"):
                parts = self.kin._parts(pts, s)
                out["paddle" + s] = self._paddle(pts, s)
                out["upperStart" + s] = parts["upper"][0].cpu().numpy()
        yaw = np.radians((np.asarray(q)[:, 8] - self.zero8) * self.sense8)
        self.yaw = yaw
        return {k: self.turn(v, yaw) for k, v in out.items()}

    def _paddle(self, pts, s):
        arm = 0 if s == "L" else 1
        turn = math.radians((self.rig.get("palmTurn") or [0, 0])[arm] or 0)
        from .kin import _qmul, _qrot
        qh = _qmul(pts["q" + s], torch.tensor([math.cos(turn / 2), 0, math.sin(turn / 2), 0],
                                               dtype=self.kin.dtype).expand_as(pts["q" + s]))
        corners = [(-17, -7), (17, -7), (17, -53), (-17, -53)]
        w = pts["wr" + s]
        return np.stack([(w + _qrot(qh, torch.tensor([x, y, 0.0], dtype=self.kin.dtype).expand_as(w))).cpu().numpy()
                         for x, y in corners], 1)

    @staticmethod
    def turn(v, yaw):
        c, s = np.cos(yaw), np.sin(yaw)
        shape = (-1,) + (1,) * (v.ndim - 2)
        c, s = c.reshape(shape), s.reshape(shape)
        x, y, z = v[..., 0], v[..., 1], v[..., 2]
        return np.stack([c * x + s * z, y, -s * x + c * z], -1)

    def ghost(self, shapes, bones, ok, f):
        """The dancer's bones hung from this robot's shoulders (world frame)."""
        out = []
        for a, s in enumerate(("L", "R")):
            if not ok[a]:
                continue
            up, fo = self.turn(bones[a][None], np.array([self.yaw[f]]))[0]
            sh = shapes["sh" + s][f]
            el = sh + up * self.len[s][0]
            out.append((sh, el, el + fo * self.len[s][1]))
        return out

    def draw(self, img, rect, shapes, f, angle, color, ghost=()):
        x0, y0, w, h = rect
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), PANEL, -1)
        yaw, pitch = math.radians(angle["yaw"]), math.radians(angle["pitch"])
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        scale = min(w / 900.0, h / 820.0)
        ox, oy = x0 + w / 2, y0 + h * 0.62

        def proj(p):
            x, y, z = p[..., 0], p[..., 1], p[..., 2]
            x1, z1 = cy * x - sy * z, sy * x + cy * z            # turn the camera round the robot
            y2, z2 = cp * y - sp * z1, sp * y + cp * z1           # then look down a little
            return np.stack([ox + x1 * scale, oy - y2 * scale], -1), z2
        items = []
        # floor ring under the base
        ring = np.array([[math.cos(t) * 160, -self.H / 2, math.sin(t) * 160] for t in np.linspace(0, 2 * math.pi, 40)])
        r2, _ = proj(ring)
        cv2.polylines(img, [r2.astype(np.int32)], True, GRID, 1, cv2.LINE_AA)

        def seg(a, b, width, col, depth_bias=0.0):
            (pa, za), (pb, zb) = proj(a), proj(b)
            items.append(((za + zb) / 2 + depth_bias, "seg", (pa, pb, max(1, int(width * scale)), col)))

        def ball(p, r, col):
            pp, z = proj(p)
            items.append((z, "ball", (pp, max(2, int(r * scale)), col)))
        g = lambda k: shapes[k][f]
        top = np.array([0, self.H / 2, 0.0])
        seg(self.turn(np.array([[0, -self.H / 2, 0.0]]), self.yaw[f:f + 1])[0],
            self.turn(top[None], self.yaw[f:f + 1])[0], 14, (120, 110, 100))
        ball(self.turn(np.array([[0, self.H / 2 + 68, 0.0]]), self.yaw[f:f + 1])[0], 46, (150, 140, 130))
        seg(g("shL"), g("shR"), 10, (120, 110, 100))
        dark = tuple(int(c * 0.7) for c in color)
        for s in ("L", "R"):
            c = color if s == "L" else dark
            seg(g("shL" if s == "L" else "shR"), g("el" + s), 2 * self.rig["barR"][0] + 6, c)
            seg(g("el" + s), g("wr" + s), 2 * self.rig["barR"][1] + 6, c)
            ball(g("sh" + s), self.rig["jointR"][0], c)
            ball(g("el" + s), self.rig["jointR"][1], c)
            pad, z = proj(shapes["paddle" + s][f])
            items.append((z.mean(), "poly", (pad, (200, 190, 230) if s == "L" else (160, 150, 190))))
        for sh, el, wr in ghost:
            seg(sh, el, 4, GHOST, 1e4)
            seg(el, wr, 4, GHOST, 1e4)
        for _, kind, p in sorted(items, key=lambda it: it[0]):
            if kind == "seg":
                cv2.line(img, tuple(np.int32(p[0])), tuple(np.int32(p[1])), p[3], p[2], cv2.LINE_AA)
            elif kind == "ball":
                cv2.circle(img, tuple(np.int32(p[0])), p[1], p[2], -1, cv2.LINE_AA)
            else:
                cv2.fillConvexPoly(img, p[0].astype(np.int32), p[1], cv2.LINE_AA)


class SourceVideo:
    """The dancer's own video, read forward in time (seeking every frame is slow)."""

    def __init__(self, path, start_s):
        self.cap = cv2.VideoCapture(str(path)) if path and Path(path).exists() else None
        self.start = start_s
        self.frame, self.t = None, -1.0
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, start_s * 1000)

    def at(self, t):
        if not self.cap:
            return None
        while self.t < self.start + t:
            ok, img = self.cap.read()
            if not ok:
                break
            self.frame, self.t = img, self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        return self.frame


class VideoWriter:
    """Raw frames -> ffmpeg, with the song from the source video under them."""

    def __init__(self, path, size, fps, crf, audio=None):
        w, h = size
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
               "-r", str(fps), "-i", "-"]
        if audio and Path(audio[0]).exists():
            cmd += ["-ss", "%.3f" % audio[1], "-t", "%.3f" % audio[2], "-i", str(audio[0]),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "160k"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-shortest", str(path)]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, img):
        self.proc.stdin.write(np.ascontiguousarray(img).tobytes())

    def close(self):
        self.proc.stdin.close()
        if self.proc.wait():
            raise RuntimeError("ffmpeg failed")


class ComparisonVideo:
    """One video: dancer on the left, a row per contender, a column per angle."""

    def __init__(self, painter, dance, cfg, title, subtitle):
        self.p, self.dance, self.cfg, self.title, self.subtitle = painter, dance, cfg, title, subtitle

    def make(self, path, rows, source_path, length_s=None, size=None, note=""):
        """rows: [{"label", "color", "q" (F,10) at 50 Hz, "err" (F,) or None, "tag"}]."""
        cfg = self.cfg
        W, H = size or (cfg["width"], cfg["height"])
        fps = cfg["fps"]
        length = min(length_s or self.dance.length, self.dance.length)
        angles = cfg["angles"]
        shapes = [self.p.frames(r["q"]) for r in rows]
        src = SourceVideo(source_path, self.dance.source["from"])
        left = int(W * 0.33)
        head = int(H * 0.075)
        rh = (H - head) // len(rows)
        cw = (W - left) // len(angles)
        base = np.full((H, W, 3), BG, np.uint8)
        put_text(base, (20, 12), self.title, int(head * 0.42))
        put_text(base, (20, int(head * 0.55)), self.subtitle, int(head * 0.28), DIM)
        vid_h = int(left * 9 / 16)
        put_text(base, (16, head + vid_h + 14), "ผู้เต้นต้นฉบับ (เป้าหมาย) · เส้นม่วง = ท่าคนบนแขนหุ่น", int(H * 0.018), DIM)
        for r, row in enumerate(rows):
            put_text(base, (left + 12, head + r * rh + 6), row["label"], int(H * 0.02), row["color"])
            for a, ang in enumerate(angles):
                put_text(base, (left + a * cw + cw - 140, head + r * rh + 6), ang["label"], int(H * 0.016), DIM)
        if note:
            put_text(base, (16, H - int(H * 0.05)), note, int(H * 0.016), DIM)
        audio = (source_path, self.dance.source["from"], length)
        out = VideoWriter(path, (W, H), fps, cfg["crf"], audio)
        bone_i = lambda t: min(len(self.dance.times) - 1, int(np.searchsorted(self.dance.times, t)))
        try:
            for k in range(int(length * fps)):
                t = k / fps
                img = base.copy()
                frame = src.at(t)
                if frame is not None:
                    img[head:head + vid_h, 0:left] = cv2.resize(frame, (left, vid_h))
                i = bone_i(t)
                for r, row in enumerate(rows):
                    f = min(len(row["q"]) - 1, int(round(t * 50)))
                    ghost = self.p.ghost(shapes[r], self.dance.bones[i], self.dance.arm_ok[i], f)
                    for a, ang in enumerate(angles):
                        rect = (left + a * cw + 4, head + r * rh + 4, cw - 8, rh - 8)
                        self.p.draw(img, rect, shapes[r], f, ang, row["color"], ghost)
                        cv2.rectangle(img, rect[:2], (rect[0] + rect[2], rect[1] + rect[3]), GRID, 1)
                    self._stats(img, (16, head + vid_h + 50 + r * 46), row, f, t)
                cv2.putText(img, "%5.1f s" % t, (W - 170, int(head * 0.62)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, TEXT, 2, cv2.LINE_AA)
                out.write(img)
        finally:
            out.close()

    @staticmethod
    def _stats(img, xy, row, f, t):
        x, y = xy
        cv2.circle(img, (x + 8, y + 10), 7, row["color"], -1, cv2.LINE_AA)
        err = row.get("err")
        e = "" if err is None else "err %4.1f deg" % err[min(len(err) - 1, f)]
        lag = row.get("lag")
        lg = "" if lag is None else "  late %+5.1f s" % lag(t)
        cv2.putText(img, "%s  %s%s" % (row["tag"], e, lg), (x + 24, y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT, 1, cv2.LINE_AA)
