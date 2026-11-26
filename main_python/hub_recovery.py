"""Getting back into the hub when the password is forgotten.

Two ways, and only two:

1. THE RECOVERY CODE. When a person sets their own password, the hub shows them
   a code ONCE (save it, print it). The hub keeps only a salted slow hash of it,
   so a stolen hub_auth.json does not hand over the code. The code works one
   time: using it sets a new password AND hands out a new code.
2. THE RESET FILE on the hub PC (tools/hub_reset_password.py, started by
   "Reset Hub Password.bat"). It edits the local file directly. There is no
   network route for it at all, so there is nothing to attack from the WiFi.

This module holds the parts with no hub state: making a code, checking one,
and the lockout that keeps someone from guessing codes.

THE LOCKOUT (user 2026-11-27: attempt limit, growing lockout, per source and
global, no information leak). A guesser has two levers: more tries from one
address, and many addresses. So there are two counters:
  * per source: 5 wrong tries lock that source for 1 minute, then 2, 4, 8 ...
    minutes, up to 1 hour;
  * global: 30 wrong tries from anywhere in 10 minutes lock EVERYONE's recovery
    for 5 minutes, then 10, 20 ... up to 1 hour. A flood of addresses therefore
    still hits a wall, and the owner just waits (the reset file always works).
The wait is the same whether the name or the code was wrong, and unknown names
cost the same time as known ones.
"""
import hashlib
import hmac
import secrets
import threading
import time

# 20 symbols with no 0/O/1/I/L/U look-alikes, 16 of them: 20^16 = 6.5e20
# possibilities (about 69 bits), shown as four groups of four so it can be read
# over the phone or copied by hand.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
GROUPS, GROUP_LEN = 4, 4
_ITERATIONS = 240_000


def new_code() -> str:
    """A fresh random code like K7QM-2XPD-9TRB-4WNC."""
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(GROUP_LEN))
                    for _ in range(GROUPS))


def normalise(code: str) -> str:
    """What a person may type: any case, spaces or dashes in odd places."""
    return "".join(c for c in (code or "").upper() if c in ALPHABET)[:GROUPS * GROUP_LEN * 2]


def hash_code(code: str, salt: bytes = None) -> dict:
    salt = salt or secrets.token_bytes(16)
    return {"salt": salt.hex(),
            "hash": hashlib.pbkdf2_hmac("sha256", normalise(code).encode(),
                                        salt, _ITERATIONS).hex()}


def check_code(rec, code: str) -> bool:
    """Constant time. A missing record still pays for one hash, so a name with
    no code and a name with a wrong code take the same time."""
    try:
        salt = bytes.fromhex(rec["salt"])
        want = bytes.fromhex(rec["hash"])
    except (TypeError, KeyError, ValueError):
        salt, want = b"\0" * 16, b"\0" * 32
        hashlib.pbkdf2_hmac("sha256", normalise(code).encode(), salt, _ITERATIONS)
        return False
    got = hashlib.pbkdf2_hmac("sha256", normalise(code).encode(), salt, _ITERATIONS)
    return hmac.compare_digest(want, got)


class Throttle:
    """Wrong tries per source and for everyone, with a growing wait."""

    def __init__(self, per_tries=5, per_base=60, per_cap=3600,
                 all_tries=30, all_window=600, all_base=300, all_cap=3600,
                 clock=time.monotonic):
        self.per_tries, self.per_base, self.per_cap = per_tries, per_base, per_cap
        self.all_tries, self.all_window = all_tries, all_window
        self.all_base, self.all_cap = all_base, all_cap
        self._now = clock
        self._lock = threading.Lock()
        self._src = {}            # source -> {"n", "until", "level"}
        self._all = {"hits": [], "until": 0.0, "level": 0}

    def wait_for(self, source: str) -> int:
        """Seconds this caller must wait, 0 when they may try."""
        now = self._now()
        with self._lock:
            left = max(self._all["until"] - now,
                       (self._src.get(source) or {}).get("until", 0.0) - now)
        return int(left) + 1 if left > 0 else 0

    def wrong(self, source: str):
        """Count one wrong try."""
        now = self._now()
        with self._lock:
            s = self._src.setdefault(source, {"n": 0, "until": 0.0, "level": 0})
            s["n"] += 1
            if s["n"] >= self.per_tries:
                s["until"] = now + min(self.per_cap, self.per_base * (2 ** s["level"]))
                s["level"] += 1
                s["n"] = 0
            hits = self._all["hits"]
            hits.append(now)
            hits[:] = [h for h in hits if now - h <= self.all_window]
            if len(hits) >= self.all_tries:
                self._all["until"] = now + min(
                    self.all_cap, self.all_base * (2 ** self._all["level"]))
                self._all["level"] += 1
                hits.clear()
            if len(self._src) > 5000:                 # never grow without end
                for k in [k for k, v in self._src.items()
                          if v["until"] < now and v["n"] == 0][:2500]:
                    self._src.pop(k, None)

    def right(self, source: str):
        """A good try clears that source's count (not the growing level)."""
        with self._lock:
            if source in self._src:
                self._src[source]["n"] = 0
