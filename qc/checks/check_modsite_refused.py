"""A refused command SAYS so, and names the gate that refused it.

The user pressed the Speaker triangle on the module page and nothing happened
(2026-09-07). The board had answered `401 ERR log in first` and the page threw
the answer into the technical log, so the button looked broken. The same hole
was under every button on that page.

Worse, the page could blame the wrong thing. Opened through the hub, a command
goes out over `/api/dev/cmd`, which the HUB gates: with no hub session it
answers `{"need_login": true}`, and the login form printed *wrong user or
password* for it. The user's password was right and had never reached the
board - they were sent to change a password that was fine, twice.

So the page holds one function that reads an answer and says who said no:

  * the BOARD refusing (`ERR log in first`) points at Setup login on this page,
    which is the way in when no hub is running at all (A24-29);
  * the HUB refusing points at the hub's own login, and says the board can be
    opened directly instead;
  * anything else that comes back ERR is shown as it is, rather than hidden;
  * and a correct login that lands on the shipped-password box now says the
    login WORKED - a red box on its own reads as a rejection.
"""
import re

import qc as F

AREA = "modsite"
TITLE = "a refused command says who refused it, and what to do"


def run(t):
    page = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8",
                                                      errors="replace")

    # ---- one place that knows what an answer means --------------------
    t.contains(page, "function refusal(", "the page has one reader for refusals")
    fn = page[page.find("function refusal("):]
    fn = fn[:fn.find("\nasync function cmd(")]
    t.contains(fn, "need_login",
               "it knows the HUB's refusal, which never reaches the board")
    t.contains(fn, "log in first",
               "and the BOARD's own, which the Setup login on this page fixes")
    t.ok("hub page" in fn and "Setup login" in fn,
         "each one points at the login that would actually help",
         "the two gates need different actions from the person: sending them "
         "to the wrong one is how a right password gets changed")

    # ---- the speaker button uses it -----------------------------------
    play = page[page.find("async function playSel("):]
    play = play[:play.find("\nfunction ", 1)]
    t.contains(play, "sayRefusal('nowPlaying'",
               "the Speaker triangle says why nothing played")
    t.contains(play, "choose a track first",
               "and says what to do when no track is picked at all")

    # ---- the login no longer blames the password for a hub refusal ----
    login = page[page.find("async function doLogin"):]
    login = login[:login.find("function doLogout")]
    t.ok(re.search(r"refusal\(r\)\s*\|\|\s*'wrong user or password'", login),
         "a refusal from the hub is not reported as a wrong password",
         "the hub answers before the board ever sees the password")
    t.contains(login, "logged in as ",
               "and a correct login says so even when a password change is "
               "still needed")
    box = page[page.find('id="mustChangeBox"'):]
    box = box[:box.find("</div>")]
    t.contains(box, "You are logged in",
               "the shipped-password box opens by saying the login worked")
