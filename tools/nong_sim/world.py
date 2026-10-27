"""N Nong robots in one MuJoCo world, each following the board's clock.

The tree comes from kinematics.NongTree (Studio's own build), so a MuJoCo hinge
angle is Studio's jointDelta in radians. MuJoCo adds what Studio cannot know:
servo lag, the speed cap acting on the real arm, gravity, and contacts between
the real swept shapes. Only a true overlap pushes parts apart; how
close every pair that could meet came is measured (mj_geomDistance) and reported.
"""
import math
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np

from .board_clock import BoardClock
from .kinematics import NongTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_urdf import EFFORT_NM  # noqa: E402  stall torque per joint, one source

MM = 0.001
FRAME_S = 0.02            # the board writes the servos at 50 Hz (frameHz)
Y_UP_TO_Z_UP = "0.70710678 0.70710678 0 0"


def _v(values, scale=MM):
    return " ".join("%.6g" % (v * scale) for v in values)


class NongWorld:
    def __init__(self, rig, facts, config, sequences):
        import mujoco                       # optional: only this tool needs it
        self.mj = mujoco
        self.rig, self.facts, self.cfg = rig, facts, config
        self.tree = NongTree(rig, facts)
        near = config["report"].get("nearMm")
        self.near_mm = near if near is not None else facts.clear_mm + (rig.get("extraClearanceMm") or 0)
        count = max(1, int(config["robots"]["count"]), len(sequences))
        lo, hi = config["robots"]["vary"].get("lagMs", [config["servo"]["lagMs"]] * 2)
        self.robots = []
        for k in range(count):
            clock = BoardClock(rig, facts, config.get("safeDps"))
            moves = clock.plan(sequences[k % len(sequences)][1])
            lag = config["servo"]["lagMs"] if count == 1 else lo + (hi - lo) * k / (count - 1)
            self.robots.append({"name": sequences[k % len(sequences)][0], "moves": moves, "clock": clock,
                                "lag": lag / 1000, "servo": None})
        self.model = mujoco.MjModel.from_xml_string(self.xml())
        self.data = mujoco.MjData(self.model)
        self._index()

    # ---- the model ------------------------------------------------------
    def _joint_range(self, j):
        a, b = (self.tree.delta(self.rig[k], j) for k in ("min", "max"))
        return math.radians(min(a, b)), math.radians(max(a, b))

    def _torque(self, j):
        gear = (self.rig["gearGear"][j] or 1) / (self.rig["gearPinion"][j] or 1)
        return EFFORT_NM[j] * gear

    def _robot_xml(self, k):
        p, body_xml, close = "r%d_" % k, [], {}
        children = {}
        for b in self.tree.bodies:
            children.setdefault(b.parent, []).append(b)

        def emit(b, depth):
            pad = "  " * depth
            out = [pad + '<body name=%s pos="%s" quat="%s">' % (quoteattr(p + b.name), _v(b.pos), _v(b.quat, 1))]
            if b.joint is not None:
                lo, hi = self._joint_range(b.joint)
                out.append(pad + '  <joint name="%sj%d" type="hinge" axis="%s" range="%.5f %.5f" limited="true"/>'
                           % (p, b.joint, _v(b.axis, 1), lo, hi))
            if b.slide is not None:
                rises = [pt.get("lr"[b.arm], 0) for pt in self.rig["shrugCurve"]]
                out.append(pad + '  <joint name="%ss%d_%d" type="slide" axis="0 1 0" range="%s"/>'
                           % (p, b.slide, b.arm, _v((min(rises) - 1, max(rises) + 1))))
            for g in b.geoms:
                if g.kind == "box":
                    out.append(pad + '  <geom name="%s" type="box" size="%s" pos="%s"/>' % (p + g.part, _v(g.size), _v(g.pos)))
                elif g.kind == "sphere":
                    out.append(pad + '  <geom name="%s" type="sphere" size="%s" pos="%s"/>' % (p + g.part, _v(g.size), _v(g.pos)))
                else:
                    out.append(pad + '  <geom name="%s" type="capsule" size="%s" fromto="%s %s"/>'
                               % (p + g.part, _v(g.size), _v(g.pos), _v(g.to)))
            for c in children.get(b.name, []):
                out += emit(c, depth + 1)
            out.append(pad + "</body>")
            return out

        x = (k - (len(self.robots) - 1) / 2) * self.cfg["robots"]["spacingMm"] * MM
        body_xml.append('    <body name="%sbase" pos="%.4f 0 %.4f" quat="%s">'
                        % (p, x, self.rig["dims"]["torsoH"] / 2 * MM + 0.02, Y_UP_TO_Z_UP))
        for b in children["world"]:
            body_xml += emit(b, 3)
        body_xml.append("    </body>")
        return body_xml

    def xml(self):
        ph, sv = self.cfg["physics"], self.cfg["servo"]
        out = ['<mujoco model="nong">', '  <compiler angle="radian" autolimits="true" boundmass="1e-4" boundinertia="1e-9"/>',
               '  <option timestep="%g" gravity="0 0 -9.81" integrator="implicitfast"/>' % ph["timestep"],
               '  <default><geom density="%g" rgba="0.75 0.78 0.85 1"/>'
               '<joint damping="%g" armature="%g"/></default>' % (ph["densityKgM3"], ph["jointDamping"], ph["armature"]),
               '  <visual><global offwidth="1280" offheight="720"/></visual>',
               '  <worldbody>', '    <light pos="0 -2 3" dir="0 0.6 -1"/>',
               '    <geom name="floor" type="plane" size="4 4 0.01" contype="0" conaffinity="0" rgba="0.3 0.32 0.36 1"/>']
        for k in range(len(self.robots)):
            out += self._robot_xml(k)
        out.append("  </worldbody>")
        # same-arm parts touch at every joint by design (Studio skips them too)
        out.append("  <contact>")
        armed = [b for b in self.tree.bodies if b.arm is not None and b.geoms]
        for k in range(len(self.robots)):
            for i, a in enumerate(armed):
                for b in armed[i + 1:]:
                    if a.arm == b.arm:
                        out.append('    <exclude body1="r%d_%s" body2="r%d_%s"/>' % (k, a.name, k, b.name))
        out.append("  </contact>")
        out.append("  <actuator>")
        for k in range(len(self.robots)):
            for j in range(10):
                kp = self._torque(j) / math.radians(sv["fullTorqueDeg"])
                tq = self._torque(j)
                target = None
                if any(b.joint == j for b in self.tree.bodies):
                    target = "r%d_j%d" % (k, j)
                if target:
                    out.append('    <position name="r%d_a%d" joint="%s" kp="%.4g" kv="%.4g" forcerange="%.4g %.4g"/>'
                               % (k, j, target, kp, kp * sv["kvPerKp"], -tq, tq))
            for arm in (0, 1):
                if any(b.slide is not None for b in self.tree.bodies):
                    out.append('    <position name="r%d_s%d" joint="r%d_s9_%d" kp="%g" kv="%g"/>'
                               % (k, arm, k, arm, sv["shrugSlideKp"], sv["shrugSlideKp"] * sv["kvPerKp"]))
        out.append("  </actuator>")
        out.append("</mujoco>")
        return "\n".join(out)

    def _index(self):
        mj, m = self.mj, self.model
        for k, r in enumerate(self.robots):
            r["act"] = {j: mj.mj_name2id(m, mj.mjtObj.mjOBJ_ACTUATOR, "r%d_a%d" % (k, j)) for j in range(10)}
            r["qadr"] = {j: m.jnt_qposadr[mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "r%d_j%d" % (k, j))]
                         for j in range(10) if r["act"][j] >= 0}
            r["slide"] = [mj.mj_name2id(m, mj.mjtObj.mjOBJ_ACTUATOR, "r%d_s%d" % (k, a)) for a in (0, 1)]
            r["sadr"] = [m.jnt_qposadr[i] if i >= 0 else -1 for i in
                         (mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "r%d_s9_%d" % (k, a)) for a in (0, 1))]
        self.geom_robot = {}
        for g in range(m.ngeom):
            name = mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g) or ""
            if name.startswith("r") and "_" in name:
                self.geom_robot[g] = (int(name[1:name.index("_")]), name[name.index("_") + 1:])
        # every pair of one robot that may meet: not the same arm (those
        # touch at each joint by design), so arm-arm and arm-torso/head
        arm_of = {g: self.model.body(int(m.geom_bodyid[g])).name for g in self.geom_robot}
        side = {b.name: b.arm for b in self.tree.bodies}
        self.pairs = []
        for a in self.geom_robot:
            for b in self.geom_robot:
                ra, rb = self.geom_robot[a][0], self.geom_robot[b][0]
                sa, sb = (side.get(arm_of[g].split("_", 1)[1]) for g in (a, b))
                if a < b and ra == rb and sa != sb:      # body vs arm, or arm vs arm
                    self.pairs.append((a, b))
        self._fromto = np.zeros(6)

    # ---- playing --------------------------------------------------------
    def reset(self):
        self.mj.mj_resetData(self.model, self.data)
        for r in self.robots:
            start = r["moves"][0].start_pose if r["moves"] else self.rig["home"]
            r["servo"] = list(start)
            for j, adr in r["qadr"].items():
                self.data.qpos[adr] = math.radians(self.tree.delta(start, j))
            rise = self.tree.shrug_rise(start[9])
            for arm, adr in enumerate(r["sadr"]):
                if rise and adr >= 0:
                    self.data.qpos[adr] = rise[arm] * MM
        self.mj.mj_forward(self.model, self.data)
        self.t = 0.0

    def _servo_step(self, r, target, dt):
        """Rate cap at servoMaxDps, then a first-order lag: what the horn does."""
        out = r["servo"]
        a = 1 - math.exp(-dt / max(1e-4, r["lag"]))
        for j in range(10):
            want = out[j] + (target[j] - out[j]) * a
            cap = r["clock"].max_dps[j] * dt
            out[j] += max(-cap, min(cap, want - out[j]))
        return out

    def step_frame(self):
        """One 20 ms board frame: new targets, then physics until the next."""
        for r in self.robots:
            target = BoardClock.target(r["moves"], self.t) if r["moves"] else self.rig["home"]
            r["target"] = target
        n = max(1, round(FRAME_S / self.model.opt.timestep))
        for _ in range(n):
            for r in self.robots:
                servo = self._servo_step(r, r["target"], self.model.opt.timestep)
                for j, a in r["act"].items():
                    if a >= 0:
                        self.data.ctrl[a] = math.radians(self.tree.delta(servo, j))
                rise = self.tree.shrug_rise(servo[9])
                if rise and r["slide"][0] >= 0:
                    self.data.ctrl[r["slide"][0]], self.data.ctrl[r["slide"][1]] = rise[0] * MM, rise[1] * MM
            self.mj.mj_step(self.model, self.data)
        self.t += FRAME_S

    def joint_deg(self, r):
        """Back from hinge radians to Studio joint degrees."""
        out = list(r["target"])
        for j, adr in r["qadr"].items():
            sense = self.facts.base_dir[j] * (-1 if self.rig["invert"][j] else 1)
            out[j] = self.rig["zero"][j] + math.degrees(self.data.qpos[adr]) / sense
        return out

    def contacts(self):
        """(robot, part A, part B, gap mm) for every pair closer than near_mm."""
        out, reach = [], self.near_mm * MM
        for a, b in self.pairs:
            gap = self.mj.mj_geomDistance(self.model, self.data, a, b, reach, self._fromto)
            if gap < reach:
                out.append((self.geom_robot[a][0], self.geom_robot[a][1], self.geom_robot[b][1], gap / MM))
        return out

    def length(self):
        return max(r["clock"].length for r in self.robots)
