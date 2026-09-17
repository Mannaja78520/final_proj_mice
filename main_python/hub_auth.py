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
import threading
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
    # ...and the same overwrite by command channel - it reaches a cable, the
    # bus, WiFi or another PC's module, so leaving it open was wider than any
    # single transport (found by the A22-1 sweep, 2026-08-25).
    "/api/flash/bus",
    # files are written or destroyed ON A BOARD
    "/api/robot/upload", "/api/robot/delete",
    "/api/dev/upload", "/api/dev/delete",
    "/api/settings/peer",
    # Which OTHER hubs this one talks to. Not a reading route: an
    # address added here is probed, trusted enough to list, and offered
    # as a link. Left open, anyone on the network could point this hub
    # at a machine of their choosing.
    "/api/hubs/add", "/api/hubs/forget",
    # a cable is taken away from whoever is using it
    "/api/usb/close",
    # who may use this hub at all
    "/api/users/add", "/api/users/remove", "/api/users/rename", "/api/users/password",
    # Pairing, from BOTH ends. /api/pair/status is a GET and still gated:
    # it hands back the code on the screen, which is the one secret in the
    # whole exchange. /api/pair/link makes this hub take another hub's
    # accounts, which decides who can drive the robots here.
    "/api/pair/start", "/api/pair/stop", "/api/pair/status", "/api/pair/link",
}

# Proved by something OTHER than a session. There is exactly one, and it is
# the point of pairing: the far hub has no account here yet, so a login is
# impossible by definition. The pairing code is the credential — five minutes,
# one use, five wrong tries and it dies (hub_pair.Pairing).
CODE_GATED = {"/api/pair/claim"}

# Paths that READ on GET and CHANGE on POST. Gating the whole path would take
# away the status the pages poll for, so only the writing half is gated.
GATED_POST = {
    "/api/settings",      # GET reads the shared settings, POST writes them
    "/api/play",          # GET reports the show, POST starts it
    # Live audio out of a robot standing in a room full of people: starting it
    # is as much "make the rig do something" as starting a show. Reading where
    # it is up to stays open, like every other status.
    "/api/stream/start", "/api/stream/feed",
    "/api/flash",         # GET reports progress, POST starts a reflash
    # Voice endpoints: asked 2026-09-14 to require login first before doing anything
    "/api/voice/start",
    "/api/voice/stop",
    "/api/voice/ask",
    "/api/voice/transcribe",
    "/api/voice/say",
    # A20-12 settings: reading the voice stores is open, saving them rewrites
    # what the rig answers and how it listens - gated like /api/settings.
    "/api/voice/config",
    "/api/voice/faq",
    # Reading which build is available is as harmless as reading the module
    # list; replacing the hub is the most destructive thing it can be asked to
    # do, and it is on a network several people share.
    "/api/selfupdate",   # GET says what version is offered; POST replaces the program itself.
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
#   /api/stopall    the same argument, for every board at once. Added with the
#                   stop control that reaches every screen (A11-3). If anything,
#                   the case is stronger: this is the one somebody presses while
#                   an arm is moving towards a person, and it is the only
#                   control in the product where a login prompt could cause an
#                   injury rather than prevent one. It stops things; it starts
#                   nothing.
#
#   THE TOOLS. Asked for directly, 2026-08-21: *make the tool can use everytime
#                   like the nong studio... but when need to command the robot
#                   need to use the login*. Studio is not only a way to drive a
#                   robot - most of the work in it happens before there is one:
#                   posing, timing a sequence, saving it, exporting the YAML.
#                   None of that reaches a board, and a password in front of it
#                   made the editor unusable until a robot existed. So a project
#                   saved, a sequence exported, an STL uploaded and a rig kept as
#                   the default are all open, and the routes that reach a BOARD
#                   are exactly as gated as they were.
#
#                   What this costs: anyone on the venue WiFi can write a
#                   project or a sequence file into this PC's own folders. They
#                   could already read them, and they still cannot send one to a
#                   robot, replace firmware, or delete anything off an SD card.
#
# Listed rather than merely absent, so nobody "tidies" it into GATED later.
NEVER_GATED = {"/api/play/stop", "/api/stopall",
               # and silence: a robot talking over a room must be
               # stoppable by whoever is standing next to it, for the
               # same reason a moving one must be.
               "/api/stream/stop",
               "/api/save", "/api/export", "/api/model/upload", "/api/rigdefault"}

# Read-only siblings that must NOT be gated, listed so the intent is explicit
# rather than implied by absence. The QC check asserts against this.
OPEN = {
    "/api/status", "/api/scan", "/api/ports", "/api/mine", "/api/allmods",
    "/api/scanusb", "/api/hubs", "/api/servos", "/api/apps", "/api/list",
    "/api/modules", "/api/modules/all",
    "/api/load", "/api/loadseq", "/api/flash/images",
    # Watching a write on another PC reads that PC; it changes nothing
    # here, and the page needs it precisely while it is not able to ask
    # the other hub itself.
    "/api/flash/at",
    # The QR is how a phone GETS to the login screen. Gating it would
    # be a lock on the outside of the front door.
    "/api/qr",
    # Which pages work with no login, and which cards ask first. A page has
    # to draw itself BEFORE anybody has signed in, so gating this would put
    # the sign-in box behind a sign-in box. It says nothing secret either:
    # the same list is written on the help page in plain words.
    "/api/access",
    # Where the outside programs live, and what each of their event sources can
    # report. Addresses only - the logins are not in that file and never will
    # be - and the tile has to draw itself before anybody has signed in.
    "/api/partners",
    "/api/all-jao/start", "/api/reconize/start",
    # Opening an outside app from this PC needs no hub login (they have their
    # own); main.py still asks a caller on the network to log in.
    "/api/partners/start",
    # A report is a complaint, not a command: it changes nothing on any
    # board, and complaining must never need a password (A21-6).
    "/api/report",
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
DEFAULT_USER = "super_admin"
# THE SHIPPED LOGIN (user 2026-09-17: super_admin/admin123 and admin/admin123
# everywhere, shown as default until changed). Any account still on it has
# must_change set, and every page says so.
DEFAULT_PASSWORD = "admin123"
ROLE_SUPER, ROLE_USER = "super_admin", "user"
# The real hub's store. Any OTHER name is somebody's throwaway (a QC run
# makes one per process), and its password file is named after it.
DEFAULT_STORE_NAME = "hub_auth.json"

COOKIE = "mice_session"
_ITERATIONS = 240_000
_MAX_TRIES = 5
_LOCK_SECONDS = 60
_IDLE_SECONDS = 12 * 3600      # a show is long; a working day is not


def _is_hex(s: str, length: int) -> bool:
    """Exactly `length` hex characters — the shape _hash() writes."""
    if len(s) != length:
        return False
    try:
        bytes.fromhex(s)
    except ValueError:
        return False
    return True


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
        self._fails = {}
        self._count_lock = threading.Lock()             # who -> [count, locked until]
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
                users = self._data.setdefault("users", {})
                if DEFAULT_USER not in users:
                    pw = DEFAULT_PASSWORD
                    users[DEFAULT_USER] = self._hash(pw)
                    if "admin" not in users:
                        users["admin"] = self._hash(pw)
                    self._save()
                self._normalise()
                return
            except (OSError, ValueError):
                self._out("[auth] password file unreadable — generating a new one")
        self._claim_or_adopt()

    def _claim_or_adopt(self):
        """First run — possibly SHARED by two hub processes at once.

        Two starts racing on one store both used to see no file, both
        generated, and the console printed two different passwords while the
        files described only the second (seen 2026-08-26). An exclusive
        create decides who generates; everyone else adopts the winner's file.
        """
        try:
            os.close(os.open(self.store, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            if self._await_adopt():
                return
            # Nobody produced a readable store in time: the placeholder is
            # ours to fill. Same as before, last writer wins.
        self._generate()

    def _await_adopt(self, seconds=5.0) -> bool:
        """Another process claimed this first run; wait for its store."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            time.sleep(0.05)
            try:
                data = json.loads(self.store.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and data.get("users"):
                self._data = data
                self._out("[auth] another hub process set the password "
                          "first — adopting %s" % self.store.name)
                return True
        return False

    def _generate(self):
        pw = DEFAULT_PASSWORD
        self._data = {"users": {
            "admin": self._hash(pw),
            "super_admin": self._hash(pw)
        }}
        self._normalise()
        self._save()
        self._write_plain(pw, "admin")
        self._write_plain(pw, "super_admin")
        self.first_run_password = pw
        self._out("")
        self._out("  This hub now needs a password before anything can be moved,")
        self._out("  flashed or deleted. Reading stays open.")
        self._out("")
        self._out("      admin password:  %s" % pw)
        self._out("      super_admin password:  %s" % pw)
        self._out("")
        self._out("  Stored hashed in %s, and written in plain text in %s"
                  % (self.store.name, self.plain_file().name))
        self._out("  so it cannot be lost. Both stay on this PC.")
        self._out("")
        self._out("  This hub now needs a password before anything can be moved,")
        self._out("  flashed or deleted. Reading stays open.")
        self._out("")
        self._out("      admin password:  %s" % pw)
        self._out("      super_admin password:  %s" % pw)
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

        THE NAME FOLLOWS THE STORE. It used to be hub_password.txt for every
        store, so each QC run - which makes its own mice_qc_auth_<pid>.json -
        wrote its throwaway password over the real one. Found 2026-09-07 when
        the file offered a password the hub had never had, and the user could
        not log in.
        """
        if self.store.name == DEFAULT_STORE_NAME:
            return self.store.with_name("hub_password.txt")
        return self.store.with_suffix(".txt")

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

    # ------------------------------------------------------------ roles
    # user 2026-09-17: *each user can change it own pass and user but
    # super_admin is can change everyone user and pass also can delete or add
    # new user*. Authority is the ROLE on the record, never the account name:
    # renaming super_admin must not take its power away (Codex review).
    def _normalise(self):
        """Give every record a role and a must_change flag; keep >=1 super."""
        users = self._data.setdefault("users", {})
        changed = False
        for name, rec in users.items():
            if rec.get("role") not in (ROLE_SUPER, ROLE_USER):
                rec["role"] = ROLE_SUPER if name == DEFAULT_USER else ROLE_USER
                changed = True
            if "must_change" not in rec:
                rec["must_change"] = self._rec_matches(rec, DEFAULT_PASSWORD)
                changed = True
        if users and not any(r.get("role") == ROLE_SUPER for r in users.values()):
            first = DEFAULT_USER if DEFAULT_USER in users else sorted(users)[0]
            users[first]["role"] = ROLE_SUPER
            changed = True
        if changed:
            self._save()

    @staticmethod
    def _rec_matches(rec, password):
        try:
            want = bytes.fromhex(rec["hash"])
            got = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                      bytes.fromhex(rec["salt"]), _ITERATIONS)
        except (KeyError, ValueError):
            return False
        return hmac.compare_digest(want, got)

    def role_of(self, name: str) -> str:
        return (self._data.get("users", {}).get(name) or {}).get("role", "")

    def is_super(self, name: str) -> bool:
        return self.role_of(name) == ROLE_SUPER

    def must_change(self, name: str) -> bool:
        return bool((self._data.get("users", {}).get(name) or {}).get("must_change"))

    def accounts(self):
        """name, role and whether it still has the shipped password. Never a hash."""
        return [{"name": n, "role": r.get("role", ROLE_USER),
                 "mustChange": bool(r.get("must_change"))}
                for n, r in sorted(self._data.get("users", {}).items())]

    def _supers(self):
        return [n for n, r in self._data.get("users", {}).items()
                if r.get("role") == ROLE_SUPER]

    def rename_user(self, old: str, new: str):
        """-> (ok, why). Sessions follow the account, so nobody is logged out."""
        users = self._data.setdefault("users", {})
        if old not in users:
            return False, "there is no account called %s" % old
        if not self.valid_name(new):
            return False, "a name is 1 to %d letters, digits, _ or -" % NAME_MAX
        if new == old:
            return True, None
        if new in users:
            return False, "there is already an account called %s" % new
        users[new] = users.pop(old)
        for token, (seen, who) in list(self._sessions.items()):
            if who == old:
                self._sessions[token] = (seen, new)
        self._save()
        return True, None

    def change_password(self, name: str, password: str, keep_token: str = ""):
        """-> (ok, why). Ends that account's OTHER sessions, keeps the caller's."""
        users = self._data.setdefault("users", {})
        if name not in users:
            return False, "there is no account called %s" % name
        if not self.valid_password(password):
            return False, ("a password is %d to %d characters, no spaces"
                           % (PASS_MIN, PASS_MAX))
        rec = users[name]
        rec.update(self._hash(password))
        rec["must_change"] = password == DEFAULT_PASSWORD
        self._save()
        for token, (_seen, who) in list(self._sessions.items()):
            if who == name and token != keep_token:
                self._sessions.pop(token, None)
        return True, None

    def check_password(self, name: str, password: str) -> bool:
        rec = self._data.get("users", {}).get(name)
        return bool(rec) and self._rec_matches(rec, password or "")

    def add_user(self, name: str, password: str, role: str = ROLE_USER):
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
        users[name] = dict(self._hash(password),
                           role=role if role in (ROLE_SUPER, ROLE_USER) else ROLE_USER,
                           must_change=password == DEFAULT_PASSWORD)
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
        if users[name].get("role") == ROLE_SUPER and len(self._supers()) <= 1:
            return False, ("%s is the last super_admin — nobody could manage the "
                           "accounts" % name)
        del users[name]
        self._save()
        # a removed person must not stay logged in - but whoever removed them does
        for token, (_seen, who) in list(self._sessions.items()):
            if who == name:
                self._sessions.pop(token, None)
        return True, None

    # ------------------------------------------------------------- pairing
    # One login on every PC (A14-1). The accounts are COPIED once, after a
    # person proved a pairing code on both machines — see hub_pair.py.
    def export_accounts(self) -> dict:
        """Every account as name -> {salt, hash}. Never a password.

        These bytes leave the PC, which is the whole point — the same password
        then works on the other hub with no internet and no link between them
        afterwards. It is also why nothing may call this without a live
        pairing code.
        """
        return {n: {"salt": r["salt"], "hash": r["hash"],
                    "role": r.get("role", ROLE_USER),
                    "must_change": bool(r.get("must_change"))}
                for n, r in self._data.get("users", {}).items()
                if r.get("salt") and r.get("hash")}

    def import_accounts(self, accounts, replace: bool = False):
        """Take another hub's accounts. -> dict(added, clashed, replaced,
        skipped, why).

        NEVER DELETES, and never overwrites unless a person asked twice.

        A clash is not the rare case, it is the normal one: every hub
        generates the DEFAULT_USER account on first run, so two fresh PCs both
        have that name with different passwords. Skipping it silently would
        make pairing useless exactly when both are new — and the local one
        often cannot be removed first, because remove_user refuses the last
        account. So the first attempt REPORTS the clash and changes nothing,
        and the page offers replacing it as a second, deliberate press.
        """
        users = self._data.setdefault("users", {})
        out = {"added": [], "clashed": [], "replaced": [], "skipped": [],
               "why": None}
        for name, rec in sorted((accounts or {}).items()):
            if not self.valid_name(name) or not isinstance(rec, dict):
                out["skipped"].append(str(name)[:NAME_MAX])
                continue
            salt, digest = str(rec.get("salt") or ""), str(rec.get("hash") or "")
            # A record that is not hex would raise inside _matches and take
            # the login route down with it, so it is refused here instead.
            if not _is_hex(salt, 32) or not _is_hex(digest, 64):
                out["skipped"].append(name)
                continue
            here = name in users
            if here and users[name].get("salt") == salt \
                    and users[name].get("hash") == digest:
                # Already the same account — pairing twice is not a change,
                # and calling it one would end every session for nothing.
                continue
            if here and not replace:
                out["clashed"].append(name)
                continue
            if not here and len(users) >= MAX_USERS:
                out["why"] = ("this hub is full at %d accounts — remove one "
                              "and pair again" % MAX_USERS)
                out["skipped"].append(name)
                continue
            users[name] = {"salt": salt, "hash": digest,
                           # a pairing never promotes anyone the far hub did not
                           "role": rec.get("role") if rec.get("role") in (ROLE_SUPER, ROLE_USER) else ROLE_USER,
                           "must_change": bool(rec.get("must_change"))}
            out["replaced" if here else "added"].append(name)
        if out["added"] or out["replaced"]:
            self._save()
        if out["replaced"]:
            # A replaced account has a different password now. Whoever is
            # logged in under the old one must not stay logged in, for the
            # same reason set_password ends every session.
            self._sessions.clear()
        return out

    def note_paired(self, host: str, names):
        """Append to the readable password file: these logins live elsewhere.

        hub_password.txt says *this PC's login*, and after pairing that is no
        longer the whole truth — the imported accounts have no password on
        this machine to write down. Someone reading the file to get into the
        hub would otherwise be told about one account out of five.
        """
        if not names:
            return
        try:
            with open(self.plain_file(), "a", encoding="utf-8",
                      newline="") as f:
                f.write("\nPaired with %s on %s: %s\nTheir passwords are set "
                        "on %s, not here.\n"
                        % (host or "another PC",
                           time.strftime("%Y-%m-%d %H:%M"),
                           ", ".join(sorted(names)), host or "that PC"))
        except OSError:                     # a read-only folder is not fatal
            pass

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
        users[user] = dict(users.get(user) or {}, **self._hash(password))
        users[user]["must_change"] = password == DEFAULT_PASSWORD
        self._normalise()                 # a new record still gets its role
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

    def _resync(self) -> bool:
        """Adopt the store from disk if it changed under us -> did it change?

        A file read costs nothing next to the PBKDF2 that always follows a
        mismatch, so re-reading on every wrong password is free.
        """
        try:
            data = json.loads(self.store.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict) or not data.get("users") \
                or data == self._data:
            return False
        self._data = data
        # The sessions in memory belonged to accounts this file no longer
        # describes — the same reason set_password clears them.
        self._sessions.clear()
        return True

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
            # THE FILE IS THE TRUTH, NOT THIS PROCESS'S MEMORY. Seen
            # 2026-08-26: a second hub process regenerated the password while
            # this one served; the files described the new one and this one
            # went on refusing it — the operator locked out of their own hub.
            # Re-read once before counting a failed try.
            self._resync()
        if not self._matches(password or "", user):
            # COUNTED UNDER A LOCK. Read-modify-write from two request threads
            # interleaves and loses a try, so five wrong passwords could take
            # more than five attempts to lock out - a brute-force gate quietly
            # weaker than the number it advertises. Found 2026-08-21.
            with self._count_lock:
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
        self._sessions[token] = (time.monotonic(), user or DEFAULT_USER)
        return token, None

    def logout(self, token: str):
        self._sessions.pop(token or "", None)

    def valid(self, token: str) -> bool:
        seen = self._sessions.get(token or "")
        if seen is None:
            return False
        last_time, user = seen
        if time.monotonic() - last_time > _IDLE_SECONDS:
            self._sessions.pop(token, None)
            return False
        self._sessions[token] = (time.monotonic(), user)    # still being used
        return True

    def user_of(self, token: str) -> str:
        seen = self._sessions.get(token or "")
        if seen is None:
            return ""
        last_time, user = seen
        if time.monotonic() - last_time > _IDLE_SECONDS:
            self._sessions.pop(token, None)
            return ""
        self._sessions[token] = (time.monotonic(), user)
        return user

    def token_of(self, cookie_header: str) -> str:
        for part in (cookie_header or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                return v
        return ""
