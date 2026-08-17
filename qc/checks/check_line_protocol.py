"""One command in, ONE line out. Every channel here depends on it.

USB, RS485 and the hub's proxy are all line-based: a command is written, and
the first non-log line back is its reply. A command that answers with several
lines poisons the NEXT one — the extra lines are still arriving when that
reply is read, so the caller gets a fragment of the previous answer.

That is not hypothetical. On the bench, `HELP` printed 54 lines and the `CAL`
after it came back as `-line status JSON`. Nothing errored; the wrong text just
appeared in the right place, which is the worst way for it to fail.
"""
import re

import fake_serial
import qc as F

AREA = "protocol"
TITLE = "every command answers with exactly one line"
SLOW = False

SRC = ("src/core/CommandRouter.cpp",
       "src/modules/nong/NongModule.cpp", "src/modules/lift/LiftModule.cpp")


def run(t):
    # ---- no reply may contain a newline -----------------------------
    # A `\n` inside a returned String is a second line on the wire.
    # CommandHelp.h is generated per build (one binary per module type), so it
    # is read from the generated tree rather than from src/.
    for rel in SRC + (F.generated("core/CommandHelp.h"),):
        f = F.FIRMWARE / rel if isinstance(rel, str) else rel
        src = f.read_text(encoding="utf-8", errors="replace")
        src = re.sub(r"//.*", "", src)              # comments may say \n freely
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        bad = []
        for m in re.finditer(r"(reply\s*=|reply\s*\+=|return)\s*[^;]*?\\n", src):
            frag = m.group(0).replace("\n", " ")
            if "Serial" in frag:                    # console logging is fine
                continue
            bad.append(frag.strip()[:70])
        t.eq(bad, [], "%s builds no multi-line reply" % f.name)

    # ---- and the reply the module actually sends is one line ---------
    fake_serial.reset()
    base, main = F.start_hub()
    for c in ("PING", "INFO", "PIN?", "FILES /moves"):
        s, b = F.cmd(base, c)
        t.eq(s, 200, "%s answers" % c)
        t.ok("\n" not in b.strip(),
             "%s comes back as one line" % c,
             "a multi-line reply leaks into the next command")

    # ---- a long reply must not be truncated either -------------------
    # The other failure mode: one line, but cut short. INFO is the longest
    # thing the module says.
    s, b = F.cmd(base, "INFO")
    t.ok(b.strip().endswith("}"),
         "a long reply arrives whole, not cut short", b[-60:])

    # ---- HELP specifically: it is the one that broke this ------------
    hdr = F.generated("core/CommandHelp.h").read_text(
        encoding="utf-8", errors="replace")
    body = re.sub(r"//.*", "", hdr)
    fn = body[body.find("inline String commandHelp"):]
    t.ok("'\\n'" not in fn and '"\\n"' not in fn,
         "HELP builds a single line",
         "HELP with a newline poisons whatever command follows it")
    t.contains(hdr, "HELP <name> for one",
               "bare HELP lists names and points at the detailed form")
