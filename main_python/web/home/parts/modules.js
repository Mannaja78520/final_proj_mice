// When the module list was last actually confirmed, so a stale list can say so
// instead of quietly presenting old modules as if they were still there.
var modsAt = 0, modsHtml = '';
// A wall-clock stamp: 2026-08-22 00:41. Written out rather than left to
// toLocaleString, which prints a different order on every machine - and this
// is read beside timestamps the hub and the plan write in exactly this shape.
function stamp(ms){
  if(!ms) return '';
  var d = new Date(ms), p = function(n){ return (n < 10 ? '0' : '') + n; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
       + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
}
function agoText(ms){
  if(!ms) return '';
  var s = Math.round((Date.now()-ms)/1000);
  if(s < 5) return 'just now';
  if(s < 90) return s + 's ago';
  // "4470 min ago" was on the Home card 2026-09-21: nobody reads that as 3 days
  var m = Math.round(s/60), h = Math.round(s/3600), d = Math.round(s/86400);
  if(m < 90) return m + ' min ago';
  if(h < 36) return h + ' hours ago';
  return d + ' days ago';
}
function modsMeta(){
  if(document.hidden) return;
  var el = document.getElementById('modsmeta');
  if(el) el.textContent = modsAt ? ('checked ' + agoText(modsAt)) : '';
}
setInterval(modsMeta, 5000);

// Which scan is the current one. The wider sweep below finishes seconds after
// the local list, so a sweep started before a newer scan - or before a scan
// that FAILED - must not repaint over what the newer one put there. Without
// this the error banner was drawn and then quietly replaced by rows from a
// sweep that had been in flight the whole time, which reads as the failure
// never having happened.
var scanGen = 0;
async function scan(force){
  const el=document.getElementById('mods');
  const gen = ++scanGen;
  if(force)el.innerHTML='<span class="mini spin">looking for modules… (a few seconds)</span>';
  try{
    // THIS PC FIRST, and drawn the moment it answers. Asking for everything
    // in one call made the list wait on a sweep of the whole network before it
    // could draw the board plugged into this very machine - seconds of empty
    // screen for a fact the hub already had.
    const r=await fetch('/api/modules'+(force?'?force=1':'')).then(r=>r.json());
    // A SLOWER, OLDER scan must not paint over a newer one. A cold hub takes
    // ~4-6 s to answer, so a Rescan that failed meanwhile showed its "Could
    // not reach" banner and the late answer wiped it (check_ui_states, red
    // when run alone, 2026-10-10).
    if(gen !== scanGen) return;
    window.MODS = r.modules || [];
    repaintMods();
    if(!(r.modules||[]).length)
      el.innerHTML='<span class="mini">no modules found on '+ (r.lan||'?') +'/24 — are they powered and on the same WiFi? (⟳ Rescan)</span>';
    modsAt = Date.now(); modsHtml = el.innerHTML;
  }catch(e){
    // Keep the last good list rather than going blank — but mark it plainly as
    // old, and give the one control that fixes it. A control panel that blanks
    // when the network hiccups is worse than one that admits the data is old.
    el.innerHTML =
      '<div class="banner err" role="alert">Could not reach the hub just now — '+
      esc(String(e && e.message || e))+
      ' <button onclick="scan(true)">Try again</button></div>' +
      (modsHtml ? '<div class="stale">showing what was found '+agoText(modsAt)+
                  ' — these may no longer be there</div>'+modsHtml : '');
    modsMeta();
    return;                       // nothing local to merge the far ones into
  }
  mergeFar(force, gen);           // ...and the other PCs' boards, when they answer
  modsMeta();
}

// ...and then the boards OTHER PCs hold, merged into the same rows.
//
// A second call on purpose. Asking every hub on the network takes a sweep, and
// waiting for it before drawing anything left the screen empty for seconds
// while the hub already knew about the board on this PC's own cable. So the
// local list is painted first and this repaints it when the wider answer
// arrives - each board still ONE row, because the merge is done in the hub
// (modules_everywhere) on the board's chip, not here.
async function mergeFar(force, gen){
  try{
    const r = await fetch('/api/modules/all'+(force?'?force=1':'')).then(x=>x.json());
    if(gen !== scanGen) return;          // a newer scan has happened since
    if(!r || !r.ok || !Array.isArray(r.modules)) return;
    window.MODS = r.modules;
    window.MODS_HOST = r.host || '';
    window.HUB_ERRS = r.errors || [];
    repaintMods();
    modsHtml = document.getElementById('mods').innerHTML;
    paintHome();
  }catch(e){
    // The other PCs not answering is not this list being wrong: what is on
    // screen is still every board THIS machine can reach. The card further
    // down is where that failure belongs, and it says so itself.
  }
}

// Draw the module list from what is already known, pinned modules first.
// Split out of scan() so that PINNING costs a repaint and not a network sweep:
// a sweep takes seconds and pokes every board on the venue WiFi, which is a
// silly price for reordering a list. Also means the order is re-applied after
// a pin without waiting for the next scan.
function repaintMods(){
  const el=document.getElementById('mods');
  if(!el) return;
  const mods = pinnedFirst(window.MODS || []);
  // Nothing to draw: scan() writes its own "no modules found" message, so the
  // rows are left alone - but the FILTER still has to be settled, or
  // #modFindNone keeps saying "3 of 5 hidden by the filter" beside a message
  // saying none were found at all. Two statements, contradicting each other,
  // no error anywhere.
  const home = document.getElementById('homeMods');
  if(!mods.length){
    if(home) home.innerHTML='';
    filterMods(); return;
  }
  el.innerHTML='';
  if(home) home.innerHTML='';
  // ONE row per board, drawn into BOTH lists from the same data - but not the
  // same amount of it. Asked for 2026-08-22: *make the home show the each
  // module once easy to use but in module you show like before which from
  // what*. So Home is the short answer (this robot is here, open it) and the
  // Modules tab is the long one (and here is every cable, PC and bus it can
  // be reached through). Same rows, same order, one line of detail fewer.
  mods.forEach(m=>{
      const wifi=(m.routes||[]).filter(x=>x.kind==='wifi')[0];
      const cable=(m.routes||[]).filter(x=>x.kind==='usb'||x.kind==='rs485')[0];
      const far=(m.routes||[]).filter(x=>x.kind==='hub')[0];
      // `wifiSeen` is the only honest answer to "can THIS hub reach it over
      // WiFi": a wifi route exists only when the sweep really got an answer
      // back. m.ip and m.wifi_mode are the board's own claim, learned over the
      // cable - true about the board, and no promise at all that this PC
      // shares that network. Opening a module on an unreachable claimed IP is
      // what made the hub say "no reply" with the cable sitting right there
      // (A26-7).
      // ...and a live route is not the last word either. MEASURED ON THE BENCH
      // 2026-09-18, nong 67 on COM12 and WiFi: WIFI OFF over the cable, and the
      // page still opened wifi:10.126.95.70 - because a route only turns stale
      // after a SWEEP fails, and until the next sweep the hub still believed
      // it. The board was saying `wifi_mode: off` in the same breath, over the
      // cable, and the line below was overwriting that honest answer with
      // 'sta'. A board saying its own radio is off beats a cached sweep result
      // every time: it is newer, and it is first-hand.
      const radioOff = (m.wifi_mode||'') === 'off';
      const shown = Object.assign({}, m, {wifi_mode: wifi ? 'sta' : (m.wifi_mode||''),
                                          radioOff: radioOff,
                                          wifiSeen: !!wifi && !wifi.stale && !radioOff,
                                          ip: wifi ? wifi.ip : (m.ip||'')});
      const port = cable ? cable.port : null;
      const bus = cable && cable.kind==='rs485' ? cable.bus : 0;
      el.appendChild(modRow(shown, m.sd?'SD':'', port, bus, null, far));
      if(home) home.appendChild(modRow(shown, m.sd?'SD':'', port, bus, null, far,
                                       {via: false}));
    });
  // The filter is applied to ROWS, so a repaint has to re-apply it or a
  // pin would silently un-hide everything the person had filtered out.
  filterMods();
  // Keep the last-good markup in step with what is on screen. The error path
  // in scan() restores `modsHtml` when a sweep fails; without this line a pin
  // made between two scans would vanish the moment one failed - the rows would
  // come back in the old order with the old star, while localStorage still
  // held the pin. That reads as the pin not having worked.
  //
  // `modsAt` is deliberately NOT touched: it records when the DATA was
  // fetched, and a repaint learns nothing new about the rig. Moving it would
  // make stale rows claim to be fresh, which is the one thing the stale
  // banner exists to prevent.
  modsHtml = el.innerHTML;
}
// HOW this module is reached, in words, one line per way in. Asked for
// 2026-08-21: *the other like this pc can see the module from which module or
// other make it below*. It used to be a heading over a separate list ("On
// other PCs"), which turned one robot into two rows; as a detail under the row
// it says the same thing without splitting the board in half.
// ADDRESSES stay inside .tech, which the "technical detail" switch hides: an
// IP is the thing this page agreed to keep out of a normal person's way, and a
// new line that prints one in plain text undoes that everywhere at once.
// Which PC, and which cable, are not addresses - they are how you tell one
// robot from another, so they stay.
function viaHtml(r, me){
  const where = (!r.host || r.host === me || r.mine) ? 'this PC' : r.host;
  const tech = function(s){ return '<span class="tech">' + esc(s) + '</span>'; };
  if(r.kind === 'wifi')  return 'over WiFi' + tech(' · ' + (r.ip || '?'));
  if(r.kind === 'usb')   return 'cable ' + esc(r.port || '?') + ' · ' + esc(where);
  if(r.kind === 'rs485') return 'RS485 #' + esc(r.bus != null ? r.bus : '?')
                              + ' behind ' + esc(r.port || '?') + ' · ' + esc(where);
  if(r.kind === 'hub'){
    const tail = String(r.dev || '').split('/').slice(1).join('/');
    return 'through ' + esc(r.host || 'another PC')
         + (tail ? tech(' · ' + tail.replace('usb:', 'cable ')) : '');
  }
  return esc(r.kind || 'unknown');
}
// `opts.via === false` draws the row without its ways-in line: that detail
// belongs on the Modules tab, and Home is the screen somebody glances at.
function modRow(m,extra,port,busId,peer,far,opts){
  opts = opts || {};
  const d=document.createElement('div');d.className='mod';
  // The type colour on the row's left edge. mice.css has styled `.mod.t-nong`,
  // `.t-lift` and `.t-cam` for a long time and NOTHING ever added those
  // classes - modRow only ever set `mod` - so every board has been showing the
  // default grey and the colour coding never once worked. Found 2026-08-20 by
  // grepping for who sets them: only the stylesheet mentions them.
  //
  // Sanitised rather than escaped: a type comes off the wire from a board and
  // classList.add throws on a string with a space in it, which would take the
  // whole row down. esc() is the right tool for markup and the wrong one here.
  const tyClass=String(m.type||'').replace(/[^a-z0-9-]/gi,'');
  if(tyClass) d.classList.add('t-'+tyClass);
  // A board that missed a sweep is LATE, not gone. The hub keeps it listed for
  // a grace period (see Finder.grace) because the venue WiFi drops - and the
  // row has to say so, or a lingering row is just a nicer-looking lie. It is
  // marked in words as well as colour: never colour alone.
  if(m.stale) d.classList.add('late');
  // Everything here comes off the wire from a board, so it goes through esc()
  // like the rest of the page. A module name is user-settable (SET NAME, the
  // module site) and any board on the same WiFi answers the sweep — an
  // unescaped name lands inside a class attribute and inside markup, in the
  // one page that holds every serial port and the flash API.
  // THE STALE NOTE IS ITS OWN SLOT, not more text inside .ip. Inside, it made
  // the meta line longer, the line wrapped, the row grew and every row below
  // jumped down the page. Keeping .ip to one line fixed the jump but then
  // clipped the note itself away — a page that has stopped shifting and
  // started lying. As a separate flex item that never shrinks it is always
  // readable, and the technical tail is what truncates instead.
  d.innerHTML=`<span class="nm">${esc(m.name||'?')}</span>
    <span class="ty ${esc(m.type||'')}">${esc(m.type||'?')}</span>
    <span class="ip">#${esc(m.id!=null?m.id:'?')}${extra?' · '+esc(extra):''}<span class="tech">${
      m.ip?' · '+esc(m.ip):''}</span></span>${
      m.stale ? '<span class="state-stale">last answered '+
                esc(m.lastSeen!=null?m.lastSeen+'s ago':'a while ago')+'</span>' : ''}${
      openedText(m) ? '<span class="mini opened">'+esc(openedText(m))+'</span>' : ''}`;
  // The pin, first in the row so the pinned ones are scannable down one edge.
  // It is a toggle and it says which state it is in, in WORDS as well as the
  // symbol - a filled star against an outlined one is not a difference
  // everybody can see, and this page never uses colour or shape alone.
  if(m.id!=null){
    const pin=document.createElement('button');
    pin.className='pin'+(isPinned(m.id)?' on':'');
    pin.setAttribute('aria-pressed', isPinned(m.id)?'true':'false');
    pin.textContent=isPinned(m.id)?'★':'☆';
    pin.title=(isPinned(m.id)?'Pinned — click to unpin. ':'Pin this module. ')
             +'Pinned modules are listed first, on this computer only.';
    pin.onclick=(ev)=>{ ev.stopPropagation(); togglePin(m.id);
      // Repaint from what is already known rather than re-scanning the
      // network: a pin is a local preference and must not cost a sweep of
      // the venue WiFi, which takes seconds and hits every board.
      repaintMods(); };
    d.insertBefore(pin, d.firstChild);
  }

  // ONE site for every transport: the module's own website, served by the hub
  // with a transport shim (?dev=wifi:<ip> | usb:<port>[:<id>]). Same UI, same
  // config, same login — no matter how the module is reached.
  // `peer` = this module is not on the cable itself; it is on the HOTSPOT of
  // the module that is. With no venue WiFi that is the only way to reach it,
  // and "@name" is all the hub needs to route every call through the middle
  // module (see parse_dev in main.py). Everything below — the module site,
  // Studio, file transfer — then works unchanged.
  // A board this PC cannot reach itself is still openable THROUGH the PC that
  // holds it - the hub passes every call on, which is what `hub:<ip>/<dev>`
  // means. Last, because a way in that goes through one more machine is one
  // more thing that can be switched off.
  // WiFi only outranks the cable when the hub ACTUALLY reached the board that
  // way this sweep (wifiSeen). A claimed IP from a cable probe is not a route:
  // it sent people to an address on a network this PC may not be on, while the
  // cable that was working sat unused (A26-7, user: *hub can see it via rs485
  // but cannot control the robot*).
  const byWifi = m.wifiSeen && m.ip;
  // More than one way in on THIS PC: let the hub pick the fastest on every
  // call (auto:), so the page follows the board if the best route changes.
  // Studio also understands auto:, so its commands and monitor keep following.
  const local = (m.routes||[]).filter(function(r){
    return !r.stale && (r.kind==='usb'||r.kind==='rs485'||r.kind==='wifi'); });
  const auto = (!peer && m.key && m.best && local.length > 1) ? ('auto:'+m.key) : '';
  const dev=peer?('usb:'+port+'@'+peer)
    :auto?auto
    :byWifi?('wifi:'+m.ip)
    :(port?('usb:'+port+(busId?(':'+busId):''))
    :((m.wifi_mode==='sta'&&m.ip&&!m.radioOff)?('wifi:'+m.ip)
    :((far&&far.dev)?far.dev:'')));
  if(dev){
    const open=document.createElement('button');open.className='primary';
    open.textContent='⚙ Open module';
    open.title='the full module site (control + setup + pins) over '+(auto?'the fastest way in (the hub keeps choosing)':dev.indexOf('wifi')===0?'WiFi':'USB/RS485');
    open.onclick=()=>{ rememberOpened(dev, m.name||('#'+m.id), m.key);
      window.open('/mod?dev='+encodeURIComponent(dev)+'&name='+encodeURIComponent(m.name||''),'_blank'); };
    d.appendChild(open);
  }
  if(m.wifi_mode==='sta'&&m.ip){
    const open=document.createElement('button');
    open.textContent='direct';
    open.title='open the module\'s website directly (no hub) — same site';
    open.onclick=()=>window.open('http://'+m.ip+'/','_blank');
    d.appendChild(open);
  }else if(m.wifi_mode==='ap'){
    const s=document.createElement('span');s.className='mini';
    // Named "the USB page" until 2026-08-18, which was a page nothing linked
    // to and which redirected away — instructions pointing at a dead end. The
    // module's own website is the same site over WiFi and over the cable, so
    // say where it actually is: plug the board in and it appears below.
    s.textContent='⚠ hosts its OWN hotspot ('+(m.ip||'192.168.4.1')+') — join that WiFi to open the site, or plug it into this PC: it appears under "plugged in by cable" below, where you can set the real WiFi';
    d.appendChild(s);
  }else if(!port){
    const s=document.createElement('span');s.className='mini';
    s.textContent='WiFi off';
    d.appendChild(s);
  }
  // Nong Studio on the same link as the module site. Over USB it uses the
  // hub's shared port proxy, so Studio and "⚙ Open module" can BOTH be open
  // on that one cable — no "serial port already in use".
  if(m.type==='nong'&&dev){
    const sdev = auto ? 'auto:'+m.key : dev;
    const st=document.createElement('button');st.className='primary';
    st.textContent='Studio + monitor';
    st.title=auto?'pose editor + live 3D over the fastest route, switching when a faster route takes over'
      :'pose editor + live 3D over '+(sdev.indexOf('wifi')===0?'WiFi':'this USB cable (shared — the module site can stay open too)');
    st.onclick=()=>window.open('/studio/?dev='+encodeURIComponent(sdev)+'&monitor=1','_blank');
    d.appendChild(st);
  }
  // Update over WiFi. The board has two app slots, so the firmware being
  // replaced is never the one running: a failed or half-sent update leaves it
  // booting what it already had. Offered only on a module we can actually
  // reach by IP — over its own hotspot the PC is on that hotspot anyway.
  // Offered on a BLANK board too. It used to be hidden for type "blank", which
  // is backwards: a blank board is exactly the one that needs new firmware and
  // a type. A board reports blank whenever its stored type is not in the binary
  // it is running — the normal state after being flashed as something new — and
  // hiding this button left no way to finish the job without finding a cable.
  if(m.wifi_mode==='sta'&&m.ip){
    // The row is where you NOTICE a board needs new firmware, so the way there
    // stays here — but the writing itself happens on one screen. Three ways to
    // do the least undoable thing in the product is how they drift apart.
    const ota=document.createElement('button');
    ota.textContent='⚡ firmware…';
    ota.title=(m.type&&m.type!=='blank')
      ? 'open Firmware to write this PC\'s '+m.type+' build to '+m.ip
      : 'this board has no module type yet — open Firmware to give it one';
    ota.onclick=()=>showTab('firmware');
    d.appendChild(ota);
  }
  if(m.type==='lift'&&(port||(m.wifi_mode==='sta'&&m.ip))){
    const rb=document.createElement('button');
    rb.textContent='💡 RGB';
    rb.title='RGB modes: manual / effects / SD sequence / follow the PC speaker';
    const target=(m.wifi_mode==='sta'&&m.ip)?('ip='+encodeURIComponent(m.ip))
      :('port='+encodeURIComponent(port)+(busId?('&id='+busId):''));
    rb.onclick=()=>window.open('/rgb.html?'+target+'&name='+encodeURIComponent(m.name||''),'_blank');
    d.appendChild(rb);
  }
  // ...and, underneath, every way this board can be reached. One line each, so
  // "it is on the other laptop" is a fact about THIS module rather than a
  // second list of modules somewhere else on the page.
  if(m.routes && m.routes.length && opts.via !== false){
    const via=document.createElement('div');
    via.className='via';
    // which way is fastest is measured by the hub (A26-79): the one in use
    // says so in plain words, the milliseconds sit behind the technical switch
    via.innerHTML='reached ' + m.routes.map(function(r){
      const ms = r.ms != null ? '<span class="tech"> · ' + esc(r.ms) + ' ms</span>' : '';
      const used = (m.best && r.dev === m.best && m.routes.length > 1) ? ' <b>(fastest, in use)</b>' : '';
      return viaHtml(r, window.MODS_HOST || '') + ms + used; }).join('&nbsp; · &nbsp;');
    d.appendChild(via);
  }
  return d;
}
// streaming probe: one request PER port, each slot fills in the moment its
// port answers — fast ports never wait for slow ones, order stays stable
