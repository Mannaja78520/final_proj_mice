"""Who else is running on this PC (user 2026-11-23, every app alone AND together).

    GET /api/peers    every live program that announced itself: the full hub,
                      and each app started alone (`--alone <app>`), with what
                      it can do (caps) and where to open it
        ?cap=prize    only the ones that can do that (a program asks "who can
                      give a prize?" and does not care whether it is the hub
                      or the prize machines app by itself)
        ?app=gacha    only that app

Reading is open like the other lists. The records come from peers.py, which
drops the ones whose program has gone, so this is always the true list.
"""
import peers

NOT_MINE = object()


class PeersRoutes:
    def api_peers(self, method, path, q):
        if path == "/api/peers" and method == "GET":
            return self.send_json({"ok": True, "peers": peers.peers(
                app=(q.get("app") or [""])[0] or None,
                cap=(q.get("cap") or [""])[0] or None)})
        return NOT_MINE
