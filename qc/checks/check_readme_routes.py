"""The README says how to get JUST the part you need, and the commands are real.

Asked for 2026-08-19. Three routes: the built app on its own, one branch without
the history, and one folder out of the repository. Written for somebody standing
at another PC who has not read anything else.

What is guarded, and why:

  * **the commands name the real remote and a branch that exists.** A README
    command that fails is worse than no README - the person is at another PC,
    with no way to tell a typo from a broken repo;
  * **the folder path matches the repository's real shape.** The repo root IS
    this `code` folder, so `git sparse-checkout set main_python` works and
    `code/main_python` silently checks out nothing at all - it succeeds, prints
    no error, and leaves only the root files. Found while testing this;
  * **no route promises a GitHub release.** There is none, and `gh` is not
    installed here to make one. Documenting what exists beats documenting what
    the plan assumed.
"""
import re
import subprocess

import qc as F

AREA = "docs"
TITLE = "the README's three ways to get just one part are real commands"


def run(t):
    md = (F.CODE / "README.md").read_text(encoding="utf-8", errors="replace")
    i = md.find("## Just give me the part I need")
    if not t.ok(i > 0, "the README has the section"):
        return
    sec = md[i:md.find("\n## ", i + 10)]

    # ---- the remote in the text is THIS repository -------------------
    try:
        real = subprocess.run(["git", "remote", "get-url", "origin"],
                              cwd=str(F.CODE), capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:                                         # noqa: BLE001
        real = ""
    if real:
        base = real[:-4] if real.endswith(".git") else real
        t.contains(sec, base,
                   "every command points at this repository's real remote")

    # ---- three routes, each with a command ---------------------------
    cmds = re.findall(r"```\n(.*?)```", sec, re.S)
    t.ok(len(cmds) >= 3, "there are three routes with commands",
         "found %d code blocks" % len(cmds))
    joined = "\n".join(cmds)
    t.contains(joined, "--branch app --depth 1",
               "one route takes the built app alone")
    t.contains(joined, "--branch main --depth 1",
               "one takes a branch without the history")
    t.contains(joined, "git sparse-checkout set",
               "and one takes a single folder")

    # ---- the branches named really exist -----------------------------
    try:
        heads = subprocess.run(["git", "branch", "-a"], cwd=str(F.CODE),
                               capture_output=True, text=True,
                               timeout=30).stdout
    except Exception:                                         # noqa: BLE001
        heads = ""
    if heads:
        for br in re.findall(r"--branch (\w+)", joined):
            t.ok(br in heads,
                 "the branch it names exists: %s" % br,
                 "a clone command naming a branch that is not there fails with "
                 "a message about a remote ref, at another PC, with nothing to "
                 "tell a typo from a broken repository")

    # ---- the sparse path matches the repo's real shape ---------------
    # `code/main_python` SUCCEEDS and checks out nothing: sparse-checkout does
    # not complain about a pattern that matches no directory, so the person is
    # left with only the root files and no error to search for.
    m = re.search(r"git sparse-checkout set (\S+)", joined)
    if t.ok(m, "the sparse route names a folder"):
        folder = m.group(1)
        t.ok((F.CODE / folder).is_dir(),
             "and that folder is really at the repository root: %s" % folder,
             "the root IS the code folder, so a path like code/%s matches "
             "nothing - and sparse-checkout reports no error for a pattern "
             "that matches nothing" % folder)
    t.ok("code/main_python" not in joined,
         "and the wrong path is not offered anywhere")

    # ---- it does not promise a release that does not exist -----------
    t.ok("/releases" not in sec and "release page" not in sec.lower(),
         "no route sends anyone to a GitHub release",
         "there is none; the app lives on the app branch, and pointing at a "
         "release that was never cut is a dead end at somebody else's PC")

    # ---- and it says the download sizes ------------------------------
    t.ok(re.search(r"\d+\s*MB", sec),
         "the sizes are stated",
         "the whole point of these three routes is that one is much smaller "
         "than another, and a person choosing between them needs the number")
