// ---- last: what runs once every part is in --------------------------
// Home repaints on its own timer while it is the tab on screen.
setInterval(function(){
  if (document.hidden) return;
  var home = document.querySelector('[data-tab="home"]');
  if (home && home.style.display !== 'none') paintHome();
}, 10000);

// Rest background timers when hidden; wake up and refresh immediately on visible.
document.addEventListener('visibilitychange', function(){
  if (!document.hidden){
    if (!flashActive){
      scan(false);
      var auto = document.getElementById('autoUsb');
      if (auto && auto.checked) scanUsb();
    }
    checkVer();
    modsMeta();
    var home = document.querySelector('[data-tab="home"]');
    if (home && home.style.display !== 'none') paintHome();
  }
});

// The page chose its tab in boot_scans.js, BEFORE the later parts had said
// what their tabs draw - so the panel it opened was never painted. Open it
// again now that every part is in. Cheap, and it means a first load and a
// tab click go through exactly the same path.
showTab((function(){ try{ return localStorage.getItem('hubTab') || 'home'; }
                     catch(e){ return 'home'; } })());
