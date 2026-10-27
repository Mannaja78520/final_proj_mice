// ===================== CAD PIECES: WHICH PART EACH BOLT RIDES ON =====================
// A48-19 (user 2026-10-27): "why aren't the bolts locked to their axes" and
// "the ring fixed to the body must not turn with the shoulder roll". A
// SolidWorks export puts every link in one STL, and the bolts of a joint sit
// in the PARENT's file (PC run: shrug_link holds the shoulder bolts, waist_link
// the shrug's), so they stayed behind when the joint turned. Here each mesh is
// split into its separate pieces and, from urdf_view.json "pieces":
//   links: a whole link rides on another (the shoulder ring on the body);
//   lock:  a small piece follows the big piece its corners touch most;
//   pick:  a named piece rides where it says (wins over both).
// The URDF is never changed. tools/urdf_parts.py --assign prints the same
// numbers and choices for a real file, to write "pick" from.

const urdfSplitDone = new WeakMap();    // geometry -> its pieces, kept across rebuilds
let urdfPieceInfo = null;               // the last pass: {pieces, moved} (QC and the tech line)

function urdfPiecesCfg() { return (URDF_CFG && URDF_CFG.pieces) || null; }
function urdfPiecesOn() {
  const c = urdfPiecesCfg();
  return !!c && (!!(c.links || []).length || !!(c.pick || []).length || (c.lock || {}).on !== false);
}

// Triangles sharing a corner (welded to q mm) are one piece; biggest first,
// ties in file order - the numbering tools/urdf_parts.py prints.
function urdfSplit(geo, mm, q) {
  const key = mm + "|" + q, had = urdfSplitDone.get(geo);
  if (had && had.key === key) return had.pieces;
  const pos = geo.attributes.position.array, nt = Math.floor(pos.length / 9);
  const ids = new Map(), par = [], first = new Int32Array(nt);
  const find = (x) => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
  const r = (v) => Math.floor(v * mm / q + 0.5);
  for (let t = 0; t < nt; t++) {
    let a = -1;
    for (let c = 0; c < 3; c++) {
      const o = t * 9 + c * 3, k = r(pos[o]) + "," + r(pos[o + 1]) + "," + r(pos[o + 2]);
      let n = ids.get(k);
      if (n === undefined) { n = par.length; par.push(n); ids.set(k, n); }
      if (c === 0) { first[t] = n; a = find(n); } else { const b = find(n); if (a !== b) par[b] = a; }
    }
  }
  const groups = new Map();
  for (let t = 0; t < nt; t++) {
    const g = find(first[t]);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(t);
  }
  const pieces = [...groups.values()].sort((x, y) => y.length - x.length);
  urdfSplitDone.set(geo, { key, pieces });
  return pieces;
}

// mm from point p to triangle abc (closest point, Ericson 5.1.5)
const _pA = new THREE.Vector3(), _pB = new THREE.Vector3(), _pC = new THREE.Vector3(), _pT = new THREE.Triangle();
function urdfTriDist(p, t) {
  _pT.set(_pA.fromArray(t, 0), _pB.fromArray(t, 3), _pC.fromArray(t, 6));
  return _pT.closestPointToPoint(p, new THREE.Vector3()).distanceTo(p);
}

// Which link each piece rides on: the twin of tools/urdf_parts.py assign().
function urdfAssign(P, cfg) {
  const owner = P.map(pc => pc.link);
  (cfg.links || []).forEach(r => P.forEach((pc, k) => { if (pc.link === r.link) owner[k] = r.to; }));
  const lock = cfg.lock || {};
  if (lock.on !== false) {
    const smallMm = +lock.smallMm || 12, touch = +lock.touchMm || 0.3, nPts = +lock.points || 120, cell = +lock.cellMm || 4;
    const size = (pc) => Math.max(pc.hi[0] - pc.lo[0], pc.hi[1] - pc.lo[1], pc.hi[2] - pc.lo[2]);
    const big = P.map((pc, k) => k).filter(k => size(P[k]) > smallMm);
    const grids = {};
    const cellOf = (x, y, z) => Math.floor(x / cell) + "," + Math.floor(y / cell) + "," + Math.floor(z / cell);
    const grid = (k) => {
      if (grids[k]) return grids[k];
      const g = new Map(), w = P[k].w;
      for (let o = 0; o < w.length; o += 9) {
        const t = w.subarray(o, o + 9);
        const lo = [0, 1, 2].map(a => Math.floor((Math.min(t[a], t[a + 3], t[a + 6]) - touch) / cell));
        const hi = [0, 1, 2].map(a => Math.floor((Math.max(t[a], t[a + 3], t[a + 6]) + touch) / cell));
        for (let x = lo[0]; x <= hi[0]; x++) for (let y = lo[1]; y <= hi[1]; y++) for (let z = lo[2]; z <= hi[2]; z++) {
          const c = x + "," + y + "," + z;
          if (!g.has(c)) g.set(c, []);
          g.get(c).push(t);
        }
      }
      return (grids[k] = g);
    };
    const p = new THREE.Vector3();
    P.forEach((s, si) => {
      if (size(s) > smallMm) return;
      const nv = s.w.length / 3, step = Math.max(1, Math.floor(nv / nPts));
      let best = -1, score = 0;
      big.forEach(bk => {
        const b = P[bk];
        for (let a = 0; a < 3; a++) if (s.lo[a] > b.hi[a] + touch || s.hi[a] < b.lo[a] - touch) return;
        const g = grid(bk);
        let n = 0;
        for (let v = 0; v < nv; v += step) {
          p.fromArray(s.w, v * 3);
          const near = g.get(cellOf(p.x, p.y, p.z));
          if (near && near.some(t => urdfTriDist(p, t) <= touch)) n++;
        }
        if (n > score || (n === score && n && owner[bk] === owner[si])) { best = bk; score = n; }
      });
      s.touch = best >= 0 ? [P[best].link, P[best].i, score] : null;
      if (best >= 0) owner[si] = owner[best];
    });
  }
  (cfg.pick || []).forEach(r => P.forEach((pc, k) => {
    if (pc.link === r.link && (r.pieces || []).includes(pc.i)) owner[k] = r.to;
  }));
  return owner;
}

// Called by urdfBuildInto once every mesh is in (all joints still at zero):
// split, decide, then hang each piece on its link. put: [{name, holder, mesh}]
// with holder.userData.zero = its world matrix at zero; linkG/zeroOf per link.
function urdfPieces(put, linkG, linkZero, matOf, pairOf) {
  urdfPieceInfo = null;
  const cfg = urdfPiecesCfg();
  if (!urdfPiecesOn() || !put.length) return;
  const q = +((cfg.lock || {}).weldMm) || 0.01;
  const P = [], perLink = {};
  put.forEach((u, vi) => {
    const geo = u.mesh.geometry, mm = u.mesh.scale.x;
    const M = new THREE.Matrix4().copy(u.holder.userData.zero).multiply(new THREE.Matrix4().makeScale(u.mesh.scale.x, u.mesh.scale.y, u.mesh.scale.z));
    const pos = geo.attributes.position.array;
    urdfSplit(geo, mm, q).forEach(tris => {
      const w = new Float32Array(tris.length * 9), v = new THREE.Vector3();
      const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
      tris.forEach((t, j) => {
        for (let c = 0; c < 3; c++) {
          v.fromArray(pos, t * 9 + c * 3).applyMatrix4(M).toArray(w, j * 9 + c * 3);
          for (let a = 0; a < 3; a++) { lo[a] = Math.min(lo[a], w[j * 9 + c * 3 + a]); hi[a] = Math.max(hi[a], w[j * 9 + c * 3 + a]); }
        }
      });
      perLink[u.name] = (perLink[u.name] || 0);
      P.push({ link: u.name, i: perLink[u.name]++, vi, tris, w, lo, hi });
    });
  });
  const owner = urdfAssign(P, cfg);
  const moved = [];
  put.forEach((u, vi) => {
    const src = u.mesh.geometry, pos = src.attributes.position.array, nor = src.attributes.normal && src.attributes.normal.array;
    const byOwner = {};
    P.forEach((pc, k) => { if (pc.vi === vi) (byOwner[owner[k]] = byOwner[owner[k]] || []).push(pc); });
    if (Object.keys(byOwner).length === 1 && byOwner[u.name]) return;      // nothing leaves this mesh
    u.holder.remove(u.mesh);
    const at = pickMeshes.indexOf(u.mesh); if (at >= 0) pickMeshes.splice(at, 1);
    Object.entries(byOwner).forEach(([to, pcs]) => {
      if (!linkG[to]) to = u.name;                     // data naming a part the file lacks: stays
      const n = pcs.reduce((s, pc) => s + pc.tris.length, 0);
      const ps = new Float32Array(n * 9), ns = nor ? new Float32Array(n * 9) : null;
      let o = 0;
      pcs.forEach(pc => pc.tris.forEach(t => {
        ps.set(pos.subarray(t * 9, t * 9 + 9), o);
        if (ns) ns.set(nor.subarray(t * 9, t * 9 + 9), o);
        o += 9;
      }));
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(ps, 3));
      if (ns) g.setAttribute("normal", new THREE.BufferAttribute(ns, 3)); else g.computeVertexNormals();
      const pair = pairOf(to);
      const m = new THREE.Mesh(g, matOf(pair));
      m.scale.copy(u.mesh.scale);
      m.userData.pair = pair; m.userData.urdfLink = to; m.userData.urdfFrom = u.name;
      if (pair >= 0) pickMeshes.push(m);
      if (to === u.name) { u.holder.add(m); return; }
      // hung on the other link where it is drawn: that link's zero frame -> the holder's
      const h = new THREE.Group(); h.name = "pieces_from_" + u.name;
      new THREE.Matrix4().copy(linkZero[to]).invert().multiply(u.holder.userData.zero)
        .decompose(h.position, h.quaternion, h.scale);
      h.add(m); linkG[to].add(h);
      pcs.forEach(pc => moved.push(u.name + "#" + pc.i + "->" + to));
    });
  });
  urdfPieceInfo = { pieces: P.map((pc, k) => ({ link: pc.link, i: pc.i, to: owner[k], touch: pc.touch || null,
                    lo: pc.lo, hi: pc.hi })), moved };
}
