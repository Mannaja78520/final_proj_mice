"""The REAL firmware, running on an emulated ESP32 (Espressif's QEMU fork).

`fake_serial` and `fake_wifi` are Python stand-ins that answer the way we
BELIEVE the firmware answers. This runs the compiled `firmware.bin` itself, so
CommandRouter, the identity store, BusUpdate (FWBEGIN/FWDATA/FWEND) and the OTA
slot logic are the genuine code, on a chip that boots from a flash image.

    qemu_board.find_qemu()                -> path or None
    qemu_board.images("mice_nong")        -> (bootloader, partitions, app) or None
    with QemuBoard("mice_nong") as b:     # boots, waits for "[boot] ready"
        b.cmd("PING")                     # one command line -> one reply line

What QEMU does NOT have (measured 2026-11-20): the WiFi radio (register_chipv7_phy
crashes on start), so the seeded NVS sets `wmode=off`; no SD card; servos and
motors are not wired to anything. Only the command/flash/identity logic is real.
Still tested against an emulator, not a board.
"""
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent.parent
FIRMWARE = CODE / "firmware"
NVS_IMAGE = CODE / "qc" / "data" / "qemu_nvs_nong_wifi_off.bin"
NVS_OFFSET = 0x9000
FLASH_SIZE = 4 * 1024 * 1024
EXE = "qemu-system-xtensa" + (".exe" if os.name == "nt" else "")


def find_qemu():
    """MICE_QEMU, then `.local/qemu/bin`, then PATH (tools/qemu_esp32.py installs the 2nd)."""
    for p in (os.environ.get("MICE_QEMU"), CODE / ".local" / "qemu" / "qemu" / "bin" / EXE,
              shutil.which("qemu-system-xtensa")):
        if p and Path(p).is_file():
            return str(p)
    return None


def images(env):
    d = FIRMWARE / ".pio" / "build" / env
    parts = (d / "bootloader.bin", d / "partitions.bin", d / "firmware.bin")
    return parts if all(p.is_file() for p in parts) else None


def flash_image(parts, nvs=NVS_IMAGE):
    """bootloader + partition table + app + the seeded NVS, as one 4 MB flash dump."""
    boot, table, app = parts
    flash = bytearray(b"\xff" * FLASH_SIZE)
    for off, p in ((0x1000, boot), (0x8000, table), (0x10000, app)):
        data = Path(p).read_bytes()
        flash[off:off + len(data)] = data
    seed = Path(nvs).read_bytes()
    flash[NVS_OFFSET:NVS_OFFSET + len(seed)] = seed
    return bytes(flash)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QemuBoard:
    """One emulated board. UART0 is a TCP socket, so cmd() is the same line
    protocol the hub speaks over USB."""

    def __init__(self, env="mice_nong", boot_timeout=60, flash=None, nvs=NVS_IMAGE, bus=False):
        self.nvs = nvs
        self.bus = bus                      # expose UART2 (RS485) as a TCP port: self.bus_port
        self.bus_port = None
        self.env = env
        self.boot_timeout = boot_timeout
        self.log = ""                       # everything the board printed
        self.proc = None
        self.sock = None
        self.dir = Path(tempfile.mkdtemp(prefix="mice_qemu_"))
        self.flash_path = self.dir / "flash.bin"
        self._flash = flash

    # ---- lifecycle --------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *a):
        self.stop()

    def start(self):
        qemu = find_qemu()
        if not qemu:
            raise RuntimeError("QEMU for ESP32 not found (python tools/qemu_esp32.py install)")
        if self._flash is None:
            parts = images(self.env)
            if not parts:
                raise RuntimeError("no %s build (pio run -e %s)" % (self.env, self.env))
            self._flash = flash_image(parts, self.nvs)
        self.flash_path.write_bytes(self._flash)
        port = _free_port()
        uarts = ["-serial", "tcp:127.0.0.1:%d,server=on,wait=off" % port]
        if self.bus:                                      # UART1 unused, UART2 = RS485 (Serial2)
            self.bus_port = _free_port()
            uarts += ["-serial", "null", "-serial", "tcp:127.0.0.1:%d,server=on,wait=off" % self.bus_port]
        # wdt_disable: without it the emulated bootloader trips the watchdog in a loop.
        self.proc = subprocess.Popen(
            [qemu, "-display", "none", "-monitor", "none", "-machine", "esp32",
             "-global", "driver=timer.esp32.timg,property=wdt_disable,value=true",
             "-drive", "file=%s,if=mtd,format=raw" % self.flash_path,
             *uarts],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        end = time.time() + 10
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                if time.time() > end:
                    raise RuntimeError("QEMU did not open its serial port")
                time.sleep(0.1)
        self.sock.settimeout(0.2)
        self.wait_for("[boot] ready", self.boot_timeout)
        self.wait_for("\n", 5, since=self.log.rindex("[boot] ready"))   # finish that line

    def stop(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.proc:
            self.proc.kill()
            self.proc.wait()
            self.proc = None
        shutil.rmtree(self.dir, ignore_errors=True)

    def reboot(self, timeout=90):
        """REBOOT, then wait for the next boot to reach "[boot] ready" again."""
        mark = len(self.log)
        self.cmd("REBOOT")
        ok = self.wait_for("[boot] ready", timeout, since=mark)
        self.wait_for("\n", 5, since=self.log.rindex("[boot] ready"))
        return ok

    # ---- serial -----------------------------------------------------
    def _pump(self):
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            return False
        except OSError:
            return False
        self.log += chunk.decode("utf-8", "replace")
        return bool(chunk)

    def wait_for(self, text, timeout=10, since=0):
        end = time.time() + timeout
        while time.time() < end:
            if text in self.log[since:]:
                return True
            self._pump()
        return text in self.log[since:]

    def write(self, line):
        self.sock.sendall(line.encode() + b"\n")

    def ask(self, line, prefix, timeout=10):
        """For the RS485 master: send `#<id> CMD` and wait for the reply line that
        starts with `prefix` (`@9 `). The master first prints `-> sent...`, the
        module's answer arrives later. Returns the line, or "" on timeout."""
        mark = len(self.log)
        self.write(line)
        end = time.time() + timeout
        while time.time() < end:
            self._pump()
            for ln in self.log[mark:].split("\n")[:-1]:
                if ln.strip().startswith(prefix):
                    return ln.strip()
        return ""

    def cmd(self, line, timeout=10):
        """Send one command line; return its reply line. Log lines start with
        '[' (`[boot] ...`, `[ 123][E]...`) and are skipped; the echo is too."""
        mark = len(self.log)
        self.write(line)
        end = time.time() + timeout
        while time.time() < end:
            self._pump()
            done = self.log[mark:].split("\n")[:-1]          # complete lines only
            for ln in done:
                s = ln.strip()
                if s and not s.startswith("[") and s != line.strip():
                    return s
        return ""


class Rs485Bus:
    """A shared RS485 pair for several QemuBoards: whatever one board's UART2
    sends is delivered to every OTHER board's UART2 (the real bus is one wire
    pair, so a talker hears no echo here - the firmware ignores its own anyway)."""

    def __init__(self, boards):
        import threading
        self.socks = [socket.create_connection(("127.0.0.1", b.bus_port), timeout=5) for b in boards]
        self.frames = []                    # every chunk that crossed the bus: (sender index, bytes)
        self.timed = []                     # (sender index, bytes, time.time()), appended in one step
        self._stop = False
        self._threads = [threading.Thread(target=self._pipe, args=(i,), daemon=True)
                         for i in range(len(self.socks))]
        for th in self._threads:
            th.start()

    def _pipe(self, i):
        s = self.socks[i]
        s.settimeout(0.2)
        while not self._stop:
            try:
                data = s.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not data:
                return
            self.frames.append((i, data))
            self.timed.append((i, data, time.time()))
            for j, o in enumerate(self.socks):
                if j != i:
                    try:
                        o.sendall(data)
                    except OSError:
                        pass

    def close(self):
        self._stop = True
        for s in self.socks:
            s.close()

    def text(self, since=0):
        """Everything that crossed the bus from frame number `since` on."""
        return b"".join(d for _, d in self.frames[since:]).decode("utf-8", "replace")
