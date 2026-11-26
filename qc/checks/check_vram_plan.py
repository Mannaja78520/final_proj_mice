"""GPU memory is placed by live free VRAM and priority: no fixed GB tiers.

2026-11-25 (user): "2, 4, 6, 8, 10, 12 GB - make it dynamic, apps should not get
slower than they must". A fake card (total, other apps' use, our loaded models)
drives the real tools/vramplan.py through every size and through other apps
starting and stopping.
"""
import json
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "models are placed by live free VRAM and priority, on any card size"

MODELS = ["stt:large-v3", "stt:thonburian-medium", "llm:Qwen2.5-0.5B-Instruct", "tts:spark"]


class Card:
    """A GPU: total, what OTHER programs use, and what our loaded models hold."""

    def __init__(self, total, others=0):
        self.total, self.others, self.ours = total, others, {}

    def probe(self):
        return {"totalMiB": self.total, "freeMiB": max(0, self.total - self.others - sum(self.ours.values()))}


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import vramplan as v
    def fresh_reg(path=None):
        return v.Registry.from_file(F.CODE / "config" / "vram_models.json", path)

    reg = fresh_reg()

    def load_all(card, arb, keys):
        placed = {}
        for k in keys:
            r = arb.request(k, unload=lambda k=k: card.ours.pop(k, None))
            for e in r["evict"]:
                card.ours.pop(e, None)
            if r["device"] == "cuda":
                card.ours[k] = reg.info(k)["mib"]
            arb.loaded(k, r["device"], unload=lambda k=k: card.ours.pop(k, None))
            placed[k] = r["device"]
        return placed

    # 1. Every card size: never more on the GPU than it can hold, and the hearing model is first in line.
    results = {}
    for gb in (2, 4, 6, 8, 10, 12, 16, 24):
        card = Card(gb * 1024)
        arb = v.Arbiter(reg, card.probe, cap_mib=None)
        placed = load_all(card, arb, MODELS)
        results[gb] = placed
        used = sum(card.ours.values())
        t.ok(used <= card.total - reg.headroom_mib(card.total) + 1, "%d GB: never over the card" % gb, "%d MiB in use of %d" % (used, card.total))
    t.ok(results[24] == {k: "cuda" for k in MODELS}, "a big card holds everything on the GPU", str(results[24]))
    t.ok(results[2]["stt:large-v3"] == "cpu" and results[2]["llm:Qwen2.5-0.5B-Instruct"] == "cuda",
         "2 GB: the big hearing model spills to the CPU, the small local AI still uses the GPU", str(results[2]))
    gpu_counts = [sum(1 for d in results[g].values() if d == "cuda") for g in (2, 4, 6, 8, 10, 12, 16, 24)]
    t.ok(gpu_counts == sorted(gpu_counts), "a bigger card never puts fewer models on the GPU", str(gpu_counts))

    # 2. Who wins a small card: the model that saves the most time per MiB (measured in
    # tools/bench_vram.py), a less important one is pushed out only for a MORE valuable newcomer.
    card = Card(4 * 1024)
    arb = v.Arbiter(reg, card.probe)
    load_all(card, arb, ["llm:Qwen2.5-0.5B-Instruct"])
    r = arb.request("stt:large-v3", unload=lambda: None)
    t.ok(r["device"] == "cuda" and r["evict"] == ["llm:Qwen2.5-0.5B-Instruct"],
         "hearing (saves more per MiB, more important) pushes the small local AI off a 4 GB card", str(r))
    card = Card(5 * 1024)
    arb = v.Arbiter(reg, card.probe)
    load_all(card, arb, ["tts:spark"])
    r = arb.request("stt:large-v3", unload=lambda: None)
    t.ok(r["device"] == "cpu" and r["evict"] == [],
         "speech that saves 5.8 s in 3 GB keeps its place; hearing takes the CPU instead of pushing it out", str(r))
    arb2 = v.Arbiter(reg, Card(4 * 1024).probe)
    c2 = Card(4 * 1024)
    arb2 = v.Arbiter(reg, c2.probe)
    load_all(c2, arb2, ["stt:large-v3"])
    r = arb2.request("stt:medium-other", unload=lambda: None)
    t.ok(r["evict"] == [] and r["device"] == "cpu", "an equally important newcomer takes the CPU instead of thrashing the resident model", str(r))

    # 3. Other apps change the room at run time: a new load sees it, no restart, no setting.
    card = Card(12 * 1024, others=0)
    arb = v.Arbiter(fresh_reg(), card.probe)
    a = arb.request("stt:large-v3")["device"]
    card.others = 11 * 1024                                 # the face app and a game grab the card
    b = arb.request("stt:small")["device"]
    card.others = 0                                         # and let go again
    c = arb.request("stt:small")["device"]
    t.ok((a, b, c) == ("cuda", "cpu", "cuda"), "free VRAM is read at load time: other apps coming and going change the placement", str((a, b, c)))

    # 4. No GPU reading at all means CPU, never a crash.
    arb = v.Arbiter(reg, lambda: (_ for _ in ()).throw(OSError("no nvidia-smi")))
    t.ok(arb.request("llm:Qwen2.5-0.5B-Instruct")["device"] == "cpu", "no GPU reading: the CPU, no crash")

    # 5. The size cap pretends to be a smaller card (used for testing 2..12 GB on one machine).
    real = Card(12 * 1024, others=1024)
    small = v.Arbiter(reg, real.probe, cap_mib=4096)
    st = small.status()["card"]
    t.ok(st["totalMiB"] == 4096 and st["freeMiB"] == 4096 - 1024, "the VRAM cap shows a smaller card minus what is really in use", str(st))

    # 6. Real sizes are measured after loading and remembered next time.
    with tempfile.TemporaryDirectory() as d:
        learned = Path(d) / "learned.json"
        reg2 = v.Registry.from_file(F.CODE / "config" / "vram_models.json", learned)
        card = Card(12 * 1024)
        arb = v.Arbiter(reg2, card.probe)
        r = arb.request("stt:small")                              # a clean reading: nothing pushed out
        before = r["card"]["freeMiB"]
        card.ours["stt:small"] = 950
        arb.loaded("stt:small", "cuda", before_free_mib=before)
        again = v.Registry.from_file(F.CODE / "config" / "vram_models.json", learned)
        t.ok(again.info("stt:small")["mib"] == 950 and again.info("stt:small")["measured"], "a measured size is remembered for the next start", str(again.info("stt:small")))

    # 7. The registry is data: every model key has a rule, and the catch-all exists.
    data = json.loads((F.CODE / "config" / "vram_models.json").read_text(encoding="utf-8"))
    t.ok(data["rules"][-1]["match"] == "^" and all({"match", "mib", "priority"} <= set(r) for r in data["rules"]),
         "registry rules are complete and end with a catch-all")

    # 8. Two loads at the same moment are not both promised the same room (the boot preload and a live question).
    card = Card(4 * 1024)
    arb = v.Arbiter(fresh_reg(), card.probe)
    a = arb.request("stt:large-v3")["device"]               # reserved, not yet loaded: the card still shows it free
    b = arb.request("llm:Qwen2.5-0.5B-Instruct")["device"]
    t.ok(a == "cuda" and b == "cpu", "a load that has started holds its room against a second one at the same moment", str((a, b)))
    arb.released("stt:large-v3")                              # that load failed: the room comes back
    t.ok(arb.request("llm:Qwen2.5-0.5B-Instruct")["device"] == "cuda", "a failed load gives its room back")

    # 9. A size measured right after pushing another model out is not learned (it would come out too small).
    with tempfile.TemporaryDirectory() as d:
        reg3 = v.Registry.from_file(F.CODE / "config" / "vram_models.json", Path(d) / "l.json")
        card = Card(4 * 1024)
        arb = v.Arbiter(reg3, card.probe)
        load_all(card, arb, ["llm:Qwen2.5-0.5B-Instruct"])
        r = arb.request("stt:large-v3", unload=lambda: None)
        card.ours.pop("llm:Qwen2.5-0.5B-Instruct", None)    # the evicted model's memory was freed
        before = r["card"]["freeMiB"]
        card.ours["stt:large-v3"] = 3400
        arb.loaded("stt:large-v3", "cuda", before_free_mib=before)
        t.ok(r["evict"] and "stt:large-v3" not in reg3.learned, "a size measured with an eviction mixed in is not remembered", str(reg3.learned))

    # 10. A model that is busy answering refuses to be pushed off the GPU: the newcomer uses the CPU instead.
    card = Card(4 * 1024)
    arb = v.Arbiter(fresh_reg(), card.probe)
    load_all(card, arb, ["llm:Qwen2.5-0.5B-Instruct"])
    arb._held["llm:Qwen2.5-0.5B-Instruct"]["unload"] = lambda: False      # busy
    r = arb.request("stt:large-v3")
    t.ok(r["device"] == "cpu" and r["evict"] == [] and "llm:Qwen2.5-0.5B-Instruct" in arb._held,
         "a busy model is not pulled from under its answer", str(r))

    # 11. Room that another program (the face app) was seen to grow into stays free for it.
    with tempfile.TemporaryDirectory() as d:
        reg4 = v.Registry.from_file(F.CODE / "config" / "vram_models.json", Path(d) / "l.json")
        card = Card(12 * 1024, others=6 * 1024)
        arb = v.Arbiter(reg4, card.probe)
        arb.request("stt:small")                              # sees the other program at 6 GB
        arb.released("stt:small")
        card.others = 1024                                    # it shrinks now ...
        room_now = arb.status()["headroomMiB"]
        t.ok(4 * 1024 <= room_now <= 0.4 * 12 * 1024, "room the other program grew into stays reserved for it, capped at a share of the card", str(room_now))

    # 12. A Voice budget (testing 2 or 3 GB for the Voice while another program holds the real card).
    import os
    os.environ["MICE_VRAM_VOICE_BUDGET_MIB"] = "2048"
    try:
        full = Card(12 * 1024, others=12 * 1024)              # the real card has no room at all: it must not matter
        arb = v.Arbiter(fresh_reg(), full.probe)
        a = arb.request("stt:small")
        arb.loaded("stt:small", "cuda", None, None)
        b = arb.request("llm:Qwen2.5-0.5B-Instruct")
        c = arb.request("stt:Thaweewat/whisper-th-medium-ct2")
        st = arb.status()
        t.ok(a["device"] == "cuda" and b["device"] == "cpu" and c["device"] == "cpu",
             "a 2 GB Voice budget holds the best-value model and spills the rest, whatever the real card shows", str((a["device"], b["device"], c["device"])))
        t.ok(st["card"]["totalMiB"] == 2048 and st["card"]["freeMiB"] < 2048 and st["voiceBudgetMiB"] == 2048,
             "the budget shows as the card in the planner status", str(st["card"]))
    finally:
        os.environ.pop("MICE_VRAM_VOICE_BUDGET_MIB", None)
