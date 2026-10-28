"""Click the actual Gacha page and load Voice with the real shared App in Edge."""
import browser
import fake_serial
import qc as F

AREA = "tools"
TITLE = "loaded Gacha removal, checked preset start, Voice and theme selectors work in Edge"
SLOW = True

DRIVER = r"""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="/mice.css"><script src="/mice.js"></script>
<div id="left"></div><div id="right"></div>
<iframe id="gacha" src="/app/gacha/"></iframe><iframe id="voice" src="/app/voice/"></iframe>
<script>
const mark=(k,v)=>qcMark('LIFE~'+k+'='+Boolean(v));
window.addEventListener('load',async()=>{
 try {
  const gf=document.getElementById('gacha'),w=gf.contentWindow,d=gf.contentDocument;
  if(!await qcWaitFor(()=>w.gachaApp&&d.querySelector('#mTable tbody'),15000)) throw Error('Gacha did not initialize');
  const app=w.gachaApp;
  const machine=(id,label)=>({id,label,module:id,item:'gift',near:[],live:{cfg:{},stock:1}});
  app.S={machines:[machine('first','first'),machine('second','second')],items:{gift:{label:'Gift'}},event:{},rules:{},messages:{}};
  app.drawMachines();
  d.querySelectorAll('#mTable tr[data-i]')[1].querySelector('[data-k="label"]').value='unsaved edit';
  [...d.querySelectorAll('#mTable button')].find(b=>b.textContent==='remove').click();
  await mark('machine_remove',app.S.machines.length===1&&app.S.machines[0].id==='second'&&app.S.machines[0].label==='unsaved edit'&&!!app.S.machines[0].live);
  app.ED=[['name'],['remove'],['keep']];app.edDraw();
  d.querySelector('[data-r="2"][data-c="0"]').value='unsaved edit';
  d.querySelectorAll('#edT button')[1].click();
  await mark('sheet_remove',app.ED.length===2&&app.ED[1][0]==='unsaved edit');
  app.applyPreset('giveaway');app.load=async()=>true;
  let calls=[],reject=true;
  const original=w.fetch.bind(w);
  w.fetch=async(url,opts)=>{
   if(!opts||opts.method!=='POST') return original(url,opts);
   const body=JSON.parse(opts.body);calls.push({url:String(url),body});
   const key='name' in body?'name':'open';const replies={};app.readMachines().forEach(m=>replies[m.id]='OK');
   return {ok:!reject,status:reject?403:200,json:async()=>({ok:!reject,error:reject?'Denied fixture':'',sent:{[key]:replies}})};
  };
  d.querySelector('[data-preset-start]').click();
  if(!await qcWaitFor(()=>!app.preset.busy,10000)) throw Error('Denied preset did not finish');
  await mark('preset_denied',calls.length===1&&calls[0].body.open===false&&d.getElementById('presetNotice').textContent.includes('ไม่สำเร็จ'));
  await mark('preset_retry',!!d.querySelector('[data-preset-start]'));
  reject=false;calls=[];d.querySelector('[data-preset-start]').click();
  if(!await qcWaitFor(()=>!app.preset.busy,10000)) throw Error('Accepted preset did not finish');
  await mark('preset_order',calls.length===5&&calls[0].body.open===false&&!!calls[1].body.machines&&!!calls[2].body.items&&!!calls[3].body.name&&calls[4].body.open===true);
  await mark('preset_ready',d.getElementById('presetNotice').textContent.includes('ตอบรับการเปิดงาน'));
  const vf=document.getElementById('voice'),v=vf.contentWindow;
  if(!await qcWaitFor(()=>v.voiceApp,15000)) throw Error('Voice did not initialize');
  v.voiceApp.say('Shared App browser fixture');
  await mark('voice',vf.contentDocument.getElementById('stat').textContent.includes('Shared App browser fixture'));
  const a=miceTheme.picker(document.getElementById('left')),b=miceTheme.picker(document.getElementById('right'));
  const themes=miceTheme.list();if(themes.length<2)throw Error('Missing themes');
  miceTheme.set(themes[1].id);
  await mark('theme_sync',a.value===themes[1].id&&b.value===themes[1].id);
  window.dispatchEvent(new StorageEvent('storage',{key:'mice_theme',newValue:null}));
  await mark('theme_reset',a.value===themes[0].id&&b.value===themes[0].id&&!document.documentElement.hasAttribute('data-theme'));
 }catch(e){await qcMark('LIFE~error='+String(e));}
 await qcMark('done');
});
</script>"""


def run(t):
    if not browser.available():
        t.give_up("Edge is required for the app integration journey")
        return
    fake_serial.reset()
    base, _main = F.start_hub()
    try:
        browser.raw_page(DRIVER, base, seconds=55)
        got = {}
        for mark in fake_serial.qc_marks:
            if mark.startswith("LIFE~") and "=" in mark:
                key, value = mark[5:].split("=", 1)
                got[key] = value
        t.ok("error" not in got, "app browser journey completes", str(got))
        for key in ("machine_remove", "sheet_remove", "preset_denied", "preset_retry",
                    "preset_order", "preset_ready", "voice", "theme_sync", "theme_reset"):
            t.eq(got.get(key), "true", "real browser: " + key)
    finally:
        browser.kill()
