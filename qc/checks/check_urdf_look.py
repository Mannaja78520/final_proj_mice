"""The robot look: simple shapes or the CAD model (URDF), same motion (A48-1).

User 2026-10-23: "เพิ่มตัวเลือก Nong Studio แบบเดิม/URDF โดย URDF ใช้ขนาดจริงจาก
ไฟล์ ตอนกลับแบบเดิมให้ถามว่าจะใช้ขนาด URDF หรือปรับเอง ... ทดสอบตาม video,
realtime, playback และ monitor ว่าซ้าย-ขวา ทิศยกมือ และทุก joint ตรงกับ URDF จริง".

The trap: drawing CAD parts over the old pivots looks right in a still picture
and is wrong the moment an arm moves (the importer of A31-7 did that). So the
URDF tree IS the robot while it is shown (urdf_view.js) and this check proves
the motion, not the picture:

- A fixture URDF is written HERE, in Python, from the same rig the page is
  given: every link frame turned by a random rpy, two joint axes written
  backwards, the forearm meshes placed through a visual origin, sizes in
  metres. Read correctly, it is the old robot in disguise, so for random
  poses every shoulder, elbow and hand must land where the simple shapes put
  them (independent maths: python rpy/frames here vs three.js there). Left
  and right have different arm lengths, so a swapped side cannot pass.
- each joint alone, the left hand raised (IK), a video fit (arm up), the
  dummy's realtime pose, a timeline scrub (playback) and the module's
  reported pose (monitor) are all checked on the URDF and then on the shapes.
- the look never changes what is sent: playback keys and the YAML are the
  same in both looks, and the monitor shows the module's own joint values.
- going back asks: CAD sizes / my own sizes / stay; your own sizes survive a
  round trip through the CAD look and are saved.
- a missing file or a file whose parts form a loop says so in plain words and
  keeps the simple shapes; a missing mesh is named, the rest still shown.

MICE_URDF_MODEL=<package folder> (the PC's real SolidWorks export, never
committed) also loads that model and reports every joint binding, its sense
and how each joint moves a hand against the shapes.
"""
import json
import math
import os
import random
import shutil
import struct
import tempfile
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "robot look: CAD model (URDF) moves exactly like the simple shapes in video, realtime, playback and monitor"
SLOW = True

# the rig the page is given (Studio mm); left/right differ on purpose
DIMS = {"shoulderX": 120, "shoulderY": 110, "upperLenL": 115, "upperLenR": 104,
        "foreLenL": 131, "foreLenR": 122, "torsoW": 100, "torsoH": 250, "torsoD": 70,
        "shrugPivot": 60}
AXIS = ["x", "z", "x", "z", "x", "z", "x", "z", "y", "x"]
FLIP = {"L_EL_R", "R_SH_P"}          # written backwards in the file
MON_POSE = [100, 80, 110, 95, 70, 100, 85, 105, 96, 92]

V = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


def ros(v):                      # Studio (X left, Y up, Z front) -> ROS
    return (v[2], v[0], v[1])


def rpy_mat(r, p, y):            # URDF fixed-axis rpy = Rz(y) Ry(p) Rx(r)
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def mat_rpy(m):
    p = math.asin(max(-1.0, min(1.0, -m[2][0])))
    return (math.atan2(m[2][1], m[2][2]), p, math.atan2(m[1][0], m[0][0]))


def tr(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def app(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"qc".ljust(80, b" ") + struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<12fH", 0, 0, 0, *t[0], *t[1], *t[2], 0))


def box_tris(lo, hi):
    c = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    out = []
    for a, b, cc, d in faces:
        out += [(c[a], c[b], c[cc]), (c[a], c[cc], c[d])]
    return out


def write_fixture(root):
    """The old robot (rig above) written as a URDF with turned frames."""
    rnd = random.Random(48)
    d = DIMS
    m = 0.001                                  # mm -> m
    # joints in the WORLD at the zero pose, Studio mm (the simple shapes)
    J = {"waist": ("base_link", "waist_link", (0, 0, 0), "y"),
         "shrug": ("waist_link", "shrug_link", (0, d["shoulderY"] + d["shrugPivot"], 0), "z")}
    for s, sx, up, fo in (("L", 1, d["upperLenL"], d["foreLenL"]), ("R", -1, d["upperLenR"], d["foreLenR"])):
        b = 0 if s == "L" else 4
        sh = (sx * d["shoulderX"], d["shoulderY"], 0)
        el = (sh[0], sh[1] - up, 0)
        J[s + "_SH_P"] = ("shrug_link", s + "_sh_mid", sh, AXIS[b])
        J[s + "_SH_R"] = (s + "_sh_mid", s + "_upper_link", sh, AXIS[b + 1])
        J[s + "_EL_P"] = (s + "_upper_link", s + "_el_mid", el, AXIS[b + 2])
        J[s + "_EL_R"] = (s + "_el_mid", s + "_fore_link", el, AXIS[b + 3])
    links = ["base_link", "waist_link", "shrug_link", "head_link"] + \
            [s + n for s in "LR" for n in ("_sh_mid", "_upper_link", "_el_mid", "_fore_link")]
    Q = {n: rpy_mat(rnd.uniform(-3, 3), rnd.uniform(-1.2, 1.2), rnd.uniform(-3, 3)) for n in links}
    Q["base_link"] = rpy_mat(0, 0, 0)          # the file's base IS its world
    O = {"base_link": (3, -170, -4)}           # the base sits below and aside
    for n, (p, c, at, ax) in J.items():
        O[c] = at
    J["head"] = ("shrug_link", "head_link", (0, d["shoulderY"] + d["shrugPivot"] + 40, 0), None)
    O["head_link"] = J["head"][2]
    vis = {}
    for s in "LR":
        el = O[s + "_el_mid"]
        fo = d["foreLen" + s]
        lo, hi = (el[0] - 9, el[1] - fo, -9), (el[0] + 9, el[1], 9)
        corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        # the mesh goes through a visual origin, in METRES like a SolidWorks export
        vq = rpy_mat(0.3, -0.7, 1.1)
        vxyz = (0.004, -0.002, 0.01)
        link = s + "_fore_link"
        to_link = lambda w: app(tr(Q[link]), ros(sub(w, O[link])))
        to_vis = lambda w: app(tr(vq), sub(tuple(x * m for x in to_link(w)), vxyz))
        tris = [tuple(to_vis(p) for p in t) for t in box_tris(lo, hi)]
        assert len(corners) == 8
        stl(root / "meshes" / (s + "_fore.STL"), tris)
        vis[link] = ('<visual><origin xyz="%g %g %g" rpy="%.9g %.9g %.9g"/><geometry>'
                     '<mesh filename="package://qc_bot/meshes/%s_fore.STL"/></geometry></visual>'
                     % (vxyz + mat_rpy(vq) + (s,)))
    vis["head_link"] = ('<visual><geometry><mesh filename="package://qc_bot/meshes/head_gone.STL"/>'
                        '</geometry></visual>')
    vis["base_link"] = '<visual><geometry><box size="0.06 0.05 0.2"/></geometry></visual>'
    out = ['<?xml version="1.0"?>', '<robot name="qc_bot">']
    out += ['<link name="%s">%s</link>' % (n, vis.get(n, "")) for n in links]
    for n, (p, c, at, ax) in J.items():
        rel = mul(tr(Q[p]), Q[c])
        xyz = tuple(x * m for x in app(tr(Q[p]), ros(sub(at, O[p]))))
        out.append('<joint name="%s" type="%s"><parent link="%s"/><child link="%s"/>'
                   '<origin xyz="%.9g %.9g %.9g" rpy="%.9g %.9g %.9g"/>' %
                   ((n, "fixed" if ax is None else "revolute", p, c) + xyz + mat_rpy(rel)))
        if ax:
            a = app(tr(Q[c]), ros(V[ax]))
            if n in FLIP:
                a = tuple(-x for x in a)
            out.append('<axis xyz="%.9g %.9g %.9g"/><limit lower="-2" upper="2" effort="1" velocity="1"/>' % a)
        out.append("</joint>")
    out.append("</robot>")
    (root / "urdf" / "qc_bot.urdf").write_text("\n".join(out), encoding="utf-8")
    # a file whose parts hang in a loop
    (root / "urdf" / "loop.urdf").write_text(
        '<robot name="loop"><link name="a"/><link name="b"/>'
        '<joint name="j1" type="revolute"><parent link="a"/><child link="b"/></joint>'
        '<joint name="j2" type="revolute"><parent link="b"/><child link="a"/></joint></robot>',
        encoding="utf-8")


DRIVER = r"""
function report(s){ qcMark("ULOOK~" + s); }
function W(o){ return o.getWorldPosition(new THREE.Vector3()); }
function pts(p){
  pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
  // + a point 100 mm out of each palm: the hand's facing must agree too
  return [W(jointGroups[0].parent), W(jointGroups[4].parent), W(elbowBalls[0]), W(elbowBalls[1]),
          W(wristBalls[0]), W(wristBalls[1]),
          palmMarks[0].localToWorld(new THREE.Vector3(0, -30, 100)), palmMarks[1].localToWorld(new THREE.Vector3(0, -30, 100))];
}
function worst(A, B){ var w = 0; A.forEach(function(a, i){ a.forEach(function(v, k){ w = Math.max(w, v.distanceTo(B[i][k])); }); }); return w; }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function until(f, ms){ var t = performance.now(); while (!f() && performance.now() - t < ms) await sleep(50); return f(); }
function f1(v){ return Math.round(v * 10) / 10; }
var CFG = __CFG__;
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof setLook === "function" && URDF_CFG && palmMarks.length === 2
           && document.getElementById("lookSel") && typeof haveRobot === "function" && haveRobot();
  }, 20000).then(async function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try {
    var r = {};
    RIG = mergeRig({ dims: CFG.dims, axis: CFG.axis, tilt: CFG.axis.map(function(){ return [0,0,0]; }),
                     invert: new Array(10).fill(0), zero: new Array(10).fill(90), shrugCurve: [],
                     view: { look: "rig", model: CFG.model, sizes: "custom", custom: null, urdfDims: null } });
    saveRig(); buildRobot();
    var seed = 9; function rnd(){ seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    var poses = [];
    for (var n = 0; n < 14; n++) poses.push(RIG.min.map(function(lo, i){ return Math.round(lo + (RIG.max[i] - lo) * rnd()); }));
    var iso = [];
    for (var i = 0; i < 10; i++) { var q = RIG.zero.slice(); q[i] += i === 9 ? 10 : 25; iso.push(q); }
    var rigP = poses.map(pts), rigIso = iso.map(pts), rigZero = pts(RIG.zero);
    keys = [{ pose: poses[0].slice(), t: 1000, hold: 0 }, { pose: poses[1].slice(), t: 1000, hold: 0 }];
    bumpKeys();
    var yamlRig = buildYaml().yaml, keysRig = JSON.stringify(playKeys());
    // the user's own sizes, different from the file's
    RIG.dims.upperLenL = 99; RIG.dims.foreLenL = 88; rigChanged();

    // ---- into the CAD look
    await setLook("urdf");
    await until(function(){ return urdfOn && urdfTip.L && urdfTip.L.fromMesh && urdfTip.R.fromMesh; }, 15000);
    r.on = urdfOn; r.fromMesh = !!(urdfTip.L && urdfTip.L.fromMesh && urdfTip.R.fromMesh);
    r.signs = urdfJ.map(function(b){ return b ? b.sign : 0; }).join("_");
    r.names = urdfJ.map(function(b){ return b ? b.name : "-"; }).join(",");
    r.dimsUrdf = ["upperLenL", "upperLenR", "foreLenL", "foreLenR", "shoulderX"].map(function(k){ return f1(RIG.dims[k]); }).join("_");
    r.custom = RIG.view.custom ? RIG.view.custom.upperLenL + "_" + RIG.view.custom.foreLenL : "none";
    r.links = 0; robot.traverse(function(o){ if (o.isMesh && o.userData.urdfLink) r.links++; });
    r.stat = $("lookStat").textContent.replace(/[~ ]/g, "_");
    r.poseErr = f1(worst(poses.map(pts), rigP));
    r.isoErr = iso.map(function(q, i){ return f1(worst([pts(q)], [rigIso[i]])); }).join("_");
    r.zeroErr = f1(worst([pts(RIG.zero)], [rigZero]));
    // left hand raised by IK: the robot's left is +X, up is +Y
    pose = RIG.zero.slice(); applyPose(); var sh = pts(RIG.zero)[0], rw0 = pts(RIG.zero)[5];
    solveIK(0, sh.clone().add(new THREE.Vector3(30, 150, 40)), 40);
    var up = pts(pose); r.raise = f1(up[4].y - sh.y) + "_" + f1(up[4].x) + "_" + f1(up[5].distanceTo(rw0));
    var ikPose = pose.slice();
    // video: the person's left arm straight up, right arm out to their side
    pose = RIG.zero.slice(); applyPose();
    vidFitArm(0, { upper: new THREE.Vector3(0, 1, 0), fore: new THREE.Vector3(0, 1, 0) }, true);
    vidFitArm(1, { upper: new THREE.Vector3(-1, 0, 0), fore: new THREE.Vector3(-1, 0, 0) }, true);
    var vidPose = pose.slice(), vp = pts(vidPose);
    r.video = f1(vp[4].y - vp[0].y) + "_" + f1(vp[5].x - vp[1].x);
    // realtime: the dummy's pose
    var dum = [120, 70, 100, 110, 60, 95, 120, 80, 100, 95];
    dummyApply(dum); r.dummy = pose.join("_") === dum.join("_");
    var dumPts = pts(pose);
    // playback: a scrub half way between two keys
    scrubTo(750);
    var playPose = pose.slice(), playPts = pts(playPose);
    r.keysUrdf = JSON.stringify(playKeys()) === keysRig;
    // monitor: the module's own reported joints
    await monitorTick();
    var monPose = pose.slice(); r.monitor = monPose.map(f1).join("_");
    var monPts = pts(monPose);
    var yu = buildYaml().yaml;
    r.yamlSame = yu === yamlRig;
    if (!r.yamlSame) { var A = yamlRig.split("\n"), B = yu.split("\n"); for (var li = 0; li < A.length; li++) if (A[li] !== B[li]) { r.yamlDiff = (A[li] + " | " + B[li]).replace(/[~]/g, "_"); break; } }

    // ---- back: the question
    var p1 = setLook("rig"); await sleep(150);
    r.asked = $("lookAsk").open === true;
    r.askText = $("lookAskMine").textContent.replace(/[~ ]/g, "_");
    $("lookStay").click(); await p1;
    r.stay = urdfOn && $("lookSel").value === "urdf";
    var p2 = setLook("rig"); await sleep(150); $("lookUseMine").click(); await p2;
    r.mine = !urdfOn + "_" + RIG.dims.upperLenL + "_" + RIG.dims.foreLenL + "_" + RIG.view.sizes;
    // the same poses on the simple shapes (at the fixture's sizes again)
    Object.assign(RIG.dims, CFG.dims); rigChanged();
    r.pathErr = [worst([pts(vidPose)], [vp]), worst([pts(dum)], [dumPts]), worst([pts(playPose)], [playPts]),
                 worst([pts(monPose)], [monPts]), worst([pts(ikPose)], [up])].map(f1).join("_");
    r.keysSame = JSON.stringify(playKeys()) === keysRig;
    RIG.dims.upperLenL = 99; RIG.dims.foreLenL = 88; rigChanged();
    await setLook("urdf"); await until(function(){ return urdfOn; }, 5000);
    var p3 = setLook("rig"); await sleep(150); $("lookUseUrdf").click(); await p3;
    r.useUrdf = !urdfOn + "_" + f1(RIG.dims.upperLenL) + "_" + f1(RIG.dims.foreLenL) + "_" + RIG.view.sizes;
    await setLook("urdf"); await until(function(){ return urdfOn; }, 5000);
    var saved = mergeRig(JSON.parse(localStorage.getItem("nong_rig")));
    var sc = saved.view.custom || {}; r.kept = saved.view.look + "_" + sc.upperLenL + "_" + sc.foreLenL;
    // ---- a missing mesh, a missing file, a loop
    r.meshWarn = urdfLast.warn.join("|").indexOf("head_gone.STL") >= 0;
    await urdfPickModel("qc_bot/urdf/nothing.urdf");
    r.missing = (urdfOn && RIG.view.model === CFG.model) + "_" + $("lookStat").textContent.replace(/[~ ]/g, "_");
    // a saved look whose file is broken (a project from another PC): shapes + why
    RIG.view.model = "qc_bot/urdf/loop.urdf"; rigChanged();
    await until(function(){ return !!urdfLast.error; }, 5000);
    r.loop = !urdfOn + "_" + $("lookStat").textContent.replace(/[~ ]/g, "_");
    report("res=" + JSON.stringify(r));

    if (CFG.real) {
      // the PC's real model: bindings, senses, and each joint against the shapes
      RIG.view.look = "rig"; RIG.view.model = CFG.real; urdfLast.error = ""; rigChanged();
      var base = iso.map(pts), z0 = pts(RIG.zero);
      await setLook("urdf"); await until(function(){ return urdfOn && urdfTip.L.fromMesh; }, 30000);
      var Z = pts(RIG.zero), rr = { on: urdfOn, error: urdfLast.error, warn: urdfLast.warn,
        bind: urdfJ.map(function(b, i){ return JOINT_NAMES[i] + "=" + (b ? b.name + (b.sign < 0 ? "(-)" : "") + " axis " + b.quality.toFixed(2) : "none"); }),
        sizes: urdfLast.dims, agree: [] };
      iso.forEach(function(q, i){
        var P = pts(q), arm = i < 4 ? 0 : 1, k = i < 8 ? 4 + arm : 4;
        var a = P[k].clone().sub(Z[k]), b = base[i][k].clone().sub(z0[k]);
        rr.agree.push(JOINT_NAMES[i] + "=" + (a.length() < 1 || b.length() < 1 ? "still" : (a.normalize().dot(b.normalize())).toFixed(2)));
      });
      report("real=" + JSON.stringify(rr));
    }
    setTimeout(function(){ report("done"); }, 200);
  } catch(e) { report("ERR-" + String(e && e.stack || e).slice(0, 160).replace(/~/g, "_")); report("done"); }
}); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    models = Path(tempfile.mkdtemp(prefix="mice_qc_models_"))
    try:
        pkg = models / "qc_bot"
        (pkg / "urdf").mkdir(parents=True)
        (pkg / "meshes").mkdir()
        write_fixture(pkg)
        real = os.environ.get("MICE_URDF_MODEL", "")
        real_rel = ""
        if real and Path(real).is_dir():
            shutil.copytree(real, models / Path(real).name)
            urdfs = sorted((models / Path(real).name).rglob("*.urdf"))
            real_rel = urdfs[0].relative_to(models).as_posix() if urdfs else ""
        base, main = F.start_hub()
        main.MODELS = models
        fake_serial.NONG.joints = [float(v) for v in MON_POSE]
        cfg = {"dims": DIMS, "axis": AXIS, "model": "qc_bot/urdf/qc_bot.urdf", "real": real_rel}
        browser.page(DRIVER.replace("__CFG__", json.dumps(cfg)),
                     query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT),
                     seconds=120)
    finally:
        shutil.rmtree(models, ignore_errors=True)
    marks = [m[6:] for m in fake_serial.qc_marks if m.startswith("ULOOK~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("res=")), "")
    if not t.ok(got, "the driver measured both looks", marks):
        return
    r = json.loads(got[4:])

    t.ok(r["on"] and r["links"] >= 3, "the CAD look draws the URDF's own parts (%s meshes)" % r["links"], r)
    t.ok(r["names"] == "L_SH_P,L_SH_R,L_EL_P,L_EL_R,R_SH_P,R_SH_R,R_EL_P,R_EL_R,waist,shrug",
         "every Studio joint is bound to its URDF joint by name", r["names"])
    signs = r["signs"].split("_")
    t.ok(signs == ["1", "1", "1", "-1", "-1", "1", "1", "1", "1", "1"],
         "joints written backwards in the file are turned the other way (auto sense)", r["signs"])
    t.ok(float(r["zeroErr"]) < 0.6, "at zero every shoulder, elbow and hand is where the shapes have it (%s mm)" % r["zeroErr"], r)
    t.ok(float(r["poseErr"]) < 0.6,
         "14 random poses: every shoulder, elbow and hand lands on the shapes' (worst %s mm)" % r["poseErr"], r)
    t.ok(all(float(x) < 0.6 for x in r["isoErr"].split("_")),
         "each of the 10 joints alone moves the arm exactly like the shapes", r["isoErr"])
    t.ok(r["fromMesh"] and r["dimsUrdf"] == "115_104_131_122_120",
         "the CAD look uses the file's own sizes, forearm tips from the meshes", r["dimsUrdf"])
    h, x, other = (float(v) for v in r["raise"].split("_"))
    t.ok(h > 50 and x > 0 and other < 0.5,
         "raising the LEFT hand lifts the hand on the robot's left (+X), the right one stays", r["raise"])
    vh, vx = (float(v) for v in r["video"].split("_"))
    t.ok(vh > 50 and vx < -100,
         "video: the person's left arm up raises the robot's left hand, their right arm out goes to the robot's right", r["video"])
    t.ok(r["dummy"], "realtime: the dummy's pose is the pose shown", r)
    t.ok(r["monitor"] == "_".join(str(float(v)).rstrip("0").rstrip(".") for v in MON_POSE)
         or [float(v) for v in r["monitor"].split("_")] == [float(v) for v in MON_POSE],
         "monitor: the module's reported joints are shown on the CAD model", r["monitor"])
    errs = [float(v) for v in r["pathErr"].split("_")]
    t.ok(all(e < 0.6 for e in errs),
         "video, realtime, playback, monitor and the raised hand: the CAD model and the shapes agree (%s mm)" % r["pathErr"], r)
    t.ok(r["yamlSame"] and r["keysSame"] and r["keysUrdf"], "the look never changes what is sent (keys and YAML identical)", r)
    t.ok(r["asked"], "going back to the shapes asks which sizes", r)
    t.ok("99" in r["askText"], "and shows your own sizes in the question", r["askText"])
    t.ok(r["stay"], "'Stay on the CAD model' keeps it", r)
    t.ok(r["mine"] == "true_99_88_custom", "'Use my own sizes' brings back your sizes", r["mine"])
    t.ok(r["useUrdf"] == "true_115_131_urdf", "'Use the CAD model's sizes' takes the file's", r["useUrdf"])
    t.ok(r["custom"] == "99_88" and r["kept"] == "urdf_99_88",
         "your own sizes are kept (not overwritten by the CAD sizes) and saved", r)
    t.ok(r["meshWarn"], "a missing mesh is named, the rest still shown", r)
    t.ok(r["missing"].startswith("true_") and "Cannot_open" in r["missing"],
         "picking a missing file says so and keeps the model shown", r["missing"])
    t.ok(r["loop"].startswith("true_") and "Cannot_show" in r["loop"] and "loop" in r["loop"],
         "a saved look whose file forms a loop says so and shows the simple shapes", r["loop"])

    real = next((m for m in marks if m.startswith("real=")), "")
    if real:
        rr = json.loads(real[5:])
        t.ok(rr["on"] and not rr["error"], "the real model opens (%s)" % "; ".join(rr["bind"]), rr)
        t.ok(all(a.split("=")[1] == "still" or float(a.split("=")[1]) > 0.5 for a in rr["agree"][:8]),
             "the real model: each arm joint moves its hand the way the shapes do (%s)" % ", ".join(rr["agree"]), rr)
