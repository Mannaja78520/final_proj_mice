#!/usr/bin/env python3
"""testapp.py — the measuring instrument for the tests your eye cannot do.

The problem this solves: most dependent variables in these tests are
milliseconds. A 20 ms servo tick, an 80 ms minimum move, a 150 ms physical
floor, a 500 ms status push — none of that is visible by watching the robot.
Only the slow, big DVs (a 2 s lift stage, a joint angle, a tape measurement,
a current reading) can be taken by a human.

So the work is split:

    the APP measures        anything timed in milliseconds, and anything the
                            module already knows: reported vs executed move
                            duration, the 20 ms update tick, encoder counts,
                            arrival spread, latency, loss, throughput
    YOUR EYE measures       things that hold still: a joint angle with a
                            gauge, a position with a tape, "did it arrive"
    AN INSTRUMENT measures  current, rail voltage, temperature

How it measures time without any extra hardware: it polls the module's own
state as fast as the link allows and timestamps every reply on the PC.
`POSE?` is a short reply, so over USB it samples at roughly 100-200 Hz — about
5-10 ms per sample, fine enough to see the firmware's 20 ms interpolation
steps. The achieved sample rate is printed with every result, so you always
know the resolution of the number you got.

    python testapp.py info        --transport usb --port COM5
    python testapp.py watch       --transport usb --port COM5
    python testapp.py trace-nong  --transport usb --port COM5 --joint 3 --to 150 --T 300
    python testapp.py nong-sweep  --transport usb --port COM5 --iv speed --values 30,60,120,200
    python testapp.py nong-sweep  --transport usb --port COM5 --iv T     --values 1000,300,150,50
    python testapp.py nong-sweep  --transport usb --port COM5 --iv maxdps --values 400,200,100
    python testapp.py trace-lift  --transport usb --port COM5 --stage 1
    python testapp.py lift-sweep  --transport usb --port COM5 --values 200,400,700,900,1023
    python testapp.py lift-repeat --transport usb --port COM5 --stage 2 --n 10
    python testapp.py latency     --transport wifi --host nong.local -n 50 --rate 10

Every command writes a CSV (raw samples and/or a summary row) and can write a
self-contained HTML plot with --html, so you can SEE the trajectory that was
too fast to watch. No pip installs for WiFi mode; USB/RS485 need pyserial.
"""
import argparse
import csv
import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import open_link, percentile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TRACES = RESULTS / "traces"

JOINT_NAMES = ["L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
               "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R", "WAIST", "SHRUG"]

# a joint is "moving" once it differs from its start by more than this (deg).
# The firmware reports one decimal, so 0.15 is just above the reporting noise.
ANGLE_EPS = 0.15


# --------------------------------------------------------------- small helpers

def now_ms():
    return time.monotonic() * 1000.0


def parse_reported_T(reply):
    """'OK pose T=150ms' / 'OK L_EL_P=150.0 T=300ms' -> 150 / 300, else None."""
    if not reply or "T=" not in reply:
        return None
    tail = reply.split("T=", 1)[1]
    digits = ""
    for c in tail:
        if c.isdigit():
            digits += c
        else:
            break
    return int(digits) if digits else None


def parse_pose(reply):
    """'90.0 45.0 ...' -> [floats]; None if this is not a pose reply."""
    try:
        vals = [float(x) for x in reply.split()]
    except ValueError:
        return None
    return vals if len(vals) >= 8 else None


def settle(link, poll_cmd, parse, quiet_ms=400, max_ms=8000):
    """Wait until the polled value stops changing. Returns the samples taken."""
    samples = []
    t0 = now_ms()
    last_change = t0
    prev = None
    while True:
        t = now_ms()
        if t - t0 > max_ms:
            break
        try:
            v = parse(link.send(poll_cmd))
        except Exception:
            continue
        if v is None:
            continue
        samples.append((t - t0, v))
        if prev is not None and _changed(prev, v):
            last_change = t
        prev = v
        if t - last_change > quiet_ms and t - t0 > quiet_ms:
            break
    return samples


def _changed(a, b):
    if isinstance(a, list):
        return any(abs(x - y) > ANGLE_EPS for x, y in zip(a, b))
    return abs(a - b) > 1e-9


def analyse_trace(samples, index=None):
    """Turn (t_ms, values) samples into the DVs the test tables ask for.

    duration_ms      first change -> last change. Simple, but the cosine ease
                     starts and ends below the 0.1 deg reporting step, so it
                     reads a little SHORT.
    duration_fit_ms  unbiased: a straight-line fit of the firmware's own cosine
                     ease over every sample between 5 % and 95 % of the travel
                     (see the code below). This is the number to compare against
                     the reported T.
    tick_ms          mean gap between value changes = the firmware's update
                     period (20 ms at 50 Hz). Mean, not median: the median is
                     biased by the polling grid.
    """
    out = {"samples": len(samples), "duration_ms": None, "duration_fit_ms": None,
           "start_ms": None, "end_ms": None, "tick_ms": None,
           "tick_median_ms": None, "sample_hz": None, "travel": None}
    if len(samples) < 3:
        return out

    span = samples[-1][0] - samples[0][0]
    if span > 0:
        out["sample_hz"] = round(len(samples) / (span / 1000.0), 1)

    def val(s):
        v = s[1]
        if not isinstance(v, list):
            return v
        return v[index] if index is not None else max(v)

    v0 = val(samples[0])
    moving_ts, change_ts, prev = [], [], v0
    for s in samples:
        v = val(s)
        if abs(v - v0) > ANGLE_EPS:
            moving_ts.append(s[0])
        if abs(v - prev) > ANGLE_EPS:
            change_ts.append(s[0])
        prev = v

    if moving_ts:
        out["start_ms"] = round(moving_ts[0], 1)
        out["end_ms"] = round(change_ts[-1] if change_ts else moving_ts[-1], 1)
        out["duration_ms"] = round(out["end_ms"] - out["start_ms"], 1)
    if len(change_ts) >= 3:
        gaps = [b - a for a, b in zip(change_ts, change_ts[1:]) if b - a > 0]
        if gaps:
            out["tick_median_ms"] = round(statistics.median(gaps), 1)
            out["tick_ms"] = round((change_ts[-1] - change_ts[0]) / len(gaps), 1)

    total = val(samples[-1]) - v0
    out["travel"] = round(abs(total), 2)
    if abs(total) > 1.0:
        # Fit the firmware's own ease instead of guessing from two thresholds.
        # progress p = 0.5 - 0.5·cos(pi·u)  =>  u = acos(1 - 2p) / pi, and u is
        # linear in time. A straight-line fit of t against u gives the move's
        # duration as the slope and its start as the intercept — every sample
        # contributes, so the 20 ms quantisation averages out instead of
        # biasing one threshold crossing.
        us, ts = [], []
        for s in samples:
            p = (val(s) - v0) / total
            if 0.05 <= p <= 0.95:
                us.append(math.acos(max(-1.0, min(1.0, 1 - 2 * p))) / math.pi)
                ts.append(s[0])
        if len(us) >= 4:
            um, tm = statistics.mean(us), statistics.mean(ts)
            den = sum((u - um) ** 2 for u in us)
            if den > 1e-9:
                slope = sum((u - um) * (t - tm) for u, t in zip(us, ts)) / den
                if slope > 0:
                    out["duration_fit_ms"] = round(slope, 1)
                    out["fit_start_ms"] = round(tm - slope * um, 1)
                    out["fit_points"] = len(us)
    return out


def pick_moving_joint(samples):
    """Index of the joint that moved the most across a nong trace."""
    if not samples:
        return 0
    first, last = samples[0][1], samples[-1][1]
    deltas = [abs(b - a) for a, b in zip(first, last)]
    return deltas.index(max(deltas)) if max(deltas) > ANGLE_EPS else 0


def write_samples_csv(path, header, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for t, v in samples:
            w.writerow([round(t, 2)] + (v if isinstance(v, list) else [v]))
    print("samples -> %s" % path)


def append_summary(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(list(row.keys()))
        w.writerow(list(row.values()))
    print("summary row -> %s" % path)


# ------------------------------------------------------------------ html plot

def write_html(path, title, series, xlabel="time (ms)", ylabel="", notes=()):
    """Self-contained SVG line chart — no libraries, opens in any browser.

    series: [(name, [(x, y), ...]), ...]
    """
    W, H, PAD = 900, 420, 56
    xs = [p[0] for _, pts in series for p in pts]
    ys = [p[1] for _, pts in series for p in pts]
    if not xs or not ys:
        print("nothing to plot")
        return
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    if x1 - x0 < 1e-9:
        x1 = x0 + 1
    if y1 - y0 < 1e-9:
        y0, y1 = y0 - 1, y1 + 1
    pad_y = (y1 - y0) * 0.08
    y0, y1 = y0 - pad_y, y1 + pad_y
    colors = ["#2f7bd6", "#d9534f", "#3aa76d", "#b07cc6", "#d18b2c",
              "#4aa3c7", "#c2557a", "#7a8b3d", "#8a6ad1", "#c96f3f"]

    def sx(x):
        return PAD + (x - x0) / (x1 - x0) * (W - 2 * PAD)

    def sy(y):
        return H - PAD - (y - y0) / (y1 - y0) * (H - 2 * PAD)

    parts = []
    for i in range(6):
        gy = y0 + (y1 - y0) * i / 5.0
        parts.append('<line class="grid" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                     % (PAD, sy(gy), W - PAD, sy(gy)))
        parts.append('<text class="tick" x="%.1f" y="%.1f" text-anchor="end">%.6g</text>'
                     % (PAD - 8, sy(gy) + 4, gy))
    for i in range(6):
        gx = x0 + (x1 - x0) * i / 5.0
        parts.append('<line class="grid" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                     % (sx(gx), PAD, sx(gx), H - PAD))
        parts.append('<text class="tick" x="%.1f" y="%.1f" text-anchor="middle">%.6g</text>'
                     % (sx(gx), H - PAD + 20, gx))
    legend = []
    for i, (name, pts) in enumerate(series):
        c = colors[i % len(colors)]
        d = " ".join("%.1f,%.1f" % (sx(x), sy(y)) for x, y in pts)
        parts.append('<polyline class="ln" style="stroke:%s" points="%s"/>' % (c, d))
        for x, y in pts:
            parts.append('<circle cx="%.1f" cy="%.1f" r="1.7" style="fill:%s"/>'
                         % (sx(x), sy(y), c))
        legend.append('<span class="k"><i style="background:%s"></i>%s</span>' % (c, name))

    html = """<!doctype html>
<meta charset="utf-8"><title>%(title)s</title>
<style>
 :root{color-scheme:light dark}
 body{font:14px/1.5 system-ui,sans-serif;margin:24px;max-width:960px}
 h1{font-size:18px;margin:0 0 4px}
 .sub{opacity:.7;margin:0 0 16px}
 .wrap{overflow-x:auto}
 svg{background:transparent}
 .grid{stroke:currentColor;opacity:.15;stroke-width:1}
 .tick{fill:currentColor;opacity:.65;font-size:11px}
 .ln{fill:none;stroke-width:1.8}
 .lg{margin:10px 0 0;display:flex;gap:14px;flex-wrap:wrap}
 .k{display:flex;align-items:center;gap:6px;font-size:12px}
 .k i{width:12px;height:3px;border-radius:2px;display:inline-block}
 ul{margin:14px 0 0;padding-left:20px}
 li{font-size:13px;opacity:.85}
 .ax{fill:currentColor;opacity:.7;font-size:12px}
</style>
<h1>%(title)s</h1>
<p class="sub">%(xlabel)s &rarr; %(ylabel)s</p>
<div class="wrap"><svg viewBox="0 0 %(W)d %(H)d" width="%(W)d" height="%(H)d">
%(parts)s
<text class="ax" x="%(midx).1f" y="%(H)d" text-anchor="middle">%(xlabel)s</text>
</svg></div>
<div class="lg">%(legend)s</div>
<ul>%(notes)s</ul>
""" % {"title": title, "xlabel": xlabel, "ylabel": ylabel, "W": W, "H": H,
       "parts": "\n".join(parts), "legend": "".join(legend),
       "midx": W / 2.0,
       "notes": "".join("<li>%s</li>" % n for n in notes)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print("plot -> %s   (open it in a browser)" % path)


# -------------------------------------------------------------------- commands

def cmd_info(link, args):
    reply = link.send("INFO")
    try:
        st = json.loads(reply)
    except Exception:
        print(reply)
        return 1
    print("id=%s  name=%s  type=%s  fw=%s  sd=%s"
          % (st.get("id"), st.get("name"), st.get("type"), st.get("fw"), st.get("sd")))
    w = st.get("wifi") or {}
    print("wifi: mode=%s ip=%s rssi=%s host=%s"
          % (w.get("mode"), w.get("ip"), w.get("rssi"), w.get("host")))
    m = st.get("module") or {}
    if st.get("type") == "nong":
        print("joints:   %s" % m.get("joints"))
        print("moving=%s attached=%s speed_dps=%s link=%s peer=%s move_ms=%s left=%s"
              % (m.get("moving"), m.get("attached"), m.get("speed_dps"),
                 m.get("link"), m.get("peer"), m.get("move_ms"), m.get("move_left")))
    else:
        print("state=%s stage=%s/%s homed=%s enc=%s counts=%s pos_mm=%s"
              % (m.get("state"), m.get("stage"), m.get("stages"), m.get("homed"),
                 m.get("enc"), m.get("encoder"), m.get("pos_mm")))
        print("speed_pwm=%s est_mms=%s vel_mms=%s limit_top=%s limit_down=%s"
              % (m.get("speed_pwm"), m.get("est_mms"), m.get("vel_mms"),
                 m.get("limit_top"), m.get("limit_down")))
    return 0


def cmd_watch(link, args):
    print("polling every %d ms — Ctrl-C to stop" % args.interval)
    t0 = now_ms()
    try:
        while True:
            t = now_ms()
            try:
                st = json.loads(link.send("INFO"))
                m = st.get("module") or {}
                if st.get("type") == "nong":
                    line = "moving=%-5s joints=%s" % (m.get("moving"), m.get("joints"))
                else:
                    line = ("state=%-6s stage=%-3s counts=%-7s pos_mm=%-8s vel=%s"
                            % (m.get("state"), m.get("stage"), m.get("encoder"),
                               round(m.get("pos_mm") or 0, 1), round(m.get("vel_mms") or 0, 1)))
                print("%8.0f ms  %s" % (t - t0, line))
            except Exception as e:
                print("%8.0f ms  ERR %s" % (t - t0, e))
            time.sleep(max(0, args.interval / 1000.0))
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


def _nong_move(link, args, joint, to, T, tag):
    """One measured nong move: send it, then sample POSE? until it settles."""
    link.send("HOME")
    settle(link, "POSE?", parse_pose, quiet_ms=300, max_ms=6000)
    start_pose = parse_pose(link.send("POSE?")) or []

    cmd = "JOINT %d %g" % (joint, to) + (" T %d" % T if T else "")
    t_cmd = now_ms()
    reply = link.send(cmd)
    reported = parse_reported_T(reply)

    samples = settle(link, "POSE?", parse_pose,
                     quiet_ms=args.settle,
                     max_ms=(reported or 2000) * 3 + 3000)
    idx = joint - 1
    a = analyse_trace(samples, index=idx)

    end_pose = parse_pose(link.send("POSE?")) or []
    commanded_delta = abs(to - (start_pose[idx] if start_pose else 90))
    reached = end_pose[idx] if end_pose else None

    err = (a["duration_fit_ms"] - reported) if (reported and a["duration_fit_ms"]) else None
    print("\n%s" % tag)
    print("  sent          : %s" % cmd)
    print("  reply         : %s" % reply)
    print("  reported T    : %s ms   (what the firmware says the move will take)" % reported)
    print("  executed (fit): %s ms   <- compare with reported T%s"
          % (a["duration_fit_ms"], ("   error %+.0f ms" % err) if err is not None else ""))
    print("  executed (raw): %s ms   (first change -> last change; reads short because"
          " the ease starts below 0.1 deg)" % a["duration_ms"])
    print("  update tick   : %s ms   (mean gap between changes; firmware writes at 50 Hz"
          " = 20 ms; median %s)" % (a["tick_ms"], a["tick_median_ms"]))
    print("  sample rate   : %s Hz   (%d samples — this is your time resolution)"
          % (a["sample_hz"], a["samples"]))
    print("  angle travel  : %s deg reported by the module (commanded %.1f)"
          % (a["travel"], commanded_delta))
    print("  final angle   : %s deg  <- check THIS one with a gauge on the joint" % reached)

    row = {
        "when": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag,
        "joint": JOINT_NAMES[idx] if idx < len(JOINT_NAMES) else joint,
        "command": cmd, "reply": reply,
        "commanded_T_ms": T or "", "reported_T_ms": reported or "",
        "executed_fit_ms": a["duration_fit_ms"], "executed_raw_ms": a["duration_ms"],
        "error_ms": round(err, 1) if err is not None else "",
        "tick_ms": a["tick_ms"], "tick_median_ms": a["tick_median_ms"],
        "sample_hz": a["sample_hz"], "samples": a["samples"],
        "commanded_delta_deg": round(commanded_delta, 1),
        "reported_travel_deg": a["travel"], "final_reported_deg": reached,
    }
    if args.csv:
        append_summary(Path(args.csv), row)
    if args.trace_csv or args.html:
        stem = tag.replace(" ", "_").replace("=", "").replace("/", "-")
        if args.trace_csv:
            write_samples_csv(TRACES / ("nong_%s.csv" % stem),
                              ["t_ms"] + JOINT_NAMES, samples)
        if args.html:
            pts = [(t, v[idx]) for t, v in samples]
            write_html(Path(args.html) if args.html != "auto"
                       else TRACES / ("nong_%s.html" % stem),
                       "nong %s — %s" % (JOINT_NAMES[idx], tag),
                       [("%s (deg)" % JOINT_NAMES[idx], pts)],
                       ylabel="joint angle (deg)",
                       notes=["reported T = %s ms, executed (ease fit) = %s ms"
                              % (reported, a["duration_fit_ms"]),
                              "mean update tick = %s ms (firmware target: 20 ms)" % a["tick_ms"],
                              "sampled at %s Hz — the staircase is the firmware's 50 Hz "
                              "interpolation, the S-curve is its cosine ease" % a["sample_hz"]])
    return row


def cmd_trace_nong(link, args):
    _nong_move(link, args, args.joint, args.to, args.T,
               "trace J%d to %g%s" % (args.joint, args.to,
                                      (" T%d" % args.T) if args.T else ""))
    return 0


def cmd_nong_sweep(link, args):
    values = [v.strip() for v in args.values.split(",") if v.strip()]
    csv_path = Path(args.csv) if args.csv else RESULTS / "nong_measured.csv"
    args.csv = str(csv_path)
    print("sweep: IV=%s values=%s   joint=%d  %g -> %g deg"
          % (args.iv, values, args.joint, 90.0, args.to))

    for v in values:
        if args.iv == "speed":
            print("\n== SPEED %s ==" % v)
            print("  %s" % link.send("SPEED %s" % v))
            _nong_move(link, args, args.joint, args.to, None, "speed=%s" % v)
        elif args.iv == "T":
            print("\n== T %s ms ==" % v)
            _nong_move(link, args, args.joint, args.to, int(float(v)), "T=%s" % v)
        elif args.iv == "maxdps":
            print("\n== max_dps %s ==" % v)
            print("  %s" % link.send("PULSE %d %d %d %s"
                                     % (args.joint, args.pulse_min, args.pulse_max, v)))
            _nong_move(link, args, args.joint, args.to, args.T or 50, "maxdps=%s" % v)
        else:
            print("unknown --iv %r" % args.iv)
            return 2

    print("\nAll rows are in %s." % csv_path)
    print("Compare 'reported_T_ms' with 'executed_ms': the firmware's promise vs what it")
    print("actually ran. Then check the final angle with a gauge — that part needs your eye.")
    return 0


def _lift_status(reply):
    try:
        m = json.loads(reply).get("module") or {}
    except Exception:
        return None
    return {"state": m.get("state"), "stage": m.get("stage"),
            "counts": m.get("encoder"), "pos_mm": m.get("pos_mm"),
            "vel_mms": m.get("vel_mms"), "homed": m.get("homed"),
            "limit_top": m.get("limit_top"), "limit_down": m.get("limit_down")}


def _lift_trace(link, args, action, tag):
    """Send a lift motion command and sample INFO until the state returns to idle."""
    t_cmd = now_ms()
    reply = link.send(action)
    samples, t0 = [], now_ms()
    last_moving = t0
    while True:
        t = now_ms()
        if t - t0 > args.max_ms:
            break
        st = _lift_status(link.send("INFO"))
        if st is None:
            continue
        samples.append((t - t0, st))
        if st["state"] != "idle":
            last_moving = t
        if t - last_moving > args.settle and t - t0 > args.settle:
            break

    times = [s[0] for s in samples]
    counts = [(s[0], s[1]["counts"] or 0) for s in samples]
    vels = [(s[0], s[1]["vel_mms"] or 0) for s in samples]
    pos = [(s[0], s[1]["pos_mm"] or 0) for s in samples]
    moving = [s for s in samples if s[1]["state"] != "idle"]
    hz = round(len(samples) / ((times[-1] - times[0]) / 1000.0), 1) if len(times) > 2 else None
    travel_ms = round(moving[-1][0] - moving[0][0], 1) if len(moving) >= 2 else None
    d_counts = (counts[-1][1] - counts[0][1]) if counts else 0
    peak_vel = max((abs(v) for _, v in vels), default=0)
    mean_vel = (statistics.mean([abs(v) for _, v in vels if abs(v) > 1])
                if any(abs(v) > 1 for _, v in vels) else 0)
    end = samples[-1][1] if samples else {}

    print("\n%s" % tag)
    print("  sent        : %s   ->  %s" % (action, reply))
    print("  travel time : %s ms  (state left 'idle' -> returned to 'idle')" % travel_ms)
    print("  sample rate : %s Hz  (%d samples — INFO is a big reply, so this is your"
          " resolution)" % (hz, len(samples)))
    print("  counts moved: %s   final counts=%s  pos_mm=%s"
          % (d_counts, end.get("counts"), round(end.get("pos_mm") or 0, 1)))
    print("  speed       : peak %.1f mm/s   mean-while-moving %.1f mm/s  (encoder measured)"
          % (peak_vel, mean_vel))
    print("  ended at    : state=%s stage=%s homed=%s limits(top=%s,down=%s)"
          % (end.get("state"), end.get("stage"), end.get("homed"),
             end.get("limit_top"), end.get("limit_down")))
    print("  -> now read the TAPE for the true position; the app cannot see the rack.")

    row = {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag, "command": action,
           "reply": reply, "travel_ms": travel_ms, "sample_hz": hz,
           "samples": len(samples), "counts_moved": d_counts,
           "final_counts": end.get("counts"), "final_pos_mm": end.get("pos_mm"),
           "final_stage": end.get("stage"), "peak_vel_mms": round(peak_vel, 1),
           "mean_vel_mms": round(mean_vel, 1), "homed": end.get("homed")}
    if args.csv:
        append_summary(Path(args.csv), row)
    stem = tag.replace(" ", "_").replace("=", "").replace("/", "-")
    if args.trace_csv:
        with (TRACES / ("lift_%s.csv" % stem)).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_ms", "state", "stage", "counts", "pos_mm", "vel_mms",
                        "limit_top", "limit_down"])
            for t, s in samples:
                w.writerow([round(t, 1), s["state"], s["stage"], s["counts"],
                            s["pos_mm"], s["vel_mms"], s["limit_top"], s["limit_down"]])
        TRACES.mkdir(parents=True, exist_ok=True)
        print("samples -> %s" % (TRACES / ("lift_%s.csv" % stem)))
    if args.html:
        write_html(Path(args.html) if args.html != "auto"
                   else TRACES / ("lift_%s.html" % stem),
                   "lift — %s" % tag,
                   [("position (mm)", pos), ("speed (mm/s)", vels)],
                   ylabel="mm  /  mm per s",
                   notes=["travel time %s ms, peak %.1f mm/s" % (travel_ms, peak_vel),
                          "sampled at %s Hz — INFO is a long reply, so this trace is "
                          "coarser than the nong one" % hz,
                          "encoder resolution is 3.57 mm per count: a step in the position "
                          "line IS one count"])
    return row


def cmd_trace_lift(link, args):
    link.send("HOME")
    time.sleep(0.3)
    _lift_trace(link, args, "HOME", "home")
    _lift_trace(link, args, "GOTO %d" % args.stage, "goto %d" % args.stage)
    return 0


def cmd_lift_sweep(link, args):
    values = [v.strip() for v in args.values.split(",") if v.strip()]
    csv_path = Path(args.csv) if args.csv else RESULTS / "lift_measured.csv"
    args.csv = str(csv_path)
    for v in values:
        print("\n== SPEED %s ==" % v)
        print("  %s" % link.send("SPEED %s" % v))
        _lift_trace(link, args, "HOME", "home before pwm=%s" % v)
        _lift_trace(link, args, "GOTO %d" % args.stage, "pwm=%s" % v)
    print("\nAll rows are in %s." % csv_path)
    print("The app gives you time and encoder speed. The tape gives you the true mm —")
    print("write it in the 'notes' column and the two together are the result.")
    return 0


def cmd_lift_repeat(link, args):
    """LIFT-08 arrival spread — fully automatic, no eye needed (encoder counts)."""
    csv_path = Path(args.csv) if args.csv else RESULTS / "lift_measured.csv"
    args.csv = str(csv_path)
    finals = []
    for i in range(args.n):
        print("\n-- cycle %d/%d --" % (i + 1, args.n))
        _lift_trace(link, args, "HOME", "repeat home %d" % (i + 1))
        row = _lift_trace(link, args, "GOTO %d" % args.stage,
                          "repeat goto%d #%d" % (args.stage, i + 1))
        if row["final_counts"] is not None:
            finals.append(row["final_counts"])
    if len(finals) >= 2:
        spread = max(finals) - min(finals)
        print("\n=== arrival spread over %d cycles ===" % len(finals))
        print("counts: %s" % finals)
        print("mean %.1f   spread %d counts   = %.1f mm   (1 count = 3.57 mm)"
              % (statistics.mean(finals), spread, spread * 3.57))
        print("stdev  %.2f counts" % (statistics.pstdev(finals)))
        append_summary(csv_path, {
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tag": "arrival spread stage %d x%d" % (args.stage, len(finals)),
            "command": "GOTO %d" % args.stage, "reply": "", "travel_ms": "",
            "sample_hz": "", "samples": len(finals), "counts_moved": "",
            "final_counts": ";".join(str(c) for c in finals),
            "final_pos_mm": "", "final_stage": args.stage,
            "peak_vel_mms": "", "mean_vel_mms": "",
            "homed": "spread=%d counts / %.1f mm" % (spread, spread * 3.57)})
    return 0


def cmd_latency(link, args):
    lat, lost = [], 0
    interval = (1.0 / args.rate) if args.rate else 0.0
    t_series = time.monotonic()
    for i in range(args.n):
        if interval:
            due = t_series + i * interval
            if due > time.monotonic():
                time.sleep(due - time.monotonic())
        t0 = now_ms()
        try:
            link.send(args.cmd_text)
            lat.append(now_ms() - t0)
        except Exception:
            lost += 1
    print("sent %d  replied %d  lost %d  success %.1f %%"
          % (args.n, len(lat), lost, 100.0 * len(lat) / args.n if args.n else 0))
    if lat:
        print("latency ms: min %.1f  mean %.1f  p95 %.1f  max %.1f"
              % (min(lat), statistics.mean(lat), percentile(lat, 0.95), max(lat)))
    if args.html:
        write_html(Path(args.html) if args.html != "auto" else TRACES / "latency.html",
                   "round-trip latency — %s" % args.cmd_text,
                   [("ms", [(i + 1, v) for i, v in enumerate(lat)])],
                   xlabel="command number", ylabel="round trip (ms)",
                   notes=["%d sent, %d lost" % (args.n, lost),
                          "spikes are retries or a busy module loop"])
    return 0


# ------------------------------------------------------------------------ main

GLOBAL_DEFAULTS = {"transport": "usb", "port": None, "host": None, "id": 0,
                   "sim": "nong", "timeout": 2.0, "csv": None,
                   "trace_csv": False, "html": None}


def main():
    # The connection options work BEFORE or AFTER the subcommand — argparse
    # normally forbids the second form, so they live in a parent parser with
    # SUPPRESS defaults (an option not typed anywhere simply stays absent and
    # is filled in from GLOBAL_DEFAULTS below).
    S = argparse.SUPPRESS
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--transport", choices=["usb", "wifi", "rs485", "sim"], default=S,
                        help="how to reach the module (default usb; 'sim' = no hardware)")
    common.add_argument("--port", default=S, help="usb/rs485 serial port, e.g. COM5")
    common.add_argument("--host", default=S, help="wifi ip or <name>.local")
    common.add_argument("--id", type=int, default=S, help="rs485 module address")
    common.add_argument("--sim", choices=["nong", "lift"], default=S,
                        help="with --transport sim: which fake module to talk to")
    common.add_argument("--timeout", type=float, default=S)
    common.add_argument("--csv", default=S, help="summary CSV to append to")
    common.add_argument("--trace-csv", action="store_true", default=S,
                        help="also write the raw samples")
    common.add_argument("--html", nargs="?", const="auto", default=S,
                        help="write a self-contained plot (default path under results/traces)")

    p = argparse.ArgumentParser(
        parents=[common],
        description="measuring app for the scient_test experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="every command prints the sample rate it achieved — that is the "
               "resolution of the numbers it gives you.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("info", parents=[common], help="identity + status sanity check")

    w = sub.add_parser("watch", parents=[common], help="live status printout")
    w.add_argument("--interval", type=int, default=200, help="poll interval ms")

    tn = sub.add_parser("trace-nong", parents=[common],
                        help="one measured nong move (ms + 20 ms tick)")
    tn.add_argument("--joint", type=int, default=3)
    tn.add_argument("--to", type=float, default=150.0)
    tn.add_argument("--T", type=int, default=0, help="commanded T ms (0 = let SPEED decide)")
    tn.add_argument("--settle", type=int, default=400, help="quiet time that ends a move")

    ns = sub.add_parser("nong-sweep", parents=[common],
                        help="automated NONG-03 / 04 / 05 sweeps")
    ns.add_argument("--iv", choices=["speed", "T", "maxdps"], required=True)
    ns.add_argument("--values", required=True, help="comma separated, e.g. 30,60,120,200")
    ns.add_argument("--joint", type=int, default=3)
    ns.add_argument("--to", type=float, default=150.0)
    ns.add_argument("--T", type=int, default=0)
    ns.add_argument("--settle", type=int, default=400)
    ns.add_argument("--pulse-min", type=int, default=500)
    ns.add_argument("--pulse-max", type=int, default=2400)

    tl = sub.add_parser("trace-lift", parents=[common], help="one measured lift move")
    tl.add_argument("--stage", type=int, default=1)
    tl.add_argument("--settle", type=int, default=600)
    tl.add_argument("--max-ms", type=int, default=60000)

    ls = sub.add_parser("lift-sweep", parents=[common],
                        help="automated LIFT-01 speed sweep")
    ls.add_argument("--values", required=True, help="comma separated PWM values")
    ls.add_argument("--stage", type=int, default=1)
    ls.add_argument("--settle", type=int, default=600)
    ls.add_argument("--max-ms", type=int, default=60000)

    lr = sub.add_parser("lift-repeat", parents=[common],
                        help="LIFT-08 arrival spread, N cycles")
    lr.add_argument("--stage", type=int, default=2)
    lr.add_argument("-n", type=int, default=10)
    lr.add_argument("--settle", type=int, default=600)
    lr.add_argument("--max-ms", type=int, default=60000)

    la = sub.add_parser("latency", parents=[common], help="round-trip latency + loss")
    la.add_argument("--cmd", dest="cmd_text", default="PING")
    la.add_argument("-n", type=int, default=50)
    la.add_argument("--rate", type=float, default=0)

    args = p.parse_args()
    for k, v in GLOBAL_DEFAULTS.items():
        if not hasattr(args, k):
            setattr(args, k, v)

    try:
        if args.transport == "sim":
            from simulator import SimLink
            link = SimLink(args.sim)
            # simulated runs never land in results/ next to real measurements
            global RESULTS, TRACES
            RESULTS = RESULTS / "sim"
            TRACES = RESULTS / "traces"
            print("[sim] talking to a fake %s module — no hardware, firmware maths only."
                  "\n[sim] output goes to results/sim/, never mixed with real data.\n"
                  % args.sim)
        else:
            link = open_link(args.transport, host=args.host, port=args.port,
                             id=args.id, timeout=args.timeout)
    except ValueError as e:
        p.error(str(e))

    handlers = {
        "info": cmd_info, "watch": cmd_watch, "trace-nong": cmd_trace_nong,
        "nong-sweep": cmd_nong_sweep, "trace-lift": cmd_trace_lift,
        "lift-sweep": cmd_lift_sweep, "lift-repeat": cmd_lift_repeat,
        "latency": cmd_latency,
    }
    try:
        return handlers[args.command](link, args)
    finally:
        link.close()


if __name__ == "__main__":
    sys.exit(main())
