"""Live audio from the PC to a robot's speaker, over UDP (A24-32).

The user asked for the robot to play what the PC plays, like a bluetooth
speaker. It does not go through the web server and it does not touch the SD
card: the board listens on a UDP port, fills a 200 ms ring buffer and feeds
I2S from the module loop.

MEASURED ON THE REAL BOARD, 2026-09-07 (nong id 67, MAX98357A, WiFi): 250
datagrams, 0 dropped, 0 lost, and the longest gap between two feeds was 9 ms
against a 200 ms buffer - twenty times the headroom, with ten servos, RS485
and the web server all running. That number is the acceptance test Gemini Pro
asked for, and the board reports it in `STREAM?` so it can be watched instead
of assumed.

What this holds, against a real socket rather than a mock:

  * the sender PACES - a 3-second sound takes about 3 seconds to send, because
    a board with 200 ms of buffer cannot take it all at once;
  * a FILE loses nothing: feed() drops what will not fit (right for live
    audio, wrong for a file), and that shipped a 4-second tone that played for
    1 second until feed_all() was written;
  * every datagram fits in one Ethernet frame, so a packet is never split;
  * the firmware side exists and is declared in DATA - core/AudioStream, the
    STREAM command for both types that carry a speaker, and the routing;
  * starting a stream is gated like every other command that makes the rig do
    something, and STOPPING it is not - silence must never need a password.
"""
import re
import socket
import sys
import threading
import time

import qc as F

AREA = "hub"
TITLE = "live audio streams to a board, paced, whole, and gated"


def run(t):
    sys.path.insert(0, str(F.HUB))
    import stream_audio                                    # noqa: E402
    import hub_auth                                        # noqa: E402

    # ---- a real socket on this PC, standing in for the board ----------
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.4)
    port = sock.getsockname()[1]

    got = []

    def listen():
        while True:
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                if done.is_set():
                    return
                continue
            except OSError:
                return
            got.append((time.time(), len(data)))

    done = threading.Event()
    ear = threading.Thread(target=listen, daemon=True)
    ear.start()

    rate = 22050
    # LONGER THAN THE QUEUE HOLDS (about a second). With a shorter sound the
    # queue never fills, so the difference between "wait for room" and "drop
    # what will not fit" cannot show - and that difference is the bug this
    # check exists for: a 4-second tone that played for 1 second.
    seconds = 3.0
    pcm = bytes(int(rate * seconds) * 2)          # silence is fine: this is timing
    s = stream_audio.Sender()
    s.start("127.0.0.1", port, rate, "qc")
    t0 = time.time()
    sent = s.feed_all(pcm)
    while s.q.qsize() and time.time() - t0 < 9:
        time.sleep(0.02)
    time.sleep(0.3)
    took = time.time() - t0
    s.stop()
    done.set()
    ear.join(timeout=1.5)
    sock.close()

    t.eq(sent, len(pcm), "a file is fed whole, not truncated at the queue")
    t.ok(len(got) >= 140,
         "every chunk of it reached the board (%d datagrams of about 150)" % len(got),
         "three seconds at %d ms a chunk" % stream_audio.CHUNK_MS)
    t.ok(took >= 2.5,
         "and it took about as long as the sound lasts (%.2fs for 3.0s)" % took,
         "sending faster than real time overruns the board's ring buffer and "
         "the extra is silently dropped - it sounds like a gap, not like speed")
    big = [n for _, n in got if n > 1400]
    t.eq(big, [], "no datagram is big enough to be split across two frames")

    # ---- the firmware half exists, and is declared in data -------------
    fw = F.FIRMWARE
    for f in ("src/core/AudioStream.h", "src/core/AudioStream.cpp"):
        t.ok((fw / f).is_file(), "the board carries %s" % f)
    cpp = (fw / "src/core/AudioStream.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(cpp, "WiFiUDP", "it listens on UDP, not on the web server")
    t.ok("max_gap_ms" in cpp and "underruns" in cpp,
         "and reports the starvation numbers the design is judged on",
         "servo timers and the web server can starve the audio task; the "
         "board measures that rather than anyone guessing")

    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                        # noqa: E402
    scopes = {c["scope"] for c in registry.commands() if c["name"] == "STREAM"}
    t.eq(sorted(scopes), ["lift", "nong"],
         "STREAM is declared for both types that wire a speaker")
    for name in ("nong", "lift"):
        src = (fw / ("src/modules/%s/%sModule.cpp" % (name, name.capitalize()))
               ).read_text(encoding="utf-8", errors="replace")
        t.contains(src, 'cmd == "STREAM"', "%s routes STREAM" % name)

    # ---- two sources, and no picture -----------------------------------
    # Chrome and Edge on Windows only give system audio together with a screen
    # or a tab, so the picker cannot be avoided for the PC's own sound - but
    # the video is stopped at once (only the sound was ever sent), and TALKING
    # through the robot uses the microphone, which needs no picker at all.
    # The user asked why a whole screen had to be shared, 2026-09-07.
    page = (fw / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    # the sound engine moved to shared/web/cast.js (one file, three pages)
    eng = (F.CODE / "shared/web/cast.js").read_text(encoding="utf-8", errors="replace")
    t.contains(eng, "getUserMedia({audio:",
               "the microphone is its own source, with no screen picker")
    t.contains(eng, "castStream.getVideoTracks().forEach(t=>t.stop())",
               "and the shared picture is stopped the moment it arrives")
    fn = eng[eng.find("async function castSource("):]
    fn = fn[fn.find("getDisplayMedia("):]
    fn = fn[:fn.find("}catch(e){")]
    t.ok(0 <= fn.find("getVideoTracks") < fn.find("createMediaStreamSource"),
         "the video goes before any audio is wired up",
         "leaving it running keeps the browser's sharing bar and the capture "
         "alive for a picture nobody wanted")

    # ---- the chunk time in the comment is the real one -------------------
    # A24-32's comment said a dropped chunk costs 46 ms. It never did: the
    # graph is 2048 samples at castRate 22050, which is 93. 46 is the figure
    # for 44100. A number in a comment that nobody can check rots, and this one
    # is the number a person uses to decide whether a gap matters (A26-8), so
    # it is computed from the code rather than trusted.
    rate = re.search(r"castRate\s*=\s*(\d+)", eng)
    buf = re.search(r"createScriptProcessor\((\d+)", eng)
    if t.ok(rate and buf, "the page says its sample rate and its buffer size",
            "castRate / createScriptProcessor not found in WebUI.h"):
        want = round(1000 * int(buf.group(1)) / int(rate.group(1)))
        t.contains(eng, "the next one is %d ms away" % want,
                   "and the comment quotes that same chunk time (%d ms)" % want)

    # ---- the cracking: MCLK on the LRC pin (2026-09-28) ------------------
    # SD playback was clean and live sound cracked on the real nong. The
    # library installs I2S with MCLK on GPIO0, and GPIO0 is the nong's LRC
    # pin; play() re-pinned after begin(), AudioStream::start never did, so
    # every stream ran with a broken word clock.
    st = cpp[cpp.find("bool AudioStream::start("):]
    st = st[:st.find("\n}\n")]
    t.ok(0 <= st.find("out_->begin()") < st.find("repin_()"),
         "the stream re-pins I2S right after the driver is installed",
         "without it MCLK sits on GPIO0 = LRC on a nong and the sound cracks")
    ap = (fw / "src/core/AudioPlayer.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(ap, "applyPins(); });", "and the player hands it the same re-pin SD playback uses")

    # ---- the burst after a late chunk ------------------------------------
    # A late browser chunk used to be followed by up to 0.5 s sent at once
    # into the ~100 ms the board has spare - dropped there, heard as a crack.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.05)
    port = sock.getsockname()[1]
    s = stream_audio.Sender()
    s.start("127.0.0.1", port, 22050, "qc-burst")
    one = bytes(s.chunk_bytes())
    s.feed(one)
    time.sleep(0.4)                          # the source is late by 400 ms
    s.feed(one * 15)                         # then 300 ms arrives at once
    arrive = []
    end = time.time() + 1.0
    while time.time() < end:
        try:
            sock.recvfrom(4096)
            arrive.append(time.time())
        except socket.timeout:
            pass
    s.stop()
    sock.close()
    late = arrive[1:]
    burst = [x for x in late if late and x - late[0] < 0.03]
    # The room is the board's, read from its header: it primes at half the
    # ring, so half of BUF_MS is what a burst may fill before it is dropped.
    hdr = (fw / "src/core/AudioStream.h").read_text(encoding="utf-8", errors="replace")
    spare = int(re.search(r"BUF_MS = (\d+);", hdr).group(1)) // 2
    room = spare // stream_audio.CHUNK_MS + 1
    t.ok(len(late) >= 14 and len(burst) <= room,
         "after a late chunk the sender catches up in at most the board's spare "
         "%d ms (%d of %d chunks inside 30 ms, room for %d)"
         % (spare, len(burst), len(late), room),
         "a burst bigger than the board's spare room is dropped on the board")

    # ---- two starters at once leave ONE sender (A4-4) -------------------
    # Measured 2026-09-29 before the lock: 20 racing starts left 8 orphan
    # senders, the survivors draining one queue at twice real time.
    s = stream_audio.Sender()
    gate = threading.Barrier(20)

    def racer():
        gate.wait()
        s.start("127.0.0.1", 9, 22050, "race")
    ths = [threading.Thread(target=racer) for _ in range(20)]
    for th in ths:
        th.start()
    for th in ths:
        th.join(15)
    mine = "mice-audio-sender-%x" % id(s)
    alive = [th for th in threading.enumerate() if th.name == mine and th.is_alive()]
    s.stop()
    t.eq(len(alive), 1, "twenty starts at once leave one sender, not a crowd")

    # ---- a feeder from the last stream never reaches the next -------------
    s = stream_audio.Sender()
    old = s.start("127.0.0.1", 9, 22050, "one")["session"]
    s.start("127.0.0.1", 9, 22050, "two")
    t.eq(s.feed(bytes(s.chunk_bytes() * 3), old), -1,
         "a feed naming an older session is refused")
    t.eq(s.q.qsize(), 0, "and none of it lands in the new stream's queue")
    s.stop()

    # ---- a file is resampled, not sample-picked --------------------------
    import array
    import math
    def peak(freq):
        a = array.array("h", [int(10000 * math.sin(2 * math.pi * freq * i / 44100))
                              for i in range(22050)])
        o = stream_audio.resample(a, 44100, 22050)
        return max(abs(x) for x in o[200:-200])
    hi, lo = peak(15000), peak(1000)
    t.ok(hi < 3500 and lo > 9000,
         "going down to 22 kHz a 15 kHz tone is filtered (%d of 10000 left) "
         "and a 1 kHz tone is kept (%d)" % (hi, lo),
         "nearest-sample picking folds treble back as harsh fizz")

    # ---- the phone road and the mix ---------------------------------------
    wp = (fw / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(wp, 'wsAudio_.setFilter([this](AsyncWebServerRequest* req) {\n'
                   '        return allowedCommand(req, "STREAM ON");',
               "a phone on the robot's WiFi streams to /ws/audio, behind the STREAM gate")
    for box in ("cast_song", "cast_pc", "cast_mic"):
        t.contains(page, 'id="%s"' % box, "the page has its own switch for %s" % box)
    t.contains(eng, "castMix.connect(lp); lp.connect(lim); lim.connect(castNode);",
               "the mix goes through a limiter before it is sent, so two loud "
               "sources summed cannot clip and crack")

    # ---- the gate -----------------------------------------------------
    t.ok(hub_auth.gated("/api/stream/start", "POST"),
         "starting live audio needs a login, like every command that acts")
    t.ok(hub_auth.gated("/api/stream/feed", "POST"),
         "and so does feeding it")
    t.ok(not hub_auth.gated("/api/stream/stop", "POST"),
         "but silencing it never does",
         "a robot talking over a room must be stoppable by whoever is standing "
         "next to it - the same rule as /api/play/stop and /api/stopall")
