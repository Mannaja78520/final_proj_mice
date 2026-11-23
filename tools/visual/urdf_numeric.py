"""Numeric check of Studio's 3D robot against its URDF (plain-Python forward kinematics).

Random joint angles go through tools/visual/urdf_fk.py and through the page; every moving
link's frame and an off-axis probe point must land in the same place (mm).
  python tools/visual/urdf_numeric.py <hub base url> [urdf file] [--tol-mm 0.5]
Exit 1 on a difference. Also lists model-level problems (not mirrored, mesh on the wrong link) as NOTE.
"""
import json, math, os, random, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import urdf_fk as U  # noqa: E402

ROOT = HERE.parents[1]
DEF = ROOT / "nong/main_python_set_nong/models/nong.urdf"


def three(p):            # URDF z-up metres -> three.js y-up mm (Studio's frame.up="z": x'=y, y'=z, z'=x)
    return (p[1] * 1000, p[2] * 1000, p[0] * 1000)


def run_page(base, cases, model=""):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "cases.json"
        f.write_text(json.dumps(cases))
        env = dict(os.environ)
        env.setdefault("NODE_PATH", subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
        r = subprocess.run(["node", str(HERE / "urdf_page.js"), base, str(f), model], capture_output=True, text=True, env=env, timeout=120)
    if r.returncode:
        raise SystemExit("page script failed: " + r.stderr[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tol = 0.5
    if "--tol-mm" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tol-mm") + 1])
    base = args[0]
    path = Path(args[1]) if len(args) > 1 else DEF
    u = U.Urdf(path)
    first = run_page(base, [{"q": {}}], args[2] if len(args) > 2 else "")
    if "error" in first:
        print("FAIL page:", first["error"]); return 1
    names = [n for n in first["names"] if n]
    child = {j["name"]: j["child"] for j in u.joints}
    rnd = random.Random(7)
    cases = [{"q": {}}] + [{"q": {n: rnd.uniform(-1.2, 1.2) for n in names}} for _ in range(12)]
    page = run_page(base, cases, args[2] if len(args) > 2 else "")
    worst = (0, "")
    for ci, c in enumerate(cases):
        W = u.fk(c["q"])
        for n in names:
            M = W[child[n]]
            pr = (10, 20, 30)           # the page's probe, in mm in the link frame (the file's metres x1000)
            wp = [sum(M[i][k] * pr[k] / 1000 for k in range(3)) + M[i][3] for i in range(3)]
            for kind, exp in (("frame", U.pos(M)), ("probe", wp)):
                e = three(exp); a = page["out"][ci][n][kind]
                d = math.dist(e, a)
                if d > worst[0]:
                    worst = (d, "case %d joint %s %s: python %s page %s" % (ci, n, kind, [round(v, 1) for v in e], [round(v, 1) for v in a]))
    for b in U.model_findings(u):
        print("NOTE", b)
    print("joints checked: %d x %d cases; worst difference %.3f mm" % (len(names), len(cases), worst[0]))
    if worst[0] > tol:
        print("FAIL", worst[1]); return 1
    print("OK: the page's joints and turning match the file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
