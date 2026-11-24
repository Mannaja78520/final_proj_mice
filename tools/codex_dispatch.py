#!/usr/bin/env python3
"""Start a GPT Codex job that SHOWS UP in the Codex desktop app (project "mice").

`codex exec` jobs are hidden by the app (thread source "exec"). This wrapper runs the
same command, then flips the new thread to the app's own source ("vscode") in
~/.codex/state_5.sqlite so the app lists it under the project whose folder contains
the job's working directory (project "mice" = the mice folder). After the job ends it
also patches the rollout file's first line. A DB backup goes to ~/.codex/backups_visible.

    python tools/codex_dispatch.py --cwd E:/work/my_worktree --log .local/codex-x.log "Read CLAUDE.md ..."

Run it detached (PowerShell: Start-Process python -ArgumentList ... -WindowStyle Hidden).
The app may need a restart (or reopening the project) to refresh its list once.
Standard library only. Never edits the user's config.toml.
"""
import argparse, datetime, json, os, shutil, sqlite3, subprocess, sys, time

HOME = os.path.expanduser("~/.codex")
DB = HOME + "/state_5.sqlite"
PFX = chr(92) * 2 + "?" + chr(92)  # Windows long-path prefix


def codex_js():
    root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, shell=True).stdout.strip()
    return os.path.join(root, "@openai", "codex", "bin", "codex.js")


def norm(p):
    return os.path.normcase(os.path.abspath(p.replace(PFX, "")))


def flip(tid, rollout=False):
    c = sqlite3.connect(DB, timeout=30)
    row = c.execute("select rollout_path,title from threads where id=?", (tid,)).fetchone()
    c.execute("update threads set source='vscode', originator='codex_work_desktop' where id=? and source='exec'", (tid,))
    c.commit()
    idx = HOME + "/session_index.jsonl"
    if tid not in open(idx, encoding="utf-8").read():
        with open(idx, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": tid, "thread_name": (row[1] or "")[:60],
                                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")
    if rollout and row:
        p = row[0].replace(PFX, "")
        lines = open(p, encoding="utf-8").read().split("\n")
        d = json.loads(lines[0])
        d["payload"]["source"] = "vscode"; d["payload"]["originator"] = "codex_work_desktop"
        shutil.copy(p, p + ".bak")
        lines[0] = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
        open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True); ap.add_argument("--log", required=True)
    ap.add_argument("--model", default="gpt-6.2-sol"); ap.add_argument("--effort", default="medium")
    ap.add_argument("prompt")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
    bk = HOME + "/backups_visible"; os.makedirs(bk, exist_ok=True)
    s = sqlite3.connect(DB); d = sqlite3.connect(f"{bk}/state_5.{int(time.time())}.sqlite"); s.backup(d); d.close(); s.close()
    t0 = time.time()
    env = dict(os.environ, CODEX_INTERNAL_ORIGINATOR_OVERRIDE="codex_work_desktop")
    out = open(a.log, "ab"); err = open(a.log + ".err", "ab")
    p = subprocess.Popen(["node", codex_js(), "exec", "-m", a.model, "-c", f"model_reasoning_effort={a.effort}",
                          "--approve-for-me", "--skip-git-repo-check", "-C", a.cwd, a.prompt], env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, cwd=a.cwd)
    mine, flipped = norm(a.cwd), set()

    def scan():
        try:
            c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
            rows = c.execute("select id,cwd from threads where source='exec' and thread_source='user' and created_at>=?", (int(t0) - 2,)).fetchall()
            c.close()
            for tid, cwd in rows:
                if norm(cwd) == mine and tid not in flipped:
                    flip(tid); flipped.add(tid); print("visible:", tid, flush=True)
        except (sqlite3.Error, OSError) as e:
            print("scan retry:", e, flush=True)

    while p.poll() is None:
        scan()
        time.sleep(3)
    scan()
    p.wait()
    for tid in flipped:
        flip(tid, rollout=True)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
