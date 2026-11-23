// Studio side of the numeric 3D check: load the CAD look, turn the URDF joints named in the cases,
// print where a probe point of each moving link lands (three.js world, mm).
// usage: NODE_PATH=... node urdf_page.js <base> <cases.json> [model path]   cases: [{q:{jointName:rad}}]
const { chromium } = require("playwright");
const fs = require("fs");
(async () => {
  const [base, casesFile, model] = process.argv.slice(2);
  const cases = JSON.parse(fs.readFileSync(casesFile, "utf8"));
  const br = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
  const p = await (await br.newContext({ viewport: { width: 1200, height: 800 } })).newPage();
  await p.goto(base + "/studio/", { waitUntil: "load" });
  await p.waitForFunction(() => typeof setLook === "function" && typeof URDF_CFG !== "undefined" && URDF_CFG && typeof robot !== "undefined" && palmMarks.length === 2, null, { timeout: 30000 });
  const res = await p.evaluate(async ([cases, model]) => {
    if (model) { RIG.view.model = model; }
    await setLook("urdf", true);
    for (let t = 0; t < 100 && !urdfOn; t++) await new Promise(r => setTimeout(r, 100));
    if (!urdfOn) return { error: urdfLast.error || "CAD look did not start" };
    const names = urdfJ.map(b => b && b.name);
    const probe = new THREE.Vector3(10, 20, 30);        // an off-axis point in the link frame: tests turning, not just position
    const out = cases.map(c => {
      urdfJ.forEach(b => { if (b) b.mov.quaternion.setFromAxisAngle(b.axis, (c.q || {})[b.name] || 0); });
      robot.updateMatrixWorld(true);
      const o = {};
      urdfJ.forEach(b => { if (b) { const w = b.mov.localToWorld(probe.clone()); const f = b.mov.getWorldPosition(new THREE.Vector3()); o[b.name] = { probe: [w.x, w.y, w.z], frame: [f.x, f.y, f.z] }; } });
      return o;
    });
    return { names, out };
  }, [cases, model || ""]);
  console.log(JSON.stringify(res));
  await br.close();
})();
