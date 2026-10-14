// The picker fills itself from the stylesheet - see shared/web/mice.js. The
// page does not know which themes exist, and must not: that is the whole point
// of keeping them in one file. The technical switch is the shared one in the
// head (miceAdv + Mice.TopBar), the same on every page.
document.addEventListener('DOMContentLoaded', function(){
  if (window.miceTheme) miceTheme.picker(document.getElementById('themePick'));
});

function paintSettings(){
  loadUsers();
  $('setWho').textContent = authed
    ? ('Logged in on ' + (MY_PC || 'this PC') + ' — you can move, flash and delete.')
    : ('Not logged in' + (MY_PC ? ' on ' + MY_PC : '') + ' — you can look at '
       + 'everything, but changing anything needs the hub password.');
}

onTab('settings', paintSettings);
