"""Static MuJoCo geometry from Studio's NongTree; no simulation or GPU tensors."""
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

from .render_meshes import CadAppearance


def vector(values, scale=1.0):
    return " ".join(str(float(x) * scale) for x in values)


class RenderScene:
    """One compiled scene, moved to exact tree frames for each labelled pose."""

    def __init__(self, kp, width, height):
        # A Linux box with no screen (the cloud QC) has no GL window: render
        # off-screen with OSMesa there. Windows and a desktop keep MuJoCo's default.
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            os.environ.setdefault("MUJOCO_GL", "osmesa")
        import mujoco
        self.mj, self.kp = mujoco, kp
        root = ET.Element("mujoco", model="nong_pose")
        ET.SubElement(root, "visual").append(ET.Element("global", offwidth=str(width), offheight=str(height)))
        asset = ET.SubElement(root, "asset")
        ET.SubElement(asset, "texture", name="tiles", type="2d", builtin="checker", width="128", height="128",
                      rgb1=".9 .9 .9", rgb2=".4 .4 .4")
        ET.SubElement(asset, "material", name="floor", texture="tiles", texrepeat="6 6", reflectance="0")
        world = ET.SubElement(root, "worldbody")
        ET.SubElement(world, "camera", name="view", pos="0 0 2", sensorsize="1 1",
                      resolution=f"{width} {height}", focal="1 1")
        ET.SubElement(world, "light", pos="0 1 2", dir="0 -1 -1", diffuse=".8 .8 .8")
        floor_y = -kp.rig["dims"]["torsoH"] / 2000 - .02
        ET.SubElement(world, "geom", name="floor", type="plane", size="4 4 .01", material="floor",
                      pos=f"0 {floor_y} 0", quat=".70710678 .70710678 0 0")
        self.cad = CadAppearance(kp)
        self.bodies = [b for b in kp.tree.bodies if b.geoms or (self.cad.enabled and self.cad.key_for_body(b.name))]
        for b in self.bodies:
            body = ET.SubElement(world, "body", name=b.name, mocap="true")
            key = self.cad.key_for_body(b.name) if self.cad.enabled else None
            if key:
                self.cad.attach(asset, body, key)
            for g in ([] if key or (self.cad.enabled and b.name.endswith("_hand")) else b.geoms):
                attrs = dict(name=g.part, type=g.kind, size=vector(g.size, .001))
                if g.to is None:
                    attrs["pos"] = vector(g.pos, .001)
                else:
                    attrs["fromto"] = vector((*g.pos, *g.to), .001)
                ET.SubElement(body, "geom", **attrs)
        self.model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height, width)
        self.mocap = {b.name: self.model.body(b.name).mocapid[0] for b in self.bodies}

    def place(self, pose, camera):
        frames = self.kp.tree.frames(pose)
        for name, index in self.mocap.items():
            pos, quat = frames[name]
            self.data.mocap_pos[index] = pos * .001
            self.data.mocap_quat[index] = quat
        # MuJoCo cameras look along -Z, +Y up; OpenCV looks +Z, +Y down.
        rotation = camera.R.T @ np.diag([1., -1., -1.])
        self.model.cam_pos[0] = camera.center * .001
        self.mj.mju_mat2Quat(self.model.cam_quat[0], rotation.ravel())
        w, h = camera.width, camera.height
        self.model.cam_intrinsic[0] = [camera.f / w, camera.f / h,
                                       (w / 2 - camera.cx) / w, (h / 2 - camera.cy) / h]
        self.mj.mj_forward(self.model, self.data)

    def draw(self):
        self.renderer.disable_depth_rendering()
        self.renderer.update_scene(self.data, camera="view")
        rgb = self.renderer.render().copy()
        self.renderer.enable_depth_rendering()
        depth = self.renderer.render().copy() * 1000  # camera-plane depth, mm
        self.renderer.disable_depth_rendering()
        return rgb, depth

    def close(self):
        self.renderer.close()
