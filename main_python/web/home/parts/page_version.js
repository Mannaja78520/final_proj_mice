// ---- is this page still the one the hub is serving? ------------------
// The version is whatever /api/version said when the tab loaded. If it ever
// differs, the files behind this page changed and what you are looking at is
// old. Checked on the timer that was already running rather than a new one:
// one more request every 20 seconds, and none while the tab is in the
// background - a laptop with the hub open on a second screen should not be
// polling all night.
// The hub says which of its own source files changed since the exe was built,
// so this only has to show the sentence - deciding what counts as stale is the
// hub's job, and only the hub can see the files.
function paintStale(r){
  // Kept for any message that needs to say WHICH build is speaking - the tool
  // list's error is the one that needed it.
  window.HUB_BUILT = (r && r.built) || '';
  var b = document.getElementById('staleExe');
  if(!b) return;
  b.hidden = !(r && r.stale);
  if(b.hidden) return;
  document.getElementById('staleExeWhy').textContent = '⚠ ' + (r.staleWhy || '');
  document.getElementById('staleExeFix').textContent = r.rebuild || '';
}

var myVer = null, verHidden = false;
function dismissVer(){
  verHidden = true;
  var b = document.getElementById('newVer');
  if(b) b.hidden = true;
}
async function checkVer(){
  if(document.hidden) return;
  try{
    const r = await fetch('/api/version').then(r=>r.json());
    if(!r || !r.version) return;
    paintStale(r);            // before the baseline return: a stale exe is
                              // true on the very first answer, not only after
                              // something changes
    if(myVer === null){ myVer = r.version; return; }   // first answer is the baseline
    if(r.version === myVer) return;
    if(verHidden) return;            // asked to be left alone until next load
    var b = document.getElementById('newVer');
    if(b) b.hidden = false;
  }catch(e){ /* hub restarting, or offline: say nothing, try again later */ }
}
setInterval(checkVer, 20000);
checkVer();

