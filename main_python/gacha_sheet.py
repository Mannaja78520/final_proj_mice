"""A Google Sheet the Prize machines page reads AND writes (A47-15).

User 2026-10-23: "ขอให้แก้ไฟล์ใน google sheet ได้ด้วยถ้าเอาลิ้งมาใส่" - paste the
sheet's link, then edit it from the hub. Reading a sheet shared "anyone with
the link" needs nothing; WRITING needs something Google trusts, so there are
several ways and config picks one (rules.sheet_way in config/gacha.json):

  link     read only: the sheet's CSV export (gviz). No setup but sharing.
  script   an Apps Script web app the user deploys once from the sheet
           (apps/gacha/sheet_script.gs). It runs as the sheet's owner, so a
           private sheet works too. The hub sends a secret it made itself
           (<data>/sheet_secret.txt), so the web app's address alone writes nothing.
  service  a Google service account's key file in <data>/ (never git); the
           sheet is shared with its e-mail. Needs the `cryptography` package.
  auto     the first of AUTO_ORDER that is set up.

A new way is one class with ready/tabs/read/write/append and one WAYS entry.
Rows are lists of strings; row 0 is the header. Every way raises SheetError
with words for the page; nothing here knows about prizes.
"""
import base64
import csv
import io
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_PLACEHOLDER = "__MICE_SECRET__"
SHEETS_API = "https://sheets.googleapis.com/v4"
SCOPE = "https://www.googleapis.com/auth/spreadsheets"
_TOKENS = {}          # key file -> (access token, good until): one sign-in an hour


class SheetError(Exception):
    pass


def sheet_id(link):
    """The id out of a pasted sheet link (or an id pasted alone), or ''."""
    link = (link or "").strip()
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]{20,})", link)
    if m:
        return m.group(1)
    return link if re.fullmatch(r"[A-Za-z0-9_-]{20,}", link) else ""


def http(method, url, body=None, headers=None, timeout=20):
    """-> (status, text). A JSON body is sent as JSON; a str/bytes as it is."""
    data = None
    h = {"User-Agent": "MiceHub-sheet"}
    if body is not None:
        data = body if isinstance(body, bytes) else (
            body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8"))
        h["Content-Type"] = "application/json" if not isinstance(body, (str, bytes)) else \
            "application/x-www-form-urlencoded"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8-sig", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise SheetError("the sheet could not be reached (%s)" % getattr(e, "reason", e))


def csv_rows(text):
    return [[c.strip() for c in r] for r in csv.reader(io.StringIO(text or ""))]


def rows_csv(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def square(rows):
    """Every row as long as the longest, all strings (Sheets wants a rectangle)."""
    rows = [["" if c is None else str(c) for c in (r or [])] for r in rows or []]
    w = max([len(r) for r in rows] or [0])
    return [r + [""] * (w - len(r)) for r in rows]


class Way:
    name = ""
    writes = True

    def __init__(self, rc, data_dir, http_=None):
        self.rc = rc
        self.data = Path(data_dir)
        self.http = http_ or http
        self.id = sheet_id(rc.get("sheet_link"))

    def ready(self):
        return False

    def tabs(self):
        return [t for t in (self.rc.get("sheet_tabs") or {}).values() if t]

    def append(self, tab, row, head=None):
        """One row at the end; `head` first when the tab is new or empty."""
        rows = self.read(tab)
        self.write(tab, (rows or ([head] if head else [])) + [row])


class LinkWay(Way):
    """Read only, through the CSV export of a sheet shared 'anyone with the link'."""
    name = "link"
    writes = False

    def ready(self):
        return bool(self.id)

    def read(self, tab):
        if not self.id:
            raise SheetError("paste the sheet's link first")
        url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&sheet=%s"
               % (self.id, urllib.parse.quote(tab)))
        st, text = self.http("GET", url)
        if st != 200 or text.lstrip().startswith("<"):
            raise SheetError("the sheet is not shared for reading: Share ▸ General access ▸ "
                             "Anyone with the link (%s)" % st)
        return csv_rows(text)

    def write(self, tab, rows):
        raise SheetError("this sheet can only be read: set up writing (the Google Sheet tab, steps 1-5)")

    def append(self, tab, row, head=None):
        self.write(tab, [row])


def secret(data_dir):
    """The hub's own secret for the sheet's script; made once, kept in .local."""
    p = Path(data_dir) / "sheet_secret.txt"
    if p.is_file() and p.read_text(encoding="utf-8").strip():
        return p.read_text(encoding="utf-8").strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    s = secrets.token_urlsafe(24)
    p.write_bytes(s.encode("utf-8"))
    return s


def script_text(template, data_dir):
    """The Apps Script to paste, with this hub's secret filled in."""
    return template.replace(SCRIPT_PLACEHOLDER, secret(data_dir))


class ScriptWay(Way):
    """The user's Apps Script web app (apps/gacha/sheet_script.gs)."""
    name = "script"

    def ready(self):
        return bool(self.rc.get("sheet_write_url"))

    def ask(self, op, **kw):
        url = self.rc.get("sheet_write_url")
        if not url:
            raise SheetError("no script address yet (the Google Sheet tab, step 4)")
        st, text = self.http("POST", url, dict(kw, op=op, secret=secret(self.data)))
        try:
            got = json.loads(text)
        except ValueError:
            # A sign-in page instead of JSON: deployed for "Only myself".
            raise SheetError("the script did not answer (%s): deploy it with access 'Anyone'" % st)
        if not got.get("ok"):
            raise SheetError("the sheet's script said no: %s" % (got.get("error") or "no reason"))
        return got

    def tabs(self):
        return self.ask("tabs").get("tabs") or []

    def read(self, tab):
        return self.ask("read", tab=tab).get("rows") or []

    def write(self, tab, rows):
        self.ask("write", tab=tab, rows=square(rows))

    def append(self, tab, row, head=None):
        self.ask("append", tab=tab, rows=square([row]), head=head or [])


class ServiceWay(Way):
    """A service account: Sheets API v4 with a token signed from its key file."""
    name = "service"

    def key_path(self):
        return Path(self.rc.get("sheet_key_file") or (self.data / "google_service.json"))

    def ready(self):
        return bool(self.id) and self.key_path().is_file()

    def token(self):
        tok, until = _TOKENS.get(str(self.key_path()), (None, 0))
        if tok and time.time() < until - 60:
            return tok
        try:
            key = json.loads(self.key_path().read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SheetError("the service account's key file could not be read (%s)" % e)
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError:
            raise SheetError("this PC lacks the 'cryptography' package for this way; "
                             "the script way needs nothing")
        b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=")
        now = int(time.time())
        uri = key.get("token_uri") or "https://oauth2.googleapis.com/token"
        head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claim = b64(json.dumps({"iss": key.get("client_email"), "scope": SCOPE, "aud": uri,
                                "iat": now, "exp": now + 3600}).encode())
        pk = serialization.load_pem_private_key(key.get("private_key", "").encode(), password=None)
        sig = b64(pk.sign(head + b"." + claim, padding.PKCS1v15(), hashes.SHA256()))
        st, text = self.http("POST", uri, urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": (head + b"." + claim + b"." + sig).decode()}))
        got = json.loads(text) if text.startswith("{") else {}
        if st != 200 or not got.get("access_token"):
            raise SheetError("Google did not accept the service account (%s)" % (got.get("error") or st))
        _TOKENS[str(self.key_path())] = (got["access_token"], now + int(got.get("expires_in") or 3600))
        return got["access_token"]

    def api(self, method, path, body=None):
        base = (self.rc.get("sheet_api") or SHEETS_API).rstrip("/")
        st, text = self.http(method, "%s/spreadsheets/%s%s" % (base, self.id, path), body,
                             {"Authorization": "Bearer " + self.token()})
        got = json.loads(text) if text.startswith("{") else {}
        if st >= 300:
            msg = (got.get("error") or {}).get("message") if isinstance(got.get("error"), dict) else st
            raise SheetError("the sheet refused (%s): share it with the service account's e-mail" % msg)
        return got

    def rng(self, tab, suffix=""):
        return "/values/" + urllib.parse.quote("'%s'" % tab.replace("'", "''"), safe="") + suffix

    def tabs(self):
        got = self.api("GET", "?fields=sheets.properties.title")
        return [s["properties"]["title"] for s in got.get("sheets") or []]

    def read(self, tab):
        return [[str(c) for c in r] for r in self.api("GET", self.rng(tab)).get("values") or []]

    def write(self, tab, rows):
        if tab not in self.tabs():
            self.api("POST", ":batchUpdate", {"requests": [{"addSheet": {"properties": {"title": tab}}}]})
        self.api("POST", self.rng(tab, ":clear"), {})
        self.api("PUT", self.rng(tab, "?valueInputOption=RAW"), {"values": square(rows)})

    def append(self, tab, row, head=None):
        if head and tab not in self.tabs():
            return self.write(tab, [head, row])
        self.api("POST", self.rng(tab, ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"),
                 {"values": square([row])})


WAYS = {w.name: w for w in (LinkWay, ScriptWay, ServiceWay)}
AUTO_ORDER = ["script", "service", "link"]
TABS = {"items": "items", "people": "people", "log": "log"}


def tab_names(rc):
    return dict(TABS, **{k: v for k, v in (rc.get("sheet_tabs") or {}).items() if v})


def open_way(rc, data_dir, http_=None):
    """The way config names (rules.sheet_way), or the first set up; None if none."""
    rc = dict(rc, sheet_tabs=tab_names(rc))
    want = rc.get("sheet_way") or "auto"
    names = AUTO_ORDER if want == "auto" else [want]
    for n in names:
        if n in WAYS:
            w = WAYS[n](rc, data_dir, http_)
            if want != "auto" or w.ready():
                return w
    return None
