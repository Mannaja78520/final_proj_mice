// A write in progress must not be interrupted by the page's own rescans: the
// rows redraw, the progress bar is torn out, and the screen looks idle while a
// board is being overwritten. Removing the old per-row flash path (A2-2) took
// this counter with it and left four calls to a function that no longer
// existed, so the FIRST click on Write threw before anything was sent.
let flashActive=0;
function flashBusy(on){ flashActive=Math.max(0,flashActive+(on?1:-1)); }

let autoUsbTimer=null;
function autoUsbChanged(){
  const on=document.getElementById('autoUsb').checked;
  localStorage.setItem('hub_autousb',on?'1':'0');
  clearInterval(autoUsbTimer);autoUsbTimer=null;
  if(on)autoUsbTimer=setInterval(()=>{

    if(!document.hidden&&!flashActive)scanUsb();
  },12000);
}
document.getElementById('autoUsb').checked=localStorage.getItem('hub_autousb')==='1';
autoUsbChanged();
// Start on the tab you were last on. Defaults to Modules, so a fresh browser
// opens exactly the page it always did.
showTab((function(){ try{ return localStorage.getItem('hubTab')||'home'; }
                     catch(e){ return 'modules'; } })());
// Home shows "looking…" until these have answered at least once, and repaints
// the moment they do rather than waiting for its own timer.
window.HOME_SCANNED = false;
Promise.allSettled([scan(false), scanUsb(), loadShared(false)]).then(function(){
  window.HOME_SCANNED = true;
  if (typeof paintHome === 'function') paintHome();
});
setInterval(()=>{ if(!document.hidden&&!flashActive)scan(false); },15000);

