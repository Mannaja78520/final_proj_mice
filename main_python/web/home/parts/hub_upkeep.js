// ---- handing the app to the PC reading this page ----------------------
// Only offered when this hub HAS one: a hub run from source has no exe, and a
// download link that 404s is worse than no link.
async function paintGetApp(){
  const a = $('getApp');
  if (!a) return;
  try{
    const d = await fetch('/api/app/version').then(r => r.json());
    if (!d.sha && !d.bytes) { a.hidden = true; return; }
    a.hidden = false;
    a.textContent = '⬇ Get the hub for this PC (' +
      (d.bytes / 1048576).toFixed(0) + ' MB)';
    a.title = "Run this on the PC with the cable. A browser cannot reach that "
            + "PC's USB ports from here — the program can, and this hub finds "
            + "it by itself once it is running.";
  }catch(e){ a.hidden = true; }
}

// ---- updating the hub itself -----------------------------------------
// Two presses, never one. Checking is safe and says what is offered; the
// replace is a second, separate decision, because it swaps the program the
// person is currently using.
async function checkUpdate(){
  const say = $('updSay');
  say.textContent = 'asking GitHub…';
  let s;
  try{ s = await fetch('/api/selfupdate').then(r => r.json()); }
  catch(e){ say.textContent = '⚠ ' + (e && e.message || e); return; }
  if (!s.can){
    // No internet is the ordinary case at a venue, so this is a plain
    // sentence rather than an error.
    say.textContent = s.why || 'nothing to update';
    return;
  }
  say.textContent = '';
  const line = document.createElement('span');
  line.textContent = 'A newer build is offered: ' + (s.offered || '').slice(0, 12) +
    (s.when ? ' (' + s.when.slice(0, 10) + ')' : '') +
    (s.message ? ' — ' + s.message : '') + '  ';
  const go = document.createElement('button');
  go.className = 'danger';
  go.textContent = '⭳ Replace this hub now';
  go.onclick = async () => {
    go.disabled = true;
    say.textContent = 'downloading…';
    let r;
    try{ r = await fetch('/api/selfupdate', {method: 'POST'}).then(x => x.json()); }
    catch(e){ say.textContent = '⚠ ' + (e && e.message || e); return; }
    say.textContent = (r.ok ? '✓ ' : '⚠ ') + (r.message || '');
  };
  say.appendChild(line);
  say.appendChild(go);
}

// ---- the diagnostics bundle ------------------------------------------
// One button, because the four questions asked after "it does not work" are
// always the same ones and getting them out of somebody over chat takes half
// an hour.
//
// The text is fetched from the hub rather than built here: which PC this is,
// which firmware images are built, whether esptool exists - the page does not
// know any of that, and a bundle assembled from what the browser happens to
// have loaded would be missing exactly the parts that matter.
//
// TWO HALVES (A21-5): the plain summary renders on the card; the technical
// rest shows only under the page-wide technical switch. The Copy button and
// the fallback always carry the WHOLE bundle - support needs both halves.
const DIAG_MARK = '--- technical detail below, for support ---';
function showDiag(text){
  const i = text.indexOf(DIAG_MARK);
  const cut = i < 0 ? text.length : i;
  $('diagPlain').textContent = text.slice(0, cut).trim();
  $('diagPlain').hidden = false;
  $('diagTechWrap').hidden = false;
  $('diagTechText').textContent =
      i < 0 ? '' : text.slice(i + DIAG_MARK.length).trim();
}
async function copyDiag(){
  const say = $('diagSay'), fall = $('diagFall');
  say.textContent = 'collecting…';
  fall.hidden = true;
  let text;
  try{
    text = await fetch('/api/diag').then(r => r.text());
  }catch(e){
    say.textContent = '⚠ could not reach the hub: ' + (e && e.message || e);
    return;
  }
  showDiag(text);
  // navigator.clipboard is undefined outside a secure context, and this hub is
  // plain http on a LAN address - so on a phone this branch is the NORMAL one,
  // not the failure. Both paths end with the person holding the text.
  try{
    if (!navigator.clipboard) throw new Error('no clipboard here');
    await navigator.clipboard.writeText(text);
    say.textContent = '✓ Copied — paste it wherever you were asked for it.';
    return;
  }catch(e){
    fall.hidden = false;
    const box = $('diagText');
    box.value = text;
    box.focus();
    box.select();
    say.textContent = 'Ready to copy by hand:';
  }
}

