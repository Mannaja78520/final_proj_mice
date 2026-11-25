"""A problem report can carry pictures, in every language, and the hub does not trust them.

User 2026-11-25: a screenshot says more than words, and the report must work in many languages.
The page shrinks each picture (long side 1280, JPEG), shows a preview with a remove button, and
sends at most three; the hub stores them as files beside the report (gitignored, machine-local)
after checking the first bytes - a text file called .png, a fourth picture, or a path in the id
must not get in or out.
"""
import glob
import os

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "Report pictures: pick, preview, send, view - th/en/zh/ja, and the hub refuses fakes"
SLOW = False
SOLO = True   # leaves Thai/Chinese reports in the list for a moment: check_visual_language must not see them

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && f.contentWindow.MiceLang && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 25000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function blob(w){ return new Promise(function(res){ var c = document.createElement("canvas"); c.width = w; c.height = 300; var g = c.getContext("2d"); g.fillStyle = "#c33"; g.fillRect(0, 0, w, 300); g.fillStyle = "#fff"; g.fillRect(20, 20, 80, 80); c.toBlob(res, "image/png"); }); }
var TEXT = {th: "ปุ่มไม่ตอบสนอง qc pics", en: "Button does nothing qc pics", zh: "按钮没有反应 qc pics", ja: "ボタンが反応しません qc pics 🙂"};
async function one(lang){
  localStorage.setItem("mice.lang", lang);
  var f = document.createElement("iframe");
  f.style.cssText = "width:800px;height:900px";
  document.body.appendChild(f);
  f.src = "/";
  await ready(f); await sleep(1500);
  var w = f.contentWindow, d = f.contentDocument;
  w.openReport(); await sleep(500);
  qcMark("P~" + lang + "~label~" + d.getElementById("reportPicFileBtn").textContent.trim());
  qcMark("P~" + lang + "~title~" + d.getElementById("reportTitle").textContent.trim());
  d.getElementById("reportText").value = TEXT[lang];
  await w.addReportPictures([await blob(3000), await blob(400)]);
  qcMark("P~" + lang + "~previews~" + d.querySelectorAll("#reportPics .report-pic").length);
  d.querySelector("#reportPics .report-pic-x").click();
  qcMark("P~" + lang + "~afterx~" + d.querySelectorAll("#reportPics .report-pic").length);
  await w.addReportPictures([await blob(500), await blob(500), await blob(500)]);
  qcMark("P~" + lang + "~cap~" + d.querySelectorAll("#reportPics .report-pic").length);
  await w.submitReport(); await sleep(800);
  var list = (await (await fetch("/api/reports")).json()).reports;
  var mine = list.filter(function(r){ return r.text === TEXT[lang]; })[0];
  qcMark("P~" + lang + "~saved~" + (mine ? mine.images : "none"));
  if (mine) {
    var im = await fetch("/api/report/image?id=" + mine.id + "&n=0");
    var b = new Uint8Array(await im.arrayBuffer());
    qcMark("P~" + lang + "~image~" + im.headers.get("Content-Type") + "~" + b[0].toString(16) + b[1].toString(16));
    w.showTab("complaints"); await sleep(1200);
    var row = Array.prototype.filter.call(d.querySelectorAll("#complaintsList .mod"), function(r){ return r.textContent.indexOf("qc pics") >= 0 && r.textContent.indexOf("🖼") >= 0; });
    qcMark("P~" + lang + "~mark~" + (row.length > 0 ? 1 : 0));
    if (row.length) { w.openComplaintDetail(mine); await sleep(300);
      qcMark("P~" + lang + "~detail~" + d.querySelectorAll("#reportPics img").length + "~" + (d.getElementById("reportPicBar").hidden ? 1 : 0));
      w.closeReport();
      qcMark("P~" + lang + "~reset~" + d.querySelectorAll("#reportPics .report-pic").length + "~" + (d.getElementById("reportPicBar").hidden ? 1 : 0)); }
  }
}
async function run(){
  for (var l of ["th", "en", "zh", "ja"]) await one(l);
  localStorage.setItem("mice.lang", "en");
  var png = await blob(50); var url = await new Promise(function(r){ var fr = new FileReader(); fr.onload = function(){ r(fr.result); }; fr.readAsDataURL(png); });
  var fake = "data:image/png;base64," + btoa("this is just text, not a picture");
  var r = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "raw qc pics", images: [fake, url, url, url, url] }) }).then(function(x){ return x.json(); });
  var list = (await (await fetch("/api/reports")).json()).reports;
  var m = list.filter(function(x){ return x.id === r.id; })[0];
  qcMark("R~count~" + (m ? m.images : "none"));
  qcMark("R~trav~" + (await fetch("/api/report/image?id=../../main&n=0")).status + "~" + (await fetch("/api/report/image?id=" + r.id + "&n=7")).status);
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=120)
    marks = list(fake_serial.qc_marks)
    rep = os.path.join(F.CODE, "main_python", "reports")
    for f in glob.glob(os.path.join(rep, "*.json")):
        try:
            if "qc pics" in open(f, encoding="utf-8").read():
                rid = os.path.basename(f).rsplit("_", 1)[-1][:-5]
                for p in glob.glob(os.path.join(rep, "img", rid + "_*")):
                    os.remove(p)
                os.remove(f)
        except OSError:
            pass
    got = {}
    for m in marks:
        if m.startswith("P~"):
            _, lang, key, val = m.split("~", 3)
            got[(lang, key)] = val
    label = {"th": "เพิ่มรูป", "en": "Add a picture", "zh": "添加图片", "ja": "画像を追加"}
    for lang in ("th", "en", "zh", "ja"):
        g = lambda k: got.get((lang, k), "missing")
        t.ok(label[lang] in g("label"), "the Add a picture button speaks %s" % lang, g("label"))
        if lang != "en":
            t.ok("Report a problem" not in g("title"), "the Report box heading is translated (%s)" % lang, g("title"))
        t.eq(g("previews"), "2", "two pictures show as previews (%s)" % lang)
        t.eq(g("afterx"), "1", "the remove button takes one away (%s)" % lang)
        t.eq(g("cap"), "3", "never more than three previews (%s)" % lang)
        t.eq(g("saved"), "3", "the report arrived with 3 pictures, text intact (%s)" % lang)
        t.ok(g("image").startswith("image/jpeg~ffd8"), "the picture comes back as a shrunken JPEG (%s)" % lang, g("image"))
        t.eq(g("mark"), "1", "the list marks a report with pictures (%s)" % lang)
        t.eq(g("detail"), "3~1", "the detail shows 3 pictures and hides the add buttons (%s)" % lang)
        t.eq(g("reset"), "0~0", "the next report starts empty with add buttons back (%s)" % lang)
    t.ok("R~count~3" in marks, "the hub keeps real pictures only, at most 3, not the fake", [m for m in marks if m.startswith("R~")])
    t.ok("R~trav~404~404" in marks, "a path in the id or a missing number gives 404", [m for m in marks if m.startswith("R~")])
