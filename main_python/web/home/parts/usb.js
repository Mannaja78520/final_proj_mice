let usbBusy=false;
function renderUsbResult(slot,u){
  slot.innerHTML='';
  const head=document.createElement('div');head.className='mini';
  head.style.marginTop='8px';
  if(u.module){
    // "in use" is not a problem: the hub owns the cable and shares it, so the
    // module site and Nong Studio can both be open on this port at once
    head.textContent=u.port+' — module plugged in directly'+
      (u.inuse?' (in use — shared, open as many pages as you like):':':');
    slot.appendChild(head);
    // A LINE, NOT A SECOND ROW. Reported 2026-08-22: *i found the problem it
    // show more than 1 time that why i consern this user don't know which
    // module*. This board is already in the one list at the top of this tab,
    // with its buttons and every way it can be reached; drawing the whole row
    // again here made one robot look like two.
    const said=document.createElement('div');
    said.className='via';
    said.style.margin='0 0 4px 2px';
    said.textContent='✓ ' + (u.module.name || ('#'+u.module.id)) + ' ('
      + (u.module.type || '?') + ') — in the list at the top of this tab';
    slot.appendChild(said);
    addHotspotPeers(slot,u.port,u.module);
  }else{
    head.textContent=u.port+' — '+(u.error||'no module answered (dongle only, or not a module)');
    slot.appendChild(head);
    if(u.bt){ // recognized as Bluetooth: skipped, but allow forcing it
      const b=document.createElement('button');
      b.textContent='probe anyway';b.style.marginLeft='8px';
      b.onclick=async()=>{
        head.textContent=u.port+' — probing (Bluetooth ports can take ~40 s)…';
        b.remove();
        // An error reply has no `usb` key, so r.usb[0] threw and this slot sat
        // on "probing…" for ever with its button already gone — no result, no
        // error, and no way to ask again.
        try{
          const r=await fetch('/api/scanusb?port='+encodeURIComponent(u.port))
                    .then(r=>r.json());
          const got=(r&&r.usb&&r.usb[0])||{port:u.port,error:'no answer from that port'};
          renderUsbResult(slot,got);
        }catch(e){
          renderUsbResult(slot,{port:u.port,
            error:'could not ask the hub ('+(e.message||e)+')'});
        }
      };
      head.appendChild(b);
    }
  }
  // The boards BEHIND this cable, on the RS485 bus. A line each, for the same
  // reason as the board on the cable itself: the hub already lists them once,
  // up at the top of this tab, with "RS485 #2 behind COM9" written under the
  // row. Drawing them again here is how a bench of two boards read as four.
  (u.rs485||[]).forEach(m=>{
    const line=document.createElement('div');
    line.className='via';
    line.style.margin='0 0 4px 26px';
    line.textContent='↳ RS485 #' + (m.id != null ? m.id : '?') + '  '
      + (m.name || '') + (m.type ? ' (' + m.type + ')' : '')
      + ' — in the list at the top of this tab';
    slot.appendChild(line);
  });
  // Flashing MOVED to the Firmware screen (A2-2). This screen answers "what is
  // connected"; that one replaces firmware, which is a different job, usually
  // a different moment, and the only one of the two that cannot be undone.
  // The insight that lived here came with it: the Firmware screen lists cables
  // nothing answered on, because a blank board is never in a module list and
  // is exactly the board you need to write to.
}

// A board flashed with a DIFFERENT type still has its OLD type in its own
// memory, so it would come back as `blank` — the new firmware does not carry
// the module it is told to be. Finish the job: wait for it to answer again,
// set the type, reboot once more.
// New firmware alone does NOT make a board that type. The type is stored on the
// board, the binary only contains the module types it was built with, and
// ModuleFactory falls back to BlankModule when the stored type is not one of
// them. So a board carrying the cam firmware but still storing "blank" boots
// blank, reports blank, and has no camera — the flash looked perfect.
//
// This bit the camera both ways:
//   * over the cable, nothing set the type at all, so an ESP32-CAM flashed as
//     "cam" always came back as "blank";
//   * over WiFi, the type WAS set, but straight after an update the OLD
//     firmware is still answering for a moment. It does not know "cam", so
//     `SET TYPE cam` returned "ERR unknown type" and that was treated as a
//     hard failure and never retried. The board then rebooted into the cam
//     firmware still storing "blank".
//
// The board already reports which types its binary knows (the `types` array in
// /api/dev/status). So the rule that fixes both: only ask the binary that is
// answering RIGHT NOW, and only once it says it can actually be this type.
// Then keep watching until the board reports the type for real.
async function applyTypeAfterFlash(dev,type,stat){
  const say=t=>{ if(stat)stat.textContent=t; };
  say('✓ firmware sent — waiting for the board to restart…');
  let seen=false,asked=-99;
  for(let i=0;i<40;i++){                    // ~60 s: boards take their time
    await new Promise(r=>setTimeout(r,1500));
    let st=null;
    try{ st=await fetch('/api/dev/status?dev='+encodeURIComponent(dev))
           .then(r=>r.json()); }
    catch(e){ say('waiting for the board to come back…'); continue; }
    if(!st||!Array.isArray(st.types)){ say('waiting for the board to come back…'); continue; }
    seen=true;
    if(st.type===type){                     // confirmed by the board itself
      say('✓ done — this board is now "'+type+'"');
      setTimeout(scanUsb,1500);
      return true;
    }
    if(st.types.indexOf(type)<0){           // still the old firmware answering
      say('waiting for the new firmware to start…');
      continue;
    }
    if(i-asked<8){ say('waiting for it to restart as "'+type+'"…'); continue; }
    const r=await fetch('/api/dev/cmd?dev='+encodeURIComponent(dev)+
                        '&c='+encodeURIComponent('SET TYPE '+type))
      .then(r=>r.text()).catch(()=>'');
    if(!r||r.startsWith('ERR')){            // not ready yet — keep waiting
      say('waiting for the new firmware to start…');
      continue;
    }
    asked=i;
    say('setting it to "'+type+'" and restarting…');
    await fetch('/api/dev/cmd?dev='+encodeURIComponent(dev)+'&c=REBOOT').catch(()=>{});
  }
  say(seen
      ? '⚠ the firmware went on, but the board never confirmed it is "'+type+'". '+
        'Send it: SET TYPE '+type
      : '⚠ the firmware went on, but the board did not answer. Check its power, '+
        'then send it: SET TYPE '+type);
  return false;
}
// kept so anything still calling setType(ip,...) keeps working
async function setType(ip,type,stat){ return applyTypeAfterFlash('wifi:'+ip,type,stat); }

