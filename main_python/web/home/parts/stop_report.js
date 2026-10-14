// One press stops the show clock and every board the hub can reach. The clock
// first: stopping the boards while it runs means the next tick starts them
// again. See /api/stopall, which is deliberately never behind the login.
var stopping = false;
async function stopEverything(){
  var b = document.getElementById('stopAll');
  var said = document.getElementById('stopSaid');
  if(b){ b.textContent = '⏹ STOPPING…'; }
  stopping = true;
  try{
    const r = await fetch('/api/stopall', {method:'POST'}).then(x=>x.json());
    var n = (r.stopped||[]).length, bad = (r.failed||[]);
    said.className = 'banner ' + (bad.length ? 'warn' : 'ok');
    said.textContent = bad.length
      ? ('Stopped ' + n + ', but could NOT reach: ' + bad.join(', ') +
         ' — use the power switch for those.')
      : ('Stopped: ' + (n ? (r.stopped||[]).join(', ') : 'nothing was moving') + '.');
    said.hidden = false;
  }catch(e){
    // A stop that failed must SHOUT. Silence here reads as "it worked".
    said.className = 'banner err';
    said.textContent = 'The stop did not reach the hub (' + (e.message||e) +
                       '). Use the power switch.';
    said.hidden = false;
  }finally{
    stopping = false;
    if(b){ b.textContent = '⏹ STOP'; }
  }
}

// Report modal — anyone can send, no login, stored machine-local, never promoted.
// openReport/closeReport live further down, with the complaints screen they
// share the modal with - one definition each, or the last silently wins.
async function submitReport(){
  var text = document.getElementById('reportText');
  var busy = document.getElementById('reportBusy');
  var send = document.getElementById('reportSend');
  if(!text || !text.value.trim()){
    alert('Write what happened first.');
    return;
  }
  if(busy) busy.classList.add('show');
  if(send){ send.disabled = true; send.textContent = 'Sending…'; }
  try{
    var payload = {
      text: text.value.trim(),
      page: location.pathname + location.search,
      module: (window.CURRENT_MOD && window.CURRENT_MOD.id) || '',
      build: (window.BUILD_VER || ''),
      time: new Date().toISOString(),
      attachDiag: document.getElementById('reportAttachDiag').checked
    };
    const r = await fetch('/api/report', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    }).then(x => x.json());
    if(r && r.ok){
      closeReport();
      // Briefly show success in the stop banner area
      var said = document.getElementById('stopSaid');
      if(said){
        said.className = 'banner ok';
        said.textContent = 'Report sent — thank you.';
        said.hidden = false;
        setTimeout(function(){ said.hidden = true; }, 5000);
      }
    }else{
      throw new Error((r && r.error) || 'server said no');
    }
  }catch(e){
    if(busy) busy.classList.remove('show');
    if(send){ send.disabled = false; send.textContent = 'Send report'; }
    var here = document.getElementById('reportSaid');
    if(here) here.textContent = 'That did not send. Try again, or copy your '
      + 'text somewhere safe and send it later.';
    var said = document.getElementById('stopSaid');
    if(said){
      said.className = 'banner err';
      said.textContent = 'Report failed (' + (e.message||e) + '). Try again or copy the text and email it.';
      said.hidden = false;
    }
  }
}
