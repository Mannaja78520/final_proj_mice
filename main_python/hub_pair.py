"""Pairing two hubs, so ONE login works on every PC in the installation.

WHY NOT A GOOGLE OR FACEBOOK SIGN-IN
------------------------------------
It cannot work here, and the reason is the venue, not the code. OAuth needs
internet AT LOGIN TIME, a registered redirect URL and HTTPS. This hub runs
plain HTTP on a LAN address that changes, at a venue that often has no internet
at all — so on show day nobody could log in to stop a robot. Decided
2026-08-19, written down in the plan (A14-1) so it is not re-opened.

WHAT THIS DOES INSTEAD
----------------------
The same shape as pairing a TV. The hub that already has the accounts SHOWS a
code; a person carries that code to the other PC and types it there; that PC
asks for the accounts and proves it with the code. After that the two hubs
share the same accounts and neither needs the other again — which is the part
that matters, because the network at a venue is the first thing to fail.

The trust is a person's decision on BOTH machines: one presses Show, the other
types what is on the screen. That is the only offline option where nobody is
trusted by accident. Copying the file by hand makes one stolen PC into all of
them; deriving a secret from the group name is only as strong as a name someone
chose out loud.

WHAT TRAVELS, AND WHAT IT IS WORTH
----------------------------------
The salt and the PBKDF2 hash, never a password — the same bytes hub_auth.py
already stores. Anyone who records the exchange gets hashes at 240k iterations,
which is slow to attack but not free, so the window is deliberately small: one
code, five minutes, one use, and five wrong tries destroy it.
"""
import hmac
import secrets
import threading
import time

# No I, L, O or U. The code is read off one screen and typed on another, and
# those are the characters people get wrong. 8 of these is 40 bits.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LEN = 8
TTL_SECONDS = 300
MAX_TRIES = 5

# What a misread character almost always was. Safe because the alphabet above
# contains none of these letters.
FIXUPS = {"I": "1", "L": "1", "O": "0"}


def normalise(typed: str) -> str:
    """What a person typed, as the code that was shown.

    Case, spaces, the dash we print, and the three letters that get misread —
    a code refused because someone typed a lower-case l is a code that works
    and looks broken.
    """
    out = []
    for ch in (typed or "").upper():
        if ch in " -_\t\r\n":
            continue
        out.append(FIXUPS.get(ch, ch))
    return "".join(out)


def pretty(code: str) -> str:
    """ABCD-EFGH — four and four is what a person can carry across a room."""
    return code[:4] + "-" + code[4:] if len(code) == CODE_LEN else code


class Pending:
    """What the RECEIVING hub fetched, held just long enough to decide.

    The code is spent by the first claim, but the first attempt often changes
    nothing: an account name that exists on both PCs is reported, not
    overwritten, and the person then presses Replace. Without this they would
    have to walk back and show a second code, having decided nothing new — so
    the accounts already fetched are kept here, in memory, for one decision.
    """

    def __init__(self, ttl: int = TTL_SECONDS):
        self._lock = threading.Lock()
        self._ttl = ttl
        self._by_host = {}                   # address -> (host, accounts, at)

    def hold(self, address: str, host: str, accounts: dict):
        with self._lock:
            self._by_host[address] = (host, accounts or {}, time.monotonic())

    def get(self, address: str):
        """(host, accounts) while it is fresh, (None, None) once it is not."""
        with self._lock:
            host, accounts, at = self._by_host.get(address, (None, None, 0.0))
            if host is None or time.monotonic() - at > self._ttl:
                self._by_host.pop(address, None)
                return None, None
            return host, accounts

    def drop(self, address: str):
        with self._lock:
            self._by_host.pop(address, None)


class Pairing:
    """The live code on the hub that is GIVING its accounts away.

    One at a time on purpose: two live codes double the guessing surface and
    answer no question anyone asked.
    """

    def __init__(self, ttl: int = TTL_SECONDS):
        self._lock = threading.Lock()
        self._ttl = ttl
        self._code = ""
        self._until = 0.0
        self._tries = 0

    def start(self):
        """Show a new code. -> (code, seconds it lasts)."""
        with self._lock:
            self._code = "".join(secrets.choice(ALPHABET)
                                 for _ in range(CODE_LEN))
            self._until = time.monotonic() + self._ttl
            self._tries = 0
            return self._code, int(self._ttl)

    def stop(self):
        """Stop showing it. The person walked away, or is done."""
        with self._lock:
            self._code, self._until, self._tries = "", 0.0, 0

    def showing(self):
        """(code, seconds left) while one is live, ('', 0) when none is."""
        with self._lock:
            left = self._until - time.monotonic()
            if not self._code or left <= 0:
                return "", 0
            return self._code, int(left) + 1

    def tries_left(self) -> int:
        with self._lock:
            return max(0, MAX_TRIES - self._tries)

    def claim(self, typed: str):
        """Spend the code. -> (ok, why); `why` is shown to a person.

        Wrong tries kill the CODE, not the caller's address. A lockout per IP
        is the usual answer and it is the wrong one on a LAN: an attacker
        picks a new address for free, while the code cannot move. Five wrong
        guesses and the operator presses Show again — 40 bits are never
        reached five at a time.

        The whole thing happens under one lock: read-then-write across two
        request threads is how a five-try gate quietly allows more than five,
        which this project has already paid for once (hub_auth.login, fixed
        2026-08-21).
        """
        with self._lock:
            left = self._until - time.monotonic()
            if not self._code or left <= 0:
                return False, "that PC is not showing a pairing code"
            if not hmac.compare_digest(self._code, normalise(typed)):
                self._tries += 1
                if self._tries >= MAX_TRIES:
                    self._code, self._until = "", 0.0
                    return False, ("too many wrong codes — that code is dead. "
                                   "Show a new one on the other PC")
                n = MAX_TRIES - self._tries
                return False, "wrong code — %d %s left" % (
                    n, "try" if n == 1 else "tries")
            self._code, self._until = "", 0.0        # one code, one use
            return True, None
