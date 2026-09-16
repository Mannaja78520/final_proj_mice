// --- STL meshes ---
// Each part keeps its SKELETON (joint ball + bone) visible even with an STL,
// so joint positions and lengths always stay readable. Every STL has its own
// rotation / offset / scale (exports rarely share the robot's origin), and
// assigning an STL measures its size to set the rig lengths automatically.
const stlLoader = new THREE.STLLoader();
const stlCache = {};   // file -> BufferGeometry
let meshGen = 0;       // invalidates async STL loads after a rebuild
const PART_PAIR = { L_upper: 0, L_fore: 1, R_upper: 2, R_fore: 3 };

function getGeo(file, cb) {
  if (stlCache[file]) { cb(stlCache[file]); return; }
  stlLoader.load("/models/" + encodeURIComponent(file),
    (geo) => { stlCache[file] = geo; cb(geo); },
    undefined,
    () => { $("tlStat").textContent = "cannot load models/" + file; notice($("tlStat").textContent); });
}
// STL files carry no texture coordinates — project simple UVs from the two
// largest bounding-box axes so a painted PNG/JPG can be shown on them
function ensureUVs(geo) {
  if (geo.attributes.uv) return geo;
  geo.computeBoundingBox();
  const bb = geo.boundingBox, size = new THREE.Vector3();
  bb.getSize(size);
  const comps = ["x", "y", "z"].sort((a, b) => size[b] - size[a]); // widest first
  const [ua, va] = comps;
  const pos = geo.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  const get = { x: (i) => pos.getX(i), y: (i) => pos.getY(i), z: (i) => pos.getZ(i) };
  for (let i = 0; i < pos.count; i++) {
    uv[i * 2] = (get[ua](i) - bb.min[ua]) / (size[ua] || 1);
    uv[i * 2 + 1] = (get[va](i) - bb.min[va]) / (size[va] || 1);
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  return geo;
}
function cfgMesh(geo, cfg, part) {
  const tex = getTex(cfg.tex);
  if (tex) ensureUVs(geo);
  const mat = new THREE.MeshStandardMaterial({
    color: tex ? "#ffffff" : (cfg.color || "#8a94a6"),
    map: tex || null,
    roughness: 0.65,
  });
  const m = new THREE.Mesh(geo, mat);
  const r = cfg.rot || [0, 0, 0], o = cfg.off || [0, 0, 0];
  m.rotation.set(THREE.MathUtils.degToRad(+r[0] || 0),
                 THREE.MathUtils.degToRad(+r[1] || 0),
                 THREE.MathUtils.degToRad(+r[2] || 0));
  m.position.set(+o[0] || 0, +o[1] || 0, +o[2] || 0);
  m.scale.setScalar(+cfg.scale || 1);
  const pair = PART_PAIR[part];
  if (pair !== undefined) { m.userData.pair = pair; pickMeshes.push(m); }
  return m;
}
function applyMeshes() {
  const gen = ++meshGen;
  MESH_PARTS.forEach(part => {
    const cfg = meshCfg[part];
    const holder = linkHolders[part];
    if (!holder) return;
    // default shape: hide the "flesh" when an STL is assigned — the skeleton
    // (userData.skel) is never hidden
    holder.children[0].traverse(o => {
      if (o.isMesh && !o.userData.skel) o.visible = !cfg.file;
    });
    while (holder.children.length > 1) holder.remove(holder.children[holder.children.length - 1]);
    if (cfg.file) getGeo(cfg.file, geo => {
      if (gen !== meshGen || linkHolders[part] !== holder) return;
      holder.add(cfgMesh(geo, cfg, part));
    });
  });
  addons.forEach(ad => { // clothes & extra parts: layered on top, never replace
    const holder = linkHolders[ad.part];
    if (!holder || !ad.file) return;
    getGeo(ad.file, geo => {
      if (gen !== meshGen || linkHolders[ad.part] !== holder) return;
      holder.add(cfgMesh(geo, ad, ad.part));
    });
  });
}

// measure the (rotated, scaled) STL and take the rig lengths from it — the
// STL brings its own real dimensions, the rig follows them
function measureFromStl(part) {
  const cfg = meshCfg[part];
  if (!cfg.file) return;
  getGeo(cfg.file, geo => {
    const g = geo.clone();
    const r = cfg.rot || [0, 0, 0];
    g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(
      THREE.MathUtils.degToRad(+r[0] || 0),
      THREE.MathUtils.degToRad(+r[1] || 0),
      THREE.MathUtils.degToRad(+r[2] || 0))));
    g.computeBoundingBox();
    const size = new THREE.Vector3();
    g.boundingBox.getSize(size);
    size.multiplyScalar(+cfg.scale || 1);
    g.dispose();
    let msg = "";
    const rd = (v) => Math.max(5, Math.round(v));
    if (part === "L_upper") {           // left/right lengths stay independent
      RIG.dims.upperLenL = rd(size.y);
      msg = "LEFT upper arm length = " + RIG.dims.upperLenL + " mm (from the STL)";
    } else if (part === "R_upper") {
      RIG.dims.upperLenR = rd(size.y);
      msg = "RIGHT upper arm length = " + RIG.dims.upperLenR + " mm (from the STL)";
    } else if (part === "L_fore") {
      RIG.dims.foreLenL = rd(size.y);
      msg = "LEFT forearm length = " + RIG.dims.foreLenL + " mm (from the STL)";
    } else if (part === "R_fore") {
      RIG.dims.foreLenR = rd(size.y);
      msg = "RIGHT forearm length = " + RIG.dims.foreLenR + " mm (from the STL)";
    } else if (part === "torso") {
      RIG.dims.torsoW = rd(size.x); RIG.dims.torsoH = rd(size.y); RIG.dims.torsoD = rd(size.z);
      msg = `torso from the STL: ${RIG.dims.torsoW}×${RIG.dims.torsoH}×${RIG.dims.torsoD} mm`;
    }
    saveRig();
    renderRigUI();
    buildRobot();
    if (msg) $("tlStat").textContent = msg + " — fine-tune in Rig setup if needed";
  });
}

// back to (built-in): that part's rig lengths return to the defaults
function revertDims(part) {
  const D = DEFAULT_RIG.dims;
  if (part === "L_upper") RIG.dims.upperLenL = D.upperLenL;
  else if (part === "R_upper") RIG.dims.upperLenR = D.upperLenR;
  else if (part === "L_fore") RIG.dims.foreLenL = D.foreLenL;
  else if (part === "R_fore") RIG.dims.foreLenR = D.foreLenR;
  else if (part === "torso") {
    RIG.dims.torsoW = D.torsoW; RIG.dims.torsoH = D.torsoH; RIG.dims.torsoD = D.torsoD;
  } else return;
  saveRig();
  renderRigUI();
}

// ---- Model card UI: per-part file/color + rotation/offset/scale, addons ----
// one labelled block per transform:  rotate: / roll pitch yaw,  offset: /
// x y z,  scale: / scale — each on its own line so nothing overlaps
function vecBlock(cfg, key, title, subLabels, step, onchange) {
  const wrap = document.createElement("div");
  wrap.className = "tblock";
  const head = document.createElement("div");
  head.className = "tlabel";
  head.textContent = title + ":";
  wrap.appendChild(head);
  const row = document.createElement("div");
  row.className = "trow";
  for (let i = 0; i < 3; i++) {
    const cell = document.createElement("label");
    cell.className = "tcell";
    const inp = document.createElement("input");
    inp.type = "number"; inp.step = step;
    inp.value = (cfg[key] || [0, 0, 0])[i];
    inp.onchange = () => {
      if (!cfg[key]) cfg[key] = [0, 0, 0];
      cfg[key][i] = +inp.value || 0;
      onchange();
    };
    cell.append(inp, document.createTextNode(subLabels[i]));
    row.appendChild(cell);
  }
  wrap.appendChild(row);
  return wrap;
}
function transformRows(cfg, box, onchange) {
  box.appendChild(vecBlock(cfg, "rot", "rotate (deg)", ["roll X", "pitch Y", "yaw Z"], 15, onchange));
  box.appendChild(vecBlock(cfg, "off", "offset (mm)", ["x", "y", "z"], 5, onchange));
  const wrap = document.createElement("div");
  wrap.className = "tblock";
  const head = document.createElement("div");
  head.className = "tlabel";
  head.textContent = "scale:";
  const row = document.createElement("div");
  row.className = "trow";
  const cell = document.createElement("label");
  cell.className = "tcell";
  const sc = document.createElement("input");
  sc.type = "number"; sc.step = 0.1; sc.min = 0.01; sc.value = cfg.scale || 1;
  sc.onchange = () => { cfg.scale = +sc.value || 1; onchange(); };
  cell.append(sc, document.createTextNode("×"));
  row.appendChild(cell);
  wrap.append(head, row);
  box.appendChild(wrap);
}
const isImg = (f) => /\.(png|jpe?g|bmp|gif)$/i.test(f);
const isStl = (f) => /\.stl$/i.test(f);
function fileSelect(cfg, onpick) {
  const sel = document.createElement("select");
  sel.style.flex = "1";
  sel.innerHTML = "<option value=''>(built-in)</option>";
  modelFiles.filter(isStl).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f;
    if (cfg.file === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => { cfg.file = sel.value; onpick(); };
  return sel;
}
function texSelect(cfg, onpick) { // painted PNG/JPG applied onto the part
  const sel = document.createElement("select");
  sel.style.flex = "1";
  sel.title = "texture image (draw it in any paint program, Import it, pick it here)";
  sel.innerHTML = "<option value=''>(no texture)</option>";
  modelFiles.filter(isImg).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f;
    if (cfg.tex === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => { cfg.tex = sel.value; onpick(); };
  return sel;
}
function renderModelsUI() {
  const box = $("meshAssign");
  box.innerHTML = "";
  MESH_PARTS.forEach(part => {
    const cfg = meshCfg[part];
    const row = document.createElement("div"); row.className = "row";
    const lbl = document.createElement("span"); lbl.className = "lbl"; lbl.textContent = part;
    const sel = fileSelect(cfg, () => {
      saveMeshes();
      renderModelsUI(); // the rot/offset/scale boxes appear immediately
      if (cfg.file) measureFromStl(part);        // STL size -> rig lengths
      else { revertDims(part); buildRobot(); }   // built-in again
    });
    const col = document.createElement("input");
    col.type = "color"; col.value = cfg.color || "#8a94a6";
    col.title = "color of this part (ignored while a texture is set)";
    col.onchange = () => { cfg.color = col.value; saveMeshes(); buildRobot(); };
    row.append(lbl, sel, col);
    box.appendChild(row);
    const texRow = document.createElement("div"); texRow.className = "row";
    const texLbl = document.createElement("span");
    texLbl.className = "lbl"; texLbl.textContent = "└ texture";
    texRow.append(texLbl, texSelect(cfg, () => { saveMeshes(); buildRobot(); }));
    box.appendChild(texRow);
    if (cfg.file) { // the STL rarely shares the robot's origin: adjust here
      const sub = document.createElement("div");
      sub.style.margin = "0 0 8px 12px";
      transformRows(cfg, sub, () => { saveMeshes(); measureFromStl(part); });
      box.appendChild(sub);
    }
  });
  renderAddonsUI();
}
function renderAddonsUI() {
  const box = $("addonList");
  box.innerHTML = "";
  addons.forEach((ad, i) => {
    const row = document.createElement("div"); row.className = "row";
    const sel = fileSelect(ad, () => { saveMeshes(); buildRobot(); });
    const at = document.createElement("select");
    MESH_PARTS.forEach(p => {
      const o = document.createElement("option"); o.value = o.textContent = p;
      if (ad.part === p) o.selected = true;
      at.appendChild(o);
    });
    at.title = "which body part this piece follows";
    at.onchange = () => { ad.part = at.value; saveMeshes(); buildRobot(); };
    const col = document.createElement("input");
    col.type = "color"; col.value = ad.color || "#7a5cc4";
    col.onchange = () => { ad.color = col.value; saveMeshes(); buildRobot(); };
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => { addons.splice(i, 1); saveMeshes(); renderModelsUI(); buildRobot(); };
    row.append(sel, at, col, del);
    box.appendChild(row);
    const sub = document.createElement("div");
    sub.style.margin = "0 0 8px 12px";
    transformRows(ad, sub, () => { saveMeshes(); buildRobot(); });
    box.appendChild(sub);
  });
}
function addAddon() {
  addons.push({ file: "", part: "torso", rot: [0, 0, 0], off: [0, 0, 0], scale: 1, color: "#7a5cc4" });
  saveMeshes();
  renderModelsUI();
}
async function importStl() {
  const f = $("stlFile").files[0];
  if (!f) { alert("choose a file first: .stl shape (mm) or a painted .png/.jpg texture"); return; }
  const r = await fetch("/api/model/upload?name=" + encodeURIComponent(f.name), {
    method: "POST", body: await f.arrayBuffer(),
  }).then(r => r.json());
  if (!r.ok) { alert("import failed: " + r.error); return; }
  delete stlCache[r.file]; // re-imported file: drop the stale geometry/texture
  delete texCache[r.file];
  await refreshModels();
  $("tlStat").textContent = "imported " + r.file + " — assign it below (" +
    (isImg(r.file) ? "as a texture on a part" : "as a body part or add-on") + ")";
}
async function refreshModels() {
  const r = await fetch("/api/list?kind=models").then(r => r.json());
  modelFiles = (r.files || []).filter(f => isStl(f) || isImg(f));
  renderModelsUI();
}
