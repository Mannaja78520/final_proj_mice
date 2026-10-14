// ---- keyboard shortcuts ----------------------------------------------
// ONE LIST, read by the handler AND by the help panel. That is the whole
// point: a shortcut the handler knows and the list does not is folklore -
// it works for whoever wrote it and nobody else ever finds out. Adding one
// is a single entry here, and it appears in both places at once, which is
// the same rule the command registry and the module registry already follow.
// `var`, not `const`: a top-level const is not a property of window, and
// QC drives this page from a parent frame that has to reach it.
var SHORTCUTS = [
  {key: '/',   show: '/',   what: 'jump to the module search box',
   run: () => { showTab('modules');
                const b = $('modFind'); if (b){ b.focus(); b.select(); } }},
  {key: '?',   show: '?',   what: 'show this list', run: () => toggleKeys(true)},
  {key: 'Escape', show: 'Esc', what: 'close whatever is open',
   run: () => closeAnyOpen()},
];

// Everything a key press might need to dismiss, in one place, so Esc cannot
// half-close the page - a dialog shut while its backdrop stays is worse than
// one that never opened.
function closeAnyOpen(){
  let did = false;
  const modal = $('flashModal');
  if (modal && !modal.hidden){
    if (_fcResolve) fcClose(false); else modal.hidden = true;
    did = true;
  }
  const keys = $('keysModal');
  if (keys && !keys.hidden){ toggleKeys(false); did = true; }
  // A search box with something in it is also "something open": Esc clears the
  // filter and gives the whole list back, which is what a person means by
  // "get me out of this" while looking at three rows out of twenty.
  const find = $('modFind');
  if (!did && find && find.value){ find.value = ''; filterMods(); did = true; }
  return did;
}

// Show or hide the list, drawing it FROM THE SAME ARRAY the handler uses.
// Built each time it opens rather than once at load: it costs nothing for
// three rows, and it means a shortcut added to SHORTCUTS can never be missing
// from the list because the list was rendered before it existed.
function toggleKeys(show){
  const m = $('keysModal');
  if (!m) return;
  if (show){
    const list = $('keysList');
    list.innerHTML = '';
    SHORTCUTS.forEach(s => {
      const b = document.createElement('button');
      b.className = 'row keyrow';
      b.innerHTML = '<span class="badge"><b>' + esc(s.show) + '</b></span>' +
                    '<span>' + esc(s.what) + '</span>';
      b.onclick = () => {
        // CLOSE FIRST, then act. `/` focuses the search box, and focusing
        // something behind a dialog that is still covering it does nothing a
        // person can see - they would tap it, watch nothing happen, and stop
        // trusting the list.
        toggleKeys(false);
        s.run();
      };
      list.appendChild(b);
    });
  }
  m.hidden = !show;
  if (show) $('keysClose').focus();
  else if ($('keysOpen')) $('keysOpen').focus();
}
if ($('keysClose')) $('keysClose').onclick = () => toggleKeys(false);

document.addEventListener('keydown', e => {
  // NEVER STEAL A KEY FROM SOMEONE TYPING. `/` and `?` are ordinary characters
  // in a module name, a WiFi password or a search box, and a shortcut that
  // eats them turns every text field into a trap. Escape is the exception:
  // leaving a field is exactly what it is for.
  const el = e.target;
  const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' ||
                        el.tagName === 'SELECT' || el.isContentEditable);
  if (typing && e.key !== 'Escape'){ return; }
  if (e.ctrlKey || e.altKey || e.metaKey) return;   // leave browser keys alone
  const hit = SHORTCUTS.filter(s => s.key === e.key)[0];
  if (!hit) return;
  // Escape inside a field means "leave the field", and the browser does not do
  // that by itself. Blur first, then let the shortcut run.
  if (typing && e.key === 'Escape'){ el.blur(); }
  e.preventDefault();
  hit.run();
});

