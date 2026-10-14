// ---- complaints screen --------------------------------------------------
// Loads /api/reports, renders newest first. One line per report, click for full.
// Shows English translation (text_en) in the list, original + translation in detail.
// Fixed / Not-a-problem closes it (updates status, file stays).
async function loadComplaints(){
  var el = document.getElementById('complaintsList');
  if(!el) return;
  el.textContent = 'loading…';
  try{
    const r = await fetch('/api/reports').then(x => x.json());
    var list = r.reports || [];
    if(!list.length){
      el.innerHTML = '<div class="mini">No reports yet.</div>';
      return;
    }
    el.innerHTML = '';
    list.forEach(function(rep){
      var row = document.createElement('div');
      row.className = 'mod';
      row.style.cursor = 'pointer';
      row.style.borderLeftColor = rep.status === 'fixed' ? 'var(--ok)' :
                                    rep.status === 'not-a-problem' ? 'var(--mut)' : 'var(--warn)';
      // Use English translation for the preview
      var displayText = rep.text_en || rep.text || '';
      var short = displayText.slice(0, 120);
      if(displayText.length > 120) short += '…';
      row.innerHTML =
        '<span class="nm">' + esc(rep.time ? rep.time.replace('T', ' ').slice(0, 19) : '?') + '</span>' +
        '<span class="ip tech">' + esc(rep.module || 'no module') + '</span>' +
        '<span class="mini" style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
          esc(short) + '</span>';
      row.onclick = function(){ openComplaintDetail(rep); };
      // The whole row answers a click, so it must say where the keyboard does
      // the same job: a real button inside it, named by data-keyboard.
      row.dataset.keyboard = 'button';
      var open = document.createElement('button');
      open.className = 'linky';
      open.textContent = 'open';
      open.title = 'Read the full report and reply';
      open.onclick = function(){ openComplaintDetail(rep); };
      row.appendChild(open);
      el.appendChild(row);
    });
  }catch(e){
    el.textContent = 'Failed to load: ' + (e && e.message || e);
  }
}

function openComplaintDetail(rep){
  var m = document.getElementById('reportModal');
  if(!m) return;
  document.getElementById('reportTitle').textContent = '📋 Complaint detail';
  var t = document.getElementById('reportText');
  // Show both original and English translation
  var original = rep.text || '';
  var translated = rep.text_en || '';
  if (translated && translated !== original && translated !== "(translation unavailable)") {
    t.value = 'Original:\n' + original + '\n\nEnglish:\n' + translated;
  } else {
    t.value = original;
  }
  t.readOnly = true;
  var chk = document.getElementById('reportAttachDiag');
  chk.hidden = true;
  var busy = document.getElementById('reportBusy');
  if(busy) busy.classList.remove('show');
  var send = document.getElementById('reportSend');
  if(send){ send.hidden = true; }
  // Add status buttons
  var actions = m.querySelector('.report-actions');
  if(actions){
    var old = actions.querySelector('.status-btns');
    if(old) old.remove();
    var btns = document.createElement('div');
    btns.className = 'status-btns';
    btns.style.display = 'flex';
    btns.style.gap = '8px';
    btns.style.marginTop = '8px';
    var st = rep.status || 'open';
    ['fixed', 'not-a-problem', 'open'].forEach(function(s){
      var b = document.createElement('button');
      b.className = (st === s ? 'primary' : 'secondary');
      b.style.flex = '1';
      b.textContent = s === 'fixed' ? '✓ Fixed' : s === 'not-a-problem' ? '⦻ Not a problem' : '↺ Reopen';
      b.onclick = function(){ setComplaintStatus(rep.id, s); };
      btns.appendChild(b);
    });
    actions.insertBefore(btns, actions.firstChild);
  }
  m.hidden = false;
}

async function setComplaintStatus(id, status){
  // The ANSWER decides, not the fact that a request was sent. This closed the
  // box and reloaded the list whatever came back, so a refusal (not logged in,
  // hub busy) read as saved (panel finding, verified 2026-09-08).
  const el = document.getElementById('reportSaid');
  try{
    const r = await fetch('/api/reports', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: id, status: status})
    });
    const said = await r.json().catch(() => ({}));
    if (!r.ok || said.ok === false){
      const why = said.need_login
        ? 'log in first — the button at the top right — then set it again'
        : (said.error || 'the hub would not change it');
      if (el) el.textContent = why; else alert(why);
      return;
    }
    closeReport();
    loadComplaints();
  }catch(e){
    const why = 'the hub is not answering. Check it is still running, then try again.';
    if (el) el.textContent = why; else alert(why);
  }
}

// Report modal — anyone can send, no login, stored machine-local, never promoted.
// Lost with a duplicate-closeReport cleanup on 2026-08-25 and restored from
// patch 0003: closeReport() first so a complaint's retitled heading never
// leaks onto a fresh report.
function openReport(){
  closeReport();
  var m = document.getElementById('reportModal');
  if(!m) return;
  m.hidden = false;
  var t = document.getElementById('reportText');
  if(t){ t.focus(); }
}
function closeReport(){
  var m = document.getElementById('reportModal');
  if(m) m.hidden = true;
  // complaint detail retitles the modal - without this reset the next
  // report opens under yesterday's heading
  var title = document.getElementById('reportTitle');
  if(title) title.textContent = '🐛 Report a problem';
  var t = document.getElementById('reportText');
  if(t){ t.value = ''; t.readOnly = false; }
  var chk = document.getElementById('reportAttachDiag');
  if(chk){ chk.hidden = false; chk.checked = true; }
  var busy = document.getElementById('reportBusy');
  if(busy) busy.classList.remove('show');
  var send = document.getElementById('reportSend');
  if(send){ send.hidden = false; send.disabled = false; send.textContent = 'Send report'; }
  var actions = m && m.querySelector('.report-actions');
  if(actions){
    var btns = actions.querySelector('.status-btns');
    if(btns) btns.remove();
  }
}
onTab('complaints', loadComplaints);
