// ---- pinned modules --------------------------------------------------
// A venue rig has four modules that matter and a shelf of spares that do not,
// and the spares are not fewer than the ones you use - they are usually more.
// Scrolling past them to reach the same four boards, every time, is the whole
// problem this solves.
//
// PINNED BY BOARD ID, not by name and not by address. A name is user-settable
// (SET NAME, the module site) and an address changes whenever the board moves
// between a cable and the WiFi, or the router hands out a different lease -
// so either would silently lose the pin on the board it was pinned to. The id
// is the one thing that stays with the chip.
//
// Kept in localStorage for the same reason as the last-opened shortcut: which
// modules YOU care about is a fact about this person at this machine, not
// about the rig. Another laptop at the same venue is looking after other
// boards, and syncing this to the hub would make them fight over it.
function pinnedIds(){
  try{
    var v = JSON.parse(localStorage.getItem('pinnedMods') || '[]');
    return Array.isArray(v) ? v : [];
  }catch(e){ return []; }
}
function isPinned(id){ return id != null && pinnedIds().indexOf(id) >= 0; }
function togglePin(id){
  if (id == null) return;
  var list = pinnedIds();
  var at = list.indexOf(id);
  if (at >= 0) list.splice(at, 1); else list.push(id);
  try{ localStorage.setItem('pinnedMods', JSON.stringify(list)); }catch(e){}
}
// Pinned first, everything else in the order the hub gave. NOT sorted by name
// or id inside each group: the hub's order is already meaningful (it merges
// each board's routes) and re-sorting would move rows around for reasons a
// person watching the list cannot see.
function pinnedFirst(mods){
  var pins = pinnedIds();
  var yes = [], no = [];
  (mods || []).forEach(function(m){
    (pins.indexOf(m.id) >= 0 ? yes : no).push(m);
  });
  return yes.concat(no);
}

// When each board was last opened, ON ITS OWN ROW (A26-87, 2026-09-21). It was
// one "↩ nong" line apart from the rows: with two boards called nong nobody
// could tell which it meant, and it saved the ADDRESS - so after the robot
// changed WiFi the shortcut opened a dead one. Now it is keyed by the board
// (m.key = its chip) and the row's own Open button uses today's route.
// Kept per browser: a convenience for THIS person at THIS machine.
function openedTimes(){
  try{ return JSON.parse(localStorage.getItem('openedAt') || '{}') || {}; }
  catch(e){ return {}; }
}
function rememberOpened(dev, name, key){
  try{
    var all = openedTimes();
    all[key || dev] = Date.now();
    localStorage.setItem('openedAt', JSON.stringify(all));
  }catch(e){}
}
// THE CLOCK AND THE DATE, not only "3 min ago" (asked 2026-08-22: *make it last
// open time and date*); the relative form stays because it reads instantly.
function openedText(m){
  // by the board, or by any route to it (openers that do not know the key)
  var all = openedTimes(), at = all[m.key] || 0;
  (m.routes || []).forEach(function(r){ if ((all[r.dev] || 0) > at) at = all[r.dev]; });
  if (!at) return '';
  return 'last opened ' + stamp(at) + (agoText(at) ? ' (' + agoText(at) + ')' : '');
}
// The old single "last opened" entry, moved onto its board once, by the route
// it saved or by its name, then forgotten.
function paintLastOpened(){
  var raw = null;
  try{ raw = JSON.parse(localStorage.getItem('lastMod') || 'null'); }catch(e){}
  if (!raw || !raw.at) return;
  var live = (window.MODS || []).filter(function(m){
    return (m.routes || []).some(function(r){ return r.dev === raw.dev; }) ||
           (raw.name && m.name === raw.name); })[0];
  if (!live || !live.key) return;
  var all = openedTimes();
  if (!all[live.key]) all[live.key] = raw.at;
  try{ localStorage.setItem('openedAt', JSON.stringify(all));
       localStorage.removeItem('lastMod'); }catch(e){}
}

