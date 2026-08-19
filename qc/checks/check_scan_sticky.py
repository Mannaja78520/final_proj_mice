"""A module that is online must not vanish from the hub.

A module that shares its WiFi runs AP_STA on ONE radio: it serves the show
network and its own access point by time-slicing, so it sometimes answers a
little late. Measured on the bench over a phone hotspot — the lift answered a
0.6 s probe 7 times in 8, and 8 times in 8 at 1.0 s. The hub's subnet sweep
uses the short timeout, so it LOST that module on 2 scans out of 3 while it sat
there perfectly online, reachable, and moving when told to.

Losing a module from the hub is not cosmetic: it is the page you click to open
its website, and the list Nong Studio picks a robot from.

The fix is a second pass — sweep quickly to discover anything new, then go back
and ask the addresses already known, patiently. This drives that directly, with
a stand-in probe that answers only when it is given enough time.
"""
import qc as F

AREA = "connection"
TITLE = "a module that answers slowly is not dropped from the hub"
SLOW = False

SUBNET = "10.9.9"
SLOWPOKE = SUBNET + ".7"


def run(t):
    base, main = F.start_hub()

    real_probe, real_lan = main.probe_module, main.lan_ip
    needed = [0.0]          # how long the module currently needs to answer
    calls = []              # (ip, timeout) of every probe, to prove two passes

    def fake_probe(ip, timeout=0.6):
        calls.append((ip, timeout))
        if ip != SLOWPOKE or needed[0] < 0:
            return None
        if timeout < needed[0]:
            return None     # answered too late for this probe
        return {"ip": ip, "id": 42, "name": "slowpoke", "type": "nong", "sd": False}

    main.probe_module = fake_probe
    main.lan_ip = lambda: SUBNET + ".4"
    # And the addresses learned from CABLES, which are otherwise whatever this
    # machine happens to have plugged in. scan_modules passes them as
    # `also_ask`, so a real board on a real port - or the fake one, depending on
    # what else is running - joins the patient pass and the assertion about
    # WHICH address gets re-asked sees an extra one. It failed exactly that way
    # in the first parallel gate and passed every time on its own, which is the
    # signature of a test reading the machine instead of its own fixture.
    real_usb = main._ips_from_usb              # noqa: SLF001
    main._ips_from_usb = lambda: []            # noqa: SLF001
    main.MODULES.forget()
    try:
        # ---- answering promptly: found, as it always was ----------------
        mods = main.scan_modules(force=True)
        t.ok(any(m["id"] == 42 for m in mods),
             "the hub finds a module that answers promptly",
             "found %r" % [m.get("name") for m in mods])

        # ---- now it time-slices with its own AP -------------------------
        needed[0] = 1.2       # slower than the fast sweep allows
        del calls[:]
        mods = main.scan_modules(force=True)
        t.ok(any(m["id"] == 42 for m in mods),
             "and STILL finds it once it answers slowly",
             "an online module dropped off the hub entirely: %r"
             % [m.get("name") for m in mods])
        t.eq(len([m for m in mods if m["id"] == 42]), 1,
             "listing it exactly once, not once per pass")

        # the second pass must be small and patient, not a slow re-sweep
        patient = [c for c in calls if c[1] >= 1.0]
        t.ok(patient, "there is a patient second pass")
        t.ok(len(patient) <= 8,
             "and it only re-asks addresses already known (%d), not the subnet"
             % len(patient),
             "re-sweeping 254 hosts slowly would make every scan crawl")
        t.ok(all(c[0] == SLOWPOKE for c in patient),
             "specifically the module that went quiet")

        # ---- a module that stops answering is LATE before it is gone ----
        # Added 2026-08-19 with the venue WiFi dropping every few minutes. A
        # module that misses a sweep used to be deleted, so the screen said it
        # was gone while it sat there working. It now stays, marked, for the
        # finder's grace period - and the marking is the point, because a row
        # that lingers with no explanation is a lie of a different shape.
        needed[0] = -1        # nothing there at all now
        mods = main.scan_modules(force=True)
        late = [m for m in mods if m["id"] == 42]
        t.eq(len(late), 1, "a module that goes quiet is still listed, once")
        if late:
            t.ok(late[0].get("stale"),
                 "and is marked late rather than shown as fine",
                 "it is listed as if nothing happened: %r" % (late[0],))
            t.ok(isinstance(late[0].get("lastSeen"), int),
                 "with how long ago it last answered",
                 "the screen has to say WHEN, or late is indistinguishable "
                 "from working")

        # ---- but the grace really does expire ---------------------------
        # Time is moved, not waited for: the point is that the list empties on
        # its own, and a check that sleeps 45 seconds would never be run.
        for ip, (rec, when) in list(main.MODULES._seen.items()):
            main.MODULES._seen[ip] = (rec, when - main.MODULES.grace - 5)
        mods = main.scan_modules(force=True)
        t.ok(not any(m["id"] == 42 for m in mods),
             "a module that is really gone does disappear",
             "the grace period is keeping a dead module on the list forever")

        # ---- and it must not re-probe forever once it is gone -----------
        del calls[:]
        main.scan_modules(force=True)
        t.ok(not [c for c in calls if c[1] >= 1.0],
             "and stops being re-asked once it has dropped out",
             "a module gone for good is still being chased every scan")
    finally:
        main.probe_module, main.lan_ip = real_probe, real_lan
        main._ips_from_usb = real_usb          # noqa: SLF001
        main.MODULES.forget()

    # ---- a module on ANOTHER subnet ------------------------------------
    # The sweep only walks the PC's own /24. Seen on a dorm network: the PC on
    # 10.94.163.x, both modules on 192.168.100.x, routed and answering the PC
    # perfectly — and the hub listed nothing at all. But the hub was plugged
    # into both over USB the whole time, and INFO carries their IP.
    OFFNET = "192.168.100.50"
    real_probe2, real_lan2 = main.probe_module, main.lan_ip

    def fake_probe2(ip, timeout=0.6):
        if ip == OFFNET:      # reachable, just not on the swept subnet
            return {"ip": ip, "id": 67, "name": "offnet", "type": "nong", "sd": False}
        return None

    main.probe_module = fake_probe2
    main.lan_ip = lambda: SUBNET + ".4"
    main.MODULES.forget()
    main._usb_ident.clear()
    try:
        mods = main.scan_modules(force=True)
        t.ok(not any(m["id"] == 67 for m in mods),
             "a module on another subnet is not found by the sweep alone",
             "the sweep somehow reached outside its own /24")

        # now the hub sees it on a cable, which tells it where to look
        main._usb_ident["COM99"] = {"module": {"id": 67, "name": "offnet",
                                               "type": "nong", "ip": OFFNET}}
        mods = main.scan_modules(force=True)
        t.ok(any(m["id"] == 67 for m in mods),
             "but plugging it in once is enough to find it on WiFi",
             "a module the hub can reach is still missing from the list")
        t.eq(len([m for m in mods if m["id"] == 67]), 1, "listed exactly once")
    finally:
        main.probe_module, main.lan_ip = real_probe2, real_lan2
        main.MODULES.forget()
        main._usb_ident.clear()

    src = (F.CODE / "main_python/main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(src, "_probe_patiently", "the second pass exists in the hub")
    t.contains(src, "timeout=2.0", "and gives a known module real time to answer")
    t.contains(src, "_ips_from_usb",
               "and it learns addresses from modules seen on a cable")
