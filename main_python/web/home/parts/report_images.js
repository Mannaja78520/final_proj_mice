// Pictures on a problem report: pick, paste, take a photo, or grab the screen.
// Written in plain ES5 (no ?. or ??) for the TV browsers (Chrome 70+).
// Every picture is shrunk HERE first (long side 1280, JPEG) so a phone photo of
// 6 MB leaves as ~150 KB; the hub checks it again (report_images.py).
var reportPics = [];          // data: URLs waiting to be sent
var REPORT_PIC_MAX = 3;
var REPORT_PIC_BYTES = 400 * 1024;   // under the hub's 450 KB wall (3 pictures must fit its 2 MB request cap)

function reportPicNote(msg){
  var el = document.getElementById('reportSaid');
  if(el) el.textContent = window.MiceLang ? window.MiceLang.say(msg) : msg;
}

// File/Blob -> small JPEG data URL (white behind transparent PNGs).
function shrinkPicture(file){
  return new Promise(function(resolve, reject){
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function(){
      URL.revokeObjectURL(url);
      var w = img.naturalWidth, h = img.naturalHeight;
      var side = Math.max(w, h), size = 1280, q = 0.72, out = '';
      for(var i = 0; i < 5; i++){
        var k = Math.min(1, size / side);
        var c = document.createElement('canvas');
        c.width = Math.max(1, Math.round(w * k));
        c.height = Math.max(1, Math.round(h * k));
        var g = c.getContext('2d');
        g.fillStyle = '#fff';
        g.fillRect(0, 0, c.width, c.height);
        g.drawImage(img, 0, 0, c.width, c.height);
        out = c.toDataURL('image/jpeg', q);
        if(out.length * 0.75 <= REPORT_PIC_BYTES) break;
        size = Math.round(size * 0.75); q = Math.max(0.5, q - 0.07);
      }
      if(out.length * 0.75 > REPORT_PIC_BYTES) reject(new Error('too big'));
      else resolve(out);
    };
    img.onerror = function(){ URL.revokeObjectURL(url); reject(new Error('not a picture')); };
    img.src = url;
  });
}

function addReportPictures(files){
  var list = Array.prototype.slice.call(files || []).filter(function(f){
    return /^image\//.test(f.type);
  });
  if(!list.length){ reportPicNote('That is not a picture.'); return Promise.resolve(); }
  var chain = Promise.resolve();
  list.forEach(function(f){
    chain = chain.then(function(){
      if(reportPics.length >= REPORT_PIC_MAX){
        reportPicNote('Three pictures at most. Remove one to add another.');
        return;
      }
      return shrinkPicture(f).then(function(u){
        reportPics.push(u);
        reportPicNote('');
        drawReportPictures();
      }, function(){ reportPicNote('That picture could not be used. Try another one.'); });
    });
  });
  return chain;
}

function drawReportPictures(){
  var box = document.getElementById('reportPics');
  if(!box) return;
  box.innerHTML = '';
  reportPics.forEach(function(u, i){
    var cell = document.createElement('div');
    cell.className = 'report-pic';
    var im = document.createElement('img');
    im.src = u; im.alt = 'Picture ' + (i + 1);
    var x = document.createElement('button');
    x.type = 'button'; x.className = 'report-pic-x';
    x.textContent = '✕'; x.title = 'Remove this picture';
    x.setAttribute('aria-label', 'Remove this picture');
    x.onclick = function(){ reportPics.splice(i, 1); drawReportPictures(); };
    cell.appendChild(im); cell.appendChild(x);
    box.appendChild(cell);
  });
  var full = reportPics.length >= REPORT_PIC_MAX;
  ['reportPicFile', 'reportPicCam', 'reportPicShot'].forEach(function(id){
    var b = document.getElementById(id + 'Btn');
    if(b) b.disabled = full;
  });
}

function clearReportPictures(){ reportPics = []; drawReportPictures(); }

// One tap = a picture of this very screen. Only where the browser can share a
// screen (desktop); phones and TVs keep the photo / file buttons.
function grabReportScreen(){
  var m = document.getElementById('reportModal');
  navigator.mediaDevices.getDisplayMedia({video: true}).then(function(stream){
    var v = document.createElement('video');
    v.muted = true; v.srcObject = stream;
    return v.play().then(function(){
      if(m) m.style.visibility = 'hidden';       // not the report box itself
      return new Promise(function(r){ setTimeout(r, 450); });
    }).then(function(){
      var c = document.createElement('canvas');
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext('2d').drawImage(v, 0, 0);
      stream.getTracks().forEach(function(t){ t.stop(); });
      if(m) m.style.visibility = '';
      return new Promise(function(r){ c.toBlob(r, 'image/png'); });
    });
  }).then(function(blob){
    if(m) m.style.visibility = '';
    if(blob) return addReportPictures([blob]);
  }).catch(function(){
    if(m) m.style.visibility = '';
    reportPicNote('The screen picture was not taken.');
  });
}

function startReportPictures(){
  var file = document.getElementById('reportPicFile');
  var cam = document.getElementById('reportPicCam');
  if(file) file.onchange = function(){ addReportPictures(file.files).then(function(){ file.value = ''; }); };
  if(cam) cam.onchange = function(){ addReportPictures(cam.files).then(function(){ cam.value = ''; }); };
  var shot = document.getElementById('reportPicShotBtn');
  if(shot){
    var can = !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
    shot.hidden = !can;
    shot.onclick = grabReportScreen;
  }
  var m = document.getElementById('reportModal');
  if(m) m.addEventListener('paste', function(e){
    var items = (e.clipboardData && e.clipboardData.items) || [];
    var got = [];
    for(var i = 0; i < items.length; i++){
      if(items[i].kind === 'file' && /^image\//.test(items[i].type)) got.push(items[i].getAsFile());
    }
    if(got.length){ e.preventDefault(); addReportPictures(got); }
  });
}
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startReportPictures);
else startReportPictures();
