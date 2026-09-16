// --- scene ---
const viewport = $("viewport");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputEncoding = THREE.sRGBEncoding; // painted textures keep their colors
viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim());
const camera = new THREE.PerspectiveCamera(50, 1, 1, 8000);
// A standard view (Front/Top/Left…) is only a true PLANE view in an
// ORTHOGRAPHIC projection. Under perspective the camera merely points at the
// plane: near parts still render bigger and parallel edges converge, so what
// you drag does not match what you see — which is why these never felt flat.
// Perspective stays for the iso/free view, where depth is the point.
const orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, -10000, 20000);
let usingOrtho = false;
function activeCam() { return usingOrtho ? orthoCam : camera; }
// Keep the ortho frustum showing the SAME amount of scene as the perspective
// camera does at its current distance, so switching projection never jumps.
function syncOrtho() {
  const dist = camera.position.distanceTo(controls ? controls.target : new THREE.Vector3()) || 700;
  const h = 2 * dist * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const w = h * (camera.aspect || 1);
  orthoCam.left = -w / 2; orthoCam.right = w / 2;
  orthoCam.top = h / 2;   orthoCam.bottom = -h / 2;
  orthoCam.position.copy(camera.position);
  orthoCam.up.copy(camera.up);
  orthoCam.quaternion.copy(camera.quaternion);
  orthoCam.updateProjectionMatrix();
}
function useProjection(ortho) {
  if (ortho === usingOrtho) { if (ortho) syncOrtho(); return; }
  usingOrtho = ortho;
  if (ortho) syncOrtho();
  else {                              // carry the ortho pose back to perspective
    camera.position.copy(orthoCam.position);
    camera.up.copy(orthoCam.up);
    camera.quaternion.copy(orthoCam.quaternion);
  }
  controls.object = activeCam();      // OrbitControls drives whichever is live
  controls.update();
}
camera.position.set(380, 240, 560);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(0, -20, 0);
controls.enableDamping = true;

// ---- standard views (like a Fusion/SolidWorks view cube) ----
// clicking a view snaps the camera to look straight at that plane AND sets the
// drag plane to match, so Shift+dragging a joint moves it in that flat plane.
const VIEWS = {
  front:  { dir: [0, 0, 1],  up: [0, 1, 0],  plane: "xy" },
  back:   { dir: [0, 0, -1], up: [0, 1, 0],  plane: "xy" },
  right:  { dir: [1, 0, 0],  up: [0, 1, 0],  plane: "yz" },
  left:   { dir: [-1, 0, 0], up: [0, 1, 0],  plane: "yz" },
  top:    { dir: [0, 1, 0],  up: [0, 0, -1], plane: "xz" },
  bottom: { dir: [0, -1, 0], up: [0, 0, 1],  plane: "xz" },
  iso:    { dir: [0.6, 0.42, 0.68], up: [0, 1, 0], plane: "cam" },
};
function setView(name) {
  const v = VIEWS[name];
  if (!v) return;
  const t = controls.target;
  const dist = camera.position.distanceTo(t) || 700;
  const dir = new THREE.Vector3(...v.dir).normalize();
  const p1 = t.clone().add(dir.multiplyScalar(dist));
  // snap the camera to look straight at the plane, then sync OrbitControls so
  // orbiting continues smoothly from here
  camera.up.set(...v.up);
  camera.position.copy(p1);
  camera.lookAt(t);
  // a named plane view is flat (orthographic); iso/free keeps perspective
  useProjection(v.plane !== "cam");
  controls.update();
  // drive the drag plane + its dropdown to match the view
  if ($("dragPlane")) $("dragPlane").value = v.plane;
  document.querySelectorAll("#viewCube button").forEach(b =>
    b.classList.toggle("on", b.dataset.view === name));
}
// the sidebar drag-plane dropdown -> move the camera to a matching view
function viewForPlane(plane) {
  setView({ cam: "iso", xy: "front", yz: "right", xz: "top" }[plane] || "iso");
}

scene.add(new THREE.HemisphereLight(0xbfd4ee, 0x24303e, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(300, 500, 400);
scene.add(sun);

const grid = new THREE.GridHelper(1200, 24, 0x2a3442, 0x1c242f);
grid.position.y = -250;
scene.add(grid);

// materials
const matWrist = new THREE.MeshStandardMaterial({ color: 0x3ecf8e, emissive: 0x0e5c3a, roughness: 0.4 });
// joint balls + bone lines: the skeleton, ALWAYS visible (also under STLs)
// so joint positions and segment lengths stay readable
const matJoint = new THREE.MeshStandardMaterial({ color: 0xffd166, emissive: 0x4d3800, roughness: 0.45 });

// painted textures (PNG/JPG drawn by the user, e.g. a face for the head)
const texLoader = new THREE.TextureLoader();
const texCache = {};
function getTex(file) {
  if (!file) return null;
  if (!texCache[file]) {
    texCache[file] = texLoader.load("/models/" + encodeURIComponent(file));
    texCache[file].encoding = THREE.sRGBEncoding;
  }
  return texCache[file];
}
function partMat(part) {
  const cfg = meshCfg[part] || {};
  const tex = getTex(cfg.tex);
  return new THREE.MeshStandardMaterial({
    color: tex ? "#ffffff" : (cfg.color || "#8a94a6"),
    map: tex || null,
    roughness: 0.65,
  });
}
