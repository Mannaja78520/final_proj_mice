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
import time

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


def _answered(packet):
    """The names an answer packet is answering for."""
    out, at = [], 12
    try:
        _id, _flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", packet[:12])
        for _ in range(qd):                      # skip the question section
            name, at = _read_name(packet, at)
            at += 4
        for _ in range(an):
            name, at = _read_name(packet, at)
            _t, _c, _ttl, dlen = struct.unpack(">HHIH", packet[at:at + 10])
            at += 10 + dlen
            out.append(name.lower())
    except (struct.error, IndexError):
        pass
    return out


def answer(name, ip):
    """An mDNS response packet saying `name` is at `ip`."""
    header = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)   # authoritative answer
    body = _labels(name)
    body += struct.pack(">HHIH", 1, 0x8001, TTL, 4)          # A, IN + cache-flush
    body += socket.inet_aton(ip)
    return header + body


# How often a hub on its fallback name checks whether the short one is free
# again. Long enough that a hub is not probing constantly, short enough that
# the name is back before anyone gives up and types an IP address.
RECLAIM_EVERY = 30


class Responder:
    """Answers `<name>.local` with an address, on its own thread.

    `ip_of` is called for every answer rather than being stored, because the
    address is exactly the thing that changes: a laptop that moves from the
    venue WiFi to its own hotspot keeps running, and an mDNS responder that
    kept answering with the old address would be worse than none at all.
    """

    def __init__(self, name, ip_of, fallback=""):
        self.name = name.lower().rstrip(".")
        if not self.name.endswith(".local"):
            self.name += ".local"
        # The name to retreat to if somebody else turns out to hold this one.
        # WHAT it is belongs to the caller, which knows the machine; WHEN to
        # use it belongs here, because only this thread sees the packets that
        # prove a clash. Empty means never retreat - a name nobody shares.
        self.wanted = self.name
        self.fallback = (fallback or "").lower().rstrip(".")
        if self.fallback and not self.fallback.endswith(".local"):
            self.fallback += ".local"
        self.clashed = ""
        # Reclaiming the short name: how many probes in a row have gone
        # unanswered, and when the last one was sent. Two are required, not
        # one, because a single dropped packet is normal on the WiFi this runs
        # on and a hasty reclaim would start the very clash it is avoiding.
        self._quiet = 0
        self._checked = time.time()
        # Packets of any kind seen on 5353. A network that carries none is a
        # network whose silence proves nothing.
        self.heard = 0
        self.ip_of = ip_of
        self.sock = None
        self.thread = None
        self.stop = threading.Event()
        self.error = ""
        self.answered = 0

    def taken(self, wait=0.4):
        """Is another machine already answering this name?

        Standard mDNS behaviour, and the reason it exists: two hubs both
        claiming `mice.local` do not share it, they RACE - whichever answers a
        given lookup first wins that lookup, so the same name reaches different
        machines from one minute to the next. Asked about directly on
        2026-08-19, and adding a port does not help because the port was never
        the ambiguous part.

        So ask before claiming. A reply from an address that is not ours means
        the name belongs to someone else, and this hub takes its own instead.
        """
        q = struct.pack(">HHHHHH", 0x4d49, 0, 1, 0, 0, 0) + _labels(self.name)
        q += struct.pack(">HH", 1, 1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(wait)
        mine = ""
        try:
            mine = self.ip_of()
            # SEND IT OUT THE RIGHT ADAPTER. This machine has four - WiFi, a
            # VPN and two virtual ones - and multicast goes out whichever the
            # routing table prefers, which was not the one the hub lives on.
            # The probe then heard nothing and every hub cheerfully claimed the
            # same name. Pinning the interface is what makes the question reach
            # anyone who could answer it.
            if mine:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                             socket.inet_aton(mine))
            s.sendto(q, (GROUP, PORT))
            end = time.time() + wait
            while time.time() < end:
                try:
                    data, who = s.recvfrom(2048)
                except socket.timeout:
                    break
                # ANY answer means the name is spoken for. This runs BEFORE
                # this hub answers anything, so a reply cannot be our own -
                # and filtering by address was wrong twice over: two hubs on
                # one machine share an IP, which is exactly the case that
                # proves the feature, and it silently passed.
                if len(data) >= 12:
                    flags = struct.unpack(">H", data[2:4])[0]
                    if flags & 0x8000 and self.name in _answered(data):
                        return who[0]
        except OSError:
            pass
        finally:
            s.close()
        return ""

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
            # Join on the interface the hub is actually reachable on, not on
            # whichever one the routing table picks - see taken().
            here = ""
            try:
                here = self.ip_of()
            except Exception:                    # noqa: BLE001
                pass
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                         socket.inet_aton(GROUP) +
                         socket.inet_aton(here or "0.0.0.0"))
            if here:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                             socket.inet_aton(here))
            s.settimeout(1.0)
            self.sock = s
        except OSError as e:
            # Something else already holds 5353 - Bonjour on Windows, avahi on
            # Linux. That is not an error worth stopping the hub for: the QR
            # still works, and this says so rather than dying quietly.
            self.error = "%s is not available (%s)" % (self.name, e)
            return False
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        self.announce()
        return True

    def announce(self):
        """Say who we are without being asked, so a listener need not wait."""
        if not self.sock:
            return False          # never started, or already closed
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
                if time.time() - self._checked > RECLAIM_EVERY:
                    self._checked = time.time()
                    self._reclaim()
                continue
            except OSError:
                break

            # An ANSWER carrying our own name, from somebody else, means two
            # hubs hold it. This is why the startup probe is not enough: if the
            # other PC was off the air at boot, both claimed the name and
            # nothing said so. mDNS has no arbitration, so the packets have to
            # be listened to rather than asked for. Added 2026-08-19 after the
            # user reported the venue WiFi dropping both machines in turn.
            # Evidence that mDNS actually FLOWS on this network. Silence is
            # only meaningful if we can hear anything at all - see _reclaim.
            self.heard += 1
            flags = struct.unpack(">H", data[2:4])[0] if len(data) >= 4 else 0
            if flags & 0x8000:
                if self.name in _answered(data):
                    self._clash(addr[0])
                continue

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

    def _reclaim(self):
        """Go back to the short name when the machine that held it is gone.

        Without this the retreat is permanent. The hub that lost the tie-break
        keeps its long hostname for ever, so when the other PC is switched off
        at the end of a show `mice.local` is answered by nobody at all and the
        operator is left typing mice-win-ro2uqq0r3fn.local from memory. The
        name should come back to whoever is still running.
        """
        if not self.wanted or self.name == self.wanted:
            return
        # NO ANSWER IS NOT THE SAME AS NO HOLDER. Raised by all five panel
        # models on 2026-08-19, and true: a firewall, client isolation on a
        # venue access point, or plain packet loss makes every probe silent -
        # and a hub that treats that as *the name is free* takes a name the
        # other machine is still answering, on exactly the network where the
        # clash detector is also deaf. So silence only counts when this hub can
        # hear SOMETHING; on a network that carries no mDNS at all it keeps the
        # long name, which always works.
        if not self.heard:
            self._quiet = 0
            return
        probe = Responder(self.wanted, self.ip_of)
        try:
            if probe.taken(wait=0.6):
                self._quiet = 0                  # still held; leave it alone
                return
        finally:
            probe.close()
        self._quiet += 1
        if self._quiet < 2:
            return
        self._quiet = 0
        self.name = self.wanted
        self.clashed = ""
        self.announce()

    def _clash(self, other):
        """Somebody else answers our name. Decide, without talking to them.

        The tie-break is the numerically lower address, compared as four bytes
        rather than as text - `10.126.226.9` sorts after `10.126.226.11` as a
        string, which would have made the two machines disagree about who won
        and swap names forever. Both sides run the same comparison on the same
        two numbers, so they reach the same answer with no negotiation, and it
        does not flap: the loser stops answering the shared name, so there is
        nothing left to clash over.
        """
        mine = ""
        try:
            mine = self.ip_of()
        except Exception:                            # noqa: BLE001
            pass
        if not mine or not other or other == mine:
            return                                   # our own echo
        self.clashed = other
        try:
            lost = socket.inet_aton(mine) > socket.inet_aton(other)
        except OSError:
            return
        if not lost or not self.fallback or self.name == self.fallback:
            # We keep it. Say so again, so anything that cached the other
            # machine's answer hears ours too.
            self.announce()
            return
        self.name = self.fallback
        self.announce()

    def close(self):
        self.stop.set()
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
