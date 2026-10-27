"""Studio's cards can be taken out to their own window (A49-3, user 2026-10-23).

"studio เอามันกลับขึ้นไปในพื้นที่ของตัวเองอยู่ด้านบนเหมือนเดิม ... สามารถปิดเปิดได้หรือ
ลากออกไปด้านนอกแบบนี้ได้". app_parts/panels.js: ⧉ in a card's title floats it,
its title drags it, ⇲ puts it back, and where it floats is remembered. In a
real browser at a desk width, then phone width:

  * the tab row sits on top of the side panel, above every card;
  * ⧉ floats a Sequence card, and it stays on screen on the Pose tab;
  * dragging its title moves it, and a reload brings it back at the same spot;
  * ⇲ docks it again, and a reload keeps it docked;
  * at phone width nothing floats and no ⧉ shows (one column, nothing over it).
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio: cards float out to their own window, are dragged, remembered and docked"
SLOW = True

DRIVER = """
<style>html,body{margin:0}iframe{border:0;display:block}</style>
<iframe id="s" src="/studio/" style="width:1400px;height:900px"></iframe>
<script>
function say(k, v){ return qcMark("SP " + k + "=" + String(v).replace(/[\\s|=]+/g, "~")); }
async function ready(f){
  await qcWaitFor(function(){ var d = f.contentDocument; return d && d.querySelector("#side .card .popout"); }, 20000);
}
async function reload(f){
  var back = new Promise(r => f.onload = r);
  f.contentWindow.location.reload();
  await back; await ready(f);
}
function card(f){ return f.contentDocument.querySelector('#side div.card[data-stab="sequence"]'); }
window.addEventListener("load", async function(){
  try{
    var f = document.getElementById("s");
    await ready(f);
    var w = f.contentWindow, d = f.contentDocument;
    try { w.localStorage.removeItem("nong_panels"); } catch (e) {}
    var tabs = d.getElementById("sideTabs").getBoundingClientRect();
    var first = d.querySelector('#side div.card[data-stab="pose"]').getBoundingClientRect();
    await say("top", tabs.bottom <= first.top + 1);
    w.showTab("sequence");
    card(f).querySelector(".popout").click();
    w.showTab("pose");
    await say("float", card(f).classList.contains("floating") + "!" + (card(f).offsetWidth > 0));
    var h = card(f).querySelector("h2"), r = h.getBoundingClientRect();
    var want = Math.round(card(f).getBoundingClientRect().left + 320 - (r.left + 20)) + "px";
    var o = {bubbles: true, pointerId: 1, isPrimary: true};
    h.dispatchEvent(new w.PointerEvent("pointerdown", Object.assign({clientX: r.left + 20, clientY: r.top + 8}, o)));
    h.dispatchEvent(new w.PointerEvent("pointermove", Object.assign({clientX: 320, clientY: 210}, o)));
    h.dispatchEvent(new w.PointerEvent("pointerup", Object.assign({clientX: 320, clientY: 210}, o)));
    var spot = card(f).style.left + "," + card(f).style.top;
    await say("moved", card(f).style.left === want);   // grabbed 20 px in, let go at x 320   // grabbed 20 px in, let go at x 320
    await reload(f);
    await say("kept", card(f).classList.contains("floating") + "!" + (card(f).style.left + "," + card(f).style.top === spot));
    card(f).querySelector(".popout").click();
    await reload(f);
    await say("docked", card(f).classList.contains("floating"));
    card(f).querySelector(".popout").click();
    f.style.width = "390px";
    await qcWaitFor(function(){ return !f.contentDocument.querySelector("#side .card.floating"); }, 3000);
    var pop = f.contentDocument.querySelector("#side .card .popout");
    await say("phone", !!f.contentDocument.querySelector("#side .card.floating") + "!" + (pop.offsetWidth > 0));
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=60)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("SP "):
            k, _, v = m[3:].partition("=")
            got[k] = v
    t.ok(got.get("top") == "true", "the tab row is on top of the side panel, above every card", got)
    t.ok(got.get("float") == "true!true", "a floated card stays on screen on another tab", got)
    t.ok(got.get("moved") == "true", "dragging its title moves it", got)
    t.ok(got.get("kept") == "true!true", "a reload brings it back at the same spot", got)
    t.ok(got.get("docked") == "false", "put back, it stays in the side panel after a reload", got)
    t.ok(got.get("phone") == "false!false", "phone width: nothing floats and no take-out button shows", got)
