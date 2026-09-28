#pragma once
#include <Arduino.h>

// The secure talk page (SecureTalk.cpp, https://<board>/talk).
//
// A phone browser gives the microphone only to a secure page, and the board's
// normal page is plain http - so this small page exists for one job: sound
// from a phone to the robot, microphone included. It uses the SAME engine as
// the board page (shared/web/cast.js, served from flash) and the same look
// (mice.css). It has no cookie session of its own: it signs in on the sound
// socket, over the encrypted link, with the board's normal login.
static const char TALK_UI_HTML[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Talk through the robot</title>
<link rel="stylesheet" href="/mice.css">
<script src="/cast.js"></script>
<style>
main{max-width:520px;margin:0 auto;padding:var(--sp-4,16px)}
.statline{color:var(--mut);font-size:13px;margin-top:var(--sp-2,8px)}
input[type=text],input[type=password]{flex:1;min-width:0}
@media (pointer:coarse){button,input,label{min-height:40px}}
</style></head>
<body><main>
<h1>Talk through the robot</h1>
<div class="card">
  <div class="row"><label class="lbl" for="tUser">User</label>
    <input type="text" id="tUser" value="admin" autocomplete="username"></div>
  <div class="row"><label class="lbl" for="tPass">Password</label>
    <input type="password" id="tPass" autocomplete="current-password"></div>
  <div class="row">
    <label><input type="checkbox" id="cast_mic" checked onchange="castSource('mic',this.checked)"> &#127908; microphone</label>
  </div>
  <div class="row">
    <label><input type="checkbox" id="cast_song" onchange="castSource('song',this.checked)"> &#127925; song</label>
    <input type="file" id="castFile" accept="audio/*" style="flex:1;min-width:0"
           onchange="if(this.files[0]){document.getElementById('cast_song').checked=true; if(castOn){castSource('song',false).then(()=>castSource('song',true));}}">
  </div>
  <div class="row">
    <button class="primary" id="castBtn" onclick="castToggle()">&#127911; Send sound to the robot</button>
    <span class="lbl" id="castLevel" style="min-width:64px"></span>
  </div>
  <div class="statline" id="castStat" aria-live="polite">type the robot's login, pick the microphone, a song or both, then press Send</div>
  <p class="statline"><a id="back" href="/">back to the robot's page</a></p>
</div>
</main>
<script>
function castAuth(){
  return {user: document.getElementById('tUser').value.trim(),
          pass: document.getElementById('tPass').value};
}
// the robot's normal page is plain http on the same address
document.getElementById('back').href = 'http://' + location.hostname + '/';
</script>
</body></html>)rawliteral";
