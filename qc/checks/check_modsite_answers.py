"""A control that acts says what happened, where the person is standing.

Five faults on the module page, all the same shape and all found by the model
panel on 2026-09-08, then checked against the code before anything was
changed (a sixth finding - that #camSize was dead - was WRONG: CAM SIZE is a
live command with its own table in CamModule.cpp):

  * `changeMyPass` changed the board's password and never logged in again.
    The password ends the session, so Setup stayed open on a DEAD session:
    every card visible, every action behind it refused, nothing saying why.
    `doFirstChange` has re-logged-in since the day that bit us; this one was
    written later and did not.
  * the LIFT buttons - Up, Down, Stop, Home and the stage buttons - threw the
    board's answer away, exactly like the Speaker triangle before A24-27. On a
    board that wants a login they did nothing and said nothing.
  * `setSpeed` returned silently when the box was empty: a button that does
    nothing at all, with no hint that a number is wanted.
  * `savePair` told the person to check "the console below" - and the console
    lives on the Shows-and-files tab, while the pairing card is on Setup. A
    message naming a fix you cannot reach from where you are.
  * the Files folder list offered /music, /moves and /data, but the camera
    saves what it takes to /photos - so no picture the robot took could be
    reached from the page at all.

Read from the page source rather than a browser: each of these is about what
the code does with an answer, and a browser check would need a board that
refuses, a camera and a password change to see the same five things.
"""
import re

import qc as F

AREA = "modsite"
TITLE = "controls on the board page say what happened"


def run(t):
    page = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8",
                                                      errors="replace")

    # ---- the password change must not leave a dead session -------------
    fn = page[page.find("async function changeMyPass("):]
    fn = fn[:fn.find("\nasync function ", 1) if "\nasync function " in fn[1:] else fn.find("\nfunction ", 1)]
    t.contains(fn, "/api/login",
               "changing your own password logs the page back in")
    t.ok("still logged in" in fn or "logged in" in fn,
         "and says so, rather than leaving you to find out",
         "the session dies with the password: silence there means every later "
         "action is refused for a reason nobody can see")
    t.ok("refusal(r)" in fn,
         "a refused change is explained, not printed raw",
         "userStat used to show the board's own ERR line")
    # The login is skipped in ONE case only - through the hub, where the page
    # has no board session of its own to renew. Text alone could not tell that
    # from skipping it always: the first sabotage of this check did exactly
    # that and passed, because the login call still sat further down.
    t.contains(fn, "if(viaHub())",
               "the page only skips the fresh login where there is no session")
    t.ok(fn.find("if(viaHub())") < fn.find("/api/login"),
         "and it decides that BEFORE trying to log in",
         "an unconditional early return leaves the direct case dead again")

    # ---- the lift's buttons ------------------------------------------
    t.ok("onclick=\"liftCmd('UP')\"" in page and "onclick=\"liftCmd('DOWN')\"" in page,
         "the lift's Up and Down go through the answering helper")
    t.contains(page, "liftCmd('GOTO '+i)",
               "and so do the stage buttons it builds")
    lift = page[page.find("async function liftCmd("):]
    lift = lift[:lift.find("\nfunction ", 1)]
    t.contains(lift, "refusal(r)",
               "which puts the refusal on the lift's own status line")

    # ---- a button that needs a number says so --------------------------
    spd = page[page.find("async function setSpeed("):]
    spd = spd[:spd.find("\n}\n") + 3]
    t.contains(spd, "type a speed first",
               "Set with an empty box explains itself instead of doing nothing")

    # ---- messages point at what is on screen ---------------------------
    t.ok("Check the console below" not in page,
         "no message sends a person to a console on another tab",
         "the pairing card is on Setup; the console is on Shows and files")
    pair = page[page.find("async function savePair("):]
    pair = pair[:pair.find("\nasync function ", 1)]
    t.contains(pair, "refusal(r1)",
               "the pairing card says what the board actually answered")

    # ---- the pictures the robot takes are reachable ---------------------
    t.contains(page, "<option>/photos</option>",
               "the Files card offers the folder the camera saves into")
    t.ok(re.search(r"/photos", (F.FIRMWARE / "src/modules/cam/CamModule.cpp")
                   .read_text(encoding="utf-8", errors="replace")),
         "which is still where the camera really saves",
         "if the firmware moves it, this list has to move with it")
