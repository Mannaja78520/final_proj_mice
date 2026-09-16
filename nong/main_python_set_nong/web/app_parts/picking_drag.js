// --- picking / drag ---
const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let drag = null; // {kind:'ring'|'ik', ...}

function setMouse(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  ray.setFromCamera(mouse, activeCam());
}
function planeHit(point, normal) {
  const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(normal, point);
  const out = new THREE.Vector3();
  return ray.ray.intersectPlane(plane, out) ? out : null;
}
const AXV = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

const dragNormal = () => {
  const sel = $("dragPlane") ? $("dragPlane").value : "cam";
  return sel === "xy" ? new THREE.Vector3(0, 0, 1) :
         sel === "yz" ? new THREE.Vector3(1, 0, 0) :
         sel === "xz" ? new THREE.Vector3(0, 1, 0) :
         activeCam().getWorldDirection(new THREE.Vector3()).negate();
};

renderer.domElement.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  setMouse(e);

  // RINGS (the colored circles) are always draggable — you already clicked the
  // joint to show them, so grabbing a ring clearly means "rotate this servo".
  // No Shift needed.
  const ringHit = ray.intersectObjects(rings.map(r => r.mesh), false)[0];
  if (ringHit) {
    const r = rings.find(x => x.mesh === ringHit.object);
    // the ring's hole-axis (local Z) points along the tilted joint axis, so
    // its world Z is exactly the axis to rotate about
    const axis = new THREE.Vector3(0, 0, 1)
      .applyQuaternion(r.mesh.getWorldQuaternion(new THREE.Quaternion())).normalize();
    const center = r.mesh.getWorldPosition(new THREE.Vector3());
    const hit = planeHit(center, axis);
    if (!hit) return;
    drag = {
      kind: "ring", joint: r.joint, axis, center,
      ref: hit.clone().sub(center), start: pose[r.joint],
    };
    controls.enabled = false;
    return;
  }

  // The wrist/elbow IK balls need SHIFT held — otherwise a plain left-drag from
  // them orbits the camera (keeps orbiting and big arm moves from fighting).
  if (e.shiftKey) {
    const wristHit = ray.intersectObjects(wristBalls, false)[0];
    if (wristHit) {
      const arm = wristHit.object.userData.arm;
      const wp = wristHit.object.getWorldPosition(new THREE.Vector3());
      drag = { kind: "ik", arm, normal: dragNormal(), planePoint: wp };
      controls.enabled = false;
      return;
    }
    const elbowHit = ray.intersectObjects(elbowBalls, false)[0];
    if (elbowHit) {
      const arm = elbowHit.object.userData.arm;
      const ep = elbowHit.object.getWorldPosition(new THREE.Vector3());
      drag = { kind: "ikElbow", arm, normal: dragNormal(), planePoint: ep };
      controls.enabled = false;
      return;
    }
  }

  // plain click (no shift): select a joint's rings, or deselect on empty.
  // A plain drag from here just orbits (OrbitControls stays enabled).
  const meshHit = ray.intersectObjects(pickMeshes, true)[0];
  if (meshHit) { // clicking the same part again DESELECTS (rings disappear)
    const p = meshHit.object.userData.pair;
    showGizmo(p === selPair ? -1 : p);
    return;
  }
  bgDown = { x: e.clientX, y: e.clientY };
});

let bgDown = null;
renderer.domElement.addEventListener("pointerup", (e) => {
  if (bgDown && Math.hypot(e.clientX - bgDown.x, e.clientY - bgDown.y) < 6)
    showGizmo(-1);
  bgDown = null;
});
window.addEventListener("keydown", (e) => { if (e.key === "Escape") showGizmo(-1); });
renderer.domElement.addEventListener("dblclick", () => showGizmo(-1));

window.addEventListener("pointermove", (e) => {
  if (!drag) return;
  setMouse(e);

  if (drag.kind === "ring") {
    const hit = planeHit(drag.center, drag.axis);
    if (!hit) return;
    const v = hit.clone().sub(drag.center);
    const ang = Math.atan2(drag.axis.dot(new THREE.Vector3().crossVectors(drag.ref, v)),
                           drag.ref.dot(v));
    const j = drag.joint;
    // dragging turns the joint directly (joint degrees; gear is on the robot)
    pose[j] = clampJ(j, drag.start + jdir(j) * THREE.MathUtils.radToDeg(ang));
    poseChanged(true);
  } else if (drag.kind === "ik") {
    const target = planeHit(drag.planePoint, drag.normal);
    // strong IK per frame so the whole arm (shoulder + elbow together)
    // follows the wrist to wherever it can reach within the joint limits
    if (target) { solveIK(drag.arm, target, 16); poseChanged(true); }
  } else if (drag.kind === "ikElbow") {
    const target = planeHit(drag.planePoint, drag.normal);
    // move the elbow by rotating only the 2 shoulder servos
    if (target) { solveElbowIK(drag.arm, target); poseChanged(true); }
  }
});
window.addEventListener("pointerup", () => {
  if (drag) { drag = null; controls.enabled = true; poseChanged(false); }
});

function clampDeg(v) { return Math.min(180, Math.max(0, Math.round(v * 10) / 10)); }
