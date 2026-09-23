// --- URDF import ---
//
// User 2026-09-23: *we already have all step file when i drag it cannot be as
// my aspect make can use urdf too*.
//
// A STEP file is a solid-modelling format. A browser cannot open one, and an
// STL dragged in on its own carries no origin at all - so every part landed at
// the middle of the robot and had to be rotated, offset and scaled by hand
// until it looked right. That is what "cannot be as my aspect" was.
//
// A URDF carries exactly the numbers that were missing: where each part sits,
// which way it is turned, how big it is, and which part hangs off which. So
// importing one fills the boxes in instead of leaving them to be guessed.
//
// WHAT IS SETTABLE, BECAUSE NO TWO EXPORTS AGREE:
//   * units. URDF is metres; Studio is millimetres. SolidWorks' sw2urdf writes
//     its STL meshes in metres too, so the default is x1000 for both.
//   * which way is up. URDF/ROS is Z-up X-forward; this editor is Y-up
//     Z-forward. The default mapping is that one, and it can be changed
//     without editing code - a CAD export that was built Y-up already would
//     otherwise arrive lying on its side with no way to say so.
//   * which link is which part. An export names links after SolidWorks
//     components, so the names are guessed and then shown for correction.
// None of it is hidden: the import says what it matched, what it could not,
// and what it changed.

const URDF_DEF = { mm: 1000, up: "z" };
let urdfDoc = null;         // the parsed file, kept so a re-map costs no re-read
let urdfMap = {};           // link name -> Studio part ("" = not used)
let urdfName = "";

// Guesses a Studio part from a link name. DATA, not code: the next naming
// habit is one more row here and nothing else.
const URDF_GUESS = [
  [/(^|[_\- ])(l|left)([_\- ]|$).*(upper|shoulder|humerus)/i, "L_upper"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(upper|shoulder|humerus)/i, "R_upper"],
  [/(^|[_\- ])(l|left)([_\- ]|$).*(fore|lower|elbow|radius)/i, "L_fore"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(fore|lower|elbow|radius)/i, "R_fore"],
  [/head|skull|face/i, "head"],
  [/torso|body|chest|trunk|base/i, "torso"],
];
function urdfGuessPart(link) {
  for (const [re, part] of URDF_GUESS) if (re.test(link)) return part;
  return "";
}

function urdfNums(el, attr, fallback) {
  const raw = el && el.getAttribute(attr);
  if (!raw) return fallback.slice();
  const n = raw.trim().split(/\s+/).map(Number);
  return n.length === 3 && n.every(Number.isFinite) ? n : fallback.slice();
}

// URDF axes -> this editor's axes. ROS is Z-up X-forward; three.js here is
// Y-up Z-forward, so (x, y, z) becomes (y, z, x) - a cyclic swap, which keeps
// the handedness and therefore keeps every rotation turning the same way.
function urdfToStudioXYZ(v, up) {
  return up === "y" ? [v[0], v[1], v[2]] : [v[1], v[2], v[0]];
}
// The same swap for roll-pitch-yaw. URDF fixed-axis rpy is Rz(yaw)*Ry(pitch)*
// Rx(roll), which is THREE's Euler order "ZYX" with the SAME three numbers -
// so the only thing to do is move each number onto the axis it now turns
// about, and hand the result back in degrees, which is what meshCfg holds.
function urdfToStudioRPY(rpy, up) {
  const s = urdfToStudioXYZ(rpy, up);
  return s.map(r => Math.round(THREE.MathUtils.radToDeg(r) * 10) / 10);
}

// The one visual of a link, as {file, rot, off, scale}, or null when the link
// has no mesh (a URDF has plenty: bearings, frames, fasteners).
function urdfVisual(link, opt) {
  const vis = link.querySelector("visual");
  const mesh = vis && vis.querySelector("geometry mesh");
  if (!mesh) return null;
  const file = (mesh.getAttribute("filename") || "").split(/[\\/]/).pop();
  if (!file) return null;
  const org = vis.querySelector("origin");
  const off = urdfToStudioXYZ(urdfNums(org, "xyz", [0, 0, 0]), opt.up)
    .map(v => Math.round(v * opt.mm * 10) / 10);
  const rot = urdfToStudioRPY(urdfNums(org, "rpy", [0, 0, 0]), opt.up);
  // <mesh scale> is a per-axis scale; this editor has one number, so a mesh
  // scaled differently per axis is reported rather than silently flattened.
  const ms = urdfNums(mesh, "scale", [1, 1, 1]);
  const even = Math.abs(ms[0] - ms[1]) < 1e-9 && Math.abs(ms[1] - ms[2]) < 1e-9;
  return { file, off, rot, scale: ms[0] * opt.mm, even };
}

// Parse, and say what is in it. Never touches the rig: reading a file and
// changing the robot are two different decisions, and one button that does
// both cannot be undone halfway.
function urdfParse(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror"))
    throw new Error("this file is not valid XML, so it cannot be a URDF");
  const robot = doc.querySelector("robot");
  if (!robot) throw new Error("no <robot> in this file - is it a URDF?");
  const links = [...doc.querySelectorAll("robot > link")];
  if (!links.length) throw new Error("this URDF has no links in it");
  return { doc, robot, links,
           joints: [...doc.querySelectorAll("robot > joint")] };
}

// How long each mapped part's bar is, in mm. This is the number that makes an
// imported robot the right SIZE and not merely the right shape.
//
// A joint's origin is measured in its PARENT link's frame, so the length of a
// bar is the origin of the joint LEAVING it - the elbow's origin is the upper
// arm's length. Reading the joint that ARRIVES at a link instead gives the
// offset of the bar before it, which for this robot is the shoulder's own
// (0, 0, 0) - every arm then measured zero.
//
// Zero-length joints are skipped on purpose: a shoulder and an elbow are each
// two servos stacked at one origin, so half the joints in this tree carry no
// distance at all. A leaf link has no outgoing joint and so has no length
// here; its mesh is the only thing that says how long it is.
function urdfJointLengths(parsed, opt) {
  const out = {};
  parsed.joints.forEach(j => {
    const parent = j.querySelector("parent");
    if (!parent) return;
    const part = urdfMap[parent.getAttribute("link")];
    if (!part || out[part]) return;
    const v = urdfNums(j.querySelector("origin"), "xyz", [0, 0, 0]);
    const len = Math.round(Math.hypot(v[0], v[1], v[2]) * opt.mm * 10) / 10;
    if (len > 0) out[part] = len;
  });
  return out;
}

// ---- the screen -----------------------------------------------------------
async function importUrdf() {
  const f = $("urdfFile").files[0];
  if (!f) {
    $("urdfStat").textContent = "choose a .urdf file first. Its .stl meshes " +
      "must be imported too (Models > Import), or the parts have nothing to draw.";
    return;
  }
  try {
    const parsed = urdfParse(await f.text());
    urdfDoc = parsed;
    urdfName = f.name;
    urdfMap = {};
    parsed.links.forEach(l => {
      const name = l.getAttribute("name") || "";
      urdfMap[name] = urdfGuessPart(name);
    });
    renderUrdfUI();
    const matched = Object.values(urdfMap).filter(Boolean).length;
    $("urdfStat").textContent = `${f.name}: ${parsed.links.length} links, ` +
      `${parsed.joints.length} joints. ${matched} matched to a body part by ` +
      "name — check them below, then press Use this URDF.";
  } catch (e) {
    $("urdfStat").textContent = "could not read it: " + (e.message || e);
    notice($("urdfStat").textContent);
  }
}
function urdfOptions() {
  return { mm: +$("urdfMm").value || URDF_DEF.mm,
           up: $("urdfUp").value || URDF_DEF.up };
}
function renderUrdfUI() {
  const box = $("urdfLinks");
  if (!box) return;
  box.innerHTML = "";
  if (!urdfDoc) {
    box.innerHTML = "<div class='mini'>No URDF loaded yet.</div>";
    return;
  }
  const opt = urdfOptions();
  urdfDoc.links.forEach(l => {
    const name = l.getAttribute("name") || "";
    const vis = urdfVisual(l, opt);
    const row = document.createElement("div"); row.className = "row";
    const nm = document.createElement("span");
    nm.style.flex = "1"; nm.textContent = name;
    nm.title = vis ? "mesh: " + vis.file : "this link has no mesh to draw";
    const sel = document.createElement("select");
    sel.innerHTML = "<option value=''>(not used)</option>";
    MESH_PARTS.forEach(p => {
      const o = document.createElement("option"); o.value = o.textContent = p;
      if (urdfMap[name] === p) o.selected = true;
      sel.appendChild(o);
    });
    sel.disabled = !vis;
    sel.onchange = () => { urdfMap[name] = sel.value; };
    const note = document.createElement("span");
    note.className = "mini";
    note.textContent = vis ? (vis.even ? vis.file : vis.file + " ⚠ uneven scale")
                           : "no mesh";
    row.append(nm, sel, note);
    box.appendChild(row);
  });
}
// Apply it. Separate from reading the file on purpose: this is the step that
// changes what is on screen, and it says exactly what it changed.
function useUrdf() {
  if (!urdfDoc) { $("urdfStat").textContent = "load a .urdf file first."; return; }
  const opt = urdfOptions();
  const done = [], missing = [], uneven = [];
  urdfDoc.links.forEach(l => {
    const name = l.getAttribute("name") || "";
    const part = urdfMap[name];
    if (!part) return;
    const vis = urdfVisual(l, opt);
    if (!vis) return;
    if (!vis.even) uneven.push(vis.file);
    // The mesh file has to be in models/ already: a URDF names its meshes, it
    // does not carry them. Say which ones are absent instead of drawing
    // nothing and letting it read as a broken import.
    if (!modelFiles.some(f => f.toLowerCase() === vis.file.toLowerCase()))
      missing.push(vis.file);
    meshCfg[part] = { ...defMeshCfg(part), file: vis.file,
                      rot: vis.rot, off: vis.off, scale: vis.scale,
                      color: meshCfg[part].color };
    done.push(part);
  });
  if (!done.length) {
    $("urdfStat").textContent = "nothing was changed: no link is matched to a " +
      "body part yet. Pick a part beside a link above.";
    return;
  }
  // The joint origins are the real bar lengths. They are offered, not forced:
  // a rig that somebody measured by hand must not be overwritten by a CAD file
  // without being asked.
  const lens = urdfJointLengths(urdfDoc, opt);
  const dimOf = { L_upper: "upperLenL", R_upper: "upperLenR",
                  L_fore: "foreLenL", R_fore: "foreLenR" };
  const offer = Object.keys(lens).filter(p => dimOf[p] && lens[p] > 1);
  let sized = 0;
  if (offer.length && confirm(
      "Also set the arm lengths from this URDF?\n\n" +
      offer.map(p => "  " + dimOf[p] + ": " + RIG.dims[dimOf[p]] + " → " + lens[p] + " mm").join("\n") +
      "\n\nOK sets them. Cancel keeps the lengths you have.")) {
    offer.forEach(p => { RIG.dims[dimOf[p]] = lens[p]; sized++; });
  }
  saveMeshes();
  if (sized) rigChanged(); else buildRobot();
  renderModelsUI();
  $("urdfStat").textContent =
    `${urdfName}: placed ${done.length} part(s) — ${done.join(", ")}` +
    (sized ? `, and set ${sized} arm length(s)` : "") + ". " +
    (missing.length ? `Import these meshes too (Models > Import): ${missing.join(", ")}. ` : "") +
    (uneven.length ? `${uneven.join(", ")} is scaled differently on each axis; ` +
                     "this editor has one scale, so the first was used. " : "") +
    "Nothing else in the rig was touched.";
}
