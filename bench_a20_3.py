"""A20-3 bench test: two nongs linked over RS485 (85 = leader, 67 = partner).

Run AFTER A/A B/B (+GND) are wired between the two driver boards.
Reads both USB consoles raw; prints what a fake cannot show:
  1. can the leader reach the partner over the bus (#67 POSE?)
  2. does a JOINT move on the leader move the partner (forwarded resolved pose)
  3. drift: partner pose vs leader pose after a move chain
"""
import serial, time, sys

LEADER = ("COM26", 85)
PARTNER = ("COM29", 67)


def open_board(port):
    s = serial.Serial(port, 115200, timeout=0.05)
    s.dtr = False
    s.rts = False
    time.sleep(3.5)          # opening reboots the board
    s.reset_input_buffer()
    return s


def send(s, cmd):
    s.write((cmd + "\n").encode())


def drain(s, seconds):
    end = time.time() + seconds
    got = b""
    while time.time() < end:
        c = s.read(4096)
        if c:
            got += c
    return got.decode("utf-8", "replace")


def pose(txt):
    """last 'a b c ...' 10-number line that is not an @-reply"""
    for line in reversed(txt.splitlines()):
        line = line.strip()
        if line.startswith("@"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) == 10:
            try:
                return [float(x) for x in parts]
            except ValueError:
                pass
    return None


lead = open_board(LEADER[0])
part = open_board(PARTNER[0])

print("== 1. reach: #67 POSE? from the leader's cable")
send(lead, "#%d POSE?" % PARTNER[1])
print("   leader heard:", repr(drain(lead, 4).strip()[:200]) or "SILENCE")

print("== 2. make the leader a leader")
for cmd in ("CFG link 1", "CFG peer %d" % PARTNER[1], "INFO"):
    send(lead, cmd)
    time.sleep(0.8)
info = drain(lead, 2)
print("   link cap:", "YES" if '"link"' in info else "NO  <-- CFG did not stick")

# Physical inventory per the user (2026-08-25): leader #85 has R_SH_P wired,
# partner #67 has WAIST on a dummy servo. Forwarding sends the SAME joint
# index to both boards, so the test drives BOTH: joint 5 makes #85's shoulder
# swing (and forwards), joint 9 shows #67's waist copying. Joints 9/10 report
# pin -1 right now - if the waist stays still, `PIN waist <gpio>` maps it.
print("== 3. forward moves: JOINT 5 then JOINT 9 from the leader")
send(lead, "PINS?")
print("   leader pins:", drain(lead, 1.5).strip()[:200])
for s in (lead, part):
    send(s, "HOME T 600")
drain(lead, 2); drain(part, 0.1)

def fwd_test(j, want):
    send(lead, "JOINT %d 120 T 900" % j)
    drain(lead, 2.5); drain(part, 1.5)
    time.sleep(1.0)
    send(part, "POSE?")
    p = pose(drain(part, 2))
    print("   joint %d: partner value %s (want ~%s)" % (j, p and round(p[j-1]), want))

fwd_test(5, 120)
fwd_test(9, 120)

print("== 4. drift: five moves on joint 5, compare end poses")
seq = [70, 130, 90, 110, 90]
for v in seq:
    send(lead, "JOINT 5 %d T 500" % v)
    time.sleep(0.75)
send(lead, "POSE?"); l_end = pose(drain(lead, 2))
send(part, "POSE?"); p_end = pose(drain(part, 2))
print("   leader :", l_end and round(l_end[4], 1))
print("   partner:", p_end and round(p_end[4], 1))
if l_end and p_end:
    print("   DRIFT R_SH_P:", abs(l_end[4] - p_end[4]), "deg")

send(lead, "HOME T 800")
drain(lead, 2)
lead.close(); part.close()
print("done")
