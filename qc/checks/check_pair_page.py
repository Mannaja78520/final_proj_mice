"""The pairing card, driven in a real browser (A14-1).

`check_hub_pair` proves the RULES — what travels, what a clash does, that a
spent code is refused. This proves the SCREEN: that the card appears once
someone is logged in, that Show really puts a code on it, and that typing that
code back in really reaches the other hub and reports what it took.

Paired with ITSELF over 127.0.0.1, the way check_flash_remote sends firmware to
its own machine: both halves run for real, over HTTP, with no second PC in the
suite. What comes back is *already paired, nothing to copy* — the accounts are
byte for byte the ones this hub has — which is the honest answer and the one
worth asserting, because a page that announced *5 accounts copied* there would
be inventing work that never happened.

The hub page is loaded in an iframe from the hub's own origin (the trick
check_responsive and check_network_tab use) so its relative /api calls work,
and the driver logs in FIRST: the card is hidden without a session, and every
button behind it is gated.
"""
import browser
import fake_serial
import qc as F

AREA = "auth"
TITLE = "the pairing card shows a code, and typing one back really pairs"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f"></iframe>
<script>
function done(s){ qcMark("PAIR " + s); qcMark("done"); }
var fr, d;
async function openNetwork(){
  await new Promise(function(res){ fr.onload = res; fr.src = "/"; });
  d = fr.contentDocument;
  await qcWaitFor(function(){
    return d.querySelector('#tabs .tab[data-go="network"]'); }, 30000);
  d.querySelector('#tabs .tab[data-go="network"]').click();
}

window.addEventListener("load", async function(){
  var out = [];
  try{
    fr = document.getElementById("f");

    // ---- 1. a stranger is offered nothing -----------------------------
    // LOG OUT FIRST. browser.raw_page injects a synchronous login into every
    // driver page, so a check that just avoids logging in is still logged in
    // — this one reported the card hidden from a stranger while the browser
    // held a live session, which is the opposite of what it claimed.
    var lo = await fetch("/api/logout", {method:"POST"});
    out.push("logout=" + (lo.ok ? "yes" : "no"));
    await openNetwork();
    // Wait for the LOGIN CARD, which is the page saying /api/whoami answered,
    // and then settle. A fixed pause is the wrong tool almost everywhere in
    // this suite, but here the assertion is that something never appears,
    // and an absence has no event to wait for. 2.5s against a localhost
    // round trip of a few milliseconds.
    await qcWaitFor(function(){
      var l = d.getElementById("loginCard"); return l && !l.hidden; }, 20000);
    await new Promise(function(r){ setTimeout(r, 2500); });
    var sbox = d.getElementById("pairBox");
    out.push("stranger=" + (sbox && sbox.hidden ? "hidden" : "SHOWN"));

    // ---- 2. logged in, the card is there ------------------------------
    var lg = await fetch("/api/login", {method:"POST",
      body: JSON.stringify({user:"super_admin", password:"__PW__"})});
    out.push("login=" + (lg.ok ? "yes" : "no"));
    await openNetwork();

    // RECORD WHAT THE WAIT SAW, never a constant: qcWaitFor RESOLVES false
    // when it times out, it does not throw. Pushing card=yes after it made
    // this check pass with the card never painted at all - caught by
    // sabotaging the tab hook on 2026-08-21, which is the only reason the
    // weak assertion was found.
    var shown = await qcWaitFor(function(){
      var b = d.getElementById("pairBox"); return b && !b.hidden; }, 20000);
    var box = d.getElementById("pairBox");
    out.push("card=" + (shown ? "yes" : "no"));
    // Not hidden is not the same as on the screen: the tab it lives in can
    // be display:none, and offsetParent is what knows the difference.
    out.push("visible=" + (box && box.offsetParent !== null ? "yes" : "no"));

    // ---- show a code -------------------------------------------------
    d.querySelector("#pairIdle button.primary").click();
    out.push("shows=" + (await qcWaitFor(function(){
      var s = d.getElementById("pairShowing");
      return s && !s.hidden && d.getElementById("pairCode").textContent.length > 4;
    }, 20000) ? "yes" : "no"));
    var code = d.getElementById("pairCode").textContent.trim();
    out.push("code=" + code);
    out.push("left=" + d.getElementById("pairLeft").textContent.replace(/ /g, "_"));

    // ---- 3. a live code survives a reload -----------------------------
    // The code is counting down on the HUB, not in this page. A reload that
    // forgot it would show Start beside a live code, and the person would
    // show a second one while the first stayed valid.
    await openNetwork();
    out.push("kept=" + (await qcWaitFor(function(){
      var s = d.getElementById("pairShowing");
      return s && !s.hidden
        && d.getElementById("pairCode").textContent.trim() === code;
    }, 20000) ? "yes" : ("no:" + d.getElementById("pairCode").textContent.trim())));

    // ---- 4. and spend it, on this same hub ---------------------------
    d.querySelector("#pairIdle button:not(.primary)").click();
    d.getElementById("pairAddr").value = "127.0.0.1";
    d.getElementById("pairInput").value = code;
    d.querySelector("#pairEnter button.primary").click();

    out.push("answered=" + (await qcWaitFor(function(){
      var k = d.getElementById("pairDone"), c = d.getElementById("pairClash"),
          e = d.getElementById("pairErrBox");
      return (k && !k.hidden) || (c && !c.hidden) || (e && !e.hidden);
    }, 25000) ? "yes" : "no"));
    out.push("state=" + (!d.getElementById("pairDone").hidden ? "done"
                       : !d.getElementById("pairClash").hidden ? "clash" : "err"));
    out.push("says=" + (d.getElementById("pairDone").hidden
      ? d.getElementById("pairErr").textContent
      : d.getElementById("pairDone").textContent).replace(/ /g, "_").slice(0, 90));
    done(out.join(" "));
  } catch (e) { done(out.join(" ") + " ERR=" + String(e).slice(0, 60)); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    # The sweep would list whatever hubs are on the developer's LAN, and this
    # check pairs with an address. Everything here stays on 127.0.0.1.
    real_scan = main.scan_hubs
    main.scan_hubs = lambda force=False: []
    try:
        browser.raw_page(PAGE.replace("__PW__", F.HUB_PASSWORD), base, seconds=70)
    finally:
        main.scan_hubs = real_scan

    marks = [m for m in fake_serial.qc_marks if m.startswith("PAIR ")]
    if not t.ok(marks, "the pairing card reported back",
                "the page never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][5:].split(" ") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the page ran without throwing",
             "%s (got as far as %r)" % (got["ERR"], got))
        return

    t.eq(got.get("logout"), "yes", "the driver could log itself out to test that")
    t.ok(got.get("stranger") == "hidden",
         "a stranger is not offered the pairing card at all",
         "every button on it is gated, so showing it to someone who cannot "
         "use it is a row of controls that answer 401")
    t.eq(got.get("login"), "yes", "the driver logged in, so the card is reachable")
    t.eq(got.get("card"), "yes", "the pairing card is on the Network tab")
    t.eq(got.get("visible"), "yes",
         "and is really on the screen, not merely un-hidden")
    t.eq(got.get("shows"), "yes", "Show a code opens the code half of the card")
    t.eq(got.get("answered"), "yes",
         "and the card answers rather than sitting on the spinner")

    code = got.get("code", "")
    t.contains(code, "-", "Show puts a code on the screen, in two halves")
    t.eq(len(code), 9, "eight characters and the dash")
    t.ok(not any(c in code for c in "ILOU"),
         "and none of the characters people misread",
         "the code was %r" % code)
    t.contains(got.get("left", ""), "Good_for",
               "with the time it has left beside it")
    t.ok(got.get("kept") == "yes",
         "a code still counting down is still on the screen after a reload",
         "the code lives on the hub; a page that forgot it would have the "
         "person show a second one while the first was still valid")

    # THE ROUND TRIP. Typing the code back reaches the far hub, over HTTP,
    # and the page reports what it got - not what it hoped for.
    t.eq(got.get("state"), "done",
         "typing that code pairs, and the card says so")
    t.contains(got.get("says", ""), "Already_paired",
               "and a hub paired with itself says nothing was copied")
