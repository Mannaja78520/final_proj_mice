"""One button produces the thing everyone is asked for first — and it is safe to send.

"It does not work" is never enough to act on, and the follow-up questions are
always the same four: which PC, what does it see, what firmware is on the
boards, what can that machine even do. Getting those out of somebody over chat
takes half an hour. `/api/diag` is one button instead.

The properties, and what breaking each would cost:

  * **NO SECRETS.** This text is written to be pasted into a message, so a
    password in it is a password published — and it travels further than the
    problem it was sent about. The hub keeps one in plain text beside itself
    (`hub_password.txt`), the account store holds hashes, and a module's WiFi
    credentials come back in some replies. The test looks for the ACTUAL secret
    value, never for the word "password": the bundle's own footer says "no
    passwords are included in this text", so a check searching for that word
    fails on the very line that promises the opposite. Found while writing
    this, which is exactly the sort of thing that would have shipped as
    "verified";
  * **the firmware version is really there.** The module list is built from
    PING, which answers id, name and type and nothing else, so `fw` is simply
    not in it. Printing "?" for every board would miss the one question this
    exists to answer. Each board is asked once, on an explicit button press;
  * **plain text, not JSON.** A person pastes this into a chat window and
    should be able to read what they are handing over first;
  * **a browser with no clipboard still works.** `navigator.clipboard` exists
    only in a SECURE context — https, or localhost. This hub is plain http on a
    LAN address, so on a phone at 192.168.x.x there is no clipboard at all.
    That is the NORMAL path here, not an edge case, and the fallback has to be
    built to be used rather than apologised for.
"""
import re

import fake_serial
import qc as F

AREA = "hub"
TITLE = "one button copies a diagnostics bundle, and it carries no password"


def run(t):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")

    fake_serial.reset()
    base, main = F.start_hub()
    st, txt = F.get(base + "/api/diag")
    t.eq(st, 200, "the hub serves /api/diag")

    # ---- it is TEXT, and it is readable ------------------------------
    t.ok(not txt.lstrip().startswith("{"),
         "it is plain text, not JSON",
         "a person pastes this into a message; JSON in a chat window is a wall "
         "nobody reads")
    for want in ("THIS PC", "MODULES FOUND", "SERIAL PORTS",
                 "FIRMWARE BUILT ON THIS PC"):
        t.contains(txt, want, "it has a %s section" % want.lower())
    t.contains(txt, main.socket.gethostname(),
               "it names the PC — several run this hub at a venue")

    # ---- TWO HALVES (A21-5): a designer summary, then support detail ----
    # The person who pressed the button must be able to read the first half
    # without meeting one id, port or address; support still gets all of it
    # below the marker. Splitting on the SAME string the server and the page
    # use is the point: change one, the other two say so — so the marker is
    # read from main.py's DIAG_TECH_MARK rather than copied here.
    mm = re.search(r'DIAG_TECH_MARK = "(.+?)"', src)
    t.ok(mm, "the split marker is read from main.py, not copied")
    if not mm:
        return
    MARK = mm.group(1)
    t.contains(txt, MARK, "the bundle carries the split marker")
    plain = txt.split(MARK)[0]
    t.contains(plain, "IN PLAIN WORDS",
               "the plain half comes FIRST, before any technical section")
    # An unnamed WiFi module comes back from probe_module with its IP AS its
    # name, so a naive `name or fallback` prints the address. Both places
    # that render a robot's name must go through disp_name, which strips
    # IP-shaped names first.
    fn = src[src.find("def diagnostics()"):]
    fn = fn[:fn.find("\ndef ", 1)]
    t.ok(fn.count("disp_name(m)") >= 3 and
         r"\d{1,3}(?:\.\d{1,3}){3}" in fn,
         "robot names are rendered through disp_name, which strips IPs",
         "a module probed over WiFi carries its address AS its name when "
         "unnamed - printing it verbatim puts an IP in the designer summary")
    t.ok(bool(re.search(r"robots\s+\d+ connected", plain))
         or "none found" in plain,
         "it says what is connected in one readable line",
         "got: %r" % [l for l in plain.splitlines() if "robot" in l][:2])
    t.ok("needs attention" in plain or "all good" in plain,
         "and whether anything needs attention - never silence")
    leaks = re.findall(
        r"COM\d|#\d+|/dev/\S+|\b\d{1,3}(?:\.\d{1,3}){3}\b|:\d{4}\b", plain)
    t.ok(not leaks,
         "the plain half carries NO ids, COM ports or addresses",
         "a summary that names a port stops being a summary: %r" % leaks[:4])
    t.contains(hub, 'id="diagPlain"',
               "the page has somewhere to show the plain half")
    cp = hub[hub.find("async function copyDiag()"):]
    cp = cp[:cp.find("\n}") + 2]
    t.contains(cp, "showDiag(text)",
               "and the button fills it from the SAME fetch it copies")
    tw = hub.find('id="diagTechWrap"')
    tag_a, tag_b = hub.rfind("<div", 0, tw), hub.find(">", tw)
    t.ok(tw > 0 and 'class="tech"' in hub[tag_a:tag_b],
         "the technical rest hides behind the page-wide technical switch",
         "Gemini Pro, 2026-08-24: ride the existing .tech convention rather "
         "than adding a second toggle to this card")
    sd = hub[hub.find("function showDiag"):]
    sd = sd[:sd.find("\n}") + 2]
    t.ok("text.slice(i + DIAG_MARK.length)" in sd,
         "the technical pane starts AFTER the marker line",
         "slicing from the marker itself would print the support "
         "header twice, once above each pane")

    # ---- THE ONE THAT MATTERS: no secret escapes ----------------------
    # By VALUE, not by word. The bundle's own footer contains "passwords", so a
    # check looking for that word fails on the line promising the opposite.
    t.ok(F.HUB_PASSWORD not in txt,
         "the hub password is NOT in the bundle",
         "this text is written to be shared, so a password in it is a "
         "password published - and it travels further than the problem it was "
         "sent about")
    pw_file = F.HUB / "hub_password.txt"
    if pw_file.is_file():
        real = pw_file.read_text(encoding="utf-8", errors="replace").strip()
        if real:
            t.ok(real not in txt,
                 "and neither is the one written beside the hub")
    t.eq(re.findall(r"\b[0-9a-f]{32,}\b", txt), [],
         "no password hash leaks either")
    for bad in ("hub_password", "apPassword", "wpass"):
        t.ok(bad not in txt, "no %s value is included" % bad)

    # ---- the firmware version is really asked for --------------------
    fn = src[src.find("def diagnostics()"):]
    fn = fn[:fn.find("\ndef ", 1)]
    t.contains(fn, 'dev_cmd(dev, "INFO"',
               "each board is ASKED which firmware it runs")
    t.ok('m.get("fw")' not in fn,
         "rather than read from the module list, which does not have it",
         "the list is built from PING - id, name and type - so `fw` is not in "
         "it, and every board would print ? for the one question this bundle "
         "exists to answer")
    m = re.search(r'dev_cmd\(dev, "INFO", wait=([\d.]+)\)', fn)
    if t.ok(m, "with a stated wait"):
        t.ok(float(m.group(1)) <= 5,
             "short enough that one quiet board does not hold up the rest "
             "(%ss)" % m.group(1))
    t.contains(fn, "no answer",
               "and a board that does not answer says so, instead of ?")
    # A real module in the fake rig has a version, so this proves the path.
    t.ok(re.search(r"fw=\d", txt),
         "and a real board's version appears in the text",
         "got: %s" % (re.findall(r"fw=\S+", txt)[:2] or "no fw= line at all"))

    # ---- the button, and the phone case ------------------------------
    t.contains(hub, 'id="diagBtn"', "there is a button on the page")
    t.contains(hub, "copyDiag()", "wired to the copy action")
    cp = hub[hub.find("async function copyDiag()"):]
    cp = cp[:cp.find("\n}") + 2]
    t.contains(cp, "navigator.clipboard",
               "it uses the clipboard when there is one")
    # NAMING the fallback is not SHOWING it. Asserting that "diagFall" appears
    # passed with `fall.hidden = false` flipped to `true` - the element was
    # still mentioned, still populated, and permanently invisible, so on a
    # phone the button would do nothing whatsoever. Caught by tools/sabotage.py.
    catch = cp[cp.rfind("}catch(e){"):]
    t.contains(catch, "fall.hidden = false",
               "and really SHOWS the fallback when there is not")
    t.ok(cp.find("fall.hidden = true") < cp.find("fall.hidden = false"),
         "hidden again at the start of each attempt, shown only on failure",
         "a fallback left on screen from last time reads as this attempt "
         "having failed too")
    t.ok("select()" in cp,
         "with the text already selected, ready to copy",
         "on a phone at 192.168.x.x there is NO clipboard - that is the normal "
         "path here, not an edge case, so the fallback has to be usable rather "
         "than an apology")
    t.contains(hub, "https", "and the page says WHY the clipboard is missing")
