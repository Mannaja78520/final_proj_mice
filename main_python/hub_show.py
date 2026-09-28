"""The show player: runs a sequence on a real thread at real times.

Moved out of main.py on 2026-09-22 (A26-76 phase 2, see docs/systems/hub.md).
One player per hub. Takes over the target device, respects pauses and beats,
and silences music on panic stops. main.py imports these names back.

Names that live in main.py are read late through _hub, like every hub_*
helper, so a check that swaps main.dev_cmd reaches the clock too. Never
`import main` here: run as a script the hub is __main__, and that import
loaded a SECOND hub whose idle player /api/play then read (check_one_hub).
"""
import re
import threading
import time

_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class ShowPlayer:
    """One player per hub. Runs a sequence on a real thread, at real times."""

    TICK = 0.02          # how often the thread wakes to check the clock / stop
    # A page that asked to be WATCHED beats every second while it is on screen.
    # Silent this long without saying it was leaving = frozen: stop the arm
    # (A26-46). Longer than a slow STL load, shorter than a walk to the robot.
    BEAT_TIMEOUT = 4.0
    MIN_T = 80           # ms, the same floor the firmware and Studio use
    CATCH_UP_S = 0.25    # later than this, a move does not rush to catch up
    # A pose with no reply is a hiccup, not the end: the next one goes out on
    # its time and the arm catches up (the board caps a move that is too fast).
    # One lost reply used to end the show with its song still playing (real
    # nong, 2026-09-28). This many in a row is a robot that is gone.
    MAX_MISSES = 3

    def __init__(self, cmd_fn=None, parse_fn=None, cues_fn=None):
        self._cmd_fn = cmd_fn
        self._parse_fn = parse_fn
        self._cues_fn = cues_fn
        self.lock = threading.Lock()
        # Held across stop-then-start, so two callers cannot each find
        # nothing to stop and each spawn a clock. Separate from `lock`,
        # which the running thread takes constantly - holding that one
        # across a join would deadlock.
        self._starting = threading.Lock()
        self.thread = None
        self.stop_flag = threading.Event()
        self.dev = ""
        self.name = ""
        self.steps = []
        self.loop = False
        self.at_ms = 0
        self.total_ms = 0
        self.step = -1
        self.last = ""       # the module's answer to the most recent command
        self.error = ""
        self.started_at = 0.0
        self.entering = False
        self.watched = False     # a visible Studio page is beating for this show
        self.last_beat = 0.0
        # The show's track may outlive the moves (Shows: music_end, user
        # 2026-09-27): a timer stops it at music_stop_ms on the show's clock.
        self.music_stop_ms = None
        self._music_timer = None
        self._misses = 0         # poses in a row with no reply, this run

    def _get_cmd(self):
        if self._cmd_fn is not None:
            return self._cmd_fn
        return _hub.dev_cmd

    def _get_parse(self):
        if self._parse_fn is not None:
            return self._parse_fn
        return _hub.parse_dev

    def _get_cues(self):
        if self._cues_fn is not None:
            return self._cues_fn
        return _hub.cue_lines

    # ---- what a caller sees ----
    def status(self):
        with self.lock:
            return {
                "running": self.running(),
                "dev": self.dev, "name": self.name, "loop": self.loop,
                "at_ms": int(self.at_ms), "total_ms": int(self.total_ms),
                "step": self.step, "steps": len(self.steps),
                "last": self.last, "error": self.error,
                # travelling to keyframe 0: the show clock has not started yet,
                # so Studio holds its preview (A26-50)
                "entering": self.entering,
            }

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    @staticmethod
    def total(steps):
        return sum(int(s.get("t", 0)) + int(s.get("hold", 0)) for s in steps)

    def beat(self, leaving=False):
        """Studio is alive (leaving=False), or is going away ON PURPOSE - hidden
        or closed - and the show should carry on by itself (leaving=True)."""
        with self.lock:
            self.watched = not leaving
            self.last_beat = time.monotonic()
        return {"ok": True, "running": self.running(), "watched": self.watched}

    def start(self, dev, steps, loop=False, name="", from_ms=0, watch=False,
              music_stop_ms=None):
        """Take over this device and play. Any previous run is stopped first."""
        parse_fn = self._get_parse()
        parse_fn(dev)                       # raises on a malformed device
        cues_fn = self._get_cues()
        steps = [{"pose": [float(v) for v in s["pose"]],
                  "t": max(0, int(s.get("t", 0))),
                  "hold": max(0, int(s.get("hold", 0))),
                  # cues travel through the API as the file's own step lines
                  # (`play: song.mp3`), so an editor can carry steps it does
                  # not understand; they become commands here, once.
                  "cues": cues_fn(s.get("cues")),
                  "cues_after": cues_fn(s.get("cues_after"))}
                 for s in steps]
        if len(steps) < 2:
            raise ValueError("a show needs at least two keyframes")
        for s in steps:
            if len(s["pose"]) != 10:
                raise ValueError("every keyframe needs 10 joint angles")
        # STOP AND CLAIM UNDER ONE LOCK. stop() read self.thread outside it, so
        # two POSTs for the same robot could each find nothing to stop and each
        # spawn a clock - two threads sending POSE to one arm, which is the
        # exact fault check_takeover exists to prevent and could never see.
        # Found 2026-08-21.
        with self._starting:
            self.stop()
            with self.lock:
                self.dev, self.steps, self.loop, self.name = dev, steps, bool(loop), name
                self.music_stop_ms = (None if music_stop_ms is None
                                      else max(0, int(music_stop_ms)))
                self.total_ms = self.total(steps)
                self.at_ms = max(0, min(int(from_ms), self.total_ms))
                self.step, self.last, self.error = -1, "", ""
                self.started_at = time.time()
                self.watched, self.last_beat = bool(watch), time.monotonic()
                # set HERE, not in the thread: a status read straight after
                # start() must already say the entry travel is under way
                self.entering = self.at_ms <= steps[0]["hold"]
            # A FRESH EVENT PER RUN. stop_flag is how the old clock hears
            # "stop"; clearing one shared event here would also release a run
            # whose thread stop() gave up waiting for - and two clocks would
            # play one arm. The old thread keeps the old, SET event.
            flag = threading.Event()
            self.stop_flag = flag
            self.thread = threading.Thread(target=self._run, args=(flag,),
                                           daemon=True)
            self.thread.start()
            return self.status()

    def stop(self, freeze=True, why=""):
        """Stop playing. `freeze` also tells the module to hold where it is."""
        th = self.thread
        timer, self._music_timer = self._music_timer, None
        if timer and timer.is_alive():
            # the moves are over but the track was still playing on its
            # timer: Stop means quiet now, not when the timer comes round
            timer.cancel()
            try:
                self._say("PLAY STOP")
            except Exception:               # noqa: BLE001
                pass
        if th and th.is_alive():
            self.stop_flag.set()
            th.join(timeout=3.0)
            if th.is_alive():
                # Its OWN event is set, so it exits at its next wake-up even
                # though we stopped waiting - but say so; silence would read
                # as stopped when a command is still in flight.
                with self.lock:
                    self.error = "the previous show was still finishing"
            if freeze:
                try:
                    self._say("STOP")
                except Exception as e:      # noqa: BLE001 - a dead cable must
                    self.error = str(e)     # not stop us from marking it stopped
            if self._had_music():
                # A24-18 made the board's own STOP silence the speaker, but the
                # show is stopped here on boards that may still be older, and
                # stopall stops without freezing at all. Music over a robot that
                # has already frozen is what a panic stop must never leave.
                try:
                    self._say("PLAY STOP")
                except Exception:           # noqa: BLE001
                    pass
        self.thread = None
        if why:
            with self.lock:
                self.error = why
        return self.status()

    # ---- the clock itself ----
    def _music_off(self, flag):
        """The show's track has played as long as the show asked (music_end)."""
        if flag is not self.stop_flag:
            return                          # a newer run owns the speaker now
        try:
            self._say("PLAY STOP")
        except Exception as e:              # noqa: BLE001
            with self.lock:
                self.error = "music stop: %s" % e

    def _say(self, c):
        cmd = self._get_cmd()
        r = cmd(self.dev, c)
        with self.lock:
            self.last = r
        return r

    @staticmethod
    def _took(reply, asked):
        """How long the move really takes: the board may lengthen T (safety cap,
        servo limit) and says so as `OK pose T=<ms>ms`. Waiting only the asked
        time sent the next pose before the arm arrived (bench 2026-09-17)."""
        m = re.search(r"T=(\d+)ms", reply or "")
        return max(asked, int(m.group(1))) if m else asked

    def _sleep(self, flag, seconds):
        """Wait, but wake up immediately when someone presses stop - or when
        the watching page has frozen (see BEAT_TIMEOUT)."""
        end = time.monotonic() + max(0.0, seconds)
        while True:
            left = end - time.monotonic()
            if flag.wait(max(0.0, min(left, 0.1))):
                return False
            with self.lock:
                silent = self.watched and time.monotonic() - self.last_beat > self.BEAT_TIMEOUT
            if silent:
                flag.set()
                with self.lock:
                    self.error = ("Studio stopped answering (the page froze?), so the "
                                  "show was stopped to keep the robot safe")
                try:
                    self._say("STOP")
                except Exception:           # noqa: BLE001 - stopping is best effort
                    pass
                return False
            if left <= 0:
                return True

    def _run(self, flag):
        try:
            self._misses = 0
            # Take the robot: a module playing its own sequence would otherwise
            # be a second clock. Newer firmware also does this by itself when
            # the first POSE arrives; saying it explicitly keeps older boards
            # right and makes the intent visible on the wire.
            self._say("MOVE STOP")
            while True:
                if not self._play_once(flag):
                    return
                if not self.loop:
                    return
                with self.lock:
                    self.at_ms = 0
        except Exception as e:              # noqa: BLE001
            with self.lock:
                self.error = str(e)
            self._quiet_after_failure(flag)

    def _move(self, flag, pose, t):
        """Send one pose; a missing reply is counted, not fatal (MAX_MISSES)."""
        try:
            reply = self._say(self._pose_cmd(pose, t))
        except OSError as e:                # no reply, or the cable/WiFi went away
            if flag is not self.stop_flag:
                raise                       # an abandoned run: let it end
            self._misses += 1
            if self._misses >= self.MAX_MISSES:
                raise
            with self.lock:
                self.error = "%s - the show carried on" % e
            return ""
        self._misses = 0
        return reply

    def _quiet_after_failure(self, flag):
        """A show that died must not leave its song playing over a still arm."""
        if flag is not self.stop_flag or flag.is_set() or not self._had_music():
            return                          # a newer run, or stop(), owns the speaker
        timer, self._music_timer = self._music_timer, None
        if timer:
            timer.cancel()
        try:
            self._say("PLAY STOP")
        except Exception:                   # noqa: BLE001 - best effort
            pass

    def _play_once(self, flag):
        """One pass through the steps, from self.at_ms. False = stopped."""
        # where in the show at_ms lands: which step, and how much of it is left
        start_i, into, hold_left = 1, 0, 0
        clock = self.steps[0].get("hold", 0)
        at = self.at_ms
        if at <= clock:
            # still at (or before) the start pose — put the robot on it first
            t = max(self.MIN_T, self.steps[0].get("t", 0) or self.MIN_T)
            if flag.is_set():
                return False
            self._mark(0, at)
            try:
                t = self._took(self._move(flag, self.steps[0]["pose"], t), t)
                if not self._sleep(flag, t / 1000.0):
                    return False
            finally:
                with self.lock:
                    self.entering = False
            # THE SHOW STARTS ON ITS FIRST POSE, music and all. The first pose's
            # cues used to go out BEFORE the walk there, so the song was already
            # seconds in when the moves began (user 2026-09-27: *move to the
            # start pose first, then start everything at the same time*). Time
            # 0 on Studio's bar is the arm standing on that pose - so is this.
            self._cues(self.steps[0])
            # and a wait on that first pose is on the bar too: stand it out
            hold_left = clock - at
        else:
            for i in range(1, len(self.steps)):
                seg = self.steps[i]["t"]
                if at < clock + seg:
                    start_i, into = i, at - clock
                    break
                clock += seg
                if at < clock + self.steps[i].get("hold", 0):
                    # resumed inside a hold: wait what is LEFT of it first, or
                    # the next move goes out early (A26-50)
                    hold_left = clock + self.steps[i].get("hold", 0) - at
                    start_i, into = i + 1, 0
                    clock += self.steps[i].get("hold", 0)
                    break
                clock += self.steps[i].get("hold", 0)
                start_i = i + 1

        if hold_left and not self._sleep(flag, hold_left / 1000.0):
            return False
        # ONE CLOCK FOR THE WHOLE RUN. Each move used to sleep its T AFTER the
        # board had answered, so every command's round trip (and each cue's)
        # was added on top and never paid back - a long show drifted seconds
        # behind the time bar (user 2026-09-27: bar 49 s, robot there at 52 s).
        # Now each move leaves on a deadline counted from the start. A move
        # the board lengthens still pushes the deadline out: the arm has to
        # arrive before the next pose goes.
        due = time.monotonic()
        if self.music_stop_ms is not None and self._music_timer is None:
            # started ONCE per run, on the show's clock where this pass begins
            pos = at + hold_left             # where the show's clock stands now
            t = threading.Timer(max(0, self.music_stop_ms - pos) / 1000.0,
                                self._music_off, args=(flag,))
            t.daemon = True
            self._music_timer = t
            t.start()
        for i in range(start_i, len(self.steps)):
            s = self.steps[i]
            # A resumed move gets the time it has LEFT, not the whole time, or
            # the robot replays a move the editor has already been through.
            left = max(self.MIN_T, s["t"] - into) if into else max(self.MIN_T, s["t"])
            into = 0
            if flag.is_set():
                return False
            self._mark(i, self._elapsed_to(i))
            self._cues(s)
            # A real stall (a retried command, a slow cable) is not caught up
            # by rushing the next moves: past this much late, the clock
            # restarts from now. Small round trips are still paid back.
            if time.monotonic() - due > self.CATCH_UP_S:
                due = time.monotonic()
            took = self._took(self._move(flag, s["pose"], left), left)
            due += took / 1000.0
            if not self._sleep(flag, due - time.monotonic()):
                return False
            if s["hold"]:
                due += s["hold"] / 1000.0
                if not self._sleep(flag, due - time.monotonic()):
                    return False
        self._mark(len(self.steps) - 1, self.total_ms)
        for c in self.steps[-1].get("cues_after") or []:
            self._say(c)
        return True

    def _had_music(self):
        """Did this show start any audio? Only then is PLAY STOP worth sending
        - a board with no speaker answers ERR, and that would be the last thing
        the status line said about a stop that worked."""
        with self.lock:
            steps = list(self.steps)
        return any(c.startswith("PLAY") and not c.upper().startswith("PLAY STOP")
                   for s in steps
                   for c in (s.get("cues") or []) + (s.get("cues_after") or []))

    def _cues(self, step):
        """Fire this keyframe's cues (PLAY, VOL, RGB) before its move starts.

        A cue never blocks the clock: it is sent and the move goes out behind
        it, so music that fails to start cannot freeze the show. Cues on steps
        a resume SKIPPED are not fired - a module cannot seek inside an mp3,
        so restarting the track from the top would be worse than silence.
        """
        cues_fn = self._get_cues()
        for c in step.get("cues") or []:
            try:
                self._say(c)
            except Exception as e:          # noqa: BLE001
                with self.lock:
                    self.error = "cue %s: %s" % (c, e)

    def _pose_cmd(self, pose, t):
        vals = " ".join(("%g" % round(v, 1)) for v in pose)
        return "POSE %s T %d" % (vals, int(t))

    def _elapsed_to(self, i):
        ms = self.steps[0].get("hold", 0)
        for k in range(1, i):
            ms += self.steps[k]["t"] + self.steps[k].get("hold", 0)
        return ms

    def _mark(self, step, at_ms):
        with self.lock:
            self.step, self.at_ms = step, at_ms
