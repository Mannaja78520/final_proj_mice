// Board numbers card (Modules tab). ES5 on purpose: Android TV Chrome 75 runs it.
var busmapPollTimer = null;
function busmapEsc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function busmapPorts(){
  fetch('/api/ports').then(function(r){ return r.json(); }).then(function(d){
    var sel = document.getElementById('busmapPort');
    if(!sel) return;
    var keep = sel.value, html = '';
    (d.ports || []).forEach(function(p){
      html += '<option value="' + busmapEsc(p.port) + '">' + busmapEsc(p.port)
        + (p.who ? ' — ' + busmapEsc(p.who) : '') + '</option>';
    });
    sel.innerHTML = html || '<option value="">No cable found</option>';
    if(keep) sel.value = keep;
  }).catch(function(){});
}
function busmapRun(fix){
  var port = document.getElementById('busmapPort').value;
  var st = document.getElementById('busmapState');
  if(!port){ st.textContent = 'Pick a cable first.'; return; }
  st.textContent = 'Starting…';
  fetch('/api/busmap/' + (fix ? 'fix' : 'check') + '?port=' + encodeURIComponent(port), {method:'POST'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d && d.ok === false){ st.textContent = d.error || 'Could not start.'; return; }
      busmapPoll(port);
    }).catch(function(){ st.textContent = 'The hub did not answer.'; });
}
function busmapPoll(port){
  clearTimeout(busmapPollTimer);
  fetch('/api/busmap?port=' + encodeURIComponent(port)).then(function(r){ return r.json(); }).then(function(d){
    var st = document.getElementById('busmapState');
    if(d.state === 'running'){
      st.textContent = 'Working: ' + d.step + ' (' + Math.round(d.seconds) + ' s)…';
      busmapPollTimer = setTimeout(function(){ busmapPoll(port); }, 1500);
    } else if(d.state === 'error'){
      st.textContent = 'Could not finish: ' + d.error;
    } else if(d.state === 'done'){
      st.textContent = 'Done in ' + d.seconds + ' s.';
      busmapShow(d.result, port);
    }
  }).catch(function(){});
}
function busmapName(b){
  var n = '#' + b.id + (b.gateway ? ' (connects to more boards)' : '');
  return n;
}
function busmapShow(r, port){
  var out = document.getElementById('busmapOut'), h = '';
  var n = r.boards.length, chains = r.buses.length;
  h += '<p><b>' + n + ' board' + (n === 1 ? '' : 's') + '</b> found'
     + (chains > 1 ? ', on ' + chains + ' linked cables' : '') + '.</p>';
  if(r.duplicates.length){
    h += '<div class="banner err"><b>Some boards share a number.</b><ul>';
    r.duplicates.forEach(function(d){
      h += '<li>Number ' + d.id + (d.bus === 'root' ? '' : ' (behind another board)')
         + ' is used by ' + d.chips.length + ' boards<span class="tech"> — ' + busmapEsc(d.chips.join(', ')) + '</span></li>';
    });
    h += '</ul><button onclick="busmapAsk()">Give them new numbers…</button>'
       + '<span id="busmapAsk" hidden> This changes the number saved inside the boards that share one. '
       + '<button onclick="busmapRun(true)">Yes, change them</button></span></div>';
  } else {
    h += '<p>✅ No two boards share a number.</p>';
  }
  if(r.moved.length){
    h += '<p>Changed ' + r.moved.length + ' board' + (r.moved.length === 1 ? '' : 's')
       + ' to a free number.</p>';
  }
  if(r.failed.length){
    h += '<div class="banner err">Could not change ' + r.failed.length
       + ' board(s). The cable may be full (247 boards) — use another cable.</div>';
  }
  if(r.loops.length){
    h += '<p>⚠ ' + r.loops.length + ' board(s) can be reached two ways (a loop, or one board plugged into two cables). '
       + 'That is fine; the shortest way is used. If it is not on purpose, check the wiring.</p>';
  }
  if(r.tooDeep.length){
    h += '<p>⚠ Boards are chained too deep to reach beyond ' + r.maxHops
       + ' steps. Some are not shown.</p>';
  }
  if(chains > 1){
    h += '<div class="mini">Who is plugged into whom</div>' + busmapTree(r);
  }
  out.innerHTML = h;
}
function busmapAsk(){ document.getElementById('busmapAsk').hidden = false; }
function busmapTree(r){
  var byBus = {};
  r.boards.forEach(function(b){ (byBus[b.bus] = byBus[b.bus] || []).push(b); });
  function node(bus, depth){
    var list = byBus[bus] || [], h = '<ul>';
    list.forEach(function(b){
      h += '<li>' + busmapName(b) + '<span class="tech"> — ' + busmapEsc(b.chip) + ', path ' + busmapEsc(b.path) + '</span>';
      if(b.gateway){
        var gp = b.path.charAt(0) === '>' ? b.path : '>' + b.path;
        if(byBus[gp]) h += node(gp, depth + 1);
      }
      h += '</li>';
    });
    return h + '</ul>';
  }
  var count = (byBus.root || []).length;
  return '<div class="mini">This cable — ' + count + ' board' + (count === 1 ? '' : 's') + '</div>' + node('root', 0);
}
busmapPorts();
