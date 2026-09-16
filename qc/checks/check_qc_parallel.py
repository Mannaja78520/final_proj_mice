"""The suite runs on every core, and the things that cannot share, do not.

Asked for on 2026-08-20: *make it faster ... it will make all of my process
faster than before*. The suite took 836 seconds on one core of a 24-thread
machine. It now runs the checks in a process pool - 292 seconds for the same
2235 assertions - and process isolation is what makes that safe: a worker gets
its own `fake_serial`, its own `qc_marks` and its own hub.

What is NOT safe is anything the MACHINE has only one of, and this file is the
list. Every item on it was found by the five-model panel before a line was
written, and then confirmed in the code:

  * `_qcdriver.html` was written into the shared studio folder under a fixed
    name, so two workers would each load the OTHER's test - which does not
    fail, it passes the wrong test;
  * the hub port came from `8700 + (os.getpid() % 40) * 25`. Windows hands out
    pids in multiples of four, so that expression has ten possible values, and
    a collision means one worker's hub answers another worker's request;
  * `gen_tables.py` ran on first use in every process, all writing the same
    generated files;
  * port 80, mDNS 5353 and the firmware build directory are single-occupancy
    by nature.

A check that asserted the speed itself would be a check that fails on a slower
laptop. What is held here is the SAFETY, which is what makes the speed real.
"""
import re

import qc as F

AREA = "tools"
TITLE = "the suite runs in parallel, and single-occupancy checks stay alone"


def run(t):
    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")

    t.contains(src, "ProcessPoolExecutor",
               "checks run in separate processes, not threads")
    t.ok("--serial" in src and "--jobs" in src,
         "and it can be forced back to one at a time",
         "a parallel-only runner cannot be used to prove that a failure is "
         "real rather than a race")

    # ---- the single-occupancy list ----------------------------------
    m = re.search(r"SOLO = \{(.*?)\}", src, re.S)
    if not t.ok(m, "there is a list of checks that must run alone"):
        return
    solo = m.group(1)
    for name, why in (("check_short_name", "binds port 80"),
                      ("check_name_claim", "answers mDNS on 5353"),
                      ("check_mdns", "answers mDNS on 5353"),
                      ("check_build_split", "writes the firmware build dir"),
                      ("check_hub_clock", "measures time, which needs a quiet "
                                          "machine"),
                      ("check_themes", "rewrites the stylesheet every page "
                                       "is served"),
                      ("check_tools_list", "breaks an app.json on purpose to "
                                           "prove broken is not empty"),
                      ("check_studio_playback", "drives a browser on fixed "
                                                "timers and asserts the order")):
        t.ok(name in solo, "%s runs alone - it %s" % (name, why),
             "two of these at once fight over something the machine has one of")

    # ---- and the hazards the panel found are really fixed ------------
    qc_py = (F.QC / "lib" / "qc.py").read_text(encoding="utf-8")
    # The ASSIGNMENT, not the file: the fix's own comment quotes the old
    # expression to explain what was wrong with it, and the first version of
    # this assertion matched that comment and failed on the fix.
    t.ok("_hub_port = [_free_port()]" in qc_py
         and "_hub_port = [8700" not in qc_py,
         "hub ports are not derived from the process id",
         "Windows pids are multiples of 4, so pid %% 40 has ten values and "
         "workers collide - and a collision tests the wrong hub silently")
    t.contains(qc_py, "def _free_port",
               "they are asked of the operating system instead")

    br = (F.QC / "lib" / "browser.py").read_text(encoding="utf-8")
    t.contains(br, "def _tag",
               "browser scratch files carry a per-process suffix")
    t.ok('web / "_qcdriver.html"' not in br,
         "the driver page is never written under one shared name",
         "two workers would each load the other's test page")
    t.contains(br, 'query.replace("_qcdriver.html"',
               "and the URL follows the real file, so checks need not know")

    # The checks that write their OWN scratch page into the shared studio
    # folder, rather than going through browser.page(). Raised by the panel:
    # two of them used fixed names, so in a pool one worker could load the
    # other's page - which does not fail, it tests the wrong thing.
    import re as _re2  # noqa: PLC0415
    for f in sorted((F.QC / "checks").glob("check_*.py")):
        if f.name == "check_qc_parallel.py":
            continue          # this file QUOTES the pattern it looks for
        txt = f.read_text(encoding="utf-8")
        for m in _re2.finditer(r'web / \("?(_qc[a-z]*)', txt):
            after = txt[m.start():m.start() + 120]
            t.ok("_tag()" in after,
                 "%s names its scratch page per process" % f.stem,
                 "a fixed name in a shared folder means two workers overwrite "
                 "each other: %s" % after.splitlines()[0].strip())
        for m in _re2.finditer(r'web / "(_qc[a-z]*\.html)"', txt):
            t.ok(False, "%s names its scratch page per process" % f.stem,
                 "it writes %s, a fixed name in a folder every worker shares"
                 % m.group(1))
    t.ok("getpid" in br,
         "the suffix uses the pid, not only a timestamp",
         "workers start in the same millisecond; the pid is what differs")

    # ---- a browser is not a core ------------------------------------
    # Ten workers each starting Edge saturates the machine, and every check
    # that waits on a page then slips its deadline. Two different browser
    # checks failed in parallel gates on 2026-08-20 and passed alone every
    # time. Throttling the whole suite would have given the speed back for
    # nothing, since most checks never open a browser.
    t.contains(src, "def needs_browser",
               "browser checks are told apart from the rest")
    t.contains(src, "browser_jobs",
               "and run in a narrower lane of their own")
    m2 = re.search(r"browser_jobs = max\(1, min\((\d+), jobs\)\)", src)
    if t.ok(m2, "the lane has a width"):
        t.ok(int(m2.group(1)) <= 3,
             "and it is narrow (%s at most)" % m2.group(1),
             "the point is fewer browsers at once, not fewer workers")

    t.contains(src, "F.generated()",
               "the firmware tables are generated once, before any worker")

    # ---- the plan page is told what is happening ---------------------
    # Asked for the same day: a gate that runs for minutes while the page says
    # nothing cannot be told from a gate that died.
    t.contains(src, "def _plan",
               "the runner reports progress to the plan page")
    i = src.find("def _plan")
    t.ok("except" in src[i:i + 900],
         "and a plan it cannot write never fails the run",
         "the plan is a convenience; QC is the gate")

    # ---- a port the OS offered can still refuse to bind -----------------
    # _free_port() closes the socket before the hub binds it again. In that gap
    # Windows can give the same number to another worker, or fold it into a
    # reserved range: the hub thread dies on bind and every request answers
    # "connection refused" six seconds later, which reads as a broken check
    # rather than a busy machine. Two full gates were lost that way on
    # 2026-09-08 (check_responsive: WinError 10061, check_themes: 10013).
    lib = (F.QC / "lib" / "qc.py").read_text(encoding="utf-8", errors="replace")
    start = lib[lib.find("def start_hub("):]
    start = start[:start.find("\ndef ", 1)]
    # The WAITING loop must notice, not only the code after it: waiting out the
    # full six seconds on a thread that is already dead is the whole cost.
    t.contains(start, "if not th.is_alive():",
               "start_hub stops waiting the moment the hub thread is gone")
    t.ok(start.count("_free_port()") >= 1 and "for attempt in range" in start,
         "and tries again on a fresh port instead of failing the check",
         "a retry here costs a second; a red gate costs eleven minutes and "
         "sends the next half hour into code that was never wrong")
    t.contains(start, "could not listen on any port",
               "and says so plainly when no port can be had at all")

    # ---- and a port that must stay EMPTY is held, not merely offered ----
    # The opposite need: some checks want an address where nothing answers, to
    # prove a tool refuses instead of inventing numbers. _free_port() cannot
    # give that - it closes the socket first, so another worker can bind the
    # number and the "dead" port answers. check_voice_bench failed exactly
    # that way in the gate of 2026-09-10, on the day two more port-binding
    # checks were added, and passed alone straight afterwards.
    t.contains(lib, "def dead_port(",
               "there is a way to get an address that stays empty")
    dead = lib[lib.find("def dead_port("):]
    dead = dead[:dead.find("\ndef ", 1)] if "\ndef " in dead[1:] else dead
    t.ok("close()" not in dead,
         "and it HOLDS the socket rather than closing it",
         "closing it hands the number back to the pool, which is the whole "
         "bug: %r" % dead[:200])
    t.ok("_dead_keep" in dead,
         "keeping it for the life of the process")
    # Only the port that must ANSWER NOTHING. check_voice_move also calls
    # _free_port(), and rightly: that one is where it starts the voice helper.
    # Holding that socket stops the helper binding it, which broke two of its
    # assertions the first time this fix was applied too widely - the check
    # caught the over-correction within a minute of the correction.
    bench = (F.QC / "checks" / "check_voice_bench.py").read_text(
        encoding="utf-8", errors="replace")
    dead_line = [ln for ln in bench.splitlines() if ln.startswith("DEAD")]
    t.ok(dead_line and "dead_port()" in dead_line[0],
         "check_voice_bench's dead address is a HELD port",
         "an address that must answer nothing cannot be one the OS may hand "
         "to another worker a millisecond later: %r" % dead_line)

    # The real thing: it refuses a connection, and nobody else can take it.
    import socket as _sock
    port = F.dead_port()
    other = _sock.socket()
    try:
        other.bind(("127.0.0.1", port))
        taken = True
    except OSError:
        taken = False
    finally:
        other.close()
    t.ok(not taken, "a held port cannot be bound by anything else",
         "if it can, the gate will lose it again under load")
