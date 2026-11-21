"""The local Ollama's KV-cache type is data, validated, and reaches the server env.

User 2026-11-05: apply KV-cache quantization to the local AI if answers do not
get worse. Ollama has it only as server env (OLLAMA_KV_CACHE_TYPE, needs
OLLAMA_FLASH_ATTENTION=1): a quantized type without flash attention is silently
ignored, so the launcher refuses that combination instead of looking enabled.
Tested against fakes; the effect on speed, VRAM and score is in
docs/experiments/experiment-records.md.
"""
import importlib.util

import qc as F

AREA = "tools"
TITLE = "ollama KV-cache type comes from config and a no-op combination is refused"


def run(t):
    spec = importlib.util.spec_from_file_location("ollama_serve", F.CODE / "tools/ollama_serve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = {"OLLAMA_KV_CACHE_TYPE": "stale"}
    env = mod.server_env({"kvCache": "q8_0", "flashAttention": True, "host": "h:1"}, base)
    t.ok(env.get("OLLAMA_KV_CACHE_TYPE") == "q8_0" and env.get("OLLAMA_FLASH_ATTENTION") == "1",
         "q8_0 reaches the env", str(env))
    env = mod.server_env({"kvCache": "f16", "flashAttention": False}, base)
    t.ok("OLLAMA_KV_CACHE_TYPE" not in env and env["OLLAMA_FLASH_ATTENTION"] == "0",
         "f16 leaves the type unset (stale value removed)", str(env))
    for bad in ({"kvCache": "q4_0", "flashAttention": False}, {"kvCache": "q2"}):
        try:
            mod.server_env(bad, {})
            ok = False
        except ValueError:
            ok = True
        t.ok(ok, "refused: %s" % bad, "no ValueError")
    cfg = mod.load()
    t.ok(cfg.get("kvCache") in mod.KV_TYPES, "shipped config is valid", str(cfg))
    mod.server_env(cfg, {})

    env = mod.server_env({"keepAlive": "1h", "numParallel": 1}, {"OLLAMA_KEEP_ALIVE": "stale"})
    t.ok(env.get("OLLAMA_KEEP_ALIVE") == "1h" and env.get("OLLAMA_NUM_PARALLEL") == "1",
         "keepAlive and numParallel reach the env", str(env))
    t.ok("OLLAMA_KEEP_ALIVE" not in mod.server_env({}, {"OLLAMA_KEEP_ALIVE": "stale"}),
         "unset keepAlive leaves Ollama's own default", "stale value kept")
    try:
        mod.server_env({"keepAlive": "soon"}, {})
        ok = False
    except ValueError:
        ok = True
    t.ok(ok, "a bad keepAlive is refused", "no ValueError")
