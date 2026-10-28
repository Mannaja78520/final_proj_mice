"""Real GL pixels catch camera-axis/intrinsic drift; depth catches arm occlusion.

No board, camera capture, model inference, or training. All temporary media
stay in .local. CAD is optional; the shared primitive tree is the oracle.
"""
import copy
import json
import tempfile
from pathlib import Path

AREA = "robot-pose"
TITLE = "MuJoCo cameras, depth visibility, and private YOLO image output"
SLOW = False


def run(t):
    import numpy as np
    from tools.robot_pose.camera import Camera
    from tools.robot_pose.keypoints import RobotKeypoints, load_config
    from tools.robot_pose.render_mujoco import MujocoPoseRenderer, private_path
    from tools.robot_pose.synth import SynthViews

    cfg = copy.deepcopy(load_config())
    cfg["render"]["cad"]["enabled"] = False
    kp = RobotKeypoints(cfg=cfg)
    renderer = MujocoPoseRenderer(kp)
    try:
        for azimuth in (0, 55, 180, 275):
            cam = Camera.orbit(azimuth, 12, 1500, [0, 90, 0], 58, 640, 480)
            cam.cx += 37
            cam.cy -= 23
            rgb, uv, vis, depth = renderer.render(kp.rig["home"], cam, False)
            scene = renderer.scene
            scene.model.geom_rgba[:, :3] = 0
            scene.model.geom_rgba[scene.model.geom("head").id] = [1, 0, 0, 1]
            pixels, _ = scene.draw()
            red = (pixels[:, :, 0] > 50) & (pixels[:, :, 1] < 20)
            yy, xx = np.where(red)
            error = np.linalg.norm(np.array([xx.mean(), yy.mean()]) - uv[kp.index["head"]])
            t.ok(len(xx) > 30 and error < 2, f"actual head pixels match OpenCV projection at {azimuth}", str(error))
            frames = kp.tree.frames(kp.rig["home"])
            t.ok(all(np.allclose(scene.data.mocap_pos[i] * 1000, frames[n][0])
                     for n, i in scene.mocap.items()), "MuJoCo frames equal shared rig millimetres", "no base offset/dynamics")
        cam = Camera.orbit(90, 0, 1500, [0, 100, 0], 60, 640, 480)
        rgb, uv, vis, depth = renderer.render(kp.rig["home"], cam, False)
        a, b = kp.index["L_shoulder"], kp.index["R_shoulder"]
        t.eq(int(vis[a]), 2, "near shoulder centre stays visible inside own housing")
        t.eq(int(vis[b]), 1, "far shoulder is hidden by near arm in the depth buffer")
        baduv = np.array([[-1., 20.]] * len(kp.names))
        t.ok(not renderer.visibility(baduv, np.ones(len(kp.names)), depth).any(), "off-image labels stay zero", "no wrapped indexing")
        for path in ("relative/output", Path(__file__).resolve().parent / "private.jpg"):
            try:
                private_path(path)
                t.ok(False, "non-private output refused", str(path))
            except ValueError:
                t.ok(True, "non-private output refused", str(path))
        from tools.robot_pose.render_mujoco import REAL as code
        (code / ".local").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=code / ".local", prefix="robot_pose_qc_") as temp:
            root = Path(temp)
            rows = [{"name": f"test{i}", "split": "train", "pose": kp.rig["home"], "camera": cam.to_json()}
                    for i in range(3)]
            (root / "views.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            result = renderer.write(root / "views.jsonl", root / "dataset")
            t.eq(result["images"], 3, "all input views produce RGB images and labels")
            images = list((root / "dataset/images/train").glob("*.jpg"))
            t.eq(len(images), 3, "actual image files exist")
            values = [float(v) for v in (root / "dataset/labels/train/test0.txt").read_text().split()]
            t.eq(len(values), 5 + 3 * len(kp.names), "YOLO keypoint order and count")
            t.ok(all(0 <= v <= 1 for i, v in enumerate(values) if i < 5 or (i - 5) % 3 != 2),
                 "YOLO coordinates normalised", str(values[:5]))
            t.ok("flip_idx" in (root / "dataset/dataset.yaml").read_text(), "dataset carries left/right flip", "same registry as synth")
            try:
                renderer.write(root / "views.jsonl", root / "dataset")
                t.ok(False, "populated dataset refused", "stale file risk")
            except ValueError:
                t.ok(True, "populated dataset refused", "old images cannot enter new counts")
            draw = renderer.render
            def hidden(pose, camera):
                rgb, uv, vis, depth = draw(pose, camera, False)
                return rgb, uv, np.ones_like(vis), depth
            renderer.render = hidden
            try:
                result = renderer.write(root / "views.jsonl", root / "hidden_dataset")
                t.eq(result["images"], 0, "fully occluded robot cannot be a detector training image")
                t.eq(result["dropped"], 3, "hidden-only views counted as rejected")
            finally:
                renderer.render = draw
    finally:
        renderer.close()
    cad = MujocoPoseRenderer()
    try:
        from tools.robot_pose.render_meshes import CadAppearance
        appearance = CadAppearance(cad.kp)
        if appearance.enabled:
            cam = Camera.orbit(0, 0, 1400, [0, 40, 0], 60, 640, 480)
            image, uv, vis, depth = cad.render(cad.kp.rig["home"], cam, False)
            m, k = cad.scene.model, cad.kp
            t.ok(cad.scene.cad.enabled, "actual private CAD enabled", "no primitive-only substitute")
            for name in ("head", "neck", "chest_front", "base", "L_hand_tip", "R_hand_tip", "L_hand_edge", "R_hand_edge"):
                t.eq(int(vis[k.index[name]]), 0, "CAD absent landmark unlabelled: " + name)
            for name in ("L_shoulder", "R_shoulder", "L_elbow", "R_elbow"):
                t.eq(int(vis[k.index[name]]), 2, "own CAD housing remains visible: " + name)
            line = np.array([float(v) for v in cad.label_line(k.rig["home"], cam, uv, vis).split()])
            bottom = (line[2] + line[4] / 2) * cam.height
            t.ok(bottom >= uv[k.index["base"], 1], "box includes robot post despite unlabelled base", str(bottom))
            t.eq(int(line[7 + 3 * k.index["base"]]), 0, "box anchor is not a floating keypoint label")
            # Compare actual URDF shoulder origins with the shared anchor frame.
            import xml.etree.ElementTree as ET
            from tools.nong_sim.kinematics import quat_rotate
            source = ET.parse(appearance.root.parent / "urdf/nong_description.urdf").getroot()
            support = m.geom("cad_shrug")
            for side in ("L", "R"):
                joint = next(j for j in source.findall("joint") if j.find("child").get("link") == side + "_sh_mid")
                origin = np.fromstring(joint.find("origin").get("xyz"), sep=" ")
                mesh = int(support.dataid[0])
                inverse = m.mesh_quat[mesh].copy()
                inverse[1:] *= -1
                local = quat_rotate(inverse, origin - m.mesh_pos[mesh])
                actual = (quat_rotate(support.quat, local) + support.pos) * 1000
                target = np.asarray(next(b.pos for b in k.tree.bodies if b.name == side + "_anchor"))
                error = np.linalg.norm(actual - target)
                t.ok(error < 5, "CAD collar joins " + side + " shoulder within 5 mm", str(error))
        else:
            t.ok(True, "CAD unavailable: primitive fallback supported", "actual CAD checks run only with private assets")
    finally:
        cad.close()
