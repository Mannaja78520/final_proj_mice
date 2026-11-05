"""Start the local Ollama with the settings in config/local_ai.json.

    python tools/ollama_serve.py            start it (foreground)
    python tools/ollama_serve.py --show     print the environment it would use
    python tools/ollama_serve.py --kv q8_0  one-off override (also --flash 0/1)

Why a script: KV-cache type and flash attention are Ollama SERVER settings
(OLLAMA_KV_CACHE_TYPE, OLLAMA_FLASH_ATTENTION); nothing a request can set.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from registry import strip_jsonc

KV_TYPES = ("f16", "q8_0", "q4_0")


def load(path=None):
    p = Path(path) if path else ROOT / "config" / "local_ai.json"
    return json.loads(strip_jsonc(p.read_text(encoding="utf-8")))


def server_env(cfg, base=None):
    """The environment variables Ollama is started with. Raises on a bad value."""
    kv = str(cfg.get("kvCache", "f16"))
    if kv not in KV_TYPES:
        raise ValueError("kvCache must be one of %s, got %r" % (", ".join(KV_TYPES), kv))
    flash = bool(cfg.get("flashAttention", False))
    if kv != "f16" and not flash:
        raise ValueError("kvCache %s needs flashAttention true (Ollama ignores it otherwise)" % kv)
    env = dict(os.environ if base is None else base)
    for k in ("OLLAMA_KV_CACHE_TYPE", "OLLAMA_FLASH_ATTENTION"):
        env.pop(k, None)
    if cfg.get("host"):
        env["OLLAMA_HOST"] = cfg["host"]
    if cfg.get("modelsDir"):
        env["OLLAMA_MODELS"] = cfg["modelsDir"]
    env["OLLAMA_FLASH_ATTENTION"] = "1" if flash else "0"
    if kv != "f16":
        env["OLLAMA_KV_CACHE_TYPE"] = kv
    return env


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--kv", choices=KV_TYPES)
    ap.add_argument("--flash", choices=("0", "1"))
    a = ap.parse_args(argv)
    cfg = load(a.config)
    if a.kv:
        cfg["kvCache"] = a.kv
    if a.flash:
        cfg["flashAttention"] = a.flash == "1"
    env = server_env(cfg)
    keys = ("OLLAMA_HOST", "OLLAMA_MODELS", "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE")
    if a.show:
        for k in keys:
            print("%s=%s" % (k, env.get(k, "(unset)")))
        return 0
    return subprocess.call(["ollama", "serve"], env=env)


if __name__ == "__main__":
    sys.exit(main())
