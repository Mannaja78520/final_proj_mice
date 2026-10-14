// ---- flashing: say what is about to be overwritten, and where -------
// Which PC this hub is. Several machines on one network run this same page,
// and the operator can easily be on the wrong tab — so the confirm says the
// machine by name rather than only naming a COM port.
var MY_PC = '';
// Asked for at load so the page can show it straight away. The flash confirm
// does NOT rely on this having arrived — see whoAmI().
fetch('/api/mine').then(r => r.json()).then(j => { MY_PC = j.host || ''; })
                  .catch(() => {});

var _fcResolve = null;

function fcRow(label, value){
  return '<span class="lbl">' + esc(label) + '</span><span>' + value + '</span>';
}

// Returns a promise: true to go ahead, false to leave the board alone.
// WHICH machine is about to overwrite a board's firmware. Never guessed.
//
// The confirm used to print `MY_PC || 'this PC'`, and MY_PC is filled by a
// fetch at page load — so a quick click showed a dialog with the machine's
// name missing, which is the single fact it exists to state. Overwriting
// firmware is not undoable and the board may be in someone else's hands, so
// this waits for the name instead of shrugging, and says so plainly if the
// hub genuinely cannot answer.
async function whoAmI(){
  if (MY_PC) return MY_PC;
  try{
    const j = await fetch('/api/mine').then(r => r.json());
    MY_PC = j.host || '';
  }catch(e){ /* fall through to the honest wording below */ }
  return MY_PC || 'this PC (the hub did not give its name)';
}

async function confirmFlash(o){
  const pcName = await whoAmI();
  const m = $('flashModal');
  $('fcMeta').innerHTML =
      fcRow('Board', '<b>' + esc(o.name || 'unnamed') + '</b>' +
                     (o.id ? ' · #' + esc(String(o.id)) : '') +
                     (o.now ? ' · runs <b>' + esc(o.now) + '</b> now' : '')) +
      fcRow('Becomes', '<b>' + esc(o.type) + '</b>') +
      fcRow('Over', esc(o.via)) +
      fcRow('From this PC', '<b>' + esc(pcName) + '</b>');

  const changing = o.now && o.type && o.now !== o.type;
  $('fcChange').hidden = !changing;
  if (changing)
    $('fcChange').textContent =
      '⚠ TYPE CHANGE — it runs "' + o.now + '" now and will become "' + o.type +
      '". It reboots to apply that.';
  $('fcCost').textContent = o.cost || '';

  // The login half, shown only when the write happens somewhere else.
  $('fcLogin').hidden = !o.login;
  if (o.login) {
    $('fcLoginWhy').textContent =
      o.login + ' has its own accounts. This is used once, to send the ' +
      'firmware, and is not kept.';
    $('fcUser').value = ''; $('fcPass').value = '';
  }

  $('fcAsk').hidden = false;
  $('fcWorking').hidden = true;
  $('fcOk').hidden = true;
  $('fcErr').hidden = true;
  m.hidden = false;
  $('fcCancel').focus();               // a dialog that opens takes the keyboard
  return new Promise(res => { _fcResolve = res; });
}

// What was typed into the panel, read once by the caller straight after it
// resolves. Kept out of the resolved value so every existing caller keeps its
// simple true/false, and cleared as soon as it has been used.
let _fcLogin = {user: '', password: ''};

function fcClose(answer){
  _fcLogin = answer
    ? {user: $('fcUser').value, password: $('fcPass').value}
    : {user: '', password: ''};
  $('flashModal').hidden = true;
  const r = _fcResolve; _fcResolve = null;
  if (r) r(!!answer);
}

// Working / finished / failed, so the panel keeps telling the truth while the
// minute passes instead of vanishing the moment it is confirmed.
function fcWorking(stage, pct){
  $('fcAsk').hidden = true; $('fcErr').hidden = true; $('fcOk').hidden = true;
  $('fcWorking').hidden = false;
  $('flashModal').hidden = false;
  $('fcStage').textContent = stage || 'working…';
  if (typeof pct === 'number') $('fcBar').style.width = Math.max(0, Math.min(100, pct)) + '%';
}
function fcDone(msg){
  $('fcWorking').hidden = true; $('fcOk').hidden = false;
  $('fcOkMsg').textContent = '✓ ' + msg;
}
function fcFailed(why){
  $('fcWorking').hidden = true; $('fcErr').hidden = false;
  $('fcErrMsg').textContent = '⚠ ' + why;
}

$('fcCancel').onclick = () => fcClose(false);
$('fcGo').onclick = () => fcClose(true);
$('fcClose').onclick = () => { $('flashModal').hidden = true; };
$('fcErrClose').onclick = () => { $('flashModal').hidden = true; };
$('fcRetry').onclick = () => { $('fcErr').hidden = true; $('fcAsk').hidden = false; };
// Escape cancels. A modal a keyboard user cannot leave is a trap, and the safe
// answer is the one that should be easiest to give.
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !$('flashModal').hidden){
    if (_fcResolve) fcClose(false); else $('flashModal').hidden = true;
  }
});

