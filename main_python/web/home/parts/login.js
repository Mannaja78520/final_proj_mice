// ---- logging in -------------------------------------------------------
// hub.html had no element helper — every other line spells getElementById out.
// One here, used only by the login code, so nothing existing changes meaning.
function $(id){ return document.getElementById(id); }

// The gate is on the hub, not here: this only decides what the page SAYS.
// Hiding a button would be a lie anyway — the route is what is protected.
var authed = false;

// ONE place that knows whether somebody is signed in. Four places used to set
// `authed` and each had to remember every consequence itself; when the sign-in
// box was added three of them forgot it, so signing out left every card on
// screen unlocked. Adding the next consequence is one line, here.
function setAuthed(v){
  authed = !!v;
  $('loginCard').hidden = authed;
  $('logoutBtn').hidden = !authed;
  if (!authed) {
    if ($('loginUser') && document.activeElement !== $('loginUser')) $('loginUser').value = '';
    if ($('loginPass') && document.activeElement !== $('loginPass')) $('loginPass').value = '';
  }
  // Cards marked data-needs-login show a sign-in box instead of themselves.
  // This page keeps its own login card rather than mounting miceLogin, because
  // it carries the first-run and locked-out banners no other page has.
  if (window.miceGate) miceGate.apply(authed);
}

// Calls to the hub go through Mice.Api (shared/web/mice-ui.js): it never
// throws, so there is no empty catch, and its `says` is already in words.
async function refreshAuth(){
  const a = await Mice.Api.get('/api/whoami');
  if (!a.ok) return;          // unreachable: the module list says so already
  setAuthed(a.data.authed);
  if (a.data.locked_for > 0) showLock(a.data.locked_for);
}

function showLock(secs){
  const el = $('loginLock');
  el.hidden = false;
  $('loginErr').hidden = true;
  // The number comes from the hub. A page that counts down its own guess is
  // telling the operator something untrue while they are already annoyed.
  const tick = () => {
    if (secs <= 0){ el.hidden = true; return; }
    el.textContent = '⏳ Too many tries. Wait ' + secs + 's before trying again.';
    secs--; setTimeout(tick, 1000);
  };
  tick();
}

async function doLogin(ev){
  ev.preventDefault();
  const pass = $('loginPass').value;
  $('loginBusy').hidden = false;
  $('loginBtn').disabled = true;
  $('loginErr').hidden = true;
  // The user field is optional: a hub upgraded from the single-password
  // version has one account, and leaving it blank logs into that one.
  const who = $('loginUser') ? $('loginUser').value.trim() : '';
  const a = await Mice.Api.post('/api/login', {user: who, password: pass},
                                {timeout: 20000});
  $('loginBusy').hidden = true;
  $('loginBtn').disabled = false;
  if (a.ok){
    $('loginPass').value = '';
    setAuthed(true);
    scan(true);                       // the page can do more now — show it
    pairPaint();                      // ...including pairing this PC
  } else if (a.data.locked_for > 0){
    showLock(a.data.locked_for);
  } else {
    $('loginErr').hidden = false;
    // A refusal carries the hub's own reason; no answer at all says so.
    $('loginErr').textContent = '⚠ ' + (a.status ? (a.data.error || 'that did not work') : a.says);
  }
}

async function doLogout(){
  await Mice.Api.post('/api/logout');
  setAuthed(false);
  $('pairBox').hidden = true;           // its every button would now 401
}

// Any refused action reveals the card and says why, rather than failing
// silently or blaming the network. One wrapper, so a new call cannot forget.
(function(){
  const of = window.fetch.bind(window);
  window.fetch = async function(u, o){
    const r = await of(u, o);
    if (r.status === 401){
      setAuthed(false);
      $('loginErr').hidden = false;
      $('loginErr').textContent = '⚠ log in first — that action changes something';
      $('loginCard').scrollIntoView({block:'nearest'});
    }
    return r;
  };
})();
refreshAuth();

