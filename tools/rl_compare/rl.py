"""Contender 2: an imitation policy trained by PPO on the dancer's bones.

Training is split into rounds. After each round the policy dances the WHOLE
song once from the first key (deterministic), and that run is kept: its
board commands and servo angles (for the score and the video), the weights,
and the wall time of the round. So progress can be watched round by round.
"""
import copy
import json
import time
from pathlib import Path

import numpy as np
import torch

from .env import DanceEnv
from .ppo import PPO, ActorCritic
from .reference import DenseReference


def pick_device(want):
    if want == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return want


class RLRun:
    def __init__(self, dance, make, scenario, cfg, device, out_dir):
        """make(device) -> (TorchRig, ServoModel): one copy trains on the GPU,
        a CPU copy performs the song (one robot: small ops, a GPU only adds latency)."""
        self.dance, self.scenario, self.cfg = dance, scenario, cfg
        self.kin, self.servo = make(device)
        self.kin_cpu, self.servo_cpu = make("cpu")
        self.device, self.out = device, Path(out_dir)
        self.dense = DenseReference(dance, cfg["controlHz"], pad_s=max(cfg["lookaheadS"]) + 1,
                                    fill_weight=cfg.get("fillWeight", 0.0))
        self.env = DanceEnv(self.dense, self.kin, self.servo, scenario["safeDps"], cfg, device)
        torch.manual_seed(cfg["seed"])
        self.model = ActorCritic(self.env.obs_dim, 10, cfg["net"], cfg["ppo"]["initLogStd"]).to(device)
        self.ppo = PPO(self.model, cfg["ppo"])

    def _rollout(self, obs):
        p, env = self.cfg["ppo"], self.env
        keys = ("obs", "act", "logp", "val", "rew", "done")
        buf = {k: [] for k in keys}
        for _ in range(p["steps"]):
            self.model.norm.update(obs)
            act, logp, val = self.model.act(obs)
            nxt, rew, done, trunc = env.step(act)
            if trunc.any():                                   # time limit: not a failure, bootstrap
                with torch.no_grad():
                    _, v_end = self.model.dist(nxt[trunc])
                rew = rew.clone()
                rew[trunc] += p["gamma"] * v_end
            end = done | trunc
            for k, v in zip(keys, (obs, act, logp, val, rew, end)):
                buf[k].append(v)
            if end.any():
                env.reset(end.nonzero().squeeze(1))
                nxt = env.observe()
            obs = nxt
        with torch.no_grad():
            _, last = self.model.dist(obs)
        stack = {k: torch.stack(v) for k, v in buf.items()}
        adv, ret = PPO.gae(stack["rew"], stack["val"], stack["done"], last, p["gamma"], p["lam"])
        flat = lambda x: x.reshape(-1, *x.shape[2:])
        batch = {"obs": flat(stack["obs"]), "act": flat(stack["act"]), "logp": flat(stack["logp"]),
                 "adv": flat(adv), "ret": flat(ret)}
        return obs, batch, stack["rew"].mean().item(), stack["done"].float().mean().item()

    @torch.no_grad()
    def perform(self):
        """The whole song once from the first key: commands and servo angles per board frame."""
        dense, cfg = self.dense, dict(self.cfg)
        cfg["envs"], cfg["startNoiseDeg"] = 1, 0.0
        env = DanceEnv(dense, self.kin_cpu, self.servo_cpu, self.scenario["safeDps"], cfg, "cpu")
        model = self.model if self.device == "cpu" else copy.deepcopy(self.model).to("cpu")
        env.reset()
        start = torch.tensor([self.dance.start_pose], dtype=self.kin_cpu.dtype)
        env.q, env.c, env.t[:] = start.clone(), start.clone(), 0
        qs, cs = [start[0].clone()], [start[0].clone()]
        obs = env.observe()
        while int(env.t[0]) < dense.steps - 1:
            act, _, _ = model.act(obs, deterministic=True)
            a = act.clamp(-1, 1)
            c0 = env.c.clone()
            target = torch.maximum(torch.minimum(env.c + a * env.cap, env.hi), env.lo)
            for k in range(1, env.sub + 1):
                c = c0 + (target - c0) * (k / env.sub)
                env.q = self.servo_cpu.step(env.q, c)
                qs.append(env.q[0].clone())
                cs.append(c[0].clone())
            env.c, env.prev_a, env.t = target, a, env.t + 1
            obs = env.observe()
        return torch.stack(cs), torch.stack(qs)

    # ---- resume (lab 2026-10-28: the full run stopped at round 12/20 by hand
    # and a rerun began at round 1 again, ~115 s a round thrown away) ----------
    SAME_RUN_IGNORES = ("rounds",)   # more rounds asked = the same run, longer

    def _same_config(self):
        saved = self.out / "config.json"
        if not saved.exists():
            return True, "no config.json (a run from before resume existed): assumed the same"
        old = json.loads(saved.read_text(encoding="utf-8"))
        strip = lambda c: {k: v for k, v in c.items() if k not in self.SAME_RUN_IGNORES}
        if strip(old) != strip(json.loads(json.dumps(self.cfg))):
            return False, "the config changed since those rounds were trained"
        return True, ""

    def saved_rounds(self):
        """Rounds 1..k that finished (round.json and policy.pt both written), in order."""
        rounds = []
        for r in range(1, self.cfg["rounds"] + 1):
            folder = self.out / ("round_%02d" % r)
            if not ((folder / "round.json").exists() and (folder / "policy.pt").exists()):
                break
            rounds.append(json.loads((folder / "round.json").read_text(encoding="utf-8")))
        return rounds

    def resume(self):
        """Load the last finished round's weights (and optimizer, if saved). -> rounds so far."""
        rounds = self.saved_rounds()
        if not rounds:
            return []
        same, why = self._same_config()
        if not same:
            print("  not resuming: %s (use --fresh to start over)" % why, flush=True)
            raise SystemExit(2)
        last = self.out / ("round_%02d" % rounds[-1]["round"])
        self.model.load_state_dict(torch.load(last / "policy.pt", map_location=self.device))
        state = last / "train_state.pt"
        if state.exists():
            st = torch.load(state, map_location="cpu", weights_only=False)
            self.ppo.opt.load_state_dict(st["opt"])
            torch.set_rng_state(st["rng"])
            if self.device == "cuda" and st.get("cudaRng") is not None:
                torch.cuda.set_rng_state_all(st["cudaRng"])
            note = "weights + optimizer"
        else:
            note = "weights only (optimizer starts fresh: rounds saved before resume existed)"
        print("  resuming after round %d/%d: %s %s" % (rounds[-1]["round"], self.cfg["rounds"], note, why),
              flush=True)
        return rounds

    def _save_state(self, folder):
        torch.save({"opt": self.ppo.opt.state_dict(), "rng": torch.get_rng_state(),
                    "cudaRng": torch.cuda.get_rng_state_all() if self.device == "cuda" else None},
                   folder / "train_state.pt")

    def train(self, on_round=None, resume=True):
        cfg = self.cfg
        rounds = self.resume() if resume else []
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        obs = self.env.reset()
        sync = (lambda: torch.cuda.synchronize()) if self.device == "cuda" else (lambda: None)
        total = rounds[-1]["totalTrainS"] if rounds else 0.0
        first = len(rounds) + 1
        for r in range(first, cfg["rounds"] + 1):
            sync()
            t0 = time.perf_counter()
            log = []
            for _ in range(cfg["updatesPerRound"]):
                obs, batch, mean_r, ends = self._rollout(obs)
                stats = self.ppo.update(batch)
                log.append({"reward": mean_r, "touchEnds": ends, **stats})
            sync()
            train_s = time.perf_counter() - t0
            total += train_s
            t1 = time.perf_counter()
            c, q = self.perform()
            sync()
            info = {"round": r, "trainS": train_s, "totalTrainS": total, "performS": time.perf_counter() - t1,
                    "samples": cfg["updatesPerRound"] * cfg["ppo"]["steps"] * cfg["envs"] * r,
                    "reward": float(np.mean([x["reward"] for x in log])),
                    "touchEnds": float(np.mean([x["touchEnds"] for x in log])),
                    "kl": float(np.mean([x["kl"] for x in log])),
                    "resumedAt": first if first > 1 else None}
            folder = self.out / ("round_%02d" % r)
            folder.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), folder / "policy.pt")
            self._save_state(folder)
            np.savez_compressed(folder / "motion.npz", c=c.cpu().numpy(), q=q.cpu().numpy())
            if on_round:
                info.update(on_round(r, c, q) or {})
            (folder / "round.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            rounds.append(info)
            print("round %d/%d  train %.1fs  reward %.3f  %s" % (r, cfg["rounds"], train_s, info["reward"],
                  " ".join("%s=%.2f" % (k, v) for k, v in info.items() if k in ("boneMusicDeg", "boneShapeDeg"))), flush=True)
        return rounds
