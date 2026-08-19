"""Who is allowed to make the hub DO something.

The hub binds 0.0.0.0 so a phone on the venue WiFi can reach it, and until now
that meant anyone on the venue WiFi could drive the servos or reflash a board.
This is the gate.

WHAT IS GATED, AND WHY IT IS NOT SIMPLY "POST"
----------------------------------------------
The obvious rule — GET is safe, POST needs a login — is WRONG here, and
dangerously so. Three of the routes that move the robot are GETs:

    /api/usb/cmd?port=..&c=POSE ...     sends a command down the cable
    /api/robot/cmd?ip=..&c=..           sends a command over WiFi
    /api/robot/delete?path=..           deletes a file off the SD card

So the gate is a LIST of what changes something, not a rule about verbs. A
route that is not on the list stays open, because reading has to keep working
without a login: the module list, the help page, the pages themselves and every
status endpoint. Someone glancing at the hub to see whether a board is alive
should not have to type anything.

HOW THE SECRET IS KEPT
----------------------
No accounts, no usernames: there is one hub and the people using it are in the
same room. The password is stored as a PBKDF2 hash with a random salt, never in
the clear — a stolen file must not hand over the password itself, because
people reuse passwords.

On first run there is no password. One is GENERATED and printed on the PC's own
console, which is the one place already trusted: it is the machine the hub runs
on. It is never shown on a page and never sent over the network, so seeing it
means standing at the PC.

Sessions live in memory only. Restarting the hub logs everyone out, which at a
venue is the behaviour you want.
"""
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

# Every route that CHANGES something: the robot moves, a file is written or
# deleted, firmware is replaced, a port is taken. Anything not here is readable
# without logging in.
GATED = {
    # the robot moves
    "/api/usb/cmd", "/api/robot/cmd", "/api/dev/cmd",
    # firmware is replaced — not undoable, and the board may be in someone's hand
    "/api/ota", "/api/dev/ota",
    # ...including an image sent from another PC. /api/flash/remote overwrites
    # a board on THIS machine's cable on someone else's say-so, so it is the
    # last route that should ever be open; /api/flash/send gives this PC's
    # firmware away and needs a login for the same reason.
    "/api/flash/remote", "/api/flash/send",
    # files are written or destroyed
    "/api/robot/upload", "/api/robot/delete",
    "/api/dev/upload", "/api/dev/delete",
    "/api/model/upload", "/api/rigdefault",
    "/api/settings/peer", "/api/export",
    # Which OTHER hubs this one talks to. Not a reading route: an
    # address added here is probed, trusted enough to list, and offered
    # as a link. Left open, anyone on the network could point this hub
    # at a machine of their choosing.
    "/api/hubs/add", "/api/hubs/forget",
    # a cable is taken away from whoever is using it
    "/api/usb/close",
    # who may use this hub at all
    "/api/users/add", "/api/users/remove",
}

# Paths that READ on GET and CHANGE on POST. Gating the whole path would take
# away the status the pages poll for, so only the writing half is gated.
GATED_POST = {
    "/api/settings",      # GET reads the shared settings, POST writes them
    "/api/play",          # GET reports the show, POST starts it
    "/api/flash",         # GET reports progress, POST starts a reflash
    "/api/save",          # writes a project
}

# NEVER gated, deliberately, however much they change:
#
#   /api/play/stop  stops a moving robot. Someone watching an arm about to hit
#                   a person or a set piece has to be able to stop it, and a
#                   password prompt in that moment is a safety failure, not
#                   security. Starting a show needs a login; ending one never
#                   does. The worst an unauthenticated caller can do here is
#                   stop the show, which is the same thing the physical power
#                   switch does and is always recoverable.
#
# Listed rather than merely absent, so nobody "tidies" it into GATED later.
NEVER_GATED = {"/api/play/stop"}

# Read-only siblings that must NOT be gated, listed so the intent is explicit
# rather than implied by absence. The QC check asserts against this.
OPEN = {
    "/api/status", "/api/scan", "/api/ports", "/api/mine", "/api/allmods",
    "/api/scanusb", "/api/hubs", "/api/servos", "/api/apps", "/api/list",
    "/api/modules",
    "/api/load", "/api/loadseq", "/api/flash/images",
    # Watching a write on another PC reads that PC; it changes nothing
    # here, and the page needs it precisely while it is not able to ask
    # the other hub itself.
    "/api/flash/at",
    # The QR is how a phone GETS to the login screen. Gating it would
    # be a lock on the outside of the front door.
    "/api/qr",
    "/api/robot/status", "/api/robot/files", "/api/robot/download",
    "/api/dev/status", "/api/dev/files", "/api/dev/download", "/api/dev/peers",
}

# The same rules the module enforces (firmware/src/core/UserStore.h), so the
# two cannot disagree about what a valid account is.
NAME_MAX = 20
PASS_MIN = 8
PASS_MAX = 32
MAX_USERS = 16
# What the single password becomes when an older hub is opened for the first
# time by this version. Also the account a bare password logs into.
DEFAULT_USER = "mice"

COOKIE = "mice_session"
_ITERATIONS = 240_000
_MAX_TRIES = 5
_LOCK_SECONDS = 60
_IDLE_SECONDS = 12 * 3600      # a show is long; a working day is not


def gated(path: str, method: str = "GET") -> bool:
    """Does this call change something the caller must be logged in to change?

    Method-aware on purpose. The obvious rule — GET is safe — is WRONG here:
    /api/usb/cmd is a GET that moves servos. And the reverse also holds: a few
    paths read on GET and write on POST, so gating the path would take away a
    status the pages poll for.
    """
    if path in NEVER_GATED:
        return False
    if path in GATED:
        return True
    return path in GATED_POST and method == "POST"


class Auth:
    def __init__(self, store: Path, out=print):
        self.store = Path(store)
        self._sessions = {}          # token -> last seen (monotonic)
        self._fails = {}             # who -> [count, locked until]
        self._out = out
        self.first_run_password = None
        self._load()

    # ---------------------------------------------------------- the secret
    def _load(self):
        if self.store.is_file():
            try:
                self._data = json.loads(self.store.read_text(encoding="utf-8"))
                # An older hub stored ONE password as salt/hash at the top
                # level. Read it as an account rather than demanding a new
                # one: a hub that locks its owner out on upgrade is worse than
                # a hub with one account.
                if "users" not in self._data and "hash" in self._data:
                    self._data = {"users": {DEFAULT_USER: {
                        "salt": self._data["salt"], "hash": self._data["hash"]}},
                        "set_at": self._data.get("set_at", "")}
                    self._save()
                    self._out("[auth] the hub password is now the account "
                              + DEFAULT_USER + " — add more on the Settings screen")
                return
            except (OSError, ValueError):
                self._out("[auth] password file unreadable — generating a new one")
        # First run. Generate one, print it HERE on the PC, and never anywhere
        # else. Four words would be friendlier to type; this is short enough to
        # read off a screen and long enough not to be guessed at a venue.
        pw = secrets.token_urlsafe(9)
        self.set_password(pw)
        self.first_run_password = pw
        self._out("")
        self._out("  This hub now needs a password before anything can be moved,")
        self._out("  flashed or deleted. Reading stays open.")
        self._out("")
        self._out("      password:  %s" % pw)
        self._out("")
        self._out("  Stored hashed in %s, and written in plain text in %s"
                  % (self.store.name, self.plain_file().name))
        self._out("  so it cannot be lost. Both stay on this PC.")
        self._out("")

    def plain_file(self) -> Path:
        """Where the password is written so a person can read it.

        Deliberate, and asked for after a lockout: the generated password is
        printed once, in the window the hub started in, and if that window is
        closed or missed the operator cannot drive their own robot. A password
        nobody can look up is not security, it is a locked door with the key
        thrown away.

        What this does NOT do is put it on the network. The hub serves
        main_python/web, never main_python itself, and check_hub_auth asserts
        that no URL reaches this file. Someone who can read this file can
        already read everything else on the PC.
        """
        return self.store.with_name("hub_password.txt")

    def _write_plain(self, password: str, user: str = DEFAULT_USER):
        text = (
            "This PC's Mice hub login:\n\n"
            "    user: %s\n"
            "    %s\n\n"
            "Set %s. Anyone at this PC can read this file. Nobody on the\n"
            "network can: the hub serves main_python/web, never this folder,\n"
            "and QC asserts that no URL reaches it.\n\n"
            "Lost it anyway? Delete hub_auth.json and restart the hub - it\n"
            "generates a new one and writes it here again.\n"
            % (user, password, time.strftime("%Y-%m-%d %H:%M")))
        try:
            self.plain_file().write_text(text, encoding="utf-8")
        except OSError as e:                    # a read-only folder is not fatal
            self._out("[auth] could not write %s: %s"
                      % (self.plain_file().name, e))

    # ------------------------------------------------------------ accounts
    @staticmethod
    def valid_name(name: str) -> bool:
        return bool(name) and len(name) <= NAME_MAX and \
            all(c.isalnum() or c in "_-" for c in name)

    @staticmethod
    def valid_password(password: str) -> bool:
        return PASS_MIN <= len(password or "") <= PASS_MAX and " " not in password

    @staticmethod
    def _hash(password: str, salt: bytes = None) -> dict:
        salt = salt or secrets.token_bytes(16)
        return {"salt": salt.hex(),
                "hash": hashlib.pbkdf2_hmac("sha256", password.encode(),
                                            salt, _ITERATIONS).hex()}

    def users(self):
        """Who can log in. Names only — a hash never leaves this object."""
        return sorted(self._data.get("users", {}))

    def add_user(self, name: str, password: str):
        """-> (ok, why). `why` is shown to a person, so it says what to fix."""
        if not self.valid_name(name):
            return False, "a name is 1 to %d letters, digits, _ or -" % NAME_MAX
        if not self.valid_password(password):
            return False, ("a password is %d to %d characters, no spaces"
                           % (PASS_MIN, PASS_MAX))
        users = self._data.setdefault("users", {})
        if name in users:
            return False, "there is already an account called %s" % name
        if len(users) >= MAX_USERS:
            return False, "this hub already has %d accounts" % MAX_USERS
        users[name] = self._hash(password)
        self._save()
        return True, None

    def remove_user(self, name: str):
        users = self._data.setdefault("users", {})
        if name not in users:
            return False, "there is no account called %s" % name
        # The module refuses this too. A hub with no accounts can only be fixed
        # by deleting its password file by hand, which at a venue is a dead hub.
        if len(users) <= 1:
            return False, "this is the only account — everyone would be locked out"
        del users[name]
        self._save()
        self._sessions.clear()      # a removed person must not stay logged in
        return True, None

    def _save(self):
        self._data["set_at"] = time.strftime("%Y-%m-%d %H:%M")
        self.store.parent.mkdir(parents=True, exist_ok=True)
        self.store.write_text(json.dumps(self._data, indent=1), encoding="utf-8")
        try:                                   # best effort; Windows ignores it
            os.chmod(self.store, 0o600)
        except OSError:
            pass

    def set_password(self, password: str, user: str = DEFAULT_USER):
        """Set (or create) one account's password."""
        users = self._data.setdefault("users", {}) if hasattr(self, "_data") else {}
        if not hasattr(self, "_data"):
            self._data = {"users": users}
        users[user] = self._hash(password)
        self._save()
        self._write_plain(password, user)
        # Changing a password ends every session: if it changed because one
        # leaked, leaving the leaked sessions alive defeats the change.
        self._sessions.clear()

    def _matches(self, password: str, user: str = None) -> bool:
        """Constant time, and against ONE named account."""
        users = self._data.get("users", {})
        rec = users.get(user or DEFAULT_USER)
        if not rec:
            return False
        want = bytes.fromhex(rec["hash"])
        got = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                  bytes.fromhex(rec["salt"]), _ITERATIONS)
        return hmac.compare_digest(want, got)   # constant time, not ==

    # ---------------------------------------------------------- logging in
    def locked_for(self, who: str) -> int:
        """Seconds this caller must wait, 0 if they may try now."""
        n, until = self._fails.get(who, (0, 0.0))
        left = until - time.monotonic()
        return int(left) + 1 if left > 0 else 0

    def login(self, password: str, who: str, user: str = None):
        """-> (token, None) on success, (None, reason) on failure.

        `user` may be omitted, and then means the account an older hub's single
        password became — so a page that only asks for a password keeps working
        exactly as it did.
        """
        wait = self.locked_for(who)
        if wait:
            return None, "too many tries — wait %d seconds" % wait
        if not self._matches(password or "", user):
            n, _ = self._fails.get(who, (0, 0.0))
            n += 1
            until = time.monotonic() + _LOCK_SECONDS if n >= _MAX_TRIES else 0.0
            self._fails[who] = (n, until)
            left = _MAX_TRIES - n
            if left > 0:
                # Deliberately the same wording whether the NAME or the
                # password was wrong: saying which is how a stranger learns a
                # valid account name.
                return None, "wrong login — %d %s left" % (
                    left, "try" if left == 1 else "tries")
            return None, "too many tries — wait %d seconds" % _LOCK_SECONDS
        self._fails.pop(who, None)
        token = secrets.token_urlsafe(24)
        self._sessions[token] = time.monotonic()
        return token, None

    def logout(self, token: str):
        self._sessions.pop(token or "", None)

    def valid(self, token: str) -> bool:
        seen = self._sessions.get(token or "")
        if seen is None:
            return False
        if time.monotonic() - seen > _IDLE_SECONDS:
            self._sessions.pop(token, None)
            return False
        self._sessions[token] = time.monotonic()    # still being used
        return True

    def token_of(self, cookie_header: str) -> str:
        for part in (cookie_header or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                return v
        return ""
