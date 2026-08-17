"""Modules only link to modules in the same group.

Two companies can be working the same site. Automatic module-to-module linking
is only safe if a module can tell "one of ours" from "one of theirs" — and it
has to do that BEFORE joining anything, with no prior knowledge, on a cold
start with no venue WiFi.

The mechanism: a module's own hotspot password is **derived from its group
name**. Same group, same password, on every board, with nothing to distribute
by hand. So a grouped module can hunt for a neighbour and the only hotspot it
can actually get into is a group-mate's; another company's modules refuse it
and it refuses theirs.

The dangerous mistake would be an UNGROUPED module hunting: it would be using
the shared compiled-in password, which proves nothing about who owns a board,
and it could wander onto anyone's module.
"""
import re

import qc as F
import registry

AREA = "network"
TITLE = "modules only link within their own group"
SLOW = False


def run(t):
    ident_h = (F.FIRMWARE / "src/core/Identity.h").read_text(encoding="utf-8", errors="replace")
    ident_c = (F.FIRMWARE / "src/core/Identity.cpp").read_text(encoding="utf-8", errors="replace")

    # ---- the group is real, and survives a power cycle -----------------
    t.contains(ident_h, "String& group()", "a module knows its group")
    t.contains(ident_c, 'prefs_.putString("group"',
               "and remembers it across a power cycle")
    t.contains(ident_c, 'prefs_.getString("group"', "reading it back at boot")

    # ---- the password is DERIVED, not shared by hand -------------------
    m = re.search(r"String Identity::apPassword\(\).*?\n\}", ident_c, re.S)
    if t.ok(m, "the AP password is derived from the group"):
        body = m.group(0)
        t.contains(body, "group_", "from the group name itself")
        t.ok("sha" in body.lower() or "md_" in body,
             "through a hash, so the group name is not the password",
             "the group name would be readable off the air")
        t.contains(body, "AP_FALLBACK_PASS",
                   "with the compiled-in fallback kept for ungrouped boards",
                   )

    # ---- the radio actually uses it ------------------------------------
    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"void WebPortal::raiseAp\(\).*?\n\}", portal, re.S)
    if t.ok(m, "raiseAp exists"):
        t.contains(m.group(0), "apPassword()",
                   "our own hotspot uses the group password")
        t.ok("AP_FALLBACK_PASS" not in m.group(0),
             "and never the shared one directly",
             "a grouped module would still be joinable by anyone")

    # and when it leans on a neighbour, it offers the group password
    m = re.search(r"case wifilink::RELAY:(.*?)break;", portal, re.S)
    if t.ok(m, "the relay branch exists"):
        t.contains(m.group(1), "apPassword()",
                   "joining a neighbour uses the group password too")

    # ---- THE safety property: ungrouped modules never hunt -------------
    m = re.search(r"void WebPortal::checkLink\(.*?\n\}", portal, re.S)
    if t.ok(m, "checkLink exists"):
        body = m.group(0)
        i = body.find("if (!known)")
        t.ok(i > 0, "an unknown hotspot is treated differently from a known one")
        if i > 0:
            branch = body[i:i + 400]
            t.contains(branch, "group()",
                       "an ungrouped module never joins a hotspot it has not met",
                       )
            t.contains(branch, "triedAp_",
                       "and it rotates candidates instead of retrying one forever")

    # ---- it is a declared, documented command --------------------------
    cmds = {c["name"]: c for c in registry.commands()}
    if t.ok("GROUP" in cmds, "GROUP is declared in config/commands.json"):
        t.contains(cmds["GROUP"]["args"], "CLEAR", "including how to leave a group")
    docs = (F.CODE / "firmware/COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(docs, "`GROUP <name>`", "and COMMANDS.md documents it")

    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'if \(cmd == "GROUP"\)(.*?)\n    \}', router, re.S)
    if t.ok(m, "the GROUP command is handled"):
        body = m.group(1)
        t.contains(body, "setGroup", "it stores the group")
        t.contains(body, "wifiCommand",
                   "and re-applies the radio, since the hotspot password changed",
                   )
        # comments here TALK about reboots; only what it REPLIES counts
        t.ok("reboot" not in re.sub(r"//[^\n]*", "", body).lower(),
             "without needing a reboot",
             "a show cannot be power-cycled to link two modules")
    t.contains(router, 'doc["group"]',
               "and status reports the group, so the hub can show it")

    # ---- the hub gives you somewhere to do it --------------------------
    hub = (F.HUB / "web/hub.html").read_text(encoding="utf-8", errors="replace")
    t.contains(hub, 'data-go="network"', "the hub has a Network tab")
    t.contains(hub, 'data-tab="network"', "with its own area")
    t.contains(hub, "function linkSel", "where modules are linked by picking them")
    t.contains(hub, "GROUP ", "which sends the GROUP command")
    t.contains(hub, "unlinkSel", "and can unlink them again")

    # The tab is useless if it cannot SEE which modules are already linked, so
    # both ways the hub identifies a module must carry the group through.
    main_py = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"def probe_module\(.*?return None", main_py, re.S)
    if t.ok(m, "the WiFi probe exists"):
        t.contains(m.group(0), '"group"',
                   "a module found on WiFi reports its group")
    # Changing a module's group must not leave the hub repeating the old one.
    # The cached identity is what the hub serves while a cable is busy, and the
    # Network tab showed a module's PREVIOUS group right after linking it.
    t.contains(main_py, "_IDENTITY_CHANGING",
               "a command that changes identity drops the cached identity")
    m2 = re.search(r"_IDENTITY_CHANGING = \((.*?)\)", main_py, re.S)
    if t.ok(m2, "the list of such commands exists"):
        t.contains(m2.group(1), "GROUP", "including GROUP itself")

    m = re.search(r'out\["module"\] = \{.*?\}', main_py, re.S)
    if t.ok(m, "the USB probe builds a module record"):
        t.contains(m.group(0), '"group"',
                   "a module found on a cable reports its group too")
    # the tabs must only HIDE things — every id the rest of the page and the
    # QC drivers rely on has to stay exactly where it was
    for el in ("mods", "usbmods", "tools"):
        t.contains(hub, 'id="%s"' % el, "the %s list is still there" % el)
    m = re.search(r"function showTab\(.*?\n\}", hub, re.S)
    if t.ok(m, "showTab exists"):
        t.ok("innerHTML" not in m.group(0) and "remove(" not in m.group(0),
             "and switching tabs only shows and hides, never rebuilds",
             "rebuilding would drop the live module lists on every tab change")
