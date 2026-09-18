"""Firmware accounts: roles, hashed passwords in NVS, self-management, and super_admin controls.

Asked for in A0-27b: mirror the hub's account and role system in firmware.
UserStore keeps salted SHA-256 password hashes and roles in NVS.
Super_admin manages all accounts (add, remove, rename, reset password);
ordinary users can rename themselves and change their own password.
The last super_admin is protected against deletion or demotion.
"""
import json
import re
import sys
from pathlib import Path

import qc as F

AREA = "auth"
TITLE = "firmware accounts have roles, hashed passwords in NVS, and super_admin protection"
SLOW = False

sys.path.insert(0, str(F.CODE / "tools"))


def run(t):
    from registry import strip_jsonc

    store_h = (F.FIRMWARE / "src/core/UserStore.h").read_text(encoding="utf-8", errors="replace")
    store_c = (F.FIRMWARE / "src/core/UserStore.cpp").read_text(encoding="utf-8", errors="replace")
    router_c = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    portal_c = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    portal_h = (F.FIRMWARE / "src/core/WebPortal.h").read_text(encoding="utf-8", errors="replace")
    web_h = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    cmds_txt = strip_jsonc((F.FIRMWARE / "config/commands.json").read_text(encoding="utf-8", errors="replace"))
    cmds = json.loads(cmds_txt)["commands"]

    # ---- 1. Passwords in NVS are hashed with salt, not plain text ----
    t.contains(store_c, "hashPassword", "UserStore computes password hashes")
    t.contains(store_c, "genSalt", "passwords are salted before hashing")
    t.contains(store_c, "MBEDTLS_MD_SHA256", "hashing uses SHA-256 via mbedtls")
    t.contains(store_c, "constantTimeEquals", "password verification uses constant-time comparison")

    # In add(), setPass(), and begin() seeds, passwords must be saved as hash and salt
    add_fn = store_c[store_c.find("bool UserStore::add"):]
    add_fn = add_fn[:add_fn.find("\n}") + 2] if "\n}" in add_fn else add_fn[:600]
    t.ok('u["salt"] = s;' in add_fn and 'u["hash"] = h;' in add_fn,
         "add() stores salt and hash, never plain password in NVS")
    t.ok('users_[user] = pass;' not in add_fn,
         "plain password is never assigned directly in add()")

    setp_fn = store_c[store_c.find("bool UserStore::setPass"):]
    setp_fn = setp_fn[:setp_fn.find("\n}") + 2] if "\n}" in setp_fn else setp_fn[:600]
    t.ok('u["hash"] = h;' in setp_fn and 'u["salt"] = s;' in setp_fn,
         "setPass() updates salt and hash")

    # ---- 2. Roles: super_admin and user, with last super_admin protection ----
    t.contains(store_h, "ROLE_SUPER", "UserStore defines super_admin role")
    t.contains(store_h, "ROLE_USER", "UserStore defines user role")
    t.contains(store_h, "isSuper", "UserStore can check if a user is super_admin")
    t.contains(store_h, "countSupers", "UserStore counts active super_admins")

    rem_fn = store_c[store_c.find("bool UserStore::remove"):]
    rem_fn = rem_fn[:rem_fn.find("\n}") + 2] if "\n}" in rem_fn else rem_fn[:600]
    t.ok("isSuper(user) && countSupers() <= 1" in rem_fn,
         "remove() protects the last super_admin from being deleted")

    # ---- 3. CommandRouter commands: USER subcommands and role guards ----
    user_cmd = [c for c in cmds if c["name"] == "USER"]
    t.ok(user_cmd, "USER command exists in commands.json")
    if user_cmd:
        t.ok("RENAME" in user_cmd[0].get("args", ""),
             "USER command args document RENAME")
        t.ok("super_admin" in user_cmd[0].get("help", ""),
             "USER command help documents role support")

    cmd_user = router_c[router_c.find('if (cmd == "USER")'):]
    cmd_user = cmd_user[:cmd_user.find('if (cmd == "PIN"')] or cmd_user[:2000]

    t.contains(cmd_user, "callerIsSuper", "CommandRouter checks whether caller is super_admin")
    t.ok('if (!callerIsSuper) return "ERR only super_admin can add accounts";' in cmd_user,
         "only super_admin can run USER ADD")
    t.ok('if (!callerIsSuper) return "ERR only super_admin can remove accounts";' in cmd_user,
         "only super_admin can run USER DEL")
    t.ok('isSuper(target) && users.countSupers() <= 1' in cmd_user,
         "USER DEL refuses to remove the last super_admin")
    t.ok('target != caller && !callerIsSuper' in cmd_user,
         "only super_admin can modify someone else's password or username")
    t.contains(cmd_user, 'sub == "RENAME"', "USER command supports RENAME")

    # ---- 4. WebPortal sessions & whoami reporting roles ----
    t.contains(portal_h, "char user[21]", "WebPortal Session tracks authenticated user")
    t.contains(portal_c, "users.role(user)", "/api/login returns user role")
    t.contains(portal_c, "users.role(u)", "/api/whoami returns user role")

    # ---- 5. Module site (WebUI.h) Accounts UI ----
    t.contains(web_h, 'id="usersBox"', "WebUI has accounts card")
    t.contains(web_h, 'id="addUserRow"', "WebUI has add user controls")
    t.contains(web_h, 'id="nuRole"', "WebUI allows selecting user role when adding")
    t.contains(web_h, 'id="rnUser"', "WebUI provides self-rename control")
    t.contains(web_h, 'tech', "WebUI shows technical details behind .tech switch")
