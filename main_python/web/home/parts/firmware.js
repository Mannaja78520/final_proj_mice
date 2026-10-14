// ---- the Firmware section -------------------------------------------
// Everything here is built from two answers: what this PC has BUILT
// (/api/flash/images) and what boards are reachable. Nothing about module
// types is written down here — adding one to firmware/config/modules.json
// makes it appear, which is the same promise the rest of the project keeps.
async function fwBoards(){
  // Every board this PC could write to. Asked of the two endpoints that
  // already know — /api/mine is the cables this hub has probed, /api/scan is
  // the WiFi — rather than reaching into the Modules screen's DOM, which
  // would tie this section to how that one happens to render today.
  //
  // A board reachable BOTH ways appears once, carrying both, so it is offered
  // the cable and WiFi rather than showing up twice.
  const out = new Map();
  const key = function(m, fallback){ return m.id != null ? 'id' + m.id : fallback; };
  try{
    const mine = await fetch('/api/mine').then(x => x.json());
    (mine.modules || []).forEach(function(m){
      const parts = (m.dev || '').indexOf('usb:') === 0 ? m.dev.slice(4).split(':') : [];
      const port = parts[0] || '';
      // A MODULE ON THE BUS IS NOT A MODULE ON THE CABLE. `usb:COM23:1` names
      // board 1 out on the RS485 pair, reached through whatever is on COM23 —
      // which may be a plain dongle with no board on it at all. Slicing the
      // port out and calling it a cable board offered a write that esptool
      // would have aimed at the wrong end of the wire entirely.
      const bus = parts.length > 1 && parts[1] ? parseInt(parts[1], 10) : 0;
      const k = key(m, 'port' + port + ':' + bus);
      out.set(k, Object.assign({name: m.name || port, id: m.id, type: m.type},
                               out.get(k) || {},
                               bus ? {bus: bus, dev: m.dev}
                                   : {port: port, dev: m.dev}));
    });
  }catch(e){ /* no cables is not an error */ }
  try{
    const wifi = await fetch('/api/scan').then(x => x.json());
    (wifi.modules || []).forEach(function(m){
      const k = key(m, 'ip' + m.ip);
      out.set(k, Object.assign({name: m.name || m.ip, id: m.id, type: m.type},
                               out.get(k) || {}, {ip: m.ip}));
    });
  }catch(e){ /* nothing on the network is not an error */ }

  // And every CABLE, including the ones nothing answered on. This is the case
  // that matters most and the one a module list cannot show: a board with
  // blank or broken firmware says nothing, so it never appears as a module —
  // and it is exactly the board you need to write firmware to. The old
  // per-row control knew this ("flashing belongs on the PORT, not on the
  // module"); moving flashing here must not lose it.
  try{
    const ports = await fetch('/api/ports').then(x => x.json());
    (ports.ports || []).forEach(function(p){
      if (p.bt) return;                       // Bluetooth phantom, not a board
      const already = [...out.values()].some(function(b){ return b.port === p.port; });
      if (already) return;
      out.set('port' + p.port, {name: p.port, port: p.port, silent: true,
                               desc: p.desc || ''});
    });
  }catch(e){ /* no ports is not an error */ }

  // ...and the boards on OTHER PCs' cables. At a venue there is one laptop
  // with the toolchain on it and several without, and the board is plugged
  // into whichever machine was nearest. /api/allmods already asks every hub,
  // so the only new thing here is offering to send the firmware there.
  try{
    const all = await fetch('/api/allmods').then(x => x.json());
    const me = await whoAmI();
    (all.modules || []).forEach(function(m){
      if (!m.host || m.host === me) return;      // this PC's own cables
      const port = (String(m.dev || '').split('usb:')[1] || '').split(':')[0];
      if (!port) return;                          // only a cable can be written
      const k = key(m, 'far' + m.host + port);
      out.set(k, Object.assign({name: m.name || port, id: m.id, type: m.type},
                               out.get(k) || {},
                               {farPort: port, host: m.host, hostIp: m.hostIp}));
    });
  }catch(e){ /* no other hubs is not an error */ }
  return [...out.values()];
}

async function paintFirmware(){
  const stat = $('fwStat');
  let r;
  try{ r = await fetch('/api/flash/images').then(x => x.json()); }
  catch(e){ stat.textContent = 'could not ask this PC what it has built.'; return; }

  const images = r.images || [];
  // Anything writable AT ALL: a full set can go down a cable, an app
  // image alone can still go over WiFi. A PC that was given the images
  // rather than building them has exactly the second kind.
  const ready = images.filter(function(i){ return i.ready || i.ota_ready; });

  // 1. no esptool: nothing here can work, so say that and offer nothing.
  $('fwNoTool').hidden = !!r.esptool;
  if (!r.esptool) {
    $('fwNoTool').textContent = 'This PC cannot flash a board: ' +
      (r.why || 'esptool was not found') + '.';
    $('fwReady').hidden = true;
    stat.textContent = '';
    return;
  }

  // 2. nothing built yet: say the EXACT command, built from which envs are
  //    missing. Hardcoding one would confidently name the wrong firmware.
  $('fwNoBuild').hidden = ready.length > 0;
  if (!ready.length) {
    const envs = images.map(function(i){ return i.env; }).join(' -e ');
    $('fwNoBuild').innerHTML = 'No firmware has been built on this PC yet, so ' +
      'there is nothing to flash. Build it once:<br><code>pio run -e ' +
      esc(envs) + '</code><br>in <code>code/firmware</code>. It then appears here.';
    // The list still renders below, so every type is visible with its own
    // build command rather than one line about the first of them.
  }

  // 3. what can be written, and what cannot.
  $('fwReady').hidden = false;
  stat.textContent = '';
  const list = $('fwList');
  list.innerHTML = '';
  const boards = await fwBoards();

  // Everything this PC could flash, built or not. A type that is missing is
  // the most useful thing this screen can tell you — it names the exact
  // command — and hiding it leaves someone wondering where `lift` went.
  images.forEach(function(img){
    const box = $('tplFwImage').content.cloneNode(true);
    box.querySelector('.ty').textContent = img.type;
    box.querySelector('.ty').classList.add(img.type);
    box.querySelector('.fwtype').textContent = img.type;
    box.querySelector('.fwmeta').textContent =
      (img.bytes ? (img.bytes / 1048576).toFixed(2) + ' MB' : '') +
      (img.built_at ? ' · built ' + new Date(img.built_at * 1000).toLocaleString() : '');

    const targets = box.querySelector('.fwtargets');
    if (!img.ready && !img.ota_ready) {
      // Not built: say so, say what is missing, and give the one command that
      // fixes it. No buttons, because there is nothing to write.
      const miss = box.querySelector('.fwmissing');
      miss.hidden = false;
      miss.innerHTML = 'not built on this PC' +
        (img.missing && img.missing.length
          ? ' — missing ' + esc(img.missing.join(', ')) : '') +
        '. Build it with <code>pio run -e ' + esc(img.env) +
        '</code> in <code>code/firmware</code>.';
      box.querySelector('.fwbox').classList.add('fwunbuilt');
      list.appendChild(box);
      return;
    }
    if (!boards.length) {
      const none = document.createElement('div');
      none.className = 'mini';
      none.textContent = 'No board to write it to yet. Plug one in, or put it '
                       + 'on this WiFi, and it appears here.';
      targets.appendChild(none);
    }
    boards.forEach(function(b){ targets.appendChild(fwTarget(img, b)); });
    list.appendChild(box);
  });
}

// One board, and the ways this firmware can reach it. A board on WiFi only is
// not offered a cable button that cannot work.
function fwTarget(img, board){
  const row = $('tplFwTarget').content.cloneNode(true);
  row.querySelector('.nm').textContent = board.name;
  // The ADDRESS is technical; what the board RUNS is not, and it is what
  // decides whether to press the button. They are separated so the row still
  // says the second thing with the switch off.
  const where = row.querySelector('.ip');
  where.innerHTML = '<span class="tech"></span><span class="fwnow"></span>';
  where.querySelector('.tech').textContent =
    (board.port ? board.port : '') +
    (board.farPort ? (board.farPort + ' on ' + board.host) : '') +
    ((board.port || board.farPort) && board.ip ? ' · ' : '');
  where.querySelector('.fwnow').textContent =
    (board.silent
      ? '  — nothing answered on this cable (blank or stuck board)'
      : (board.type && board.type !== img.type
          ? '  (runs ' + board.type + ' now)' : ''));

  const go = row.querySelector('.fwgo');
  const bar = row.querySelector('.fwbar');
  const say = row.querySelector('.fwsay');
  const overCable = !!board.port;
  // Three ways to reach a board, and a row only ever offers the one it has:
  // this PC's own cable, another PC's cable, or WiFi.
  const far = !overCable && !board.ip && !!board.farPort;
  // ...and a fourth, for a board that has none of them. A module out on the
  // RS485 pair has no cable of its own and may have no radio at all, and both
  // of the usual ways need one: esptool pulls EN and IO0 with DTR and RTS,
  // which two differential wires do not have, and the WiFi updater posts to a
  // web server that is not running. It writes its own spare slot from ordinary
  // commands instead — slower, and the only thing that works.
  //
  // ONE BUTTON, not a choice. The hub knows how it can reach the board and
  // picks; nobody standing at a bench wants to choose a four-minute path when
  // a one-minute path exists. The method is NAMED on the button and again
  // while it runs, because that is what explains the wait.
  const overBus = !overCable && !far && !board.ip && !!board.bus;
  // A cable write needs the whole image set; this PC may only have the app
  // image, which is enough over WiFi or the bus and not enough over a cable.
  if ((overCable || far) && !img.ready) {
    go.disabled = true;
    go.textContent = '⚡ cable write needs the full image';
    go.title = 'this PC has ' + img.type + '.bin but not the bootloader and '
             + 'partition table, so it can update over WiFi and not over a cable';
    return row;
  }
  go.textContent = overCable ? '⚡ Write over the cable'
                 : far ? ('⚡ Write over the cable on ' + board.host)
                 : overBus ? '⚡ Write over RS485'
                       : '⚡ Write over WiFi';
  go.title = overCable
    ? 'takes the cable for about a minute'
    : far
      ? ('the firmware is sent to ' + board.host +
         ', which writes it over its own cable — this PC never touches the board')
      : overBus
        ? ('this board has no cable of its own, so the image goes out on the '
           + 'bus as ordinary commands — several minutes, and it keeps the '
           + 'firmware it has if anything goes wrong')
        : 'sent to the spare slot — if it does not finish, the board keeps what it has';
  go.onclick = function(){
    fwWrite(img, board, overCable, go, bar, say, far, overBus);
  };
  return row;
}

async function fwWrite(img, board, overCable, go, bar, say, far, overBus){
  if (!await confirmFlash({
      name: board.name, id: board.id, now: board.type, type: img.type,
      // The other PC has its own accounts, so the panel asks for a login on
      // THAT machine. This hub never keeps it: it is used for the one request
      // and forgotten, because a hub holding another hub's password is a hub
      // that can overwrite boards nobody authorised.
      login: far ? board.host : '',
      via: overCable ? ('the cable on ' + board.port)
         : far ? (board.host + ', over its cable ' + board.farPort)
         : overBus ? ('the RS485 bus, as module ' + board.bus)
               : ('WiFi at ' + board.ip),
      cost: overCable
        ? 'About a minute, and the cable cannot be used for anything else '
        + 'until it finishes. The board keeps its id, name, WiFi and pins.'
        : overBus
          // Say the number. A progress bar that moves this slowly reads as a
          // stuck one unless somebody was told in advance what to expect.
          ? 'Several minutes — the image goes out in small pieces, because a '
          + 'bus line holds only so much. It is written to the board\'s spare '
          + 'slot, so if it does not finish the module keeps the firmware it '
          + 'has now.'
          : 'It is written to the board\'s spare slot, so if it does not finish '
          + 'the module keeps the firmware it has now.'})) return;

  go.disabled = true; bar.hidden = false; say.textContent = 'starting…';
  flashBusy(true);
  try{
    let r;
    if (far) {
      // The image travels; the command does not. esptool has to run on the PC
      // holding the cable, so this PC hands over the firmware and then watches
      // that hub through the proxy — the browser cannot ask it directly.
      r = await fetch('/api/flash/send', {method: 'POST', body: JSON.stringify({
            to: board.hostIp, port: board.farPort, type: img.type,
            user: _fcLogin.user, password: _fcLogin.password})})
          .then(x => x.json());
    } else {
      const url = overCable
        ? '/api/flash?port=' + encodeURIComponent(board.port) +
          '&type=' + encodeURIComponent(img.type)
        : overBus
          ? '/api/flash/bus?dev=' + encodeURIComponent(board.dev) +
            '&type=' + encodeURIComponent(img.type)
        : '/api/ota?ip=' + encodeURIComponent(board.ip) +
          '&type=' + encodeURIComponent(img.type);
      r = await fetch(url, {method: 'POST'}).then(x => x.json());
    }
    if (r && r.ok === false) {
      say.textContent = '⚠ ' + (r.error || 'refused');
      go.disabled = false; bar.hidden = true; flashBusy(false);
      return;
    }
    fwWatch(bar, say, go, {
      dev: overCable ? ('usb:' + board.port)
         : far ? '' : overBus ? board.dev : ('wifi:' + board.ip),
      type: img.type, was: board.type},
      // A write on another PC is watched through that PC, not this one.
      far ? ('/api/flash/at?ip=' + encodeURIComponent(board.hostIp)) : '/api/flash');
  }catch(e){
    say.textContent = '⚠ the hub is not answering';
    go.disabled = false; bar.hidden = true; flashBusy(false);
  }
}

// Follow it to the end. A progress bar that stops moving with no word is the
// worst of the five states, so a stall says so rather than sitting there.
function fwWatch(bar, say, go, want, from){
  let quiet = 0, last = -1;
  const tick = setInterval(async function(){
    let s;
    try{ s = await fetch(from || '/api/flash').then(x => x.json()); }
    catch(e){
      // NOT a bare return. The hub stops answering exactly when it matters -
      // mid-flash - and returning quietly left the counter frozen, so the
      // stall line below never ran and the bar sat still for ever with no
      // word (panel finding, verified 2026-09-08).
      if (++quiet > 6)
        say.textContent = 'the hub stopped answering while it was writing. '
          + 'Leave the board alone and check the hub is still running.';
      return;
    }
    const pct = Math.round((s.percent || 0));
    bar.querySelector('i').style.width = pct + '%';
    // NAME THE ROUTE WHILE IT RUNS. The three ways take about a minute, about
    // a minute, and about five, and the slow one is slow because a bus line
    // carries 150 bytes at a time — not because anything is wrong. Without the
    // word on screen a bar creeping this slowly reads as a stuck one.
    const how = s.how === 'bus' ? ' over RS485'
              : s.how === 'wifi' ? ' over WiFi'
              : s.how === 'usb' ? ' over the cable' : '';
    say.textContent = (s.stage || (pct + '%')) + how;
    quiet = (pct === last) ? quiet + 1 : 0;
    last = pct;
    // A bus write really does sit on one percent for a while; 40 ticks of 700 ms
    // is 28 seconds, which is normal there and not normal on a cable.
    if (quiet > (s.how === 'bus' ? 140 : 40))
      say.textContent = 'still ' + pct + '%' + how + ' — it may have stalled';
    // FINISHED MEANS THE JOB STOPPED AND HAS A VERDICT.
    //
    // This used to test `s.done`, and /api/flash has never sent a `done` key —
    // status() returns running/percent/stage/ok/error/how/log and nothing else,
    // and /api/flash/at only proxies the same document. So the watcher ended on
    // an ERROR and never on success: the button stayed disabled, the bar stayed
    // on screen, and applyTypeAfterFlash never ran — which is the step that
    // stops a board running lift firmware under the name nong.
    //
    // `ok` is null while the job runs and true/false when it is over, so
    // "stopped, and it said how it went" is the honest test. `s.done` is kept
    // in case some other producer ever sends one.
    const finished = s.done || s.error ||
                     (s.running === false && s.ok !== null && s.ok !== undefined);
    if (finished) {
      clearInterval(tick);
      flashBusy(false);
      go.disabled = false;
      bar.hidden = true;
      if (s.error) {
        say.textContent = '⚠ ' + s.error;
      } else {
        say.textContent = '✓ written, the board is restarting';
        // Writing lift firmware to a board that called itself nong leaves it
        // running the new program under the old name until its TYPE is set
        // too. The old per-row flow did this; losing it would produce a board
        // that boots, answers, and is wrong about what it is.
        if (want && want.dev && want.type) applyTypeAfterFlash(want.dev, want.type, say);
        else if (want && want.type && want.was && want.was !== want.type)
          say.textContent = '✓ written. Set its type on that PC: SET TYPE ' + want.type;
      }
      setTimeout(function(){ scanUsb(); scan(true); }, 3000);
    }
  }, 700);
}
onTab('firmware', paintFirmware);
