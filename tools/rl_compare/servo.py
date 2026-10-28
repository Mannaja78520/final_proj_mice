"""How a hobby servo follows the board's 50 Hz targets - the same for every contender.

First-order lag (lagMs; a rig `servoLagMs` list wins once the lab measures it)
and the rig's own servoMaxDps. The planner's commands and the policy's
commands go through this one model, so neither is scored on motion the real
servos could not make.
"""
import torch


class ServoModel:
    def __init__(self, rig, facts, cfg, device="cpu", dtype=torch.float32):
        T = lambda v: torch.tensor(v, device=device, dtype=dtype)
        self.dt = 1.0 / cfg["frameHz"]
        lag = rig.get("servoLagMs") or [cfg["lagMs"]] * 10
        self.alpha = 1 - torch.exp(-self.dt / (T(lag).clamp_min(1) / 1000))
        self.vmax = T([max(30.0, min(facts.max_dps, v or facts.max_dps)) for v in rig["servoMaxDps"]])
        self.lo, self.hi = T(rig["min"]), T(rig["max"])

    def command_cap(self, safe_dps):
        """deg/s a command may move: the board's peak-speed cap and the servo's own."""
        return self.vmax if not safe_dps else torch.minimum(self.vmax, torch.full_like(self.vmax, float(safe_dps)))

    def step(self, q, c):
        step = ((c - q) * self.alpha).clamp(-self.vmax * self.dt, self.vmax * self.dt)
        return q + step

    def follow(self, commands, q0=None):
        """commands (F,10) one per board frame -> the servo angles (F,10)."""
        q = commands[0].clone() if q0 is None else q0.clone()
        out = torch.empty_like(commands)
        for k in range(commands.shape[0]):
            q = self.step(q, commands[k])
            out[k] = q
        return out
