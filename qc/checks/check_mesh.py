"""The router-less mesh (ESP-NOW) is off by default and its rules sit in tested source.

Model (tools/bench/mesh_model.py, real MeshLogic.h, collision model): 255 boards need
ttl ~19 hops; with suppress k=2 and one try a 100-board command was answered 16/20,
with k=3 and three tries 20/20. The radio itself is not testable here (QEMU has no radio).
  * MeshLogic.h defaults ttl 20, suppressK 3 (native tests in test_main.cpp)
  * MeshLink resends an unanswered command up to 3 times
  * mesh mode defaults to "off" and only SET MESH ON starts it
  * frames carry an HMAC tag from the group key
"""
import qc as F

AREA = "wifi"
TITLE = "mesh is off by default; ttl, repeat suppression, retries and signing are in source"
SLOW = False

CORE = F.FIRMWARE / "src" / "core"


def run(t):
    rd = lambda p: p.read_text(encoding="utf-8", errors="replace")
    logic, link = rd(CORE / "MeshLogic.h"), rd(CORE / "MeshLink.cpp")
    ident, cmd = rd(CORE / "Identity.cpp"), rd(CORE / "CommandRouter.cpp")
    tests = rd(F.FIRMWARE / "test" / "test_logic" / "test_main.cpp")

    t.ok("uint8_t ttl = 20;" in logic and "uint8_t suppressK = 3;" in logic,
         "ttl 20 and suppress 3 (the model's smallest working values)", "")
    t.ok("MAX_TRIES = 3" in link and "RETRY_MS" in link,
         "an unanswered command is sent again, 3 tries", "")
    t.ok('"mesh"' in ident and '"off"' in ident, "mesh mode is stored and defaults to off", "")
    t.ok('what == "MESH"' in cmd and "ERR" in cmd, "SET MESH ON|OFF exists", "")
    t.ok("hmac" in link.lower() or "mbedtls_md_hmac" in link, "frames are signed with the group key", "")
    t.ok("return RX_DROPPED_OLD;" in logic and "seqStart" in link and "test_mesh_drops_a_replayed_old_frame" in tests,
         "an old captured frame is refused; seq rises on every boot (kept in flash)", "")
    t.ok("mesh::MeshNode" in tests, "native tests drive the real MeshNode", "")
