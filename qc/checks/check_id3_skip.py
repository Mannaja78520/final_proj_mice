"""A song's tag is skipped in one seek, so the robot keeps answering as it starts.

On the real nong 2026-09-28 a Show walked to its start pose and then COM21 said
"no reply from bus id 67". The pose was followed by the show's first cue,
PLAY <song>. PLAY answers at once, but the song's first decode pass ran the
ESP8266Audio ID3 reader, which walks the whole ID3v2 tag ONE BYTE AT A TIME -
and that tag is where an MP3 keeps its cover picture, often hundreds of KB.
Each byte is a separate SD read, all on the loop task that also answers RS485
and drives the servos (main.cpp: rs485.loop, then router.loop -> audio_.loop),
so for seconds the robot heard nothing and froze. The hub's next POSE timed out,
and a POSE that times out ends the hub's show.

Inferred from the code, not measured: the song itself was not available here.
PERF? on the board after a show start says it (slow_part=module:<us>).

Held here: the byte reader is gone from the player, the MP3 decoder is handed
the file only after skipTags_() has sought past the tag, and the skip reads
nothing but the 10-byte headers. The arithmetic (id3::tagBytes: four 7-bit
bytes, the v2.4 footer, a non-tag is 0) is EXECUTED by the native tests that
check_firmware_build runs.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "a song's cover art is skipped in one seek, so the robot answers while music starts"


def _body(src, sig):
    """The body of the function whose definition starts with `sig`."""
    at = src.find(sig)
    if at < 0:
        return ""
    depth, i = 0, src.find("{", at)
    for j in range(i, len(src)):
        depth += {"{": 1, "}": -1}.get(src[j], 0)
        if depth == 0:
            return src[i:j + 1]
    return ""


def run(t):
    fw = F.FIRMWARE
    src = (fw / "src/core/AudioPlayer.cpp").read_text(encoding="utf-8", errors="replace")
    hdr = (fw / "src/core/AudioPlayer.h").read_text(encoding="utf-8", errors="replace")

    t.ok("AudioFileSourceID3" not in src + hdr,
         "the player no longer uses the library's byte-by-byte ID3 reader",
         "AudioFileSourceID3 reads the whole tag one byte per SD read, on the "
         "loop that answers the bus")

    open_track = _body(src, "bool AudioPlayer::openTrack_(")
    mp3 = open_track.find("new AudioGeneratorMP3")
    skip = open_track.find("skipTags_()")
    t.ok(0 <= skip < mp3,
         "openTrack_ skips the tag before the MP3 decoder is made",
         "skipTags_() at %d, new AudioGeneratorMP3 at %d" % (skip, mp3))
    t.ok(re.search(r"gen_->begin\(\s*file_\s*,", open_track[mp3:]),
         "and the decoder reads the SD file directly, from after the tag")

    skipper = _body(src, "void AudioPlayer::skipTags_(")
    t.ok("id3::tagBytes(" in skipper and "seek(" in skipper,
         "skipTags_ measures each tag with id3::tagBytes and seeks past it")
    reads = re.findall(r"read\(\s*\w+\s*,\s*(\w+)\s*\)", skipper)
    t.ok(reads and all(n == "10" for n in reads),
         "and reads nothing but the 10-byte headers", reads)

    tests = (fw / "test/test_logic/test_main.cpp").read_text(encoding="utf-8",
                                                             errors="replace")
    for name in ("test_id3_size_is_four_seven_bit_bytes",
                 "test_id3_v4_footer_is_skipped_too",
                 "test_not_a_tag_skips_nothing"):
        t.ok("RUN_TEST(%s)" % name in tests,
             "the native tests run %s" % name)
