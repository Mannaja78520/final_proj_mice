"""Answer to `mice.local`, so nobody has to type an IP address.

WHY
---
The hub's address changes: a laptop gets one IP on the venue WiFi, another on
its own hotspot, and another again tomorrow. Everyone who wants to reach it
therefore has to be told a number, and numbers get misread across a room —
192.168.137.1 typed as 192.168.13.71 is the single most common way to fail to
open this hub.

A name does not change. `mice.local` is resolved by multicast DNS, which every
phone, Mac and modern Windows already speaks, with nothing installed anywhere.

WHY THE QR EXISTS AS WELL
-------------------------
Venue networks very often block multicast between clients — guest isolation
does it by design — and then mDNS simply does not answer. That is not a fault
to fix here; it is why the plan settled on QR *and* mDNS rather than one of
them. When multicast is blocked the QR still works, and when a phone camera is
not to hand the name still works.

WHAT THIS IS NOT
----------------
Not a full mDNS stack. It answers A queries for one name, on IPv4, and it
announces itself when it starts so a listener does not have to ask. It does not
publish services (_http._tcp), does not do IPv6, and does not defend the name
against a second machine claiming it — the sensible response to two hubs both
calling themselves `mice` is to notice, not to fight, and the hub list on the
network screen is where that shows up.
"""
import socket
import struct
import threading

GROUP = "224.0.0.251"          # the mDNS multicast address, fixed by the RFC
PORT = 5353
TTL = 120                      # seconds a resolver may cache the answer


def _labels(name):
    """A DNS name as length-prefixed labels: mice.local -> 4mice5local0."""
    out = b""
    for part in name.strip(".").split("."):
        out += bytes([len(part)]) + part.encode("ascii")
    return out + b"\x00"


def _read_name(data, at):
    """Read a name, following the one kind of pointer a query can contain."""
    parts = []
    seen = 0
    while at < len(data) and seen < 20:
        n = data[at]
        if n == 0:
            at += 1
            break
        if n & 0xC0 == 0xC0:                      # compression pointer
            at = ((n & 0x3F) << 8) | data[at + 1]
            seen += 1
            continue
        parts.append(data[at + 1:at + 1 + n].decode("ascii", "replace"))
        at += 1 + n
    return ".".join(parts), at


def questions(packet):
    """Every name asked for in this packet, lower-cased. [] if it is not a query."""
    if len(packet) < 12:
        return []
    flags, qd = struct.unpack(">HH", packet[2:6])
    if flags & 0x8000:                            # this is an answer, not a query
        return []
    out, at = [], 12
    for _ in range(qd):
        name, at = _read_name(packet, at)
        if at + 4 > len(packet):
            break
        qtype, _qclass = struct.unpack(">HH", packet[at:at + 4])
        at += 4
        if qtype in (1, 255):                     # A, or ANY
            out.append(name.lower())
    return out


def answer(name, ip):
    """An mDNS response packet saying `name` is at `ip`."""
    header = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)   # authoritative answer
    body = _labels(name)
    body += struct.pack(">HHIH", 1, 0x8001, TTL, 4)          # A, IN + cache-flush
    body += socket.inet_aton(ip)
    return header + body


class Responder:
    """Answers `<name>.local` with an address, on its own thread.

    `ip_of` is called for every answer rather than being stored, because the
    address is exactly the thing that changes: a laptop that moves from the
    venue WiFi to its own hotspot keeps running, and an mDNS responder that
    kept answering with the old address would be worse than none at all.
    """

    def __init__(self, name, ip_of):
        self.name = name.lower().rstrip(".")
        if not self.name.endswith(".local"):
            self.name += ".local"
        self.ip_of = ip_of
        self.sock = None
        self.thread = None
        self.stop = threading.Event()
        self.error = ""
        self.answered = 0

    def start(self):
        """Begin answering. Never raises: no name is a nuisance, not a failure."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass                              # not on Windows, and not needed
            s.bind(("", PORT))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                         socket.inet_aton(GROUP) + socket.inet_aton("0.0.0.0"))
            s.settimeout(1.0)
            self.sock = s
        except OSError as e:
            # Something else already holds 5353 - Bonjour on Windows, avahi on
            # Linux. That is not an error worth stopping the hub for: the QR
            # still works, and this says so rather than dying quietly.
            self.error = "mice.local is not available (%s)" % e
            return False
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        self.announce()
        return True

    def announce(self):
        """Say who we are without being asked, so a listener need not wait."""
        try:
            self.sock.sendto(answer(self.name, self.ip_of()), (GROUP, PORT))
            return True
        except OSError:
            return False

    def _serve(self):
        while not self.stop.is_set():
            try:
                data, addr = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            if self.name not in questions(data):
                continue
            pkt = answer(self.name, self.ip_of())
            # STRAIGHT BACK first. The unicast reply is the one that reaches
            # the device that asked; the multicast copy is a courtesy to
            # everything else listening. Sending the courtesy first meant that
            # on a network where multicast fails - which is the case this whole
            # feature exists for - the failure threw and the real answer was
            # never sent at all.
            try:
                self.sock.sendto(pkt, addr)
                self.answered += 1
            except OSError:
                continue
            try:
                self.sock.sendto(pkt, (GROUP, PORT))
            except OSError:
                pass                                    # no multicast route here

    def close(self):
        self.stop.set()
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
