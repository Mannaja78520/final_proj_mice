"""The hub's routes for flashing: over the cable, from another PC, over WiFi, over the bus.

Moved out of main.py's Handler.api() on 2026-09-22 (A26-93). Handler inherits
FlashRoutes, and api() asks it before carrying on down its own chain. Names
that live in main.py are read late through _hub, so a check that swaps
main.<name> reaches this code too.
"""
import json
import urllib.request

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class FlashRoutes:
    def api_flash(self, method, path, q):
        # ---- flashing a board over its own cable (see Flasher) ----
        # GET  /api/flash/images   what this PC could flash, and what is missing
        # POST /api/flash?port=&type=   start (the cable is taken for the job)
        # GET  /api/flash          progress, then ok/error
        # Watching a write that is happening on ANOTHER PC. The page cannot
        # ask that hub directly - it is a different origin, so the browser
        # sends no cookie and the answer is refused - so this hub asks for it.
        if path == "/api/flash/at":
            ip = (q.get("ip") or [""])[0]
            try:
                with urllib.request.urlopen(
                        "http://%s:%d/api/flash" % (ip, _hub.PORT), timeout=8) as r:
                    return self.send_bytes(r.read(), _hub.MIME[".json"])
            except Exception as e:            # noqa: BLE001
                return self.send_json({"running": False, "ok": False,
                                       "error": "%s is not answering (%s)" % (ip, e)})

        # ---- flashing from ANOTHER PC (see remote_payload) ----
        # The image arrives over the network and esptool runs HERE, because
        # this is the PC holding the cable. Gated: it is the most destructive
        # thing this hub can be asked to do.
        if path == "/api/flash/remote" and method == "POST":
            try:
                d = json.loads(self.body(48 * 1048576).decode())
                return self.send_json(_hub.flasher.start_received(
                    d.get("port", ""), d.get("type", ""),
                    d.get("parts") or [], d.get("from", "another PC")))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        # ...and the other half: hand THIS PC's image to the hub that has the
        # cable. The operator names that hub and logs into it here, because a
        # hub does not hold another hub's password.
        if path == "/api/flash/send" and method == "POST":
            try:
                d = json.loads(self.body().decode())
                return self.send_json(_hub.send_firmware(
                    d.get("to", ""), d.get("port", ""), d.get("type", ""),
                    d.get("user", ""), d.get("password", "")))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        if path == "/api/flash/images":
            cmd, why = _hub.esptool_cmd()
            return self.send_json({"images": _hub.flash_images(),
                                   "esptool": bool(cmd), "why": why})
        if path == "/api/flash" and method == "POST":
            try:
                return self.send_json(_hub.flasher.start(
                    (q.get("port") or [""])[0], (q.get("type") or [""])[0]))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/flash":
            return self.send_json(_hub.flasher.status())
        # the same job, over WiFi: no cable, and the board keeps the firmware
        # it already has if the update does not complete
        if path == "/api/ota" and method == "POST":
            try:
                # The board's OWN login, when it is not the shipped one. Read
                # from the body as well as the query so a password never has
                # to travel in a URL, where it lands in every access log.
                try:
                    d = json.loads(self.body().decode() or "{}")
                except ValueError:
                    d = {}
                return self.send_json(_hub.flasher.start_ota(
                    (q.get("ip") or [""])[0], (q.get("type") or [""])[0],
                    user=str(d.get("user") or (q.get("user") or [""])[0]),
                    password=str(d.get("password") or (q.get("password") or [""])[0])))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        # and the same job again over the COMMAND channel, which is the only
        # one an RS485 board has — see Flash.start_bus. `dev` is an ordinary
        # dev address, so this reaches a cable, the bus, WiFi, a module behind
        # another module's hotspot, or a module on another PC, unchanged.
        if path == "/api/flash/bus" and method == "POST":
            try:
                return self.send_json(_hub.flasher.start_bus(
                    (q.get("dev") or [""])[0], (q.get("type") or [""])[0]))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        return NOT_MINE
