"""Live audio from this PC to a module's speaker, over UDP (A24-32).

The board (core/AudioStream) listens on a UDP port and plays 16-bit mono PCM
as it arrives, straight to I2S - nothing decodes, nothing touches the SD card.
This is the sending half: one thread, a queue of PCM chunks, and a paced
sender, because UDP will happily accept everything at once and a board with a
200 ms buffer cannot.

TWO SOURCES, one pipe:

  * a WAV FILE on this PC - what proves the path end to end, and what a show
    can fire at a moment;
  * whatever the PC is PLAYING - the browser captures that (getDisplayMedia,
    the same call rgb.html already uses for its music mode), downsamples it,
    and posts the chunks here.

WHY PACED, AND WHY THE QUEUE IS SMALL. Sending faster than real time overruns
the board's ring buffer and the extra is dropped - audible as a gap, not as
speed. So chunks leave on the clock, and the queue holds about a second: if
the source falls behind, the right failure is a short silence, not a growing
delay that never recovers.
"""
import queue
import socket
import threading
import time
import wave

# One datagram is 20 ms of audio. Small enough to stay inside a 1460-byte
# Ethernet payload at every rate we offer (22050 Hz mono = 882 bytes), so a
# packet is never fragmented, and a lost one costs 20 ms rather than a word.
CHUNK_MS = 20
DEF_PORT = 4210
DEF_RATE = 22050
QUEUE_SECONDS = 1.0
# How far behind the clock the sender may fall before it gives up catching
# up. The board primes at half of its 200 ms ring, so there is ~100 ms of room
# on top: a catch-up burst bigger than that is dropped on the board and heard
# as a crack. It was 0.5 s, which let a late browser chunk trigger a 500 ms
# burst into 100 ms of room (2026-09-28).
CATCHUP_S = 0.04


class Sender:
    """One sender per hub. Feed it PCM; it paces datagrams to the board."""

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.stop_flag = threading.Event()
        self.q = queue.Queue()
        self.ip = ""
        self.port = DEF_PORT
        self.rate = DEF_RATE
        self.name = ""
        self.sent = 0            # datagrams
        self.bytes = 0
        self.dropped = 0         # chunks thrown away because the queue was full
        self.error = ""
        self.started = 0.0

    # ---- what a caller sees ----
    def status(self):
        with self.lock:
            return {"running": self.running(), "ip": self.ip, "port": self.port,
                    "rate": self.rate, "source": self.name, "packets": self.sent,
                    "bytes": self.bytes, "dropped": self.dropped,
                    "seconds": round(time.time() - self.started, 1) if self.started else 0,
                    "error": self.error}

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def chunk_bytes(self):
        return int(self.rate * CHUNK_MS / 1000) * 2      # 16-bit mono

    # ---- the pipe ----
    def start(self, ip, port=DEF_PORT, rate=DEF_RATE, name="live"):
        """Open the pipe. Feeding is separate, so a caller can start before it
        has any audio - which is what the browser does."""
        if not ip:
            raise ValueError("which module? this needs its address")
        self.stop()
        with self.lock:
            self.ip, self.port, self.rate, self.name = ip, int(port), int(rate), name
            self.sent = self.bytes = self.dropped = 0
            self.error = ""
            self.started = time.time()
        self.q = queue.Queue()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run, args=(self.stop_flag,),
                                       daemon=True)
        self.thread.start()
        return self.status()

    def feed(self, pcm: bytes):
        """Hand over 16-bit mono PCM at the sender's rate. Returns what it took."""
        if not self.running():
            return 0
        limit = int(self.rate * QUEUE_SECONDS * 2 / max(1, self.chunk_bytes()))
        step = self.chunk_bytes()
        took = 0
        for i in range(0, len(pcm), step):
            if self.q.qsize() >= limit:
                with self.lock:
                    self.dropped += 1
                break            # the source is ahead of real time: let it go
            self.q.put(pcm[i:i + step])
            took += len(pcm[i:i + step])
        return took

    def feed_all(self, pcm: bytes, timeout=60.0):
        """Feed every byte, waiting for room - for a FILE, which is not live.

        feed() drops what will not fit, which is right for a live capture (the
        past is not worth delaying the present for) and wrong for a file: the
        first test streamed one second of a four-second tone and stopped,
        because the whole file was offered at once and the rest fell on the
        floor (2026-09-07).
        """
        step = self.chunk_bytes()
        limit = int(QUEUE_SECONDS * 1000 / CHUNK_MS)
        end = time.time() + timeout
        for i in range(0, len(pcm), step):
            while self.running() and self.q.qsize() >= limit:
                if time.time() > end:
                    return i
                time.sleep(CHUNK_MS / 2000.0)
            if not self.running():
                return i
            self.q.put(pcm[i:i + step])
        return len(pcm)

    def stop(self):
        th = self.thread
        if th and th.is_alive():
            self.stop_flag.set()
            th.join(timeout=2.0)
        self.thread = None
        return self.status()

    def _run(self, flag):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # The clock is the audio itself: one chunk every CHUNK_MS, measured
        # from the start rather than by sleeping CHUNK_MS each time, which
        # drifts by however long the send took.
        t0 = time.time()
        n = 0
        try:
            while not flag.is_set():
                try:
                    chunk = self.q.get(timeout=0.2)
                except queue.Empty:
                    continue          # nothing to send yet: the board holds
                sock.sendto(chunk, (self.ip, self.port))
                n += 1
                with self.lock:
                    self.sent = n
                    self.bytes += len(chunk)
                due = t0 + n * (CHUNK_MS / 1000.0)
                nap = due - time.time()
                if nap > 0:
                    flag.wait(nap)
                elif nap < -CATCHUP_S:
                    # re-base, don't sprint: late audio plays late, not crushed
                    t0 = time.time() - n * (CHUNK_MS / 1000.0) - CATCHUP_S
        except Exception as e:                       # noqa: BLE001
            with self.lock:
                self.error = str(e)
        finally:
            sock.close()


def resample(a, rate, want_rate):
    """16-bit mono samples (array 'h') from rate to want_rate.

    It used to pick the nearest sample. Going down from 44.1 kHz that folds
    every tone above 11 kHz back into the audible band - cymbals and 's'
    sounds come out as harsh fizz - and going up it is a staircase. Now: each
    output sample is the AVERAGE of the input it covers when going down (a
    box low-pass, enough to stop the folding), and a straight line between
    neighbours when going up. Pure Python, because audioop is gone in 3.13
    and the exe does not carry numpy.
    """
    import array
    n = len(a)
    if not n or rate == want_rate:
        return a
    m = int(n * want_rate / rate)
    out = array.array("h", [0]) * m
    r = rate / want_rate
    if r > 1:                                  # down: average the window
        # Twice: a box over a box is a triangle, about twice the rejection
        # of one box (a 15 kHz tone at 44.1 -> 22.05 kHz: -6 dB with one
        # pass, -12 dB with two). Prefix sums keep both O(1) per sample.
        k = max(1, int(round(r)))
        pre = [0] * (n + 1)
        acc = 0
        for i in range(n):
            acc += a[i]
            pre[i + 1] = acc
        a = [(pre[min(n, i + k)] - pre[i]) // (min(n, i + k) - i) for i in range(n)]
        pre = [0] * (n + 1)
        acc = 0
        for i in range(n):
            acc += a[i]
            pre[i + 1] = acc
        for j in range(m):
            lo = int(j * r)
            hi = min(n, max(lo + 1, int((j + 1) * r)))
            out[j] = (pre[hi] - pre[lo]) // (hi - lo)
    else:                                      # up: linear between neighbours
        for j in range(m):
            x = j * r
            i = int(x)
            fr = x - i
            b = a[i + 1] if i + 1 < n else a[i]
            out[j] = int(a[i] + (b - a[i]) * fr)
    return out


def wav_pcm(path, want_rate=DEF_RATE):
    """A wav file -> 16-bit mono PCM at want_rate. Stereo is averaged."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError("only 16-bit wav files, this one is %d-bit"
                             % (w.getsampwidth() * 8))
        ch, rate = w.getnchannels(), w.getframerate()
        raw = w.readframes(w.getnframes())
    import array
    a = array.array("h")
    a.frombytes(raw)
    if ch > 1:                                  # average the channels to mono
        mono = array.array("h", [0]) * (len(a) // ch)
        for i in range(len(mono)):
            mono[i] = sum(a[i * ch:(i + 1) * ch]) // ch
        a = mono
    return resample(a, rate, want_rate).tobytes()
