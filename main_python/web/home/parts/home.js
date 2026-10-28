// ---- Home, Firmware, Settings ---------------------------------------
// Home does not fetch anything of its own. It reads what the scans already
// found, so it can never disagree with the Modules tab — two panels showing
// different counts for the same robots is worse than one panel.
function paintHome(){
  paintLastOpened();
  // COUNT BOARDS, not rows on screen. Counting rows added the same board up
  // twice - once in the merged module list and once in the cable list - and a
  // bench with four boards reported nine, six on USB and three on WiFi. The
  // hub already merges them by chip (modules_here in main.py); Home has to ask
  // that question rather than count what three lists happen to be showing.
  // What the module scan last found, merged by the hub - not the rows three
  // lists happen to be showing.
  // ONE list now holds every board, including the ones on other PCs - so the
  // count is its length, and adding a second list's rows to it (which is what
  // this did) would count the boards on the laptop next door twice.
  var mods = window.MODS || [];

  // COUNTED PER WAY IN, and each module counted once in each. Asked for
  // 2026-08-22: *show which module connect now from wifi how many from rs485
  // from usb*. USB and RS485 were lumped together as "on a cable", which hides
  // the difference that matters when something is missing: a board on the bus
  // is reached THROUGH another board.
  function has(m, kind){
    return (m.routes || []).some(function(r){ return r.kind === kind; });
  }
  var usb   = mods.filter(function(m){ return has(m, 'usb'); }).length;
  var bus   = mods.filter(function(m){ return has(m, 'rs485'); }).length;
  var wifi  = mods.filter(function(m){ return has(m, 'wifi'); }).length;
  var other = mods.filter(function(m){ return has(m, 'hub'); }).length;
  var cable = mods.filter(function(m){ return has(m, 'usb') || has(m, 'rs485'); }).length;
  var both  = mods.filter(function(m){ return (has(m, 'usb') || has(m, 'rs485'))
                                           && has(m, 'wifi'); }).length;
  var total = mods.length;

  // This function now RESUMES after a network round trip, so the page it
  // started painting may not be there any more - a tab switch, a reload, or a
  // driver tearing the frame down. Anything looked up after an await has to be
  // checked, or the painter throws into a page nobody is looking at.
  var sum = $('homeSum');
  if (!sum) return;
  // LOADING, not empty. The scans start when the page loads and take a few
  // seconds; painting before they answer told someone with a rack of modules
  // that there were none. Empty means "we looked and there is nothing".
  if (!total && !window.HOME_SCANNED){
    sum.textContent = 'Looking for modules — over WiFi, on the cables, and on '
                    + 'any other PC running this hub…';
    $('homeWrong').innerHTML = '';
    $('homeGo').innerHTML = '';
    return;
  }
  if (!total && window.MODS_ERROR){
    sum.textContent = 'Could not check modules. Press Look again to retry.';
  } else if (!total){
    // EMPTY, not blank: say what it means and what to do about it.
    sum.textContent = 'No modules found yet. Plug a board into this PC with a '
      + 'USB cable, or put one on this WiFi, and it appears here by itself.';
  } else {
    // REACHABLE, not "on": a board with a cable and WiFi is one board with
    // two ways in, and saying "3 on cables, 2 over WiFi" about four boards
    // reads as five.
    var bits = [];
    if (usb)   bits.push(usb + ' on a USB cable');
    if (bus)   bits.push(bus + ' on the RS485 bus');
    if (wifi)  bits.push(wifi + ' over WiFi');
    if (other) bits.push(other + ' through another PC');
    sum.textContent = total + (total === 1 ? ' module' : ' modules') + ', '
                    + 'reachable: ' + bits.join(', ')
                    + (both ? ' (' + both + ' both by cable and over WiFi)' : '')
                    + '.';
  }

  // Anything the page is currently unhappy about, gathered in one place. The
  // banners already exist on the other tabs; Home repeats them so a person
  // does not have to visit four tabs to find out something is wrong.
  var wrong = $('homeWrong');
  if (!wrong) return;
  var errs = [];
  document.querySelectorAll('[data-tab] .banner.err').forEach(function(b){
    if (b.closest('[data-tab]').getAttribute('data-tab') === 'home') return;
    errs.push(b.textContent);
  });
  var errKey = errs.join('\n');
  if (wrong.getAttribute('data-errs') !== errKey){
    wrong.setAttribute('data-errs', errKey);
    wrong.innerHTML = '';
    errs.forEach(function(txt){
      var d = document.createElement('div');
      d.className = 'banner err';
      d.textContent = txt;
      wrong.appendChild(d);
    });
  }

  // One way onward. With the modules themselves on this screen, "Open Modules"
  // was a button to a copy of what was already in front of the reader; looking
  // again is the thing that is not otherwise possible from here.
  var go = $('homeGo');
  if (go){
    var goKey = total ? 'has' : 'empty';
    if (go.getAttribute('data-btn') !== goKey){
      go.setAttribute('data-btn', goKey);
      go.innerHTML = '';
      var b = document.createElement('button');
      b.className = total ? '' : 'primary';
      b.textContent = total ? '⟳ Look again' : 'Look again';
      b.onclick = function(){ scan(true); scanUsb(); };
      go.appendChild(b);
    }
  }
}

// Which firmware this PC can actually flash — the same question the Firmware
// tab is for, answered with the endpoint the module rows already use.
onTab('home', paintHome);
