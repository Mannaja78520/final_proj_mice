"""The local language model: loading, preloading, warming, unloading and one completion (moved out of Brain 2026-11-21; Brain inherits LocalLlm).

Uses from Brain: cfg, _lock, _resources, service(), chain(), run_job(), key_for() and its sibling mixins.
"""
import copy
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import providers
import registry
import local_ai
import intents
from langs import DEF_PARTICLES, DEF_PRONOUNS, detect_lang, scripts_in, drop_ghosts, drop_repeats

CODE = Path(__file__).resolve().parents[2]


class LocalLlm:
    """The local language model: loading, preloading, warming, unloading and one completion."""

    def _drop_llm(self):
        """The GPU planner needs this room for something more valuable: let the model go, it reloads when next asked."""
        self._llm = None
        self._llm_loaded_model = None
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:                            # noqa: BLE001
            pass

    def llm_device(self):
        """Where the local model runs and, if it is the CPU, why (GPU first)."""
        where, why = getattr(self, "_llm_where", ("", ""))
        out = {"device": where, "cpuBecause": why}
        # A CPU-only PyTorch on a PC that has a GPU is the usual reason the local
        # model sits on the CPU (2026-11-26: torch 2.15.0+cpu beside an RTX 5070 Ti).
        # Say it in plain words where the person looking at the status will read it.
        torch = sys.modules.get("torch")
        built_for = getattr(getattr(torch, "version", None), "cuda", "unknown") if torch else "unknown"
        try:
            loaded = (self._resources.status() or {}).get("loaded") or {}
            gpu_seen = any((rec or {}).get("hardwareGpuCount") for rec in loaded.values())
        except Exception:                                     # noqa: BLE001 - a status line must never fail
            gpu_seen = False
        if built_for is None and gpu_seen:
            out["warning"] = ("PyTorch on this PC is a CPU-only build (%s), so the local model cannot use the GPU. "
                              "Install the CUDA build: see the torch lines in requirements.txt."
                              % getattr(torch, "__version__", "?"))
        return out

    def llm_status(self):
        lcfg = self.cfg.get("llm", {})
        if not lcfg.get("enabled"):
            return "off in config/voice.json"
        if self._llm:
            return "loaded"
        if self._llm_loading:
            return "loading in background…"
        if self._llm_err:
            return "could not load: " + self._llm_err
        return "loads when first needed"


    # --- speaking out loud (A20-9) -------------------------------------
    # Windows' own synthesiser, reached through apps/voice/tts.ps1. No
    # internet, no pip install: the venue PC's own voices, named in the
    # store. Answers are cached by md5(text+voice) so a saved answer's
    # SECOND visitor hears it instantly - and a watcher thread pre-builds
    # every saved answer, re-running when qa_data.json is edited on disk.


    def _load_llm(self):
        # One load per model at a time (A55-1): the boot preload runs without
        # the GPU lock, so a first question used to load a SECOND copy beside
        # it - double VRAM on a 12 GB card the face app shares. A waiter finds
        # it loaded (or its error) and returns.
        lock = self.__dict__.setdefault("_load_lock_llm", threading.Lock())
        with lock:
            return self._load_llm_now()

    def _load_llm_now(self):
        if not self.cfg.get("llm", {}).get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._llm or self._llm_err:
            return
        self._llm_loading = True
        try:
            import torch                                    # noqa: F401
            from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
            mid = self.cfg.get("llm", {}).get("model", str(CODE / "llm"))
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=True)
            mdl = None
            resource_plan, memory_budget = self._resources.torch_plan(torch)
            why = []        # why this model is not on the GPU: shown in status, GPU first (user 2026-11-25)
            free_before = None
            if resource_plan["device"] == "cuda":
                # Live free VRAM + priority decide, not a fixed budget: a model that does not fit runs on the
                # CPU (same quality), and a less valuable resident model is pushed out for a more valuable one.
                placed = self._resources.place("llm:" + mid, self._drop_llm)
                free_before = (placed.get("card") or {}).get("freeMiB")
                if placed["device"] != "cuda":
                    resource_plan = {**resource_plan, "device": "cpu", "warning": placed["why"]}
            if resource_plan["device"] != "cuda":
                gpus = resource_plan.get("hardwareGpuCount", 0)
                why.append("no usable GPU in the plan (%d seen, torch.cuda=%s, budget: %s)" % (
                    gpus, torch.cuda.is_available(), resource_plan.get("warning") or "GPU free memory under the reserve"))
            if resource_plan["device"] == "cuda":
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                try:
                    mdl = AutoModelForCausalLM.from_pretrained(
                        mid, torch_dtype=dtype, device_map="auto", max_memory=memory_budget,
                        attn_implementation="sdpa",
                        trust_remote_code=True)
                except Exception as exc:                    # noqa: BLE001
                    why.append("GPU load failed: %s: %s" % (exc.__class__.__name__, str(exc)[:160]))
                    torch.cuda.empty_cache()
                    try:
                        from transformers import BitsAndBytesConfig
                        quant = BitsAndBytesConfig(
                            load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
                        mdl = AutoModelForCausalLM.from_pretrained(
                            mid, quantization_config=quant, device_map="auto", max_memory=memory_budget,
                            trust_remote_code=True)
                    except Exception as exc:                # noqa: BLE001
                        why.append("4-bit GPU load failed: %s: %s" % (exc.__class__.__name__, str(exc)[:160]))
                        mdl = self._resources.cpu_load(mid, AutoModelForCausalLM, AutoConfig, torch, resource_plan)
            else:
                mdl = self._resources.cpu_load(mid, AutoModelForCausalLM, AutoConfig, torch, resource_plan)
            self._resources.mark("llm:" + mid, resource_plan, str(mdl.device))
            self._llm = (tok, mdl)
            self._llm_loaded_model = mid
            self._resources.vram().loaded("llm:" + mid, "cuda" if str(mdl.device).startswith("cuda") else "cpu",
                                          self._drop_llm, free_before)
            self._llm_where = (str(mdl.device), "; ".join(why) if str(mdl.device) == "cpu" else "")
            if torch.cuda.is_available():
                try:
                    dummy_in = tok(["hi"], return_tensors="pt").to(mdl.device)
                    with torch.no_grad():
                        mdl.generate(**dummy_in, max_new_tokens=1)
                except Exception:
                    pass
        except Exception as e:                              # noqa: BLE001
            self._llm_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._llm_loading = False

    def preload(self, force=False):
        """Preload LLM and STT models in background so they are ready immediately."""
        self.maybe_reload()
        if force:
            if not self.cfg.get("llm", {}).get("enabled"):
                self.cfg.setdefault("llm", {})["enabled"] = True
            if not self.cfg.get("stt", {}).get("enabled"):
                self.cfg.setdefault("stt", {})["enabled"] = True
        if self._preload_thread and self._preload_thread.is_alive():
            return True

        def _worker():
            self._warm_local_ai(force)
            if force or self.cfg.get("llm", {}).get("enabled"):
                if not self._llm:
                    self._load_llm()
            if force or self.cfg.get("stt", {}).get("enabled"):
                if not self._stt:
                    self._load_stt()
                # A language's own hearing model too: its first load is a
                # download, which must not land on a visitor's first question.
                own = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage") or {}
                for lang in own:
                    try:
                        self._own_model(lang)
                    except Exception:                   # noqa: BLE001
                        pass              # _own_model keeps each model's error until retry succeeds

        self._preload_thread = threading.Thread(target=_worker, daemon=True)
        self._preload_thread.start()
        return True

    def _warm_local_ai(self, force):
        """Load the think model of a local server (Ollama) before the first question.

        At boot only if the server is already up (it is never started just for
        this); the Load-the-AI button (force) may start it, as any question would.
        """
        for pid in self.chain("think"):
            prov = self.service(pid)
            if not prov.get("autoStart"):
                continue
            if force:
                up, _ = local_ai.wake(prov)
            else:
                up = local_ai.is_up(prov["autoStart"]["ready"], local_ai.SHORT)
            if up:
                local_ai.warm(prov, prov["jobs"].get("think"))
            return

    def unload(self):
        """Unload LLM and STT models from memory and free GPU/RAM."""
        with self._gpu("background"):
            self._resources.clear()
            self._llm = None
            self._stt = None
            self._stt_own = {}
            self._stt_batches = {}
            self._stt_attempt_model = None
            self._stt_last = None
            self._stt_own_err = {}
            self._llm_err = None
            self._stt_err = None
            self._llm_loading = False
            self._stt_loading = False
            self._llm_loaded_model = None
            self._stt_loaded_model = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        return True

    def _complete(self, messages, max_tokens=None, details=False):
        """One model call on exactly the messages given - no persona added.

        Callers hold the lock and have already checked the model is loaded.

        `details=True` also says whether generation RAN OUT of room rather than
        finishing. That is a fact from the token count, not a guess at the
        text, and it is the only reliable way to tell "this reply is short" from
        "this reply was cut off" - which matters because Thai has no full stop
        to look for (user 2026-09-18: *it cuts replies off*).
        """
        import torch
        tok, mdl = self._llm
        try:
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False)          # Qwen3: skip the think block
        except (TypeError, ValueError):         # older template: no such arg
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
        inputs = tok([text], return_tensors="pt").to(mdl.device)
        limit = max_tokens or int(self.cfg.get("llm", {}).get("maxTokens", 128))
        with torch.inference_mode():
            out = mdl.generate(
                **inputs,
                max_new_tokens=limit,
                do_sample=False,
                use_cache=True,
                pad_token_id=tok.eos_token_id)
        made = out[0][inputs.input_ids.shape[1]:]
        reply = tok.decode(made, skip_special_tokens=False)
        if details:
            # No end-of-text token in what came back = it stopped because the
            # budget ran out, not because it had finished.
            ran_out = len(made) >= limit and (
                tok.eos_token_id is None or int(made[-1]) != int(tok.eos_token_id))
            return self.clean(reply), bool(ran_out)
        return self.clean(reply)

    def _ensure_llm(self):
        """(ready, why-not): the model gate shared by every LLM caller."""
        if not self.cfg.get("llm", {}).get("enabled"):
            return False, ("the local model is switched off "
                           "in config/voice.json")
        self._load_llm()
        if not self._llm:
            return False, ("the local model is not available (%s)"
                           % self.llm_status())
        return True, ""
