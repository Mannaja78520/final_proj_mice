// --- distances in the 3D view (A26-44) ---
//
// User 2026-09-17: *see the distance between the point that i need to know in
// robot ... elbow and hand or elbow -> elbow ... hold that key or can click*.
// Click Distances (or hold D) to see dashed lines with the length in mm. The
// pairs are DATA in distances.json: a new pair is an entry there, not code.
let distPairs = null;        // null = not read yet, [] = none listed
let distOn = false;          // switched on by the button
let distHeld = false;        // on while D is held
let distLines = [];
const distLayer = document.createElement("div");
distLayer.id = "distLayer";
distLayer.hidden = true;
viewport.appendChild(distLayer);

function distPoint(name) {   // world position of a named point, or null
  const m = /^([LR])_(elbow|hand)$/.exec(name || "");
  if (!m) return null;
  const arm = m[1] === "L" ? 0 : 1;   // arm 0 is the robot's left (+X), see buildArm
  const ball = (m[2] === "elbow" ? elbowBalls : wristBalls)[arm];
  return ball ? ball.getWorldPosition(new THREE.Vector3()) : null;
}
async function distLoad() {
  if (distPairs) return;
  try {
    const j = await fetch("distances.json").then(r => r.json());
    distPairs = (j.pairs || []).filter(p => p && p.from && p.to);
  } catch (e) {
    distPairs = [];
    distLayer.dataset.note = "the list of distances (distances.json) could not be read";
  }
}
function distShown() { return distOn || distHeld; }
function distSet(on) {
  distOn = on;
  const b = $("distBtn");
  if (b) { b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); }
  distLoad().then(distDraw);
}
function distClear() {
  distLines.forEach(l => { scene.remove(l); l.geometry.dispose(); l.material.dispose(); });
  distLines = [];
  distLayer.textContent = "";
}
// Called every frame from tick(); does nothing while switched off.
function distDraw() {
  if (!distShown() || !distPairs) {
    if (distLines.length || !distLayer.hidden) { distClear(); distLayer.hidden = true; }
    return;
  }
  distClear();
  distLayer.hidden = false;
  scene.updateMatrixWorld();
  const cam = activeCam(), rect = renderer.domElement.getBoundingClientRect();
  const color = getComputedStyle(document.documentElement).getPropertyValue("--acc").trim() || "#4ea1ff";
  let drawn = 0;
  distPairs.forEach(p => {
    const a = distPoint(p.from), b = distPoint(p.to);
    if (!a || !b) return;
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    const line = new THREE.Line(g, new THREE.LineDashedMaterial(
      { color: new THREE.Color(color), dashSize: 8, gapSize: 6, depthTest: false }));
    line.computeLineDistances();
    line.renderOrder = 30;
    scene.add(line);
    distLines.push(line);
    const mid = a.clone().add(b).multiplyScalar(0.5).project(cam);
    if (mid.z > 1) return;                      // behind the camera
    const tag = document.createElement("span");
    tag.className = "distTag";
    tag.textContent = Math.round(a.distanceTo(b)) + " mm";
    tag.title = p.label || (p.from + " to " + p.to);
    tag.style.left = ((mid.x + 1) / 2 * rect.width) + "px";
    tag.style.top = ((1 - mid.y) / 2 * rect.height) + "px";
    distLayer.appendChild(tag);
    drawn++;
  });
  if (!drawn) {
    const n = document.createElement("span");
    n.className = "distNote";
    n.textContent = distLayer.dataset.note || "no distances to show — the robot model is not built yet";
    distLayer.appendChild(n);
  }
}
window.addEventListener("keydown", (e) => {
  if (e.key !== "d" && e.key !== "D") return;
  const t = e.target;
  if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;  // typing a "d"
  if (!distHeld) { distHeld = true; distLoad().then(distDraw); }
});
window.addEventListener("keyup", (e) => { if (e.key === "d" || e.key === "D") distHeld = false; });
window.addEventListener("blur", () => { distHeld = false; });
