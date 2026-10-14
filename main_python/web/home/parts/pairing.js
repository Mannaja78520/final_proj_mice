// ---- pairing: one login on every PC (A14-1) --------------------------
// Six states in one card, and only one is ever on screen: idle, showing a
// code, typing a code, the name-clash question, done, failed.
var pairTimer = 0;

function pairFace(which){
  ['pairIdle','pairShowing','pairEnter','pairClash','pairDone','pairErrBox']
    .forEach(function(id){ $(id).hidden = (id !== which); });
}

function pairReset(){
  clearTimeout(pairTimer);
  $('pairStat').textContent = '';
  pairFace('pairIdle');
}

async function pairPaint(){
  // THE HUB DECIDES, not the page's own `authed`. A reload that lands on the
  // Network tab paints this card before /api/whoami has answered, so trusting
  // that variable hid the card from someone who was logged in — and only from
  // them, since a stranger sees the same nothing. Asking the gated route
  // answers both questions at once: may I pair, and is a code already live.
  try{
    const r = await fetch('/api/pair/status').then(x => x.json());
    const may = r.ok !== false && !r.need_login;
    $('pairBox').hidden = !may;
    if (!may) return;
    if (r.showing) pairCountdown(r.code, r.seconds); else pairReset();
  }catch(e){ $('pairBox').hidden = true; }
}

function pairCountdown(code, secs){
  $('pairCode').textContent = code;
  pairFace('pairShowing');
  clearTimeout(pairTimer);
  const tick = function(){
    if (secs <= 0){ pairReset(); return; }
    // Minutes and seconds: 240s means nothing to someone holding a phone.
    $('pairLeft').textContent = 'Good for ' + Math.floor(secs / 60) + 'm '
      + ('0' + (secs % 60)).slice(-2) + 's';
    secs--; pairTimer = setTimeout(tick, 1000);
  };
  tick();
}

async function pairShow(){
  try{
    const r = await fetch('/api/pair/start', {method:'POST'}).then(x => x.json());
    if (!r.ok) return pairFailed(r.error || 'the hub refused');
    pairCountdown(r.code, r.seconds);
  }catch(e){ pairFailed('the hub did not answer'); }
}

async function pairStop(){
  try{ await fetch('/api/pair/stop', {method:'POST'}); }catch(e){}
  pairReset();
}

function pairAskCode(){
  pairFace('pairEnter');
  $('pairAddr').focus();
}

function pairFailed(why){
  $('pairErr').textContent = why;
  pairFace('pairErrBox');
}

async function pairLink(replace){
  // The ADDRESS and the CODE are remembered across the clash question: the
  // person answering it typed them a moment ago and must not type them twice.
  const addr = $('pairAddr').value.trim(), code = $('pairInput').value.trim();
  $('pairStat').textContent = 'pairing…';
  try{
    const r = await fetch('/api/pair/link', {method:'POST',
      body: JSON.stringify({ip: addr, code: code, replace: !!replace})})
      .then(x => x.json());
    $('pairStat').textContent = '';
    if (r.ok === false) return pairFailed(r.error || 'refused');
    if ((r.clashed || []).length) return pairClash(r);
    pairDone(r);
  }catch(e){ pairFailed('the hub did not answer'); }
}

function pairClash(r){
  // Named, never a generic warning: WHICH account is the whole question, and
  // the answer decides who can still log in here in a minute.
  const names = (r.clashed || []).join(', ');
  $('pairClashWhy').textContent =
    'This PC already has an account called ' + names + '. Replacing it means '
    + names + ' logs in with the password set on ' + (r.from || 'that PC')
    + ' — and everyone logged in here is logged out. Keeping it leaves that '
    + 'one name different on the two PCs.';
  pairFace('pairClash');
}

function pairDone(r){
  const took = (r.added || []).concat(r.replaced || []);
  $('pairDone').textContent = took.length
    ? ('✓ Paired with ' + (r.from || 'that PC') + ' — ' + took.join(', ')
       + ' can now log in here with the same password.')
    : ('✓ Already paired with ' + (r.from || 'that PC') + ' — nothing to copy.');
  pairFace('pairDone');
  loadUsers();
}

