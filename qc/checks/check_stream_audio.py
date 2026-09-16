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
        src = (fw / ("src/modules/%s/%sModule.cpp" % (name, name))
               ).read_text(encoding="utf-8", errors="replace")
        t.contains(src, 'cmd == "STREAM"', "%s routes STREAM" % name)

    # ---- two sources, and no picture -----------------------------------
    # Chrome and Edge on Windows only give system audio together with a screen
    # or a tab, so the picker cannot be avoided for the PC's own sound - but
    # the video is stopped at once (only the sound was ever sent), and TALKING
    # through the robot uses the microphone, which needs no picker at all.
    # The user asked why a whole screen had to be shared, 2026-09-07.
    page = (fw / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    t.contains(page, "getUserMedia({audio:",
               "the microphone is its own source, with no screen picker")
    t.contains(page, "castStream.getVideoTracks().forEach(t=>t.stop())",
               "and the shared picture is stopped the moment it arrives")
    fn = page[page.find("async function castStart("):]
    fn = fn[:fn.find("function castStop(")]
    t.ok(fn.find("getVideoTracks") < fn.find("createMediaStreamSource")
         or "createMediaStreamSource" not in fn,
         "the video goes before any audio is wired up",
         "leaving it running keeps the browser's sharing bar and the capture "
         "alive for a picture nobody wanted")

    # ---- the gate -----------------------------------------------------
    t.ok(hub_auth.gated("/api/stream/start", "POST"),
         "starting live audio needs a login, like every command that acts")
    t.ok(hub_auth.gated("/api/stream/feed", "POST"),
         "and so does feeding it")
    t.ok(not hub_auth.gated("/api/stream/stop", "POST"),
         "but silencing it never does",
         "a robot talking over a room must be stoppable by whoever is standing "
         "next to it - the same rule as /api/play/stop and /api/stopall")
