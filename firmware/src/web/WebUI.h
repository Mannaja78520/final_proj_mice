#pragma once
#include <Arduino.h>

// Single-page control UI served from flash at "/" — works with no SD card.
// Talks to the JSON/text API in WebPortal.cpp and the /ws WebSocket.
//
// THIS FILE IS THE MASTER PAGE AND IS NOT COMPILED.
//
// A board runs one module type and should carry only that type's controls, so
// firmware/tools/gen_tables.py generates `web/ModuleUI.h` from this file for
// the type the env is building (see platformio.ini) — that generated header is
// what WebPortal.cpp includes. The hub (main_python) still reads THIS file and
// serves it whole for a module reached over USB, where the type is not known
// until the board answers.
//
// Everything that belongs to one module type is marked, each marker alone on
// its own line:
//
//     <!--#type lift-->  ...  <!--#end-->     in the HTML
//     //#type nong       ...  //#end          inside <script>
//
// Two spellings because a marker must be a comment in BOTH places: this file
// is also served as-is. Marker lines never reach the generated page.
//
// Rules for editing:
//   * a type's cards, its status rendering and its helper functions go inside
//     its own markers — anything outside them is carried by every board;
//   * shared code must never assume a type's element exists. `$('liftCard')`
//     is null on a nong board, so use showCard()/the null checks below;
//   * markers do not nest.
static const char WEB_UI_HTML[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Module Control</title>
<!-- The ONE design system, shared/web/mice.css. The BOARD serves it from flash
     (gen_tables.py compiles that file into web/MiceCss.h); the hub serves the
     same URL when this page is reached over USB — one link, either transport. -->
<link rel="stylesheet" href="/mice.css">
<script src="/mice.js"></script>
<style>
/* Only what is the MODULE WEBSITE's own. Tokens, the reset, cards, buttons,
   inputs, badges, the quiet caption and the shared floor come from mice.css. */
body{padding:14px;max-width:1100px;margin:0 auto}
header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:14px}
.grid{grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:14px}
/* The look comes from mice.css now. .mtab stays as a NAME — scripts and QC
   select on it — but it no longer describes a second kind of tab. */
#modTabs{margin:0 0 var(--sp-3)}
@media(max-width:720px){.tab{font-size:13px}}
/* the one big number on the page: what the module is doing right now */
.stage{font-size:52px;font-weight:700;text-align:center;line-height:1.1}
.stage small{display:block;font-size:13px;color:var(--mut);font-weight:400}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:6px var(--sp-2);border-bottom:1px solid var(--line);text-align:left}
td a{color:var(--acc);text-decoration:none;margin-right:var(--sp-2);cursor:pointer}
#log{background:var(--sunk);border:1px solid var(--line);border-radius:var(--r-sm);padding:var(--sp-2);height:130px;overflow-y:auto;font:12px/1.5 var(--mono);white-space:pre-wrap;word-break:break-all}
/* a link light: the word beside it says the same thing, so colour is never
   the only signal */
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--mut);margin-right:6px}
.dot.on{background:var(--ok)}.dot.warn{background:var(--warn)}
.peer{display:inline-block;background:var(--btn);border:1px solid var(--line);border-radius:var(--r-pill);
  padding:6px 14px;margin:3px;color:var(--txt);text-decoration:none;font-size:14px}
a.peer:hover{border-color:var(--acc)}
.peer.self{border-color:var(--ok);cursor:default}
.peer small{color:var(--mut)}

/* responsive: this page is opened from a phone at the robot as often as from a
   desk, and over USB it is served by the hub to whatever device is at hand. */
@media (min-width:1500px){body{max-width:1400px;margin:0 auto}}
@media (max-width:720px){
  body{padding:var(--sp-3)}
  .card{padding:var(--sp-3)}
  .row{flex-wrap:wrap}
  .row label,.row .lbl{min-width:0}
  h2 button,h2 span{float:none!important}
  /* pin rows are name + a GPIO select; let them go full width rather than
     truncating the function name to nothing */
  .pinrow{flex-wrap:wrap}
  .pinrow select{flex:1 1 120px}
  pre,#console{font-size:11px}
}
@media (max-width:430px){body{padding:9px}}
</style>
</head>
<body>
<header>
  <h1 id="hname">module</h1>
  <span class="badge">ID <b id="hid">-</b></span>
  <span class="badge">type <b id="htype">-</b></span>
  <!-- Which installation this board belongs to. The hub has a whole screen
       about grouping and the board itself never said which group it was in. -->
  <span class="badge" id="hgroupwrap" hidden>group <b id="hgroup">-</b></span>
  <!-- The first question anyone asks about a board behaving oddly. It was
       only reachable by sending INFO on a console. -->
  <span class="badge">fw <b id="hfw">-</b></span>
  <span class="badge">wifi <b id="hwifi">-</b></span>
  <span class="badge">SD <b id="hsd">-</b></span>
  <span class="badge"><span class="dot" id="wsdot"></span>live</span>
  <span style="flex:1"></span>
  <!-- The way back. Hidden until it is known to be right - see showHubLink. -->
  <a id="hubBack" class="tab" href="/" hidden>&#8592; back to the hub</a>
  <button class="primary" id="setupBtn" onclick="setupToggle()">&#9881; Setup / Login</button>
</header>

<!-- What it is doing, and how you are reached to it. Both in words, because
     someone standing next to an arm needs to know whether it is about to move
     before they reach into it, and because unplugging a cable means something
     different from losing WiFi. -->
<div id="hnow" class="statline" aria-live="polite">asking the board what it is…</div>

<!-- Tabs, not a longer page. Thirteen cards in one column meant scrolling
     past the lift controls to reach the SD card. Nothing MOVED to build this:
     each card carries data-tab and showTab() decides what is on screen, so
     every id, handler and login rule is exactly as it was. -->
<div id="modTabs" class="tabs equal">
  <button class="tab mtab on" data-mtab="control" onclick="showTab('control')">Move it</button>
  <button class="tab mtab" data-mtab="files" onclick="showTab('files')">Shows &amp; files</button>
  <button class="tab mtab" data-mtab="setup" onclick="showTab('setup')">Setup &amp; wiring</button>
</div>
<div class="grid">
  <div class="card" data-tab="setup" id="loginCard" style="grid-column:1/-1;display:none">
    <h2>Setup login &#128274;</h2>
    <div id="loginForm">
      <div class="statline">log in to configure this module — <b>identity, WiFi mode,
        Hardware pins, users, zero calibration</b>. Same over WiFi / USB / RS485.</div>
      <!-- The password used to be printed right here, on a page anyone on the
           WiFi can open. A board that has never had its password changed says
           so after logging in, and Setup stays locked until it is. -->
      <div class="row">
        <span class="lbl">User</span><input id="liUser" autocomplete="username" style="width:150px">
        <span class="lbl">Pass</span><input id="liPass" type="password" autocomplete="current-password" style="width:150px">
        <button class="primary" onclick="doLogin()">Log in</button>
        <span class="statline" id="liStat"></span>
      </div>
    </div>
    <!-- Shown only when the board is still carrying its shipped password.
         Setup stays locked behind this: a board nobody has secured is the
         same as a board with no login at all. -->
    <div id="mustChangeBox" class="banner err" style="display:none">
      <div>
        <b>This board still has the password it came with.</b>
        Every board that has not been changed has the same one, so anyone who
        has seen another board can open this one. Choose a new password to
        unlock Setup.
        <div class="row">
          <span class="lbl">New</span>
          <input id="mcPass" type="password" autocomplete="new-password" style="width:170px">
          <button class="primary" onclick="doFirstChange()">Set it</button>
          <span class="statline" id="mcStat"></span>
        </div>
      </div>
    </div>

    <div id="usersBox" style="display:none">
      <div class="row">
        <span class="statline">logged in as <b id="liWho">-</b> — the Setup cards below are now editable.</span>
        <button onclick="doLogout()">Log out</button>
      </div>
      <div class="row"><span class="lbl">Accounts</span><span id="userList" class="statline">-</span></div>
      <div class="row">
        <span class="lbl">Add user</span>
        <input id="nuUser" placeholder="username" style="width:120px">
        <input id="nuPass" placeholder="password (no spaces)" style="width:150px">
        <button onclick="addUser()">Add</button>
      </div>
      <div class="row">
        <span class="lbl">My password</span>
        <input id="pwNew" placeholder="new password" style="width:150px">
        <button onclick="changeMyPass()">Change</button>
        <span class="statline" id="userStat"></span>
      </div>
    </div>
  </div>

  <div class="card" data-tab="setup" style="grid-column:1/-1">
    <h2>Modules on network</h2>
    <div class="row">
      <div id="peerList" style="flex:1"><span class="statline">scanning...</span></div>
      <button onclick="loadPeers()">Rescan</button>
    </div>
  </div>

<!--#type lift-->
  <div class="card" data-tab="control" id="liftCard">
    <h2>Lift</h2>
    <div class="stage"><span id="stg">-</span><small id="stgState">state: -</small></div>
    <div class="row" id="gotoBtns" style="justify-content:center"></div>
    <div class="row" style="justify-content:center">
      <button onclick="cmd('UP')">&#9650; Up</button>
      <button onclick="cmd('DOWN')">&#9660; Down</button>
      <button class="danger" onclick="cmd('STOP')">&#9632; Stop</button>
      <button onclick="cmd('HOME')">&#8962; Home</button>
    </div>
    <div class="row" style="justify-content:center">
      <span class="lbl">Speed</span>
      <input type="number" id="spdVal" step="0.01" min="0" style="width:90px">
      <select id="spdUnit"><option value="pwm">PWM</option><option value="ms">m/s</option></select>
      <button onclick="setSpeed()">Set</button>
    </div>
    <div class="statline" style="text-align:center" id="spdInfo">speed: -</div>
    <div class="statline" style="text-align:center">
      <span id="limT">top:-</span> &nbsp; <span id="limD">bottom:-</span> &nbsp; <span id="homed">homed:-</span> &nbsp; <span id="encv">pos:-</span>
    </div>
  </div>

  <div class="card" data-tab="control" id="rgbCard">
    <h2>RGB Strip</h2>
    <div class="row"><span class="lbl">Color</span>
      <input type="color" id="rgbc" value="#0050ff" onchange="sendRgb()">
      <button onclick="sendRgb()">Set</button>
      <button onclick="cmd('RGB EFFECT off')">Off</button>
    </div>
    <div class="row"><span class="lbl">Bright</span>
      <input type="range" id="rgbb" min="0" max="255" value="128" onchange="cmd('RGB BRIGHT '+this.value)">
    </div>
    <div class="row"><span class="lbl">Effect</span>
      <select id="rgbe" onchange="cmd('RGB EFFECT '+this.value)">
        <option>solid</option><option>rainbow</option><option>chase</option><option>breathe</option><option>off</option>
      </select>
    </div>
  </div>

  <div class="card" data-tab="control" id="audCard">
    <h2>Speaker</h2>
    <div class="row">
      <select id="musicSel" style="flex:1"></select>
      <button class="primary" onclick="playSel()">&#9658;</button>
      <button onclick="cmd('PLAY STOP')">&#9632;</button>
    </div>
    <div class="row"><span class="lbl">Volume</span>
      <input type="range" id="vol" min="0" max="100" value="70"
             oninput="document.getElementById('volNum').value=this.value" onchange="cmd('VOL '+this.value)">
      <input type="number" id="volNum" min="0" max="100" value="70" style="width:70px"
             onchange="cmd('VOL '+this.value)">
    </div>
    <div class="statline" id="nowPlaying">stopped</div>
  </div>
<!--#end-->

<!--#type nong-->
  <div class="card" data-tab="control" id="nongCard" style="grid-column:1/-1">
    <h2>Nong Arms</h2>
    <div class="row">
      <span class="lbl">Mode</span>
      <select id="nmode" onchange="nongModeChanged()">
        <option value="slider">drag by slider</option>
        <option value="seq">follow sequence (SD card)</option>
        <option value="studio">follow Nong Studio</option>
      </select>
      <span class="statline">sliders send only in "drag by slider" mode; the <b>now</b> value is the real position</span>
    </div>
    <div id="jointRows"></div>
    <div class="statline" id="jxyz" style="white-space:pre-wrap"></div>
    <div class="row">
      <button onclick="cmd('HOME')">Neutral</button>
      <button onclick="cmd('ATTACH')">Attach (power on)</button>
      <button class="danger" onclick="cmd('RELAX')" title="cut servo power (detach) - the arms go limp">&#9211; Stop (power off)</button>
      <span class="lbl">Speed &deg;/s</span>
      <input type="number" id="ndps" min="5" max="600" style="width:80px" onchange="cmd('SPEED '+this.value)">
      <span class="statline" id="nongStat"></span>
    </div>
    <div class="row">
      <span class="lbl">2-ESP pair</span>
      <label><input type="checkbox" id="nlink"> this board is the leader</label>
      <span class="lbl" style="min-width:0">partner id</span>
      <input type="number" id="npeer" min="0" max="247" style="width:70px" title="module id of the other half (0 = broadcast to every module on the bus)">
      <button onclick="savePair()">Save &amp; reboot</button>
    </div>
    <div class="statline">only needed when the humanoid is split over two boards: the leader repeats every pose to its partner over RS485 so both move together</div>

    <div class="setupCard" style="display:none;border-top:1px solid var(--line);margin-top:12px;padding-top:10px">
      <h2>Zero position</h2>
      <div class="statline">jog the arms straight with the sliders (Attach on), then
        press <b>Set zero</b> — this pose becomes home = 90&deg; (the arm won't move).</div>
      <div class="row">
        <button class="primary" onclick="cmd('SETZERO')">&#9678; Set zero (current = home)</button>
        <button onclick="cmd('ZERO')">&#8962; Move to zero</button>
      </div>
    </div>

    <div class="setupCard" style="display:none;border-top:1px solid var(--line);margin-top:12px;padding-top:10px">
      <h2>Servo type</h2>
      <div class="statline">which servo is fitted to which joint. <b>Travel</b> is how far
        the <b>servo</b> turns end to end (180&deg; normal, 270&deg; wide-angle) &mdash; not how far
        the joint may turn. Fitting a 270&deg; servo is just this one number: poses and
        saved sequences are in joint degrees and keep working.</div>
      <div class="row">
        <select id="svJoint" style="width:120px">
          <option value="ALL">all joints</option>
          <option value="1">1 L_SH_P</option><option value="2">2 L_SH_R</option>
          <option value="3">3 L_EL_P</option><option value="4">4 L_EL_R</option>
          <option value="5">5 R_SH_P</option><option value="6">6 R_SH_R</option>
          <option value="7">7 R_EL_P</option><option value="8">8 R_EL_R</option>
          <option value="9">9 WAIST</option><option value="10">10 SHRUG</option>
        </select>
        <select id="svType" style="flex:1">
          <option value="mg90s">MG90S (180&deg;, 500-2400us, 50Hz)</option>
          <option value="pdi1181mg">PDI-1181MG (270&deg;, 500-2500us, 50Hz)</option>
          <option value="tiankong35">TianKongRC 35kg (270&deg;, 500-2500us, 50Hz)</option>
          <option value="generic180">generic 180&deg; servo</option>
          <option value="generic270">generic 270&deg; servo</option>
        </select>
        <button class="primary" onclick="setServo()">Apply</button>
      </div>
      <div class="row">
        <span class="lbl">travel only</span>
        <input type="number" id="svRange" min="60" max="360" step="10" value="180" style="width:70px"
               title="servo travel in degrees — 180 normal, 270 wide-angle">
        <button onclick="setRange()">Set travel&deg;</button>
        <span class="lbl">rate</span>
        <input type="number" id="svRate" min="40" max="400" step="10" value="50" style="width:70px"
               title="servo frame rate (Hz) — 50 normal, 330 for the PDI-1181MG digital servo">
        <button onclick="setRate()">Set Hz</button>
      </div>
      <div class="statline" id="svNow"></div>
      <div class="statline"><b>Rate</b> defaults to 50&nbsp;Hz (works). The PDI-1181MG
        datasheet says 330&nbsp;Hz, but 330 made a marginal shoulder over-current on a
        move and cut out — only raise it if a servo needs it and the current stays safe.
        After changing travel, check the movement away from home and <b>Set zero</b> if needed.</div>
    </div>
  </div>
<!--#end-->

<!--#type cam-->
  <div class="card" data-tab="control" id="camCard" style="grid-column:1/-1">
    <h2>Camera</h2>
    <div class="row">
      <button class="primary" id="camShotBtn" onclick="camShot()">&#128247; Take a picture</button>
      <label><input type="checkbox" id="camLive" onchange="camLiveToggle()"> live view</label>
      <span class="lbl">Size</span>
      <select id="camSize" onchange="cmd('CAM SIZE '+this.value)">
        <option>qqvga</option><option>qvga</option><option>vga</option>
        <option selected>svga</option><option>xga</option><option>sxga</option><option>uxga</option>
      </select>
      <span class="lbl">Quality</span>
      <input type="number" id="camQ" min="10" max="63" value="12" style="width:70px"
             title="10 = best picture, 63 = smallest file" onchange="cmd('CAM QUALITY '+this.value)">
      <label><input type="checkbox" id="camFlash" onchange="cmd('CAM FLASH '+(this.checked?'ON':'OFF'))"> flash</label>
    </div>
    <div class="row">
      <label><input type="checkbox" id="camVflip" onchange="cmd('CAM VFLIP '+(this.checked?1:0))"> flip</label>
      <label><input type="checkbox" id="camHmir" onchange="cmd('CAM HMIRROR '+(this.checked?1:0))"> mirror</label>
      <span class="statline" id="camStat">idle</span>
    </div>
    <img id="camImg" alt="the camera's view" style="display:none;max-width:100%;
         border:1px solid var(--line);border-radius:var(--r-md);margin-top:8px">
    <div class="statline">a picture is one frame over HTTP. <b>Take a picture</b> shows it here;
      <code>SNAP &lt;name&gt;</code> saves it to /photos on the SD card. The live view is the
      same frame fetched again and again — it costs WiFi, so it is off by default.</div>
  </div>
<!--#end-->

  <div class="card" data-tab="files">
    <h2>Sequences</h2>
    <div class="row">
      <select id="moveSel" style="flex:1"></select>
      <button class="primary" onclick="runSel()">Run</button>
      <button onclick="cmd('MOVE STOP')">Stop</button>
    </div>
    <div class="statline" id="seqStat">idle</div>
  </div>

  <div class="card setupCard" data-tab="setup" style="grid-column:1/-1;display:none">
    <h2>Hardware pins <span class="statline">(stored on this board — reboot to apply)</span></h2>
    <div class="statline">pick which module type's pins to configure, then wire each
      function to a GPIO (same select boxes as before). The tabs are dynamic —
      the module types THIS firmware was built with show up here.</div>
    <div id="pinTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0"></div>
    <div id="pinGroups"></div>
    <div class="row">
      <button class="primary" onclick="savePins()">Save &amp; reboot</button>
      <button onclick="cmd('PIN CLEAR').then(loadPins)">Reset to defaults</button>
      <span class="statline" id="pinStat"></span>
    </div>
  </div>

  <div class="card" data-tab="files" style="grid-column:1/-1">
    <h2>SD Files</h2>
    <div class="row">
      <select id="dirSel" onchange="loadFiles()">
        <option>/music</option><option>/moves</option><option>/data</option>
      </select>
      <input type="file" id="upFile">
      <button onclick="upload()">Upload</button>
      <span class="statline" id="upStat"></span>
    </div>
    <table id="fileTbl"><tbody></tbody></table>
  </div>

  <div class="card setupCard" data-tab="setup" style="display:none">
    <h2>Settings</h2>
    <div class="row"><span class="lbl">ID</span><input type="number" id="setId" min="1" max="247" style="width:90px"></div>
    <div class="row"><span class="lbl">Name</span><input id="setName" style="flex:1"></div>
    <div class="row"><span class="lbl">Type</span><select id="setType" style="flex:1"></select></div>
    <div class="row"><span class="lbl">WiFi SSID</span><input id="setSsid"
      placeholder="the network name, spaces are fine"
      title="The exact network name. Spaces are fine — &quot;MSI 3058&quot; works."
      style="flex:1"></div>
    <div class="row"><span class="lbl">WiFi pass</span><input id="setPass" style="flex:1"></div>
    <div class="row"><span class="lbl">WiFi mode</span>
      <select id="setRadio" style="flex:1">
        <option value="">keep current</option>
        <option value="ON">ON &mdash; join the WiFi above (AP fallback)</option>
        <option value="AP">AP &mdash; host its own hotspot only</option>
        <option value="OFF">OFF &mdash; USB / RS485 only (fastest boot)</option>
      </select>
    </div>
    <div class="statline">now: <b id="wifiNow">-</b></div>
    <div class="row"><button class="primary" onclick="saveSettings()">Save &amp; Reboot</button></div>
  </div>

  <div class="card" data-tab="files">
    <h2>Console</h2>
    <div id="log"></div>
    <div class="row">
      <input id="cli" placeholder="e.g. GOTO 2 / PING / #3 PING (RS485 bridge) / #* RGB 255 0 0" style="flex:1"
             onkeydown="if(event.key==='Enter'){cmd(this.value);this.value=''}">
    </div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
let st={},gotoBuilt=-1,W=null;

function log(t){const l=$('log');l.textContent+=t+'\n';l.scrollTop=l.scrollHeight;}
async function cmd(c){
  if(!c)return'';
  try{const r=await fetch('/api/cmd?c='+encodeURIComponent(c));const t=await r.text();log('> '+c+'  ->  '+t);return t;}
  catch(e){log('! '+c+' failed');return'';}
}
function connectWs(){
  W=new WebSocket('ws://'+location.host+'/ws');
  W.onopen=()=>$('wsdot').className='dot on';
  W.onclose=()=>{$('wsdot').className='dot';setTimeout(connectWs,2000);};
  W.onmessage=e=>{try{st=JSON.parse(e.data);render();}catch(_){log(e.data);}};
}
function render(){
  $('hname').textContent=st.name||'module';
  document.title=(st.name||'module')+' control';
  $('hid').textContent=st.id;
  // group is optional: a board that is in no installation says nothing rather
  // than showing an empty label
  if(st.group){ $('hgroup').textContent=st.group; $('hgroupwrap').hidden=false; }
  else $('hgroupwrap').hidden=true;
  $('hfw').textContent=st.fw||'?';
  showHubLink(st);
  paintNow(st);
  $('htype').textContent=st.type;
  $('hsd').textContent=st.sd?'ok':'none';
  // CONTROL is locked to the board's real type (no login needed): a nong
  // board shows only nong controls, a lift board only lift controls. The
  // module-type TABS live in the Hardware pins card (after login) — that is
  // where you pick which type's pins to configure.
  // Cards follow what the board SAYS IT CAN DO, not what type it calls
  // itself — so a new module type shows the right controls without this page
  // being taught about it. Old firmware sends no caps: fall back to the type.
  const caps=st.caps||[];
  const has=c=>caps.length?caps.indexOf(c)>=0
    :(c==='joints'||c==='servos'||c==='calibration'?st.type==='nong':st.type==='lift');
  // Since the per-type BUILD, a card the board cannot use is not on the page
  // at all — so showCard() must survive a missing element. It still decides by
  // capability, because the hub serves this same page whole for a module on a
  // USB cable, where every card is present and only the board knows which
  // ones are real.
  showCard('liftCard',has('motion'));
  showCard('nongCard',has('joints'));
  showCard('rgbCard',has('rgb'));
  showCard('audCard',has('audio'));
  showCard('camCard',has('camera'));
  if(st.wifi){
    $('hwifi').textContent=st.wifi.mode==='ap'?'AP '+st.wifi.ip:(st.wifi.mode==='sta'?st.wifi.ip+' ('+st.wifi.rssi+'dBm)':'off');
    const wm=(st.wifi.wmode||'on');
    const wn=$('wifiNow');if(wn)wn.textContent=st.wifi.mode==='sta'?('ON, joined '+st.wifi.ssid+' @ '+st.wifi.ip):(st.wifi.mode==='ap'?(wm==='ap'?('AP hotspot @ '+st.wifi.ip):('ON — AP fallback @ '+st.wifi.ip+' (no network joined yet)')):'OFF (USB/RS485 only)');
    // default is ON (join WiFi, AP fallback). Pre-select the configured mode.
    const sr=$('setRadio');
    if(sr&&document.activeElement!==sr&&!sr.dataset.touched){
      const wm=(st.wifi.wmode||'on').toUpperCase();
      sr.value=(wm==='OFF'||wm==='AP')?wm:'ON';
    }
    if(sr&&!sr.dataset.hooked){sr.dataset.hooked=1;sr.onchange=()=>sr.dataset.touched=1;}
  }
  const m=st.module||{};
  // Each module type renders its own status, in its own marked block below.
  // A build that does not carry the type does not carry the function either,
  // so ask before calling — this is the one place the page is allowed to be
  // unsure what is in it.
  if(typeof liftStatus==='function')liftStatus(m);
  if(typeof nongStatus==='function')nongStatus(m,has);
  if(typeof camStatus==='function')camStatus(m);
  if(st.seq)$('seqStat').textContent=st.seq.running?('running '+st.seq.file):'idle';
  if(st.types&&!$('setType').options.length)
    st.types.forEach(t=>{const o=document.createElement('option');o.textContent=t;$('setType').appendChild(o);});
}
// a card belonging to another module type is absent in a per-type build
function showCard(id,on){const e=$(id);if(e)e.style.display=on?'':'none';}
//#type lift
// ---- lift: stages, travel speed, RGB strip, speaker ------------------------
function liftStatus(m){
  $('stg').textContent=(m.stage===undefined||m.stage<0)?'?':m.stage;
  $('stgState').textContent='state: '+(m.state||'-')+(m.target>=0?' -> '+m.target:'');
  $('limT').textContent='top:'+(m.limit_top?'HIT':'-');
  $('limD').textContent='bottom:'+(m.limit_down?'HIT':'-');
  $('homed').textContent='homed:'+(m.homed?'yes':'no');
  $('encv').textContent=m.homed?('pos:'+(m.pos_mm||0).toFixed(0)+'mm'):('enc:'+(m.encoder!==undefined?m.encoder:'-'));
  if(m.speed_pwm!==undefined){
    $('spdInfo').textContent='speed: pwm '+m.speed_pwm+' ~'+((m.est_mms||0)/1000).toFixed(2)+' m/s'
      +' | '+(m.stage_mm||0).toFixed(0)+' mm in ~'+(m.stage_s||0).toFixed(1)+' s'
      +(m.enc?' | measured '+((m.vel_mms||0)/1000).toFixed(2)+' m/s':' | no encoder');
  }
  const gk=(m.stages||0)+'_'+(m.enc?1:0);
  if(m.stages!==undefined&&gk!==gotoBuilt){
    gotoBuilt=gk;const g=$('gotoBtns');g.innerHTML='';
    for(let i=0;i<m.stages;i++){
      if(!m.enc&&i>0&&i<m.stages-1)continue; // no encoder: endpoints only
      const b=document.createElement('button');b.textContent=i;b.onclick=()=>cmd('GOTO '+i);g.appendChild(b);
    }
  }
  if(m.rgb&&document.activeElement.id!=='rgbb'){$('rgbb').value=m.rgb.bright;}
  if(m.rgb&&document.activeElement.id!=='rgbe'){$('rgbe').value=m.rgb.effect;}
  if(m.audio){
    $('nowPlaying').textContent=(m.audio.playing?('playing '+m.audio.file):'stopped')+' | vol '+m.audio.vol;
    if(document.activeElement.id!=='vol')$('vol').value=m.audio.vol;
    if(document.activeElement.id!=='volNum')$('volNum').value=m.audio.vol;
  }
}
function setSpeed(){
  const v=$('spdVal').value;
  if(!v)return;
  cmd($('spdUnit').value==='ms'?('SPEED '+v+' MS'):('SPEED '+v));
}
function sendRgb(){
  const h=$('rgbc').value;
  cmd('RGB '+parseInt(h.substr(1,2),16)+' '+parseInt(h.substr(3,2),16)+' '+parseInt(h.substr(5,2),16));
}
function playSel(){const v=$('musicSel').value;if(v)cmd('PLAY '+v);}
//#end
//#type nong
// ---- nong: joints, kinematics readout, servo setup -------------------------
function nongStatus(m,has){
  // isNong was USED here and never defined — a ReferenceError that killed
  // the whole status handler at this line, so the joint sliders were never
  // built and everything below stopped too. It lost its definition when the
  // capability refactor replaced the type checks; ask the capabilities.
  const isNong = has('joints');
  if(isNong&&m.joints)renderNong(m);
  // servo travel + rate readout: only while the user is not typing in a box
  if(isNong&&m.servo_range&&!$('svNow').dataset.held){
    const j=$('svJoint').value, all=m.servo_range, hz=m.frame_hz||[];
    const one=v=>v.every(x=>x===v[0]);
    $('svNow').textContent='now: travel '+(one(all)?all[0]+'° (all)':all.join(',')+'°')+
      (hz.length?('  ·  rate '+(one(hz)?hz[0]+'Hz (all)':hz.join(',')+'Hz')):'');
    if(document.activeElement.id!=='svRange')
      $('svRange').value=(j==='ALL')?all[0]:all[+j-1];
    if(hz.length&&document.activeElement.id!=='svRate')
      $('svRate').value=(j==='ALL')?hz[0]:hz[+j-1];
  }
}
// nong humanoid: 10 logical joints — 8 arm (2 per universal joint) + WAIST
// (body yaw, left/right) + SHRUG (both shoulders up/down). See NongModule.h.
const JN=['L Shoulder Pitch','L Shoulder Roll','L Elbow Pitch','L Elbow Roll',
          'R Shoulder Pitch','R Shoulder Roll','R Elbow Pitch','R Elbow Roll',
          'Waist (turn L/R)','Shrug (rock L up/R down)'];
let lastNongM=null;
function nongModeChanged(){if(lastNongM)renderNong(lastNongM);}
// forward kinematics with the default geometry (shoulder +-105/95, upper 115,
// fore 105 mm) - same frame as Nong Studio: origin = torso center, Y up
function fkArm(j,side){
  const d2r=Math.PI/180,dir=[-1,side>0?1:-1,-1,side>0?1:-1];
  const a=j.map((v,i)=>(v-90)*dir[i]*d2r);
  const rx=t=>[[1,0,0],[0,Math.cos(t),-Math.sin(t)],[0,Math.sin(t),Math.cos(t)]];
  const rz=t=>[[Math.cos(t),-Math.sin(t),0],[Math.sin(t),Math.cos(t),0],[0,0,1]];
  const mul=(A,B)=>{const C=[[0,0,0],[0,0,0],[0,0,0]];for(let i=0;i<3;i++)for(let k=0;k<3;k++)for(let l=0;l<3;l++)C[i][k]+=A[i][l]*B[l][k];return C;};
  const ap=(M,v)=>[M[0][0]*v[0]+M[0][1]*v[1]+M[0][2]*v[2],M[1][0]*v[0]+M[1][1]*v[1]+M[1][2]*v[2],M[2][0]*v[0]+M[2][1]*v[1]+M[2][2]*v[2]];
  const sh=[side*105,95,0];
  const Rs=mul(rx(a[0]),rz(a[1]));
  const el=ap(Rs,[0,-115,0]).map((v,i)=>v+sh[i]);
  const Re=mul(Rs,mul(rx(a[2]),rz(a[3])));
  const wr=ap(Re,[0,-105,0]).map((v,i)=>v+el[i]);
  return {el,wr};
}
const fmt3=p=>'('+p.map(v=>Math.round(v)).join(', ')+')';
function renderNong(m){
  lastNongM=m;
  const box=$('jointRows');
  const mode=$('nmode').value;
  if(!box.dataset.built){
    box.dataset.built=1;
    JN.forEach((n,i)=>{
      const r=document.createElement('div');r.className='row';
      const l=document.createElement('span');l.className='lbl';l.style.minWidth='130px';l.textContent=n;
      const s=document.createElement('input');s.type='range';s.min=0;s.max=180;s.id='j'+i;
      const v=document.createElement('input');v.type='number';v.min=0;v.max=180;v.id='jv'+i;v.style.width='70px';
      // sliders keep what YOU set - they are never overwritten while you work;
      // the "now" label shows the robot's real position
      s.value=v.value=Math.round(m.joints[i]);
      const now=document.createElement('span');now.className='statline';now.id='jnow'+i;now.style.minWidth='84px';
      s.oninput=()=>{v.value=s.value;};
      s.onchange=()=>{if($('nmode').value==='slider')cmd('JOINT '+(i+1)+' '+s.value);};
      v.onchange=()=>{s.value=v.value;if($('nmode').value==='slider')cmd('JOINT '+(i+1)+' '+v.value);};
      r.appendChild(l);r.appendChild(s);r.appendChild(v);r.appendChild(now);
      box.appendChild(r);
    });
  }
  m.joints.forEach((a,i)=>{
    const off=(m.pins&&m.pins[i]<0)||mode!=='slider';
    $('j'+i).disabled=off;$('jv'+i).disabled=off;
    // sliders respect each servo's real travel limits (universal joint)
    if(m.min&&m.max){$('j'+i).min=$('jv'+i).min=m.min[i];$('j'+i).max=$('jv'+i).max=m.max[i];}
    $('jnow'+i).textContent='now '+a.toFixed(1)+'°';
  });
  let L=fkArm(m.joints.slice(0,4),1),R=fkArm(m.joints.slice(4,8),-1);
  // WAIST yaws the whole body about the vertical (Y) axis, so the wrist/elbow
  // world positions turn with it; SHRUG rocks the shoulder bar about the
  // front-back axis (see-saw: +X shoulder up, -X down), not a symmetric lift.
  const waist=(m.joints[8]!==undefined)?m.joints[8]:90;
  const shrug=(m.joints[9]!==undefined)?m.joints[9]:90;
  const wy=(waist-90)*Math.PI/180, sr=(shrug-90)*Math.PI/180;
  const body=p=>{ const y=p[1]+p[0]*Math.sin(sr);           // roll: up on +X, down on -X
                  return [p[0]*Math.cos(wy)+p[2]*Math.sin(wy), y, -p[0]*Math.sin(wy)+p[2]*Math.cos(wy)]; };
  L={el:body(L.el),wr:body(L.wr)};R={el:body(R.el),wr:body(R.wr)};
  $('jxyz').textContent='XYZ mm (origin = torso center):  '
    +'L elbow '+fmt3(L.el)+'  L wrist '+fmt3(L.wr)
    +'   R elbow '+fmt3(R.el)+'  R wrist '+fmt3(R.wr)
    +'  | waist '+Math.round(waist)+'° shrug '+Math.round(shrug)+'°';
  $('nongStat').textContent=(m.moving?'moving':'idle')+(m.attached?'':' | POWER OFF (relaxed)')
    +(m.link?(' | leader -> '+(m.peer>0?('module '+m.peer):'broadcast')):'');
  if(document.activeElement.id!=='ndps')$('ndps').value=Math.round(m.speed_dps);
  if(document.activeElement.id!=='npeer'&&m.peer!==undefined&&!$('npeer').dataset.touched)
    {$('npeer').value=m.peer;$('nlink').checked=!!m.link;}
}
async function savePair(){
  $('npeer').dataset.touched=1;
  const r1=await cmd('CFG link '+($('nlink').checked?1:0));
  const r2=await cmd('CFG peer '+($('npeer').value||0));
  // An EMPTY reply means the request never got through — cmd() returns '' on a
  // fetch failure. Only 'ERR' was checked, so a WiFi hiccup while saving the
  // 2-ESP pairing rebooted the humanoid mid-session with the OLD leader/partner
  // setting and told the user it had saved.
  if(!r1||!r2||r1.startsWith('ERR')||r2.startsWith('ERR')){
    alert('These settings were NOT saved, so the board has not been restarted.\n\n'
         +'Check the console below for what the module said, then try again.');
    return;
  }
  await cmd('REBOOT');
}
// ---- nong servo type / travel (which servo is on which joint) --------------
// SERVO applies a preset (pulse + speed + travel); RANGE changes only the
// travel, for a servo that is not in the list. Both are per joint or ALL.
function svReply(r){ // show the reply for a few seconds, then resume the readout
  const e=$('svNow');e.textContent=r;e.dataset.held=1;
  setTimeout(()=>{delete e.dataset.held;},6000);
}
async function setServo(){ svReply(await cmd('SERVO '+$('svJoint').value+' '+$('svType').value)); }
async function setRange(){ svReply(await cmd('RANGE '+$('svJoint').value+' '+($('svRange').value||180))); }
async function setRate(){ svReply(await cmd('RATE '+$('svJoint').value+' '+($('svRate').value||50))); }
//#end
//#type cam
// ---- camera: one frame at a time -------------------------------------------
// Every picture is a fresh GET of /api/cam.jpg. There is no stream: an MJPEG
// stream holds a connection open for as long as it runs, and this board has
// four of them in total — one live view would leave the rest of the site
// unable to answer. A cache-busting number keeps the browser from showing the
// picture it already has.
// Until when the camera line is holding a message worth reading.
//
// The status poll runs every 500 ms and used to rewrite this line each time,
// so "no picture — <the real reason>", "picture taken", "live…" and "the live
// view stopped" were all wiped within half a second of appearing. The reason a
// camera is not working is the one thing the card exists to tell you, and it
// was on screen too briefly to read. (It was meant to be guarded by camTimer,
// which was declared and then never assigned, so the guard was always open.)
let camHold=0;
function camSay(text,holdMs){
  const el=$('camStat');
  if(!el)return;
  el.textContent=text;
  camHold=Date.now()+(holdMs===undefined?8000:holdMs);
}
// Ask through FETCH, not through <img src>.
//
// The hub serves this same page for a module it reaches over WiFi or a cable,
// and it does that by patching window.fetch to re-address /api/* at the right
// board. An <img src> never goes through fetch, so it asked the HUB for
// /api/cam.jpg, got a 404, and the card blamed the ribbon cable — on a camera
// that was working perfectly. Fetching keeps every transport honest, and it
// also lets the real reason be shown instead of a guess.
async function camShot(){
  const img=$('camImg');
  try{
    const r=await fetch('/api/cam.jpg?'+Date.now());
    if(!r.ok){
      const why=(await r.text()).slice(0,160);
      camSay('no picture — '+(why||('the module answered '+r.status)),15000);
      return;
    }
    const b=await r.blob();
    if(img.dataset.url)URL.revokeObjectURL(img.dataset.url);
    img.dataset.url=URL.createObjectURL(b);
    img.src=img.dataset.url;
    img.style.display='';
    camSay('picture taken '+new Date().toLocaleTimeString()+
      ' · '+(b.size/1024).toFixed(1)+' kB');
  }catch(e){
    camSay('no picture — cannot reach the module ('+(e.message||e)+')',15000);
  }
}
// Live view: ONE connection carrying many frames (MJPEG), which the browser
// renders natively from an <img>.
//
// Measured on the board: capturing a QVGA frame costs ~25 ms, but delivering
// it as a separate request cost ~120 ms, because this server closes the
// connection after every response. So a live view built from stills spent five
// times longer opening sockets than taking pictures — 1 fps on the original
// fixed timer, 7 fps when chained. Streaming pays that once: 18.7 fps.
//
// An <img> cannot go through the hub's fetch shim, so the URL is built here
// with the same ?dev= the page was opened with.
function camUrl(path){
  const dev=new URLSearchParams(location.search).get('dev');
  return dev ? ('/api/dev/'+path+'?dev='+encodeURIComponent(dev))
             : ('/api/'+path);
}
function camLiveToggle(){
  const img=$('camImg');
  // The board has ONE frame buffer without PSRAM, and take() reclaims whatever
  // frame is out on loan. Pressing "Take a picture" while the live view is
  // running therefore pulls the frame out from under the stream mid-send, and
  // the picture arrives torn. One reader of the sensor at a time.
  const shot=$('camShotBtn');
  if(shot){
    shot.disabled=$('camLive').checked;
    shot.title=shot.disabled
      ? 'turn the live view off first — the camera can only be read by one thing at a time'
      : '';
  }
  if($('camLive').checked){
    camSay('live…',3000);
    img.style.display='';
    img.onerror=()=>camSay(
      'the live view stopped — someone else may be watching (one at a time)',15000);
    img.src=camUrl('cam.stream')+(camUrl('cam.stream').indexOf('?')<0?'?':'&')+'t='+Date.now();
  }else{
    // Dropping the src is what closes the connection, and the board only
    // allows one viewer — leaving it open would lock everyone else out.
    img.removeAttribute('src');
    camSay('live view off',3000);
  }
}
function camStatus(m){
  if(m.ready===false){
    // The camera failing to start outranks anything being held: it IS the
    // answer to "why is there no picture".
    camSay('camera not started: '+(m.error||'unknown')+
      ' — check the ribbon cable and the 5V supply',15000);
    return;
  }
  if(m.size&&document.activeElement.id!=='camSize')$('camSize').value=m.size;
  if(m.quality&&document.activeElement.id!=='camQ')$('camQ').value=m.quality;
  if(m.flash!==undefined)$('camFlash').checked=!!m.flash;
  // The idle line is the LEAST important thing this element ever shows, so it
  // waits until whatever is being held has had its time on screen.
  if(Date.now()>camHold&&m.shots!==undefined)
    $('camStat').textContent=m.shots+' picture(s) since boot'+
      (m.psram?'':' · no PSRAM: small frames only')+(m.last?(' · last '+m.last):'');
}
//#end
// ---- which cards are on screen -------------------------------------
// TWO things decide it and they must agree: the tab you picked, and whether
// the setup cards are unlocked. Splitting that across two places is how a card
// ends up visible on the wrong tab, or hidden on the right one.
let modTab='control';
function applyTabs(){
  document.querySelectorAll('[data-tab]').forEach(el=>{
    const right = el.dataset.tab === modTab;
    const allowed = !el.classList.contains('setupCard') || !!auth;
    el.style.display = (right && allowed) ? '' : 'none';
  });
  // the login card itself lives on Setup and shows whether or not you are in
  const lc=$('loginCard'); if(lc && modTab==='setup') lc.style.display='';
  document.querySelectorAll('.mtab').forEach(b=>
    b.classList.toggle('on', b.dataset.mtab===modTab));
  // cards nested INSIDE a card (zero calibration, servo type) follow the login
  // only — their parent card already handles the tab
  document.querySelectorAll('.setupCard:not([data-tab])').forEach(e=>
    e.style.display = auth ? '' : 'none');
}
function showTab(name){ modTab=name; applyTabs(); }

// ---- Setup login (accounts stored on the board, see USER) ----
// The shipped password is deliberately not written here either: this file
// is served to anyone who opens the page, and view-source is not a lock.
let auth=null; // {user,pass} while logged in
// Set from the board's own answer: it is still carrying its shipped password.
let mustChange=false;

// Choose the first real password. Until this succeeds, Setup stays shut — a
// board nobody has secured is the same as a board with no login at all.
async function doFirstChange(){
  const np=$('mcPass').value;
  if(np.length < 8){ $('mcStat').textContent='at least 8 characters'; return; }
  const r=await cmd('USER PASS '+auth.user+' '+auth.pass+' '+np);
  if(!r.startsWith('OK')){ $('mcStat').textContent=r.replace(/^ERR ?/,'') || 'the board refused it'; return; }
  // The password just changed, so the old session and the stored one are both
  // stale: log in again with the new one rather than pretending nothing moved.
  auth.pass=np; mustChange=false;
  // The new password invalidated the old session, so this is what keeps the
  // page usable. Ignoring the result meant Setup opened on a DEAD session:
  // every card visible, every action behind it refused, and nothing saying so.
  try{
    const s=await fetch('/api/login',{method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:'user='+encodeURIComponent(auth.user)+'&pass='+encodeURIComponent(np)});
    if(!s.ok){
      $('mcStat').textContent='The password was changed, but signing back in '+
        'failed. Log in again with the new one.';
      return;
    }
  }catch(e){
    $('mcStat').textContent='The password was changed, but the board stopped '+
      'answering. Reload this page and log in with the new one.';
    return;
  }
  $('mcPass').value=''; $('mcStat').textContent='';
  $('mustChangeBox').style.display='none';
  $('usersBox').style.display='';
  applyTabs(); loadUsers(); loadPins();
  $('setupBtn').textContent='⚙ Setup (open)';
}
// What this board is doing, and how this page is reached to it — one honest
// line, in words. `dev` in the address means the HUB is serving this page over
// a cable or the bus; without it the board served the page itself over WiFi.
function paintNow(st){
  var doing;
  if(st.seq && st.seq.running)
    doing = 'playing ' + (st.seq.file || 'a sequence') + ' right now';
  else
    doing = 'not running anything';

  var dev = new URLSearchParams(location.search).get('dev') || '';
  var how;
  if(dev.indexOf('usb:')===0)       how = 'reached over a cable, through the hub';
  else if(dev.indexOf('rs485:')===0)how = 'reached over the RS485 bus, through the hub';
  else if(dev)                      how = 'reached through the hub';
  else if(st.wifi && st.wifi.mode==='ap')
    how = 'you are on this board\'s own hotspot';
  else if(st.wifi && st.wifi.ip)    how = 'reached over WiFi at ' + st.wifi.ip;
  else                              how = 'reached directly';

  $('hnow').textContent = doing + ' — ' + how + '.';
}

function setupToggle(){
  // the button is now a shortcut to the Setup tab; clicking it again goes back
  // to Control, so it still toggles the way it always did
  showTab(modTab==='setup' ? 'control' : 'setup');
}
// True when the HUB is serving this page over a cable or the bus: its shim
// rewrites /api/... into /api/dev/..., so there is no board HTTP session to
// get, and holding the cable is already physical access.
function viaHub(){ return !!new URLSearchParams(location.search).get('dev'); }

// THE WAY BACK. Opening a board's page is otherwise a one-way trip: typed into
// a phone there is no Back to press, and the hub is the only screen that shows
// the other modules.
//
// Two ways to know where the hub is, and neither is a guess. Through the hub,
// this page IS on the hub, so '/' is right by construction. Reached directly,
// the board offers the hub that last identified itself to it - see noteHub in
// WebPortal.cpp - and offers nothing when no hub has been in touch, because a
// link to the wrong PC is worse than no link.
function showHubLink(st){
  const a=$('hubBack');
  if(!a) return;
  if(viaHub()){ a.href='/'; a.textContent='← back to the hub'; a.hidden=false; return; }
  const hub=(st&&st.hub)||'';
  if(!hub){ a.hidden=true; return; }
  a.href='http://'+hub+'/';
  a.textContent='← the hub on '+hub;
  a.hidden=false;
}

async function doLogin(){
  const u=$('liUser').value.trim(),p=$('liPass').value;
  const r=await cmd('AUTH '+u+' '+p);
  if(r.startsWith('OK') && !viaHub()){
    // Talking to the board directly: ask for a SESSION. Without this the page
    // would look logged in and then be refused by every route that changes
    // something — the cards would open and nothing behind them would work.
    try{
      const s=await fetch('/api/login',{method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:'user='+encodeURIComponent(u)+'&pass='+encodeURIComponent(p)});
      if(!s.ok){ $('liStat').textContent='the board refused that login'; return; }
      // If the answer cannot be read, ASK for a password rather than not.
      // Swallowing this left mustChange false, so a board still carrying the
      // shipped password quietly stopped asking anyone to change it - the
      // prompt turning itself off is the one failure mode that matters here.
      // Being asked once too often is recoverable; not being asked is not.
      try{ mustChange = (await s.json()).mustChange === true; }
      catch(e){ mustChange = true; }
    }catch(e){ $('liStat').textContent='could not reach the board to log in'; return; }
  }
  if(r.startsWith('OK') && mustChange){
    // Logged in, but this board has never had a password chosen. Do not open
    // Setup: ask for one first. Everything else stays exactly as it was.
    auth={user:u,pass:p};
    $('loginForm').style.display='none';
    $('mustChangeBox').style.display='';
    $('liWho').textContent=u;$('liPass').value='';
    return;
  }
  if(r.startsWith('OK')){
    auth={user:u,pass:p};
    $('loginForm').style.display='none';$('usersBox').style.display='';
    $('liWho').textContent=u;$('liPass').value='';
    applyTabs();
    $('setupBtn').textContent='⚙ Setup (open)';
    loadUsers();
    loadPins(); // build the pin pickers now that the card is visible
  }else{$('liStat').textContent='wrong user or password';}
}
function doLogout(){
  // End the session on the BOARD too, not just in this tab. A logout that
  // only forgets locally leaves the cookie working for whoever sits down next.
  // Told to the BOARD, and the answer is waited for. A logout that only
  // forgets locally leaves the cookie working for whoever sits down next -
  // which is the very thing the line above promises not to do, and the empty
  // catch used to break that promise silently.
  if(!viaHub()){
    fetch('/api/logout',{method:'POST'})
      .then(r=>{ if(!r.ok) throw new Error('refused'); })
      .catch(()=>{ $('liStat').textContent='Logged out here, but the board did '+
        'not confirm it. Close this browser to be sure.'; });
  }
  auth=null;
  $('loginForm').style.display='';$('usersBox').style.display='none';
  applyTabs();
  $('setupBtn').textContent='⚙ Setup / Login';
}
async function loadUsers(){
  if(!auth)return;
  const r=await cmd('USER LIST '+auth.user+' '+auth.pass);
  const box=$('userList');box.innerHTML='';
  let list;try{list=JSON.parse(r.trim());}catch(e){box.textContent=r;return;}
  list.forEach(u=>{
    const chip=document.createElement('span');chip.className='peer';chip.style.margin='2px';
    chip.textContent=u+(u===auth.user?' (you)':'');
    if(u!==auth.user&&list.length>1){
      const x=document.createElement('a');x.textContent=' ✕';x.style.cursor='pointer';x.style.color='var(--err)';
      x.onclick=()=>delUser(u);chip.appendChild(x);
    }
    box.appendChild(chip);
  });
}
async function addUser(){
  if(!auth)return;
  const u=$('nuUser').value.trim(),p=$('nuPass').value;
  if(!u||!p){$('userStat').textContent='enter a username and password';return;}
  const r=await cmd('USER ADD '+auth.user+' '+auth.pass+' '+u+' '+p);
  $('userStat').textContent=r;$('nuUser').value='';$('nuPass').value='';loadUsers();
}
async function changeMyPass(){
  if(!auth)return;
  const np=$('pwNew').value;
  if(!np){$('userStat').textContent='enter a new password';return;}
  const r=await cmd('USER PASS '+auth.user+' '+auth.pass+' '+np);
  if(r.startsWith('OK'))auth.pass=np;
  $('userStat').textContent=r;$('pwNew').value='';
}
async function delUser(u){
  if(!auth||!confirm('Delete user '+u+'?'))return;
  $('userStat').textContent=await cmd('USER DEL '+auth.user+' '+auth.pass+' '+u);
  loadUsers();
}
async function loadList(dir,sel){
  const s=$(sel);
  if(!s)return;   // /music only exists on a board that has a speaker
  // An empty dropdown means "this card has nothing on it". A dropdown that
  // could not be READ has to say so instead, or a failed request looks like
  // an empty SD card and someone goes looking for files that are there.
  try{const r=await fetch('/api/files?dir='+dir);const fs=await r.json();
    s.innerHTML='';
    fs.forEach(f=>{const o=document.createElement('option');o.value=dir+'/'+f.n;o.textContent=f.n;s.appendChild(o);});
    if(!fs.length){const o=document.createElement('option');o.disabled=true;
      o.textContent='nothing in '+dir;s.appendChild(o);}
  }catch(e){
    s.innerHTML='';
    const o=document.createElement('option');o.disabled=true;
    o.textContent='could not read '+dir+' - is the SD card in?';
    s.appendChild(o);
  }
}
function runSel(){const v=$('moveSel').value;if(v)cmd('MOVE '+v);}
async function loadFiles(){
  const dir=$('dirSel').value;
  try{
    const r=await fetch('/api/files?dir='+dir);const fs=await r.json();
    const tb=$('fileTbl').tBodies[0];tb.innerHTML='';
    fs.forEach(f=>{
      const tr=document.createElement('tr');
      const p=dir+'/'+f.n;
      const td1=document.createElement('td');td1.textContent=f.n;
      const td2=document.createElement('td');td2.textContent=(f.s/1024).toFixed(1)+' kB';
      const td3=document.createElement('td');
      const g=document.createElement('a');g.href='/api/download?path='+encodeURIComponent(p);g.textContent='get';
      const d=document.createElement('a');d.textContent='del';
      d.onclick=async()=>{
        // Name the exact file. "Delete?" on its own tells the reader nothing,
        // and this cannot be undone — the card may be the only copy.
        if(!confirm('Delete "'+p+'" from this module\'s SD card?\n\n'
                   +'This cannot be undone. If this is the only copy of that '
                   +'sequence, it is gone.'))return;
        log(await (await fetch('/api/delete?path='+encodeURIComponent(p))).text());
        refreshLists();
      };
      td3.appendChild(g);td3.appendChild(d);
      tr.appendChild(td1);tr.appendChild(td2);tr.appendChild(td3);
      tb.appendChild(tr);
    });
  }catch(e){
    // An empty catch made 'could not ask' look identical to 'nothing there'.
    // The element is fileTbl's tbody — the same one the success path fills at
    // the top of this function. An earlier version of this handler looked up
    // 'fileRows', which does not exist, so the guard swallowed it and the
    // message never appeared: an error state that was itself broken.
    const t=$('fileTbl');
    if(t&&t.tBodies[0])t.tBodies[0].innerHTML=
      '<tr><td colspan="3" class="statline">Could not read the card. The board '
      +'may be busy, or it has no SD card fitted. Press refresh to try again.'
      +'</td></tr>';
  }
}
async function upload(){
  const f=$('upFile').files[0];
  if(!f){alert('Pick a file first — use the Choose file button next to Upload.');return;}
  const fd=new FormData();fd.append('file',f,f.name);
  $('upStat').textContent='uploading...';
  try{
    const r=await fetch('/api/upload?dir='+$('dirSel').value,{method:'POST',body:fd});
    $('upStat').textContent=r.ok?'done':'failed ('+await r.text()+')';
    refreshLists();
  }catch(e){$('upStat').textContent='failed';}
}
function refreshLists(){loadFiles();loadList('/music','musicSel');loadList('/moves','moveSel');}
async function loadPeers(){
  try{
    const r=await fetch('/api/peers');const ps=await r.json();
    const g=$('peerList');g.innerHTML='';
    ps.forEach(p=>{
      const el=document.createElement(p.self?'span':'a');
      el.className='peer'+(p.self?' self':'');
      el.textContent=p.name+' #'+p.id+' ';
      const s=document.createElement('small');
      s.textContent=p.type+(p.self?' (this one)':' · '+p.ip);
      el.appendChild(s);
      if(!p.self)el.href='http://'+p.ip+'/';
      g.appendChild(el);
    });
    // An empty state says what would fill it, not just that it is empty.
    if(!ps.length)g.innerHTML='<span class="statline">No other modules have '
      +'joined this one yet. Modules appear here once they are on the same '
      +'group and within radio range.</span>';
  }catch(e){
    if(g)g.innerHTML='<span class="statline">Could not check for other modules '
      +'just now. This list will try again in a few seconds.</span>';
  }
}
setInterval(loadPeers,15000);
async function saveSettings(){
  const id=$('setId').value,name=$('setName').value,type=$('setType').value;
  const ssid=$('setSsid').value,pass=$('setPass').value;
  const reps=[];
  if(id)reps.push(await cmd('SET ID '+id));
  if(name)reps.push(await cmd('SET NAME '+name));
  if(type)reps.push(await cmd('SET TYPE '+type));
  // QUOTE the network name. wifiargs::parse treats an unquoted first argument
  // as "the ssid up to the first space", so "MSI 3058" was stored as ssid
  // "MSI" with password "3058 <the real password>" and the board simply never
  // joined — with every read-back showing exactly what you typed. Network names
  // contain spaces constantly (phone hotspots especially). The parser has
  // always handled quotes; this page just never sent them, and the field's
  // "no spaces" placeholder was covering for it.
  // The password is quoted too: parse() unquotes it, so a password with a
  // trailing space survives instead of being trimmed away.
  if(ssid)reps.push(await cmd('SET WIFI "'+ssid.replace(/"/g,'')+'" "'+
                              pass.replace(/"/g,'')+'"'));
  const sr=$('setRadio');
  if(sr.dataset.touched&&sr.value)reps.push(await cmd('SET WIFI '+sr.value));  // ON | AP | OFF
  if(reps.some(r=>r.startsWith('ERR')||r==='')){
    alert('Some settings were NOT saved - check the console. Not rebooting.');
    return;
  }
  await cmd('REBOOT');
  alert('Saved. Module reboots now - reconnect if the name/network changed.');
}
// ---- hardware pin map ----
// Only the groups this build carries: the board's own PIN? answer lists no
// other type's pins either, so a tab for them would be empty.
const PIN_GROUPS={bus:'RS485 bus',sd:'microSD card',
//#type lift
  lift:'Lift (motor / encoder / limits)',audio:'I2S speaker',
//#end
//#type nong
  nong:'Nong servos',
//#end
};
// which module type each pin group belongs to ("core" = shown for every type).
// SD + RS485 (bus) are on every module; the I2S speaker (audio) and RGB strip
// are lift-only hardware, so the audio pins show only under the lift tab.
const GROUP_TYPE={bus:'core',sd:'core',
//#type lift
  lift:'lift',audio:'lift',
//#end
//#type nong
  nong:'nong',
//#end
};
const GROUP_LABEL={
//#type lift
  lift:'Lift module',
//#end
//#type nong
  nong:'Nong module',
//#end
};
let pinValid=[],pinCur={},pinBy={},pinTab=null;
function pinClass(g){return {ok:'',strap:'color:var(--warn)',in:'color:var(--mut)',
  uart0:'color:var(--err)',flash:'color:var(--err)',rgb:'color:var(--err)'}[g]||'';}
function buildPinTabs(){
  // one tab per module type present in the pin map (dynamic — future types
  // appear automatically). The tab picks which module's pins you configure;
  // the shared buses (RS485/SD/I2S) always show under any tab.
  const modTypes=[...new Set(Object.values(pinCur).map(v=>GROUP_TYPE[v.group]))]
    .filter(t=>t&&t!=='core');
  if(!modTypes.length)return;
  if(!pinTab||!modTypes.includes(pinTab))
    pinTab=(st.type&&modTypes.includes(st.type))?st.type:modTypes[0];
  const bar=$('pinTabs');bar.innerHTML='';
  modTypes.forEach(t=>{
    const b=document.createElement('button');
    b.textContent=(GROUP_LABEL[t]||t)+(t===st.type?' ●':'');
    b.title=t===st.type?'this board runs as '+t:'configure '+t+' pins';
    b.className=(t===pinTab)?'primary':'';
    b.onclick=()=>{pinTab=t;renderPinGroups();};
    bar.appendChild(b);
  });
}
async function loadPins(){
  let vt,ct;
  try{[vt,ct]=await Promise.all([cmd('PIN VALID'),cmd('PIN?')]);}
  catch(e){$('pinStat').textContent='cannot reach the board';return;}
  // did PIN? (an OBJECT) come back but PIN VALID (an ARRAY) not? then the board
  // IS answering — something on the PC side is DROPPING the array reply (an old
  // Mice hub / MiceHub.exe that skips serial lines starting with "["). That is
  // NOT a firmware problem, so don't send the user re-flashing.
  // The failure IS handled here - okCur carries it to the message below -
  // but it says so out loud, so that an empty catch anywhere on this page
  // stays a fault rather than a thing to argue about case by case.
  let okCur=false;
  try{pinCur=JSON.parse((ct||'').trim());okCur=true;}catch(e){okCur=false;}
  try{
    pinValid=JSON.parse((vt||'').trim());
    if(!Array.isArray(pinValid)) throw new Error('not an array');
    pinBy={};pinValid.forEach(p=>pinBy[p.g]=p);
  }catch(e){
    $('pinTabs').innerHTML='';
    const msg=okCur
      ? 'the board answered <b>PIN?</b> but its <b>PIN VALID</b> list didn\'t get '+
        'through — your Mice hub is out of date and drops JSON-array replies over '+
        'USB. <b>Restart the Mice hub / rebuild MiceHub.exe</b> (run <code>python '+
        'main.py</code>). This is NOT a firmware problem — re-flashing won\'t help.'
      : 'this board\'s firmware doesn\'t support pin config yet — re-flash the latest '+
        '(pio run -e mice_nong -t upload, or mice_lift for a lift).';
    $('pinGroups').innerHTML='<div class="statline" style="color:var(--warn)">'+
      msg+'<br>reply: '+((''+vt+' / '+ct).slice(0,90))+'</div>';
    return;
  }
  buildPinTabs();
  renderPinGroups();
}
function renderPinGroups(){
  buildPinTabs();
  const box=$('pinGroups');box.innerHTML='';
  // legend
  const leg=document.createElement('div');leg.className='statline';
  leg.innerHTML='pin classes: <b>ok</b> free · '+
    '<span style="color:var(--warn)">strap</span> boot pin (care) · '+
    '<span style="color:var(--mut)">in</span> 34-39 input-only · '+
    '<span style="color:var(--err)">uart0</span> USB serial (1/3) · '+
    '<span style="color:var(--err)">flash/rgb</span> unavailable. '+
    'Each option lists its caps: <b>pwm</b> (servo/motor) · <b>adc</b> · <b>dac</b>.';
  box.appendChild(leg);
  Object.entries(PIN_GROUPS).forEach(([grp,title])=>{
    // show the selected tab's module pins + the shared/core buses.
    // (pinTab guard: if no tab yet, show everything rather than hide all)
    if(pinTab&&GROUP_TYPE[grp]!=='core'&&GROUP_TYPE[grp]!==pinTab)return;
    const items=Object.entries(pinCur).filter(([k,v])=>v.group===grp);
    if(!items.length)return;
    const h=document.createElement('div');h.className='lbl';h.style.margin='8px 0 2px';h.textContent=title;
    box.appendChild(h);
    const wrap=document.createElement('div');wrap.className='row';
    items.forEach(([k,v])=>{
      const cell=document.createElement('label');cell.style.cssText='display:flex;flex-direction:column;font-size:11px;color:var(--mut);gap:1px';
      cell.appendChild(document.createTextNode(v.label));
      const sel=document.createElement('select');sel.id='pin_'+k;sel.style.width='170px';
      const optOff=document.createElement('option');optOff.value=-1;optOff.textContent='- none (-1)';sel.appendChild(optOff);
      pinValid.forEach(p=>{
        if(v.out&&p.c==='in')return;        // input-only can't drive an output
        if(p.c==='flash'||p.c==='uart0')return; // never assignable
        const o=document.createElement('option');o.value=p.g;
        o.textContent='GPIO'+p.g+(p.c!=='ok'?(' '+p.c):'')+(p.n?(' · '+p.n):'');
        o.style.cssText=pinClass(p.c);
        sel.appendChild(o);
      });
      sel.value=v.gpio;
      sel.onchange=paintPinDupes;
      cell.appendChild(sel);wrap.appendChild(cell);
    });
    box.appendChild(wrap);
  });
  paintPinDupes();
}
function paintPinDupes(){
  const used={};
  document.querySelectorAll('[id^=pin_]').forEach(s=>{const v=+s.value;if(v>=0)used[v]=(used[v]||0)+1;});
  document.querySelectorAll('[id^=pin_]').forEach(s=>{
    const v=+s.value;s.style.borderColor=(v>=0&&used[v]>1)?'var(--err)':'';
  });
}
async function savePins(){
  const sels=document.querySelectorAll('[id^=pin_]');
  const used={};let dupe=false;
  sels.forEach(s=>{const v=+s.value;if(v>=0){if(used[v])dupe=true;used[v]=1;}});
  if(dupe&&!confirm('Two functions share a GPIO — save anyway?'))return;
  $('pinStat').textContent='Saving the pins…';
  // Every reply is READ. This loop used to ignore them all and then reboot
  // saying "Pins saved", so a rejected pin (bad GPIO, or a select that fell
  // back to empty and sent "PIN <name> ") left the board restarting with a
  // half-applied pin map and nothing on screen to say so.
  const bad=[];
  for(const s of sels){
    const k=s.id.slice(4);
    if(+s.value===pinCur[k].gpio)continue;          // unchanged
    const r=await cmd('PIN '+k+' '+s.value);
    if(!r||r.startsWith('ERR'))bad.push(k+': '+(r||'no reply'));
  }
  if(bad.length){
    $('pinStat').textContent='Not saved — '+bad.length+' pin(s) were refused.';
    alert('These pins were NOT accepted, so the board has not been restarted:\n\n  '
         +bad.join('\n  ')+'\n\nFix them and save again.');
    return;
  }
  $('pinStat').textContent='Pins saved. Restarting the board…';
  await cmd('REBOOT');
  alert('Pins saved. The board restarts now to apply them.');
}
applyTabs();   // start on Control with setup locked
connectWs();
refreshLists();
loadPeers();
fetch('/api/status').then(r=>r.json()).then(s=>{
  st=s;render();
  $('setId').value=s.id;$('setName').value=s.name;
  setTimeout(()=>{if(s.types)$('setType').value=s.type;},0);
});
</script>
</body>
</html>)rawliteral";
