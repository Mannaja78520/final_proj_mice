// --- gizmo rings ---
const gizmo = new THREE.Group();
let rings = [];            // [{mesh, joint, localAxis}]
function clearGizmo() {
  rings.forEach(r => r.mesh.parent && r.mesh.parent.remove(r.mesh));
  rings = [];
}
function showGizmo(pairIdx) {
  clearGizmo();
  selPair = pairIdx;
  if (pairIdx < 0) { renderSliders(); return; }
  const pr = PAIRS[pairIdx];
  // rings sit just outside that joint's ball, so a bigger joint gets bigger rings
  const radius = Math.max(24, (RIG.jointR[pairIdx] || 16) * 2.7);
  pr.joints.forEach((jIdx, k) => {
    const axis = RIG.axis[jIdx];
    const color = axis === "x" ? 0xff5555 : (axis === "z" ? 0x55aaff : 0x55ff88);
    const tor = new THREE.Mesh(
      new THREE.TorusGeometry(radius + k * 8, 2.6, 10, 48),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85, depthTest: false }));
    tor.renderOrder = 10;
    // the torus hole-axis is local Z. Point it along the joint's REAL rotation
    // axis = tilt(roll/pitch/yaw) applied to the primary axis, so the ring
    // follows the orientation you set in Rig setup.
    tor.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), jointAxisVec(jIdx));
    tor.userData.joint = jIdx;
    pairRingParents[pairIdx][k].add(tor);
    rings.push({ mesh: tor, joint: jIdx, localAxis: axis });
  });
  renderSliders();
}
