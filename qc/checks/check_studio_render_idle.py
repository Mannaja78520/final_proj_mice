"""After real idle, CAD pose/monitor/view/async mesh/resize redraw; idle stays idle."""
import json
import tempfile
from pathlib import Path

import browser
import fake_serial
import qc as F
from checks.check_urdf_look import AXIS, DIMS, write_fixture

AREA = "studio"
TITLE = "Studio sleeps when idle and redraws CAD pose, monitor, view, late meshes and resize"
SLOW = True

DRIVER = r"""
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const frames=n=>new Promise(resolve=>{function step(){if(--n<=0)resolve();else requestAnimationFrame(step);}requestAnimationFrame(step);});
function mark(k,v){return qcMark('RENDER~'+k+'='+v);}
window.addEventListener('load',async()=>{
 try {
  if(!await qcWaitFor(()=>URDF_CFG&&typeof setLook==='function'&&haveRobot(),15000)) throw Error('Studio did not load');
  playing=false; distOn=distHeld=false; controls.enableDamping=false; controls.autoRotate=false;
  URDF_CFG.fit.anchor='none';
  RIG=mergeRig({dims:__DIMS__,axis:__AXIS__,tilt:new Array(10).fill([0,0,0]),invert:new Array(10).fill(0),zero:new Array(10).fill(90),
    view:{look:'rig',model:'qc_bot/urdf/qc_bot.urdf',sizes:'custom'}});
  const load=stlLoader.load.bind(stlLoader); let lateHead=null;
  stlLoader.load=(url,cb,...rest)=>url.includes('head_late.STL') ? (lateHead=cb) : load(url,cb,...rest);
  await setLook('urdf');
  if(!await qcWaitFor(()=>urdfOn&&urdfTip.L&&urdfTip.L.fromMesh&&lateHead,15000)) throw Error('CAD not ready');
  let paints=0,last=null; const render=renderer.render.bind(renderer);
  renderer.render=(...args)=>{paints++;last={p:pose[0],grid:grid.visible,hand:palmMarks[0].children.filter(c=>c.isMesh).every(c=>!c.visible)};render(...args);};
  async function quiet(){await frames(85);const before=paints;await frames(12);if(paints!==before)throw Error('idle kept rendering');}
  async function changed(key,action,check){await quiet();const before=paints;await action();await frames(10);await mark(key,paints>before&&(!check||check()));}
  await quiet(); await mark('idle',true);
  await changed('cad_pose',()=>{pose[0]=105;applyPose();},()=>last.p===105);
  await changed('monitor',()=>monitorTick(),()=>last.p===101);
  await changed('grid',()=>viewSetGrid(false),()=>last.grid===false);
  await changed('hand',()=>urdfSetHandMarks(false),()=>last.hand);
  await changed('urdf_mesh',()=>{const geo=Object.values(urdfGeo)[0];lateHead(geo.clone());},()=>{
    let count=0;robot.traverse(o=>{if(o.isMesh&&o.userData.urdfLink==='head_link')count++;});return count>0;
  });
  await changed('resize',()=>{const box=viewport.getBoundingClientRect();viewport.style.width=(box.width-30)+'px';resize();});
  RIG.view.look='rig';buildRobot();
  let lateShape=null;
  stlLoader.load=(url,cb,...rest)=>url.includes('qc-delayed.STL')?(lateShape=cb):load(url,cb,...rest);
  meshCfg.L_upper.file='qc-delayed.STL';applyMeshes();
  await changed('shape_mesh',()=>lateShape(new THREE.BoxGeometry(15,20,25)),()=>linkHolders.L_upper.children.length>1);
  await quiet();await mark('idle_after',true);
 }catch(e){await mark('error',e.message);}
 await qcMark('done');
});
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found")
    fake_serial.reset()
    with tempfile.TemporaryDirectory(prefix="mice_render_models_") as folder:
        models = Path(folder)
        pkg = models / "qc_bot"
        (pkg / "urdf").mkdir(parents=True)
        (pkg / "meshes").mkdir()
        write_fixture(pkg)
        p = pkg / "urdf/qc_bot.urdf"
        p.write_text(p.read_text(encoding="utf-8").replace("head_gone.STL", "head_late.STL"), encoding="utf-8")
        base, main = F.start_hub()
        old_models, old_cad = main.MODELS, main.RIG_CAD_FILE
        main.MODELS, main.RIG_CAD_FILE = models, models / "rig_cad.json"
        fake_serial.NONG.joints = [101, 85, 95, 90, 90, 90, 90, 90, 90, 90]
        try:
            driver = DRIVER.replace("__DIMS__", json.dumps(DIMS)).replace("__AXIS__", json.dumps(AXIS))
            browser.page(driver, query=base + "/studio/_qcdriver.html?dev=usb%3ACOM99", seconds=65)
        finally:
            browser.kill()
            main.MODELS, main.RIG_CAD_FILE = old_models, old_cad
    got = dict(m[7:].split("=", 1) for m in fake_serial.qc_marks if m.startswith("RENDER~") and "=" in m)
    t.ok("error" not in got and bool(got), "the actual Studio idle driver runs", got)
    for k in ("idle", "cad_pose", "monitor", "grid", "hand", "urdf_mesh", "resize", "shape_mesh", "idle_after"):
        t.ok(got.get(k) == "true", "Studio %s renders only when needed" % k, got)
