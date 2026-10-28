"""Film sequences in the MuJoCo world from several cameras, with their song.

    python -m tools.nong_sim.record ROUND1.yaml [ROUND2.yaml ...] --music song.mp3 [--music-start 5]

User 2026-10-27: keep videos of the simulation from every angle, with the
music, each round visible, under 20 GB. Each file given is one ROUND (e.g. the
old slow dance, then the music-paced one, then the clearance fix); every round
is filmed from each camera in config/nong_sim.json `record.cameras`, with the
round, the camera and that round's numbers drawn on the picture. Files go to
`record.folder` (git-ignored), and filming stops before `record.maxGB` is
passed. Best effort: no ffmpeg, no GL or no Pillow costs a feature, not a run.
The song starts where the sequence's own `play:` step starts it on the board.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .board_clock import parse_sequence
from .play import CONFIG, load_config, run
from .studio import ROOT, StudioFacts, load_rig


def folder_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


class Caption:
    """Text on a frame, with Pillow when it is there (else none)."""

    def __init__(self, size):
        try:
            from PIL import Image, ImageDraw, ImageFont
            self.Image, self.Draw = Image, ImageDraw
            try:
                self.font = ImageFont.truetype("DejaVuSans.ttf", size)
            except OSError:
                self.font = ImageFont.load_default()
        except ImportError:
            self.Image = None

    def draw(self, frame, lines):
        if not self.Image:
            return frame
        img = self.Image.fromarray(frame)
        d = self.Draw.Draw(img)
        y = 8
        for line in lines:
            d.text((10, y), line, fill=(255, 255, 255), font=self.font, stroke_width=2, stroke_fill=(0, 0, 0))
            y += int(self.font.size * 1.3) if hasattr(self.font, "size") else 14
        import numpy as np
        return np.asarray(img)


class Film:
    """One ffmpeg process per camera, fed raw RGB frames on stdin."""

    def __init__(self, path, w, h, fps, music=None, music_at=0.0, music_start=0.0):
        self.proc = subprocess.Popen(self.command(path, w, h, fps, music, music_at, music_start),
                                     stdin=subprocess.PIPE)

    @staticmethod
    def command(path, w, h, fps, music=None, music_at=0.0, music_start=0.0):
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", "%dx%d" % (w, h), "-r", str(fps), "-i", "-"]
        if music:
            # apad: a slowed dance outlasts the song; without it -shortest ends ffmpeg at the
            # song's end and the next frame write fails (Errno 22, cheer v2 at safe 60, 2026-10-28).
            cmd += ["-ss", "%.3f" % music_start, "-itsoffset", "%.3f" % music_at, "-i", str(music),
                    "-map", "0:v", "-map", "1:a", "-af", "apad", "-c:a", "aac", "-shortest"]
        return cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", str(path)]

    def write(self, frame):
        self.proc.stdin.write(frame.tobytes())

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def camera(mujoco, spec, lookat):
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.azimuth, cam.elevation, cam.distance = spec["azimuth"], spec["elevation"], spec["distance"]
    cam.lookat[:] = lookat
    return cam


def film_round(n, label, seq, args, cfg, rig, facts, out):
    import mujoco
    from .world import NongWorld
    rec = cfg["record"]
    world = NongWorld(rig, facts, cfg, [(label, seq)])
    report = run(world)[0]                     # the numbers first, for the caption
    world.reset()
    w, h, fps = rec["width"], rec["height"], rec["fps"]
    renderer = mujoco.Renderer(world.model, h, w)
    lookat = world.data.body("r0_base").xpos.copy()
    lookat[2] += rec["lookUpMm"] / 1000
    cams = {c["name"]: camera(mujoco, c, lookat) for c in rec["cameras"]}
    music_at = world.robots[0]["clock"].music_at or 0.0
    films = {name: Film(out / ("round%02d_%s_%s.mp4" % (n, label, name)), w, h, fps,
                        args.music, music_at, args.music_start) for name in cams}
    caption = Caption(rec["captionPx"])
    head = ["Round %d: %s" % (n, label),
            "board %.1f s / music %.1f s | hits %d | closest %s mm | worst follow %.1f deg"
            % (report["boardSeconds"], report["musicSeconds"], len(report["hits"]),
               report["closestMm"], report["worstFollowDeg"])]
    end, step, shot = world.length() + 0.5, 1.0 / fps, 0.0
    try:
        while world.t < end:
            world.step_frame()
            while shot <= world.t:
                for name, cam in cams.items():
                    renderer.update_scene(world.data, camera=cam)
                    films[name].write(caption.draw(renderer.render(), head + ["%s  t=%.1f s" % (name, shot)]))
                shot += step
            if folder_bytes(out) > rec["maxGB"] * 1e9:
                print("stopped: %s is at its %g GB cap" % (out, rec["maxGB"]))
                return report, False
    finally:
        for f in films.values():
            f.close()
        renderer.close()
    return report, True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rounds", nargs="+", type=Path, help="one sequence per round, in order")
    ap.add_argument("--music", type=Path, help="the song the sequences' play: step starts")
    ap.add_argument("--music-start", type=float, default=0.0, help="seconds into the song the dance starts at")
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--out", type=Path, help="default: record.folder in the config")
    a = ap.parse_args(argv)
    if not shutil.which("ffmpeg"):
        print("ffmpeg is not installed: nothing can be filmed")
        return 2
    try:
        import mujoco  # noqa: F401
    except ImportError:
        print("MuJoCo is not installed: pip install mujoco")
        return 2
    cfg = load_config(a.config)
    cfg["robots"]["count"] = 1
    out = a.out or ROOT / cfg["record"]["folder"]
    out.mkdir(parents=True, exist_ok=True)
    rig = load_rig(ROOT / cfg["rig"] if cfg.get("rig") else None)
    facts = StudioFacts()
    for n, path in enumerate(a.rounds, 1):
        seq = parse_sequence(path.read_text(encoding="utf-8"))
        report, room = film_round(n, path.stem, seq, a, cfg, rig, facts, out)
        print("round %d %s: board %.1f s, music %.1f s, %d hits" % (n, path.stem, report["boardSeconds"],
                                                                    report["musicSeconds"], len(report["hits"])))
        if not room:
            break
    print("films in %s (%.2f GB)" % (out, folder_bytes(out) / 1e9))
    return 0


if __name__ == "__main__":
    sys.exit(main())
