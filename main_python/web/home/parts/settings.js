function paintSettings(){
  loadUsers();
  $('setWho').textContent = authed
    ? ('Logged in on ' + (MY_PC || 'this PC') + ' — you can move, flash and delete.')
    : ('Not logged in' + (MY_PC ? ' on ' + MY_PC : '') + ' — you can look at '
       + 'everything, but changing anything needs the hub password.');
}

// Repaint whenever a tab is opened, and whenever a scan lands.
(function(){
  var was = window.showTab;
  window.showTab = function(name){
    was(name);
    if (name === 'home') paintHome();
    if (name === 'firmware') paintFirmware();
    if (name === 'network') { paintQr(); pairPaint(); }
    if (name === 'settings') paintSettings();
  };
})();
setInterval(function(){
  if (document.hidden) return;
  var home = document.querySelector('[data-tab="home"]');
  if (home && home.style.display !== 'none') paintHome();
}, 10000);

// The page chose its tab near the top of this script, BEFORE the wrapper above
// existed — so the panel it opened was never painted. Open it again now that
// the wrapper is in place. Cheap, and it means a first load and a tab click
// go through exactly the same path.
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

showTab((function(){ try{ return localStorage.getItem('hubTab') || 'home'; }
                     catch(e){ return 'home'; } })());
