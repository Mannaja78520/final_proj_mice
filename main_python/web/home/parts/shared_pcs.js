// ---- modules held on OTHER PCs --------------------------------------------
//
// A module on another laptop's cable used to be invisible here, which at a
// venue is the normal setup: one PC by the arm, one at the desk. The hub that
// owns the cable stays its only owner — this page just asks that hub to pass
// the command along, so there is never a second program fighting for the same
// serial handle.
let sharedBusy = false, sharedHave = [];
async function loadShared(force){
  const box = document.getElementById('shared');
  if(!box || sharedBusy) return;
  sharedBusy = true;
  // Looking takes a subnet sweep, so say so rather than leaving a blank hole.
  box.className = 'mini spin';
  box.textContent = 'Looking for other PCs on this network…';
  let r;
  try{
    r = await fetch('/api/allmods'+(force?'?force=1':'')).then(x=>x.json());
  }catch(e){
    sharedBusy = false;
    box.className = 'mini';
    // "could not look" is a different fact from "found nothing", and saying
    // the second when the first is true is the page lying.
    box.innerHTML = 'Could not check for other PCs — this hub did not answer. '
      + '<span style="color:var(--mut)">'+esc(String(e.message||e))+'</span> '
      + '<button onclick="loadShared(true)">Try again</button>';
    return;
  }
  sharedBusy = false;
  const mods = (r && r.modules) || [];
  const errs = (r && r.errors) || [];
  sharedHave = mods;
  box.className = 'mini';
  if(!mods.length){
    box.innerHTML = 'No other PCs are sharing a module right now. Start this hub '
      + 'on the other PC and plug a module into it — it will appear here by itself.'
      + (errs.length ? ' <span style="color:var(--warn)">'+errs.length
         +' PC(s) did not answer.</span>' : '');
    return;
  }
  // ONE ROW PER PC, not per module. The modules themselves are in the one list
  // at the top of the Modules tab now, each carrying "through <that PC>" as a
  // detail - so repeating them here made one robot into two rows again, which
  // is the thing the user asked to be rid of on 2026-08-21. What is left is the
  // question this card is actually for: which machines are sharing, and how
  // much.
  const byHost = {};
  mods.forEach(function(m){
    const h = m.host || m.hostIp || '?';
    (byHost[h] = byHost[h] || {ip: m.hostIp, mods: []}).mods.push(m);
  });
  box.innerHTML = '';
  Object.keys(byHost).sort().forEach(function(host){
    const pc = byHost[host];
    const row = document.createElement('div');
    row.className = 'mod';
    row.innerHTML = '<span class="nm">🖥 '+esc(host)+'</span>'
      + '<span class="ip">'+pc.mods.length
      + (pc.mods.length === 1 ? ' module' : ' modules')
      + '<span class="tech"> · '+esc(pc.ip||'')+'</span></span>'
      + '<div class="via">'+esc(pc.mods.map(function(m){
          return (m.name || ('#'+m.id)) + ' (' + (m.type||'?') + ')'; }).join(', '))
      + '</div>';
    const go = document.createElement('button');
    go.textContent = 'Show in the list';
    go.title = 'these are already in the list at the top of this tab, with '
             + host + ' named under each one';
    go.onclick = function(){
      const f = document.getElementById('modFind');
      if(f){ f.value = ''; filterMods(); f.focus(); }
      const top = document.getElementById('mods');
      if(top) top.scrollIntoView({behavior: 'smooth', block: 'start'});
    };
    row.appendChild(go);
    box.appendChild(row);
  });
  if(errs.length){
    const w = document.createElement('div');
    w.className = 'mini';
    w.style.color = 'var(--warn)';
    w.textContent = '⚠ '+errs.length+' PC(s) on this network did not answer. '
      + 'They may have been switched off.';
    box.appendChild(w);
  }
}
// The modules that joined THIS module's own hotspot.
//
// This is the no-WiFi case, and it is the normal one at a venue: plug the PC
// into any one module, let the rest join that module's hotspot, and the whole
// installation is controllable down one cable. The hub asks the plugged-in
// module who it can see (PEERS) and routes every call through it (REACH), so
// each one gets a normal row here with its real site and Studio buttons.
async function addHotspotPeers(slot,port,self){
  let peers=[];
  try{
    peers=await fetch('/api/dev/peers?dev='+encodeURIComponent('usb:'+port))
      .then(r=>r.json());
  }catch(e){return;}
  if(!Array.isArray(peers))return;
  const others=peers.filter(p=>!p.self&&p.name&&(!self||p.id!==self.id));
  if(!others.length)return;
  const head=document.createElement('div');
  head.className='mini';
  head.style.margin='6px 0 2px 24px';
  head.textContent='through '+(self&&self.name?self.name:port)+
    '’s own hotspot — no venue WiFi needed:';
  slot.appendChild(head);
  others.forEach(p=>{
    const row=modRow(p,port+' → '+(self&&self.name?self.name:'hotspot'),port,0,p.name);
    row.style.marginLeft='24px';
    slot.appendChild(row);
  });
}
async function scanUsb(){
  if(usbBusy)return;
  usbBusy=true;
  const el=document.getElementById('usbmods');
  try{
    const r=await fetch('/api/ports').then(r=>r.json()); // typed port list, no WiFi scan
    const ports=r.ports||[];
    el.innerHTML='';
    if(!ports.length){el.innerHTML='<span class="mini">No USB cables found. '
      +'Plug a module into this PC, then press <b>Probe now</b>. If it is '
      +'plugged in already, it may need its USB driver (CH340 or CP210x).</span>';
      usbBusy=false;return;}
    const jobs=[];
    ports.forEach(p=>{
      const slot=document.createElement('div');
      el.appendChild(slot);
      if(p.bt){
        renderUsbResult(slot,{port:p.port,bt:true,module:null,rs485:[],
          error:(p.desc||'Bluetooth')+' — skipped'});
      }else{
        slot.innerHTML='<div class="mini" style="margin-top:8px">'+p.port+' — probing… <span class="spin">('+(p.desc||'')+')</span></div>';
        jobs.push(fetch('/api/scanusb?port='+encodeURIComponent(p.port))
          .then(r=>r.json())
          // same guard: an error body has no `usb` array, and throwing here
          // left the slot stuck on "probing…" for the life of the page
          .then(r=>renderUsbResult(slot,(r&&r.usb&&r.usb[0])||
                 {port:p.port,error:'no answer from that port'}))
          .catch(e=>{slot.innerHTML='<div class="mini">'+esc(p.port)+
            ' — could not check this cable. '+esc(String(e.message||e))+'</div>';}));
      }
    });
    await Promise.all(jobs);
  }catch(e){
    el.innerHTML='<span class="mini">Could not check the USB cables. Is the hub '
      +'still running? <span style="color:var(--mut)">'+esc(String(e.message||e))
      +'</span></span> <button onclick="scanUsb()">Try again</button>';
  }
  usbBusy=false;
}
// auto-check loop: re-probes every 12 s while the page is visible.
// A port that a page is already driving (module site / Nong Studio over the
// shared USB link) is NOT re-probed — the hub answers from the identity it
// already has, so the probe never stutters their commands.
