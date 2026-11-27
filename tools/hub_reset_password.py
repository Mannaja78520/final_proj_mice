"""Reset the hub's factory logins on THIS PC (the double-click "Reset Hub Password").

Forgot the hub password and lost the recovery code? Run this on the PC the hub
runs on. It puts the shipped accounts (admin and super_admin) back on the
shipped password from main_python/hub_login.default.json and asks for a new one
at the next login. Accounts people added keep their own passwords.

WHY THIS IS SAFE FROM THE NETWORK: there is no hub route for it. It edits the
local hub_auth.json file directly, so only someone who can already run programs
on the hub PC can use it. A running hub notices the change by itself the next
time a login fails (Auth._resync), so no restart is needed.

  python tools/hub_reset_password.py            ask first, then reset
  python tools/hub_reset_password.py --yes      no question (for scripts)
  python tools/hub_reset_password.py --store X  reset one named store file only
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "main_python"))

import hub_auth  # noqa: E402


def stores(explicit=None):
    """Every hub_auth.json this checkout could be using (the exe's and the source's)."""
    if explicit:
        return [Path(explicit)]
    found = []
    env = os.environ.get("MICE_HUB_AUTH")
    for p in ([Path(env)] if env else []) + [ROOT / "dist" / hub_auth.DEFAULT_STORE_NAME,
                                             ROOT / "main_python" / hub_auth.DEFAULT_STORE_NAME]:
        if p.is_file() and p not in found:
            found.append(p)
    return found


def reset(store, out=print):
    """Reset one store -> the account names put back."""
    auth = hub_auth.Auth(store, out=lambda *a: None)
    names = auth.reset_to_factory()
    out("  %s: %s are back on the shipped password" % (Path(store).parent.name or store, ", ".join(names)))
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true", help="do not ask first")
    ap.add_argument("--store", help="reset only this hub_auth.json")
    args = ap.parse_args(argv)
    found = stores(args.store)
    print()
    if not found:
        print("  No hub login file was found on this PC, so there is nothing to reset.")
        print("  A hub that starts fresh already uses the shipped login: %s / %s"
              % (" or ".join(n for n, _ in hub_auth.FACTORY_ACCOUNTS), hub_auth.DEFAULT_PASSWORD))
        return 0
    print("  This puts the hub logins %s back on the shipped password (%s)."
          % (" and ".join(n for n, _ in hub_auth.FACTORY_ACCOUNTS), hub_auth.DEFAULT_PASSWORD))
    print("  Other accounts keep their own passwords. The hub asks for a new password at the next login.")
    if not args.yes:
        if input("  Type YES to reset: ").strip().upper() != "YES":
            print("  Nothing was changed.")
            return 1
    for store in found:
        reset(store)
    print()
    print("  Done. Open the hub and log in with %s / %s, then choose a new password."
          % (hub_auth.DEFAULT_USER, hub_auth.DEFAULT_PASSWORD))
    print("  The hub does not need to be restarted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
