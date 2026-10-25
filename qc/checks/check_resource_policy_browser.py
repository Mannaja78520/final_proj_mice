"""Use the actual Hub settings page to save the isolated machine policy in Edge."""
import json
from pathlib import Path
import sys
import tempfile

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "resource settings save visibly in the Hub and keep browser choice local"
SLOW = True

DRIVER = r"""<!doctype html><meta charset="utf-8"><iframe id="hub"></iframe>
<script>
document.cookie=__COOKIE__;
const mark=(k,v)=>qcMark('RESOURCE~'+k+'='+Boolean(v));
window.addEventListener('load',async()=>{
 try{
  const f=document.getElementById('hub');f.src='/';
  if(!await qcWaitFor(()=>{try{return f.contentWindow.eval('typeof resourceView !== \"undefined\" && authed');}catch(_){return false;}},18000))throw Error('Hub login or settings did not load');
  const w=f.contentWindow,d=f.contentDocument;w.showTab('settings');
  if(!await qcWaitFor(()=>d.getElementById('resourceMode').options.length>1,10000))throw Error('Resource controls did not populate');
  await mark('choices',d.getElementById('resourceMode').querySelector('option[value="auto"]')&&d.getElementById('resourceDevice').options.length>=2);
  d.getElementById('resourceMode').value='light';d.getElementById('resourceSave').click();
  if(!await qcWaitFor(()=>d.getElementById('resourceStatus').textContent.includes('บันทึกแล้ว'),10000))throw Error('Resource save did not complete: '+d.getElementById('resourceStatus').textContent);
  const saved=await fetch('/api/resources').then(r=>r.json());
  await mark('saved',saved.settings.mode==='light'&&d.getElementById('resourceStatus').textContent.includes('บันทึกแล้ว'));
  await mark('bounded',saved.effective.cpuThreads<saved.hardware.logicalCpus);
  const revision=saved.revision;
  const client=new w.MiceResourceClient(w.MiceResourceRegistry,{hardwareConcurrency:2,deviceMemory:2},null);
  await mark('independent',client.display().id==='light');
  d.getElementById('resourceDisplay').value='fast';d.getElementById('resourceDisplay').dispatchEvent(new Event('change'));
  const unchanged=await fetch('/api/resources').then(r=>r.json());
  await mark('display_local',w.MiceResources.mode==='fast'&&unchanged.revision===revision);
  await mark('next_load',d.getElementById('resourceNotice').textContent.includes('ครั้งถัดไป'));
  d.getElementById('resourceMode').value='fast';
  w.dispatchEvent(new w.StorageEvent('storage',{key:'mice_display_mode',newValue:'light'}));
  await mark('display_sync',d.getElementById('resourceDisplay').value==='light');
  w.dispatchEvent(new w.StorageEvent('storage',{key:'mice_display_mode',newValue:null}));
  await mark('display_reset',d.getElementById('resourceDisplay').value==='auto');
  await mark('unsaved_kept',d.getElementById('resourceMode').value==='fast');
 }catch(error){await qcMark('RESOURCE~error='+String(error));}
 await qcMark('done');
});
</script>"""


def run(t):
    if not browser.available():
        t.give_up("Edge is required for the resource settings journey")
        return
    sys.path.insert(0, str(F.CODE / "main_python"))
    from resource_policy import ResourcePolicy
    from resource_hardware import Capabilities
    fake_serial.reset()
    base, _main = F.start_hub()
    import hub_api_resources
    previous = hub_api_resources._policy
    with tempfile.TemporaryDirectory(prefix="mice_resource_browser_") as folder:
        snapshot = {"logicalCpus": 16, "memoryMiB": 32768, "availableMemoryMiB": 20000, "gpus": []}
        manager = ResourcePolicy(F.CODE / "config/resource_policy.json", Path(folder) / "resources.json",
                                 Capabilities(probe=lambda: snapshot))
        hub_api_resources._policy = manager
        try:
            F.login(base)
            browser.raw_page(DRIVER.replace("__COOKIE__", json.dumps(F._cookie[0])), base, seconds=45)
            got = {}
            for value in fake_serial.qc_marks:
                if value.startswith("RESOURCE~") and "=" in value:
                    key, result = value[9:].split("=", 1)
                    got[key] = result
            t.ok("error" not in got, "real resource settings journey completes", str(got))
            for key in ("choices", "saved", "bounded", "independent", "display_local", "next_load", "display_sync", "display_reset", "unsaved_kept"):
                t.eq(got.get(key), "true", "real resource settings: " + key)
            t.eq(manager.store.read()["settings"]["mode"], "light", "browser save persisted only to its isolated machine store")
        finally:
            browser.kill()
            hub_api_resources._policy = previous
