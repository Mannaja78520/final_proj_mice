"""A pinhole camera in Studio's frame (mm, Y up), OpenCV image axes (x right, y down)."""
import math

import numpy as np


def rodrigues(r):
    """Axis-angle (3,) -> rotation matrix."""
    th = float(np.linalg.norm(r))
    if th < 1e-12:
        return np.eye(3)
    k = np.asarray(r, float) / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def axis_angle(R):
    """Rotation matrix -> axis-angle (3,)."""
    c = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    th = math.acos(c)
    if th < 1e-9:
        return np.zeros(3)
    if math.pi - th < 1e-6:                 # 180 deg: take the axis from R + I
        k = np.sqrt(np.maximum((np.diag(R) + 1) / 2, 0))
        i = int(np.argmax(k))
        k = (R[:, i] + np.eye(3)[i]) / (2 * k[i])
        return k / np.linalg.norm(k) * th
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return v / (2 * math.sin(th)) * th


class Camera:
    """f in pixels; (cx, cy) image centre; r, t: world -> camera (x_c = R x_w + t)."""

    def __init__(self, f, cx, cy, r, t, width=None, height=None):
        self.f, self.cx, self.cy = float(f), float(cx), float(cy)
        self.r, self.t = np.asarray(r, float), np.asarray(t, float)
        self.width, self.height = width, height

    @classmethod
    def look_at(cls, eye, target, fov_deg, width, height):
        eye, target = np.asarray(eye, float), np.asarray(target, float)
        fwd = target - eye
        fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, [0.0, 1.0, 0.0])
        right /= np.linalg.norm(right)
        down = np.cross(fwd, right)
        R = np.stack([right, down, fwd])
        f = (width / 2) / math.tan(math.radians(fov_deg) / 2)
        return cls(f, width / 2, height / 2, axis_angle(R), -R @ eye, width, height)

    @classmethod
    def orbit(cls, azimuth_deg, elevation_deg, distance, target, fov_deg, width, height):
        """Azimuth 0 = in front of the robot (+Z), 90 = on its left (+X)."""
        a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
        target = np.asarray(target, float)
        eye = target + distance * np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
        return cls.look_at(eye, target, fov_deg, width, height)

    @property
    def R(self):
        return rodrigues(self.r)

    @property
    def center(self):
        """Where the camera is in the world."""
        return -self.R.T @ self.t

    def params(self):
        return np.concatenate([self.r, self.t, [self.f]])

    def with_params(self, p):
        return Camera(p[6], self.cx, self.cy, p[:3], p[3:6], self.width, self.height)

    def project(self, P):
        """(N, 3) world -> (N, 2) pixels, (N,) depth (mm in front of the camera)."""
        Pc = np.asarray(P, float) @ self.R.T + self.t
        z = Pc[:, 2]
        zs = np.where(np.abs(z) < 1e-6, 1e-6, z)
        return np.stack([self.f * Pc[:, 0] / zs + self.cx, self.f * Pc[:, 1] / zs + self.cy], 1), z

    def to_json(self):
        return {"f": self.f, "cx": self.cx, "cy": self.cy, "r": self.r.tolist(), "t": self.t.tolist(),
                "width": self.width, "height": self.height}

    @classmethod
    def from_json(cls, d):
        return cls(d["f"], d["cx"], d["cy"], d["r"], d["t"], d.get("width"), d.get("height"))
