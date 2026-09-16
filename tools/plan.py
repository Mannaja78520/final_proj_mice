#!/usr/bin/env python3
"""Move a task, or say what is running. One command, so it actually gets done.

    python tools/plan.py doing A2-1 A3-1        picked up, stamped with the clock
    python tools/plan.py qc A2-1                built, waiting on the gate
    python tools/plan.py done A2-1              landed
    python tools/plan.py running full QC for the batch
    python tools/plan.py running --clear        nothing in flight
    python tools/plan.py note A2-1 what changed and why
    python tools/plan.py show                   what the page says right now

WHY THIS EXISTS
---------------
docs/PLAN.html is the only record of progress, and the page in front of the
user renders from it. When updating it meant hand-editing HTML, it got updated
at milestones — so the page said *nothing in progress* for forty minutes while
a suite ran, and the user could not tell working from stalled. The fix is not
more discipline, it is making the update cost one line.

THE TIMESTAMP COMES FROM THE CLOCK, NEVER FROM MEMORY. Stamps written by hand
drifted by up to five hours in one session and two of them were in the future,
which makes the whole page untrustworthy.

The plan lives ONLY in the real tree — it is in promote.py's SKIP_FILES,
because it records progress and a staging copy is stale the moment it is made.
This finds it whether it is run from the real tree or from a staging copy.
"""
import argparse
import os
import re
import sys
import time

from pathlib import Path

# THAI, OR ANY OTHER LANGUAGE, MUST NOT KILL A TOOL. Windows hands python a
# cp1252 console here, which cannot encode Thai at all: printing one Thai word
# raised UnicodeEncodeError and the command died after it had already changed
# the file. Measured 2026-08-22. UTF-8 out, and never crash on a character.
for _out in (sys.stdout, sys.stderr):
    try:
        _out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass        # a check that IMPORTS this tool has replaced stdout
                    # with a StringIO, which has no reconfigure at all

STATUSES = ("todo", "doing", "qc", "done", "blocked")
# What a task id looks like. The trailing letter is not decoration: A9-3b is
# the half of A9-3 that needs no hardware, and while the pattern ended at the
# digit that task was set to `doing` without complaint and then left out of
# every count and out of the page - work in progress that the page said did
# not exist. The same pattern is in PLAN.html's renderer.
ID = r"^[A-Z]\d+-\d+[a-z]?"


# The pages this tool can drive. A third one is one line here.
#   robot   docs/PLAN.html            the rig's own work, A1-A25
#   system  docs/system_integral.html joining Mice to programs outside it
PAGES = {"robot": "PLAN.html", "system": "system_integral.html"}


def plan_path(page="robot"):
    """The ONE plan, always in the real tree.

    Climbing out of `.staging` is not a nicety: a copy in there is a day old
    the moment it is written and nothing ever reads it back, so a session that
    updated it would look like it was recording progress and be recording
    nothing.

    MICE_PLAN overrides it, and exists for one reason: the QC check drives this
    tool for real, and a check that writes to the actual plan would stamp its
    own name over whatever is running while it does.
    """
    import os
    override = os.environ.get("MICE_PLAN")
    if override:
        return Path(override)
    here = Path(__file__).resolve().parent.parent
    if here.name.startswith(".staging"):
        here = here.parent
    return here / "docs" / PAGES.get(page, PAGES["robot"])


def pages_with(tid):
    """Which pages already carry this task id. Empty when the id is new.

    Two pages that resolve to the SAME file are one page, not two - MICE_PLAN
    points every page at one temporary file, and without this the QC check
    that drives this tool for real would look ambiguous to itself.
    """
    found, seen = [], set()
    for name in sorted(PAGES):
        path = plan_path(name)
        key = str(path).lower()
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        if re.search(r"^%s:\s" % re.escape(tid),
                     path.read_text(encoding="utf-8"), re.M):
            found.append(name)
    return found


def resolve_page(page, ids, action=""):
    """Which page an edit belongs to when --page was not given.

    Both plans number their tasks from A1, so `A1-1` is a real task on BOTH:
    the board's auth gate on the robot plan, and the Reconize tile on the
    integration plan. A stamp landing on the wrong one is INVISIBLE - the page
    being watched simply never changes, and the work looks stalled. So an id
    carried by more than one page is refused until --page says which.

    An id that only ONE page has needs no flag: there is nothing to confuse.
    """
    if page:
        return page
    where = {}
    for tid in ids:
        for name in pages_with(tid):
            where.setdefault(name, []).append(tid)
    if len(where) > 1:
        raise SystemExit(
            "these ids are on more than one plan, so a stamp could land on the "
            "wrong page and nobody would see it:\n"
            + "\n".join("  %-7s has %s" % (name, ", ".join(tids))
                        for name, tids in sorted(where.items()))
            + "\nSay which page you mean - one of these:\n"
            + "\n".join("  python tools/plan.py --page %s %s %s"
                        % (name, action, " ".join(ids))
                        for name in sorted(where)))
    if len(where) == 1:
        return next(iter(where))
    return "robot"


def now():
    return time.strftime("%Y-%m-%d %H:%M")


def _atomic(path, text):
    """Write a file whole, or not at all.

    A reader that catches a half-written file sees nonsense, and nothing in the
    error says so. Both the page and the published state are written this way
    because QC now updates them while it runs.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(str(tmp), str(path))


class Plan:
    """The STATE block, edited in place."""

    def __init__(self, path=None, page="robot"):
        self.path = path or plan_path(page)
        self.text = self.path.read_text(encoding="utf-8")

    def save(self):
        # Written whole, then moved into place. Since 2026-08-20 the QC runner
        # reports its progress here WHILE it runs, so something else may be
        # reading this file at the moment it is written - and a reader that
        # catches a half-written page sees a broken plan, which looked like a
        # failing check rather than a torn read. os.replace is atomic on
        # Windows and POSIX alike.
        _atomic(self.path, self.text)
        self.publish()

    def state_file(self):
        """The state script beside THIS page.

        PLAN.html keeps `plan_state.js` because that is the name its renderer
        loads; any other page gets `<name>_state.js`. One file per page: the
        integration page and the robot page would otherwise overwrite each
        other's progress, which is the whole reason they are two pages.
        """
        if self.path.name == "PLAN.html":
            return self.path.parent / "plan_state.js"
        return self.path.with_name(self.path.stem + "_state.js")

    def publish(self):
        """Write the STATE block beside the page, as a script it can load.

        The page has to update while it is open, with nothing to press - asked
        for 2026-08-19. It is opened from file:///E:/..., and a file:// page may
        not fetch() or XHR a file next to it: the browser gives it a null origin
        and blocks the read. It MAY load a script. So the state is published as
        one, the page pulls it in on a timer, and redraws itself when the stamp
        moves.

        Never required: if this fails, the page still shows the STATE block
        inside it, which is what it did before any of this existed.
        """
        import json
        import time as _t
        block = self.text
        i = block.find("<pre id=" + chr(34) + "state" + chr(34) + ">")
        if i < 0:
            return
        i = block.index(">", block.index("<code", i)) + 1
        j = block.find("</code>", i)
        raw = block[i:j]
        # The page reads this back into a <pre>, so the HTML entities the file
        # stores have to come back as the characters they stand for.
        for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                        ("&quot;", chr(34)), ("&#39;", "'")):
            raw = raw.replace(ent, ch)
        out = {"stamp": _t.strftime("%Y-%m-%d %H:%M:%S"), "raw": raw}
        try:
            _atomic(self.state_file(),
                    "window.PLAN_STATE=" + json.dumps(out) + ";" + chr(10))
        except OSError:
            pass                      # a convenience, never a requirement

    def set_status(self, tid, status, stamp=True):
        """Rewrite one task's status and timestamp, keeping everything else."""
        # Trailing spaces only, never \s: \s eats the NEWLINE after a bare task
        # line (no em-dash note), and the rewrite glues the next line onto this
        # one - the id below vanished from the block and later edits to it
        # silently did nothing.
        pat = re.compile(r"^(%s):\s+(%s)(\s+\d{4}-\d\d-\d\d(?: \d\d:\d\d)?)?([ \t]*)"
                         % (re.escape(tid), "|".join(STATUSES)), re.M)
        when = ("  " + now()) if stamp else ""
        new, n = pat.subn(lambda m: "%s: %-5s%s  " % (m.group(1), status, when), self.text)
        if not n:
            raise SystemExit("no task %s in %s" % (tid, self.path.name))
        self.text = new
        return True

    def set_running(self, what):
        line = "# RUNNING: " + (what or "nothing right now")
        if what:
            line += ", started " + now()
        new, n = re.subn(r"^# RUNNING: .*$", line, self.text, count=1, flags=re.M)
        if not n:                                  # first use: put it at the top
            new = self.text.replace("<code>STATE\n", "<code>STATE\n" + line + "\n", 1)
        self.text = new

    def append_note(self, tid, note):
        # Anything may sit between the status and the em dash — a timestamp,
        # and annotations like touches= and needs=. Match up to the dash rather
        # than trying to spell out what is allowed in front of it.
        # Anything may sit between the status and the dash: a timestamp,
        # and annotations like touches= and needs=. Match up to the dash
        # rather than trying to spell out what is allowed in front of it.
        # The dash is written as an escape — a literal one has been mangled
        # by a shell more than once in this project.
        pat = re.compile("^(" + re.escape(tid) + "[^\u2014\n]*\u2014.*)$", re.M)
        new, n = pat.subn(lambda m: m.group(1) + " " + note, self.text, count=1)
        if not n:
            raise SystemExit("no task %s" % tid)
        self.text = new

    # ---- who owns a task: provider AND session ---------------------------
    # Asked 2026-09-16: *make sure every agent save task to plan so we can
    # track each agent* and *the same agent provider but in different session*.
    # So the owner is `agent=claude:5a33`, never `claude` alone, written on the
    # task line like hw=.
    def owner(self, tid):
        m = re.search("^" + re.escape(tid) + r":[^—\n]*?\bagent=(\S+)", self.text, re.M)
        return m.group(1) if m else ""

    def silent_min(self, tid):
        """Minutes since this task's owner last stamped it, or None.

        A session cut off by its limit cannot hand off - it simply stops
        (user 2026-09-16: *is he know he hit limit?*). So an owner that has
        not stamped its task for SILENT_MIN is shown as probably stopped.
        Working sessions re-run `doing <id>` at each step, which re-stamps."""
        m = re.search("^" + re.escape(tid) + r":\s+\w+\s+(\d{4}-\d\d-\d\d \d\d:\d\d)",
                      self.text, re.M)
        if not m:
            return None
        try:
            then = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
        except ValueError:
            return None
        return int((time.time() - then) // 60)

    def status_of(self, tid):
        m = re.search("^" + re.escape(tid) + r":\s+(\w+)", self.text, re.M)
        return m.group(1) if m else ""

    def set_owner(self, tid, agent):
        line = re.compile("^(" + re.escape(tid) + r":[^—\n]*?)(\s*\bagent=\S+)?(\s*—)", re.M)
        new, n = line.subn(lambda m: m.group(1).rstrip() + "  agent=" + agent + "  " +
                           m.group(3).lstrip(), self.text, count=1)
        if not n:
            # a line with no em-dash note: the owner goes on the end
            bare = re.compile("^(" + re.escape(tid) + r":[^\n]*?)(\s+agent=\S+)?[ \t]*$", re.M)
            new, n = bare.subn(lambda m: m.group(1) + "  agent=" + agent, self.text, count=1)
        if not n:
            raise SystemExit("no task %s" % tid)
        self.text = new

    def add(self, tid, status, note, before=None, hw=None):
        """Put a NEW task into the STATE block, published like every other edit.

        Added 2026-08-20 after the user asked why the page had not changed. It
        had not, and the page was innocent: new tasks were being written into
        PLAN.html by hand, and `plan_state.js` - the file the open page pulls
        every four seconds - is only rewritten when this tool runs. So the page
        sat on the last published state until the next status change happened
        to republish it, which could be many minutes.

        Editing the page by hand is now never necessary, which is the only
        reliable way to stop it happening.
        """
        if status not in STATUSES:
            raise SystemExit("status must be one of: %s" % ", ".join(STATUSES))
        if re.search("^" + re.escape(tid) + ":", self.text, re.M):
            raise SystemExit("%s already exists" % tid)
        # hw= goes on the line itself, so the one place a task is
        # recorded is also the place that says whether a PC can finish
        # it. check_packing_list keeps it and the packing table honest.
        tag = ("  hw=%s" % hw) if hw else ""
        line = "%s: %-5s %s%s  — %s" % (tid, status, now(), tag, note)
        anchor = None
        if before:
            anchor = re.search("^" + re.escape(before) + ":", self.text, re.M)
            if not anchor:
                raise SystemExit("no task %s to put it before" % before)
        if anchor:
            at = anchor.start()
        else:
            # After the LAST task line, so a new id lands with its own area
            # rather than at the top of the block.
            ends = [m.end() for m in re.finditer(ID + r":.*$", self.text, re.M)]
            if not ends:
                raise SystemExit("no STATE block to add to")
            at = ends[-1] + 1
        self.text = self.text[:at] + line + chr(10) + self.text[at:]

    def summary(self):
        rows = re.findall("^(" + ID[1:] + r"):\s+(\w+)", self.text, re.M)
        counts = {s: sum(1 for _, x in rows if x == s) for s in STATUSES}
        run = re.search(r"^# RUNNING: (.*)$", self.text, re.M)
        def tag(tid):
            who = self.owner(tid)
            if not who:
                return tid
            quiet = self.silent_min(tid)
            if who != "open" and quiet is not None and quiet >= SILENT_MIN:
                return "%s(%s, SILENT %dm - stopped?)" % (tid, who, quiet)
            return "%s(%s)" % (tid, who)
        live = [tag(tid) for tid, s in rows if s in ("doing", "qc")]
        return counts, (run.group(1) if run else "(no RUNNING line)"), live


AGENT = re.compile(r"^[a-z][a-z0-9-]*:[A-Za-z0-9._-]+$")
# An owner that has not re-stamped its task for this long is shown as
# probably stopped (limit hit, crash, closed window). MICE_SILENT_MIN overrides.
SILENT_MIN = int(os.environ.get("MICE_SILENT_MIN") or 45)


def agent_of(given):
    """provider:session from --agent or MICE_AGENT. Refuses a bare provider:
    two sessions of one provider must never look like one owner."""
    who = (given or os.environ.get("MICE_AGENT") or "").strip()
    if not who:
        raise SystemExit(
            "who is doing this? pass --agent provider:session (or set MICE_AGENT).\n"
            "No session name yet? run:  python tools/plan.py session <provider>")
    if not AGENT.match(who):
        raise SystemExit("%r is not provider:session - e.g. claude:5a33, "
                         "codex:2241-k7. A provider alone is refused." % who)
    return who


def new_session(provider):
    import secrets
    return "%s:%s-%s" % (provider.lower(), time.strftime("%m%d%H%M"), secrets.token_hex(2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default=None, choices=sorted(PAGES),
                    help="which plan page: robot (the rig) or system "
                         "(joining Mice to outside programs). Left off, the "
                         "page is worked out from the task id - and an id "
                         "both pages have is refused rather than guessed")
    ap.add_argument("action",
                    help="one of: %s, running, note, add, publish, show"
                         % ", ".join(STATUSES))
    ap.add_argument("rest", nargs="*", help="task ids, or the text for running/note/add")
    ap.add_argument("--clear", action="store_true", help="running: nothing in flight")
    ap.add_argument("--status", default="todo", help="add: status of the new task")
    ap.add_argument("--before", help="add: put it in front of this task id")
    ap.add_argument("--agent", help="provider:session that owns this step, e.g. "
                    "claude:5a33 (or set MICE_AGENT). Required for add, doing, qc "
                    "and handoff")
    ap.add_argument("--take", action="store_true",
                    help="doing: take a task another session still owns - only "
                         "when that session stopped (limit hit) and left no handoff")
    ap.add_argument("--hw", help="add: what hardware it needs, e.g. '2 boards + RS485'. Leave it off for a task a PC alone can finish - the field is what makes a task skippable "
                    "when the boards are not on the bench, and what puts the part on the packing list.")
    a = ap.parse_args(argv)

    # Which ids this action touches, so the page can be worked out from them.
    # `add` is left out on purpose: its id does not exist yet anywhere.
    if a.action == "session":
        # No plan write: just a name this session reuses for every step.
        print(new_session(a.rest[0] if a.rest else "agent"))
        return 0

    ids = []
    if a.action in STATUSES:
        ids = list(a.rest)
    elif a.action in ("note", "handoff") and a.rest:
        ids = [a.rest[0]]
    p = Plan(page=resolve_page(a.page, ids, a.action))
    if a.action == "publish":
        # For the one case hand-editing is unavoidable: republish so the open
        # page sees it within four seconds instead of at the next status change.
        p.publish()
        print("published - the open page will pick it up")
        return 0

    if a.action == "show":
        counts, run, live = p.summary()
        print(" | ".join("%d %s" % (v, k) for k, v in counts.items() if v))
        print("RUNNING:", run)
        print("in flight:", ", ".join(live) or "nothing")
        return 0

    if a.action == "running":
        p.set_running("" if a.clear else " ".join(a.rest))
    elif a.action == "note":
        p.append_note(a.rest[0], " ".join(a.rest[1:]))
    elif a.action == "add":
        if len(a.rest) < 2:
            raise SystemExit("add: need a task id and what it is")
        # A STATUS ON ITS OWN, WITH THE NOTE AFTER IT, IS A MISTYPED --status.
        # `add A24-19 doing "..."` filed the word "doing" as the first word of
        # the NOTE and left the task `todo` while it was being worked, so the
        # page said nothing was in flight - the one thing it exists to show.
        # Caught by the user 2026-08-28, after it had happened silently once.
        # Tested on the ARGUMENT, not the joined note: "qc self-test" as one
        # quoted note is ordinary text and must still be allowed.
        if len(a.rest) > 2 and a.rest[1].lower() in STATUSES:
            raise SystemExit(
                "%r is a status, not what the task IS.\n"
                "Did you mean:  plan.py add %s \"<what it is>\" --status %s\n"
                "(the flag goes AFTER the note - argparse eats it otherwise)"
                % (a.rest[1], a.rest[0], a.rest[1].lower()))
        who = agent_of(a.agent)
        p.add(a.rest[0], a.status, " ".join(a.rest[1:]), a.before, a.hw)
        p.set_owner(a.rest[0], who)
    elif a.action == "handoff":
        # HANDOFF (user 2026-09-16: *all agent can hand off ... for the hit
        # limit one*): back to todo with the next step written on it, so ANY
        # agent or session can pick it up with `doing`.
        if len(a.rest) < 2:
            raise SystemExit("handoff: need a task id and the next step")
        who = agent_of(a.agent)
        tid = a.rest[0]
        p.set_status(tid, "todo")
        p.append_note(tid, "HANDOFF from %s %s: %s" % (who, now(), " ".join(a.rest[1:])))
        p.set_owner(tid, "open")
    elif a.action in STATUSES:
        who = agent_of(a.agent) if a.action in ("doing", "qc") else \
            (a.agent or os.environ.get("MICE_AGENT") or "")
        for tid in a.rest:
            held = p.owner(tid)
            if (a.action == "doing" and p.status_of(tid) in ("doing", "qc")
                    and held not in ("", "open", who) and not a.take):
                quiet = p.silent_min(tid)
                hint = ("it has been SILENT %d min - probably stopped (limit?); "
                        "write why in BRIDGE, then run again with --take" % quiet
                        if quiet is not None and quiet >= SILENT_MIN else
                        "it is active - ask it in BRIDGE to hand off")
                raise SystemExit("%s is %s by %s: %s."
                                 % (tid, p.status_of(tid), held, hint))
            p.set_status(tid, a.action)
            if who:
                p.set_owner(tid, who)
    else:
        raise SystemExit("unknown action: %s" % a.action)

    p.save()
    counts, run, live = p.summary()
    print("plan updated - in flight: %s | %s" % (", ".join(live) or "nothing", run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
