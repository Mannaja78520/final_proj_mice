#pragma once
#include <Arduino.h>

// Single-page control UI served from flash at "/" — works with no SD card.
// Talks to the JSON/text API in WebPortal.cpp and the /ws WebSocket.
static const char WEB_UI_HTML[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Module Control</title>
<style>
:root{--bg:#10141a;--card:#1a212b;--line:#2a3442;--txt:#dce3ec;--mut:#8b98a9;--acc:#4da3ff;--ok:#3ecf8e;--warn:#ffb454;--err:#ff6b6b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;padding:14px;max-width:1100px;margin:0 auto}
h1{font-size:22px}h2{font-size:15px;color:var(--acc);margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em}
header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:14px}
.badge{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:3px 12px;font-size:13px;color:var(--mut)}
.badge b{color:var(--txt)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
button{background:#243040;border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:9px 16px;font-size:15px;cursor:pointer}
button:hover{border-color:var(--acc)}
button.primary{background:var(--acc);border-color:var(--acc);color:#06121f;font-weight:600}
button.danger{background:#3a2020;border-color:#5c2e2e;color:var(--err)}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
input,select{background:#0d1117;border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:8px 10px;font-size:14px}
input[type=range]{padding:0;flex:1}
input[type=color]{padding:2px;width:52px;height:38px}
.stage{font-size:52px;font-weight:700;text-align:center;line-height:1.1}
.stage small{display:block;font-size:13px;color:var(--mut);font-weight:400}
.lbl{color:var(--mut);font-size:13px;min-width:72px}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
td a{color:var(--acc);text-decoration:none;margin-right:8px;cursor:pointer}
#log{background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:8px;height:130px;overflow-y:auto;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;word-break:break-all}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--mut);margin-right:6px}
.dot.on{background:var(--ok)}.dot.warn{background:var(--warn)}
.statline{font-size:13px;color:var(--mut)}
.peer{display:inline-block;background:#243040;border:1px solid var(--line);border-radius:20px;
  padding:6px 14px;margin:3px;color:var(--txt);text-decoration:none;font-size:14px}
a.peer:hover{border-color:var(--acc)}
.peer.self{border-color:var(--ok);cursor:default}
.peer small{color:var(--mut)}

/* responsive: this page is opened from a phone at the robot as often as from a
   desk, and over USB it is served by the hub to whatever device is at hand. */
@media (min-width:1500px){body{max-width:1400px;margin:0 auto}}
@media (max-width:720px){
  body{padding:12px}
  .card{padding:12px}
  .row{flex-wrap:wrap}
  .row label,.row .lbl{min-width:0}
  h2 button,h2 span{float:none!important}
  /* pin rows are name + a GPIO select; let them go full width rather than
     truncating the function name to nothing */
  .pinrow{flex-wrap:wrap}
  .pinrow select{flex:1 1 120px}
  input,select{max-width:100%}
  pre,#console{font-size:11px}
}
@media (max-width:430px){body{padding:9px}}
@media (pointer:coarse){
  button{min-height:36px;padding:8px 12px}
  input,select{min-height:34px}
}
</style>
</head>
<body>
<header>
  <h1 id="hname">module</h1>
  <span class="badge">ID <b id="hid">-</b></span>
  <span class="badge">type <b id="htype">-</b></span>
  <span class="badge">wifi <b id="hwifi">-</b></span>
  <span class="badge">SD <b id="hsd">-</b></span>
  <span class="badge"><span class="dot" id="wsdot"></span>live</span>
  <span style="flex:1"></span>
  <button class="primary" id="setupBtn" onclick="setupToggle()">&#9881; Setup / Login</button>
</header>

<div class="grid">
  <div class="card" id="loginCard" style="grid-column:1/-1;display:none">
    <h2>Setup login &#128274;</h2>
    <div id="loginForm">
      <div class="statline">log in to configure this module — <b>identity, WiFi mode,
        Hardware pins, users, zero calibration</b>. Same over WiFi / USB / RS485.
        Default account <b>manny</b> / <b>12345678</b>.</div>
      <div class="row">
        <span class="lbl">User</span><input id="liUser" autocomplete="username" style="width:150px">
        <span class="lbl">Pass</span><input id="liPass" type="password" autocomplete="current-password" style="width:150px">
        <button class="primary" onclick="doLogin()">Log in</button>
        <span class="statline" id="liStat"></span>
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

  <div class="card" style="grid-column:1/-1">
    <h2>Modules on network</h2>
    <div class="row">
      <div id="peerList" style="flex:1"><span class="statline">scanning...</span></div>
      <button onclick="loadPeers()">Rescan</button>
    </div>
  </div>

  <div class="card" id="liftCard">
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

  <div class="card" id="rgbCard">
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

  <div class="card" id="audCard">
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

  <div class="card" id="nongCard" style="grid-column:1/-1">
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

  <div class="card">
    <h2>Sequences</h2>
    <div class="row">
      <select id="moveSel" style="flex:1"></select>
      <button class="primary" onclick="runSel()">Run</button>
      <button onclick="cmd('MOVE STOP')">Stop</button>
    </div>
    <div class="statline" id="seqStat">idle</div>
  </div>

  <div class="card setupCard" style="grid-column:1/-1;display:none">
    <h2>Hardware pins <span class="statline">(stored on this board — reboot to apply)</span></h2>
    <div class="statline">pick which module type's pins to configure, then wire each
      function to a GPIO (same select boxes as before). The tabs are dynamic —
      any module type in the firmware shows up here.</div>
    <div id="pinTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0"></div>
    <div id="pinGroups"></div>
    <div class="row">
      <button class="primary" onclick="savePins()">Save &amp; reboot</button>
      <button onclick="cmd('PIN CLEAR').then(loadPins)">Reset to defaults</button>
      <span class="statline" id="pinStat"></span>
    </div>
  </div>

  <div class="card" style="grid-column:1/-1">
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

  <div class="card setupCard" style="display:none">
    <h2>Settings</h2>
    <div class="row"><span class="lbl">ID</span><input type="number" id="setId" min="1" max="247" style="width:90px"></div>
    <div class="row"><span class="lbl">Name</span><input id="setName" style="flex:1"></div>
    <div class="row"><span class="lbl">Type</span><select id="setType" style="flex:1"></select></div>
    <div class="row"><span class="lbl">WiFi SSID</span><input id="setSsid" placeholder="no spaces" style="flex:1"></div>
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

  <div class="card">
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
  $('liftCard').style.display=has('motion')?'':'none';
  $('nongCard').style.display=has('joints')?'':'none';
  $('rgbCard').style.display=has('rgb')?'':'none';
  $('audCard').style.display=has('audio')?'':'none';
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
  if(m.rgb&&document.activeElement.id!=='rgbb'){$('rgbb').value=m.rgb.bright;}
  if(m.rgb&&document.activeElement.id!=='rgbe'){$('rgbe').value=m.rgb.effect;}
  if(m.audio){
    $('nowPlaying').textContent=(m.audio.playing?('playing '+m.audio.file):'stopped')+' | vol '+m.audio.vol;
    if(document.activeElement.id!=='vol')$('vol').value=m.audio.vol;
    if(document.activeElement.id!=='volNum')$('volNum').value=m.audio.vol;
  }
  if(st.seq)$('seqStat').textContent=st.seq.running?('running '+st.seq.file):'idle';
  if(st.types&&!$('setType').options.length)
    st.types.forEach(t=>{const o=document.createElement('option');o.textContent=t;$('setType').appendChild(o);});
}
function setSpeed(){
  const v=$('spdVal').value;
  if(!v)return;
  cmd($('spdUnit').value==='ms'?('SPEED '+v+' MS'):('SPEED '+v));
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
  if(r1.startsWith('ERR')||r2.startsWith('ERR')){alert('not saved - check the console');return;}
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
// ---- Setup login (accounts stored on the board, default manny/12345678) ----
let auth=null; // {user,pass} while logged in
function setupToggle(){
  const c=$('loginCard');
  if(c.style.display==='none'){c.style.display='';c.scrollIntoView({behavior:'smooth'});}
  else{c.style.display='none';}             // click again to hide the login
}
async function doLogin(){
  const u=$('liUser').value.trim(),p=$('liPass').value;
  const r=await cmd('AUTH '+u+' '+p);
  if(r.startsWith('OK')){
    auth={user:u,pass:p};
    $('loginForm').style.display='none';$('usersBox').style.display='';
    $('liWho').textContent=u;$('liPass').value='';
    document.querySelectorAll('.setupCard').forEach(e=>e.style.display=e.dataset.disp||'');
    $('setupBtn').textContent='⚙ Setup (open)';
    loadUsers();
    loadPins(); // build the pin pickers now that the card is visible
  }else{$('liStat').textContent='wrong user or password';}
}
function doLogout(){
  auth=null;
  $('loginForm').style.display='';$('usersBox').style.display='none';
  document.querySelectorAll('.setupCard').forEach(e=>{e.dataset.disp=e.style.display;e.style.display='none';});
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
function sendRgb(){
  const h=$('rgbc').value;
  cmd('RGB '+parseInt(h.substr(1,2),16)+' '+parseInt(h.substr(3,2),16)+' '+parseInt(h.substr(5,2),16));
}
async function loadList(dir,sel){
  try{const r=await fetch('/api/files?dir='+dir);const fs=await r.json();
    const s=$(sel);s.innerHTML='';
    fs.forEach(f=>{const o=document.createElement('option');o.value=dir+'/'+f.n;o.textContent=f.n;s.appendChild(o);});}catch(e){}
}
function playSel(){const v=$('musicSel').value;if(v)cmd('PLAY '+v);}
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
        if(!confirm('Delete '+p+'?'))return;
        log(await (await fetch('/api/delete?path='+encodeURIComponent(p))).text());
        refreshLists();
      };
      td3.appendChild(g);td3.appendChild(d);
      tr.appendChild(td1);tr.appendChild(td2);tr.appendChild(td3);
      tb.appendChild(tr);
    });
  }catch(e){}
}
async function upload(){
  const f=$('upFile').files[0];
  if(!f){alert('choose a file');return;}
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
    if(!ps.length)g.innerHTML='<span class="statline">no modules found</span>';
  }catch(e){}
}
setInterval(loadPeers,15000);
async function saveSettings(){
  const id=$('setId').value,name=$('setName').value,type=$('setType').value;
  const ssid=$('setSsid').value,pass=$('setPass').value;
  const reps=[];
  if(id)reps.push(await cmd('SET ID '+id));
  if(name)reps.push(await cmd('SET NAME '+name));
  if(type)reps.push(await cmd('SET TYPE '+type));
  if(ssid)reps.push(await cmd('SET WIFI '+ssid+' '+pass));
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
const PIN_GROUPS={lift:'Lift (motor / encoder / limits)',bus:'RS485 bus',
  sd:'microSD card',audio:'I2S speaker',nong:'Nong servos'};
// which module type each pin group belongs to ("core" = shown for every type).
// SD + RS485 (bus) are on every module; the I2S speaker (audio) and RGB strip
// are lift-only hardware, so the audio pins show only under the lift tab.
const GROUP_TYPE={lift:'lift',nong:'nong',bus:'core',sd:'core',audio:'lift'};
const GROUP_LABEL={lift:'Lift module',nong:'Nong module'};
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
  let okCur=false; try{pinCur=JSON.parse((ct||'').trim());okCur=true;}catch(e){}
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
        '(pio run -e lift_module -t upload).';
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
  $('pinStat').textContent='saving...';
  for(const s of sels){const k=s.id.slice(4);if(+s.value!==pinCur[k].gpio)await cmd('PIN '+k+' '+s.value);}
  await cmd('REBOOT');
  alert('Pins saved. The board reboots to apply them.');
}
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
