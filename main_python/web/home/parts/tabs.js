// ---- tabs -------------------------------------------------------------
// Only the visibility changes; nothing is moved or re-created, so the module
// list, USB list and tools keep working exactly as before.
//
// What a tab draws when it opens is registered by the part that owns it -
// `onTab('firmware', paintFirmware)` sits next to paintFirmware - so a new
// tab is a new part and never an edit here. (It was a wrapper that replaced
// showTab at the end of the script, A41-3.)
var TAB_OPEN = {};
function onTab(name, fn){ (TAB_OPEN[name] = TAB_OPEN[name] || []).push(fn); }

function showTab(name){
  document.querySelectorAll('[data-tab]').forEach(function(el){
    el.style.display = (el.getAttribute('data-tab')===name) ? '' : 'none';
  });
  document.querySelectorAll('#tabs .tab').forEach(function(b){
    b.classList.toggle('on', b.getAttribute('data-go')===name);
  });
  try{ localStorage.setItem('hubTab', name); }catch(e){}
  helpFor(name);
  (TAB_OPEN[name] || []).forEach(function(fn){ fn(); });
}

// HELP ABOUT WHAT YOU ARE LOOKING AT. The help page has had a section anchor
// per area from the start, and nothing ever linked to one: every Help link
// went to the top of a page of over a thousand lines, so finding the paragraph
// about the screen in front of you meant scrolling past everything else. The
// link now carries the current tab's section.
//
// A tab with no section of its own keeps the plain link rather than guessing:
// landing on the wrong paragraph is worse than landing at the top, because it
// reads as an answer.
var HELP_SECTION = {
  home:       'hub',
  modules:    'modsite',
  firmware:   'firmware',
  network:    'transports',
  tools:      'hub',
  settings:   'hub',
  complaints: 'hub'
};
function helpFor(name){
  var a = document.getElementById('helpLink');
  if(!a) return;
  var sec = HELP_SECTION[name];
  a.href = sec ? ('/help#' + sec) : '/help';
  a.title = sec ? ('Help about ' + name) : 'Help';
}

// Filter the rows already on the page. Matching happens on what a person
// would type: the name, the number, the type - not the internal address.
function filterMods(){
  var q = (document.getElementById('modFind').value || '').trim().toLowerCase();
  var rows = document.querySelectorAll('#mods .mod');
  var hidden = 0, total = rows.length;
  rows.forEach(function(el){
    var hay = (el.textContent || '').toLowerCase();
    var show = !q || hay.indexOf(q) >= 0;
    el.style.display = show ? '' : 'none';
    if (!show) hidden++;
  });
  var none = document.getElementById('modFindNone');
  if (!none) return;
  if (q && hidden === total && total) {
    // The empty state of a SEARCH is not the empty state of a list: the
    // modules are still there, the word is just wrong.
    none.textContent = 'No module matches "' + q + '". All ' + total +
                       ' are still connected — clear the box to see them.';
    none.hidden = false;
  } else if (q && hidden) {
    none.textContent = hidden + ' of ' + total + ' hidden by the filter.';
    none.hidden = false;
  } else {
    none.hidden = true;
  }
}


window.addEventListener('DOMContentLoaded', function(){
  var h = (location.hash || '').replace('#', '');
  if(h && document.querySelector('#tabs [data-go="' + h + '"]')) showTab(h);
});
window.addEventListener('hashchange', function(){
  var h = (location.hash || '').replace('#', '');
  if(h && document.querySelector('#tabs [data-go="' + h + '"]')) showTab(h);
});
