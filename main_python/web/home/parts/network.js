// ---- network & linking -------------------------------------------------
// Every module the hub can reach, however it is reached, with the group it
// belongs to. Tick the ones that belong together and give them a group name:
// that is the whole linking step.
var netMods = [];
var netBusy = false;
// Other hubs: what a sweep found, plus what a person named. Both are shown
// the same way, because to the person using it there is no difference - it is
// another PC with boards on it either way.
async function loadHubs(force){
  const el = $('hubList');
  el.className = force ? 'spin' : '';
  if (force) el.textContent = 'searching this network…';
  try{
    const r = await fetch('/api/hubs' + (force ? '?force=1' : '')).then(x => x.json());
    const found = r.hubs || [], named = r.known || [];
    el.innerHTML = '';
    if (!found.length && !named.length) {
      el.innerHTML = '<span class="mini">No other PC found yet. If one is on a '
        + 'different network, type its address below - a search only covers '
        + 'this PC' + String.fromCharCode(39) + 's own network.</span>';
      return;
    }
    found.forEach(function(h){
      const ip = h.ip || h;
      const row = document.createElement('div');
      row.className = 'mod';
      const a = document.createElement('a');
      a.href = 'http://' + ip + ':' + (h.port || location.port || 8642) + '/';
      a.target = '_blank';
      a.className = 'nm';
      a.textContent = h.host || h.name || ip;   // its OWN name, not one to remember
      row.appendChild(a);
      const where = document.createElement('span');
      where.className = 'ip tech';
      where.textContent = ip;
      row.appendChild(where);
      if (named.indexOf(ip) >= 0) {
        const drop = document.createElement('button');
        drop.className = 'danger';
        drop.textContent = 'forget';
        drop.onclick = function(){ addHub(ip, true); };
        row.appendChild(drop);
      }
      el.appendChild(row);
    });
    // Named but not answering: say so rather than leaving it out, or someone
    // types the same address again wondering why nothing happened.
    named.filter(function(ip){
      return !found.some(function(h){ return (h.ip || h) === ip; });
    }).forEach(function(ip){
      const row = document.createElement('div');
      row.className = 'mod';
      row.innerHTML = '<span class="nm">' + esc(ip) + '</span>'
        + '<span class="ip">added, but not answering</span>';
      const drop = document.createElement('button');
      drop.className = 'danger';
      drop.textContent = 'forget';
      drop.onclick = function(){ addHub(ip, true); };
      row.appendChild(drop);
      el.appendChild(row);
    });
  }catch(e){
    el.innerHTML = '<div class="banner err" role="alert">Could not ask this hub '
      + 'about other PCs. <button onclick="loadHubs(true)">Try again</button></div>';
  }
}

async function addHub(ip, forget){
  const box = $('hubAdd');
  const addr = ip || (box ? box.value.trim() : '');
  if (!addr) { $('hubStat').textContent = 'type the other PC' + String.fromCharCode(39) + 's address first'; return; }
  $('hubStat').textContent = forget ? 'forgetting…' : 'adding…';
  try{
    const r = await fetch('/api/hubs/' + (forget ? 'forget' : 'add'),
      {method:'POST', body: JSON.stringify({ip: addr})}).then(x => x.json());
    if (r.ok === false) { $('hubStat').textContent = r.error || 'refused'; return; }
    $('hubStat').textContent = '';
    if (box && !forget) box.value = '';
    loadHubs(true);
  }catch(e){ $('hubStat').textContent = 'the hub did not answer'; }
}

async function loadNet(){
  var box = document.getElementById('netlist');
  if(!box) return;
  // Clicking the Network tab starts a full probe of every cable. Without a
  // guard, clicking it a few times ran several overlapping probes, each
  // holding port locks and each writing its answer into the same list — the
  // slowest one won, whichever was actually correct.
  if(netBusy) return;
  netBusy = true;
  box.className = 'spin'; box.textContent = 'looking for modules…';
  var out = [], failed = 0;
  try{
    var r = await fetch('/api/scan').then(x=>x.json());
    (r.modules||[]).forEach(function(m){
      out.push({dev:'wifi:'+m.ip, label:m.name, type:m.type, via:m.ip, group:m.group||''});
    });
  }catch(e){ failed++; }
  try{
    // /api/ports is only the TYPED port list — it carries no identity until a
    // port is actually probed, so reading it alone showed every module as
    // unnamed and ungrouped. /api/scanusb is what opens the cable and asks.
    var p = await fetch('/api/ports').then(x=>x.json());
    var real = (p.ports||[]).filter(function(x){ return !x.bt; });
    var probes = real.map(function(x){
      return fetch('/api/scanusb?port='+encodeURIComponent(x.port))
        .then(function(r){ return r.json(); })
        .then(function(r){ return (r.usb&&r.usb[0])||null; })
        .catch(function(){ return null; });
    });
    (await Promise.all(probes)).forEach(function(u){
      if(!u || !u.module) return;
      out.push({dev:'usb:'+u.port, label:u.module.name||u.port,
                type:u.module.type||'', via:u.port,
                group:u.module.group||''});
      // modules living BEHIND this one on RS485 count too
      (u.rs485||[]).forEach(function(b){
        out.push({dev:'usb:'+u.port+':'+b.id, label:b.name||('id '+b.id),
                  type:b.type||'', via:u.port+' #'+b.id, group:b.group||''});
      });
    });
  }catch(e){ failed++; }
  netBusy = false;
  // the same module can answer on WiFi AND on its cable — show it once
  var seen = {}, uniq = [];
  out.forEach(function(m){
    var k = m.label + '|' + m.type;
    if(seen[k]) return;
    seen[k] = 1; uniq.push(m);
  });
  netMods = uniq;
  if(!uniq.length){
    box.className='mini';
    // "Nothing found" and "could not look" are different facts, and saying the
    // first when the second is true is the page lying to the reader. Both
    // scans failing used to render as a confident empty list.
    if(failed >= 2){
      box.setAttribute('role','alert');
      box.innerHTML = 'Could not look for modules — the hub did not answer. '
        + 'Please check if it is running. '
        + '<button onclick="loadNet()">Try again</button>';
    }else{
      box.removeAttribute('role');
      box.textContent = 'We haven\'t found any modules yet. Please plug one in over USB, or put it '
        + 'on this WiFi, then press Refresh.';
    }
    return;
  }
  box.removeAttribute('role');
  box.className = '';
  box.innerHTML = uniq.map(function(m,i){
    return '<label class="netrow" id="netrow'+i+'">'+
      '<input type="checkbox" data-i="'+i+'" onchange="netPick()">'+
      '<span class="who">'+esc(m.label)+'</span>'+
      '<span class="mini">'+esc(m.type||'?')+' · '+esc(m.via)+'</span>'+
      '<span class="grp" style="margin-left:auto">'+
        (m.group ? 'group: '+esc(m.group) : '<i>not linked</i>')+'</span></label>';
  }).join('');
  netPick();
}

function netPick(){
  var picked = [].slice.call(document.querySelectorAll('#netlist input:checked'))
                 .map(function(c){ return parseInt(c.getAttribute('data-i'),10); });
  document.querySelectorAll('#netlist .netrow').forEach(function(el,i){
    el.classList.toggle('sel', picked.indexOf(i)>=0);
  });
  var act = document.getElementById('netact');
  if(!picked.length){
    act.innerHTML = '<div class="mini">Choose the modules you want to work together, '+
      'then give them a group name. Leave out any module that is not yours.</div>';
    return;
  }
  var suggest = '';
  for(var i=0;i<picked.length && !suggest;i++) suggest = netMods[picked[i]].group||'';
  act.innerHTML =
    '<div class="mini"><b>'+picked.length+' selected</b> — they will link to each other and to nobody else.</div>'+
    '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">'+
      '<input id="grpname" placeholder="group name (e.g. mice-show)" value="'+esc(suggest)+'" '+
        'style="flex:1;min-width:180px;padding:var(--sp-2);border-radius:var(--r-sm);border:1px solid var(--line);'+
        'background:var(--card);color:inherit">'+
      '<button onclick="linkSel()">🔗 Link these</button>'+
      '<button class="danger" onclick="unlinkSel()" title="Remove the ticked modules from their '+
      'group. They go back to the shared fallback password.">✂ Unlink the ticked modules</button>'+
    '</div><div id="grpout" class="mini" style="margin-top:8px"></div>';
}

async function groupCmd(dev, cmd){
  var u = '/api/dev/cmd?dev='+encodeURIComponent(dev)+'&c='+encodeURIComponent(cmd);
  try{ return (await fetch(u).then(x=>x.text())).trim(); }
  catch(e){ return 'ERR '+e; }
}

async function applyGroup(name){
  var picked = [].slice.call(document.querySelectorAll('#netlist input:checked'))
                 .map(function(c){ return parseInt(c.getAttribute('data-i'),10); });
  // SNAPSHOT the modules now, by value. Each groupCmd is a real round trip —
  // up to two seconds over a cable — and loadNet() replaces netMods whenever
  // the list refreshes or the tab is re-shown. Reading netMods[i] inside the
  // loop meant a refresh mid-way sent "GROUP <name>" to whatever module had
  // moved into that position: a permanent identity written to the wrong board,
  // which then leaves the installation because its hotspot password is derived
  // from the group name. A shorter list also threw on undefined and left the
  // rest silently unlinked.
  var targets = picked.map(function(i){ return netMods[i]; })
                      .filter(function(m){ return m; });
  var out = document.getElementById('grpout');
  if(!targets.length){ out.textContent = 'Tick the modules you want first.'; return; }
  out.textContent = 'applying…';
  var lines = [];
  for(var k=0;k<targets.length;k++){
    var m = targets[k];
    lines.push(m.label+': '+await groupCmd(m.dev, name ? 'GROUP '+name : 'GROUP CLEAR'));
  }
  out.innerHTML = lines.map(esc).join('<br>');
  loadNet();
}
function linkSel(){
  var n = (document.getElementById('grpname').value||'').trim();
  if(!n){ document.getElementById('grpout').textContent =
    'Type a name in the group box above first, then press this again.'; return; }
  applyGroup(n);
}
// Unlinking is not cosmetic: a module's hotspot password comes from its group
// name, so clearing the group takes that board OUT of the installation and the
// others stop finding it. Name exactly which boards are about to be changed —
// "are you sure?" on its own tells the reader nothing.
function unlinkSel(){
  var picked = [].slice.call(document.querySelectorAll('#netlist input:checked'))
                 .map(function(c){ return netMods[parseInt(c.getAttribute('data-i'),10)]; })
                 .filter(function(m){ return m; });
  if(!picked.length){
    document.getElementById('grpout').textContent =
      'Tick the modules you want to unlink first.';
    return;
  }
  var names = picked.map(function(m){ return '  · ' + m.label; }).join('\n');
  if(!confirm('Remove these ' + picked.length + ' module' +
              (picked.length === 1 ? '' : 's') + ' from their group?\n\n' + names +
              '\n\nEach one goes back to the shared fallback password, so the ' +
              'rest of the installation will no longer find it until it is ' +
              'linked again.')) return;
  applyGroup('');
}

// The address beside the QR. Read from the hub rather than from
// location.href: someone often opens the hub as 127.0.0.1, and 127.0.0.1 is
// the one address on the network that will not work from a phone.
async function paintQr(){
  try{
    const j = await fetch('/api/mine').then(x => x.json());
    const url = j.url || (location.protocol + '//' + location.host + '/');
    $('qrUrl').textContent = url;
    $('qrName').textContent = j.host ? ('this PC is ' + j.host) : '';
    $('qrNameRow').hidden = !j.name_url;
    if (j.name_url) $('qrNameUrl').textContent = j.name_url;
    $('qrWhyNoName').hidden = !!j.name_url;
    if (!j.name_url)
      $('qrWhyNoName').textContent =
        'The name mice.local is not being answered on this PC' +
        (j.name_why ? ' — ' + j.name_why : '') + '. The address above works.';
    // Re-fetch the picture whenever the address could have changed - a laptop
    // that moves between a venue WiFi and its own hotspot gets a new IP, and a
    // QR of the old one sends the phone nowhere.
    $('qrImg').src = '/api/qr?t=' + Date.now();
  }catch(e){ $('qrUrl').textContent = 'the hub did not say what its address is'; }
}
onTab('network', loadNet);
onTab('network', function(){ loadHubs(false); });
onTab('network', paintQr);
