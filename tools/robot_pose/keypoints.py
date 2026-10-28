"""Where nong's keypoints are, in 3D, for any pose of any rig.

The list is config/robot_pose.json; each keypoint sits on a body of Studio's
joint tree (tools/nong_sim NongTree), so the 3D answer is Studio's own and a
rig change (longer arm, moved shoulder) moves the keypoints with it.
"""
import ast
import json
import operator
from pathlib import Path

import numpy as np

from tools.nong_sim.kinematics import NongTree, quat_rotate
from tools.nong_sim.studio import StudioFacts, load_rig

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "robot_pose.json"
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg}


def load_config(path=None):
    return json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))


def expr(value, names):
    """A number, or arithmetic over the rig's names ("torsoH/2+68"). No calls, no attributes."""
    if isinstance(value, (int, float)):
        return float(value)

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name) and n.id in names:
            return float(names[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("robot_pose.json: cannot read %r" % value)
    return ev(ast.parse(str(value), mode="eval"))


class RobotKeypoints:
    def __init__(self, rig=None, facts=None, cfg=None):
        self.rig = rig or load_rig()
        self.facts = facts or StudioFacts()
        self.cfg = cfg or load_config()
        self.tree = NongTree(self.rig, self.facts)
        names = dict(self.rig["dims"], headR=self.facts.head_r, handY=self.facts.hand_y,
                     handW=self.facts.hand_size[0], handH=self.facts.hand_size[1])
        self.kps = self.cfg["keypoints"]
        self.names = [k["name"] for k in self.kps]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.offsets = [np.array([expr(v, names) for v in k["offset"]]) for k in self.kps]
        bodies = {b.name for b in self.tree.bodies}
        missing = [k["body"] for k in self.kps if k["body"] not in bodies]
        if missing:
            raise ValueError("robot_pose.json: no rig body %s" % missing)
        self.edges = [(self.index[a], self.index[b]) for a, b in self.cfg["skeleton"]]
        self.flip = [self.index.get(self.mirror(n), i) for i, n in enumerate(self.names)]

    @staticmethod
    def mirror(name):
        """L_x <-> R_x: the same keypoint on the other arm (YOLO flip_idx)."""
        if name.startswith("L_"):
            return "R_" + name[2:]
        if name.startswith("R_"):
            return "L_" + name[2:]
        return name

    def points3d(self, pose):
        """(K, 3) mm in Studio's frame (robot at the origin, Y up, front +Z)."""
        frames = self.tree.frames(list(pose))
        out = np.empty((len(self.kps), 3))
        for i, (k, off) in enumerate(zip(self.kps, self.offsets)):
            p, q = frames[k["body"]]
            out[i] = p + quat_rotate(q, off)
        return out

    def front(self, pose):
        """The robot's front direction in the world: +Z turned by the waist."""
        frames = self.tree.frames(list(pose))
        return quat_rotate(frames["waist"][1], np.array([0.0, 0.0, 1.0]))
