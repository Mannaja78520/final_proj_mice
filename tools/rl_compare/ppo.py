"""A small PPO (clipped policy gradient + GAE), written here so the experiment
has no trainer library to install or version-match on the PC: torch only.
Standard choices throughout (Schulman et al. 2017); nothing tuned per dance.
"""
import torch
from torch import nn


class RunningNorm(nn.Module):
    """Observation mean/std, updated from every rollout, saved with the policy."""

    def __init__(self, dim):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("var", torch.ones(dim))
        self.register_buffer("count", torch.tensor(1e-4))

    def update(self, x):
        m, v, n = x.mean(0), x.var(0, unbiased=False), x.shape[0]
        delta, total = m - self.mean, self.count + n
        self.mean += delta * n / total
        self.var = (self.var * self.count + v * n + delta ** 2 * self.count * n / total) / total
        self.count = total

    def forward(self, x):
        return ((x - self.mean) / (self.var.sqrt() + 1e-6)).clamp(-8, 8)


class ActorCritic(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden, init_log_std):
        super().__init__()

        def mlp(out):
            layers, last = [], obs_dim
            for h in hidden:
                layers += [nn.Linear(last, h), nn.ELU()]
                last = h
            layers.append(nn.Linear(last, out))
            return nn.Sequential(*layers)
        self.norm = RunningNorm(obs_dim)
        self.pi, self.v = mlp(act_dim), mlp(1)
        self.log_std = nn.Parameter(torch.full((act_dim,), float(init_log_std)))
        nn.init.uniform_(self.pi[-1].weight, -1e-3, 1e-3)
        nn.init.zeros_(self.pi[-1].bias)

    def dist(self, obs):
        x = self.norm(obs)
        return torch.distributions.Normal(self.pi(x), self.log_std.exp()), self.v(x).squeeze(-1)

    @torch.no_grad()
    def act(self, obs, deterministic=False):
        d, v = self.dist(obs)
        a = d.mean if deterministic else d.sample()
        return a, d.log_prob(a).sum(-1), v


class PPO:
    def __init__(self, model, cfg):
        self.model, self.cfg = model, cfg
        self.opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])

    def update(self, batch):
        c = self.cfg
        obs, act, logp, adv, ret = (batch[k] for k in ("obs", "act", "logp", "adv", "ret"))
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        n = obs.shape[0]
        size = n // c["minibatches"]
        stats = {"policy": 0.0, "value": 0.0, "kl": 0.0}
        for _ in range(c["epochs"]):
            perm = torch.randperm(n, device=obs.device)
            for k in range(c["minibatches"]):
                i = perm[k * size:(k + 1) * size]
                d, v = self.model.dist(obs[i])
                new = d.log_prob(act[i]).sum(-1)
                ratio = (new - logp[i]).exp()
                pg = -torch.min(ratio * adv[i], ratio.clamp(1 - c["clip"], 1 + c["clip"]) * adv[i]).mean()
                vl = ((v - ret[i]) ** 2).mean()
                loss = pg + c["valueCoef"] * vl - c["entropyCoef"] * d.entropy().sum(-1).mean()
                self.opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), c["maxGradNorm"])
                self.opt.step()
                stats["policy"] += pg.item()
                stats["value"] += vl.item()
                stats["kl"] += (logp[i] - new).mean().item()
        steps = c["epochs"] * c["minibatches"]
        return {k: v / steps for k, v in stats.items()}

    @staticmethod
    def gae(rew, val, done, last_val, gamma, lam):
        """rew/val/done (T, n); done cuts the bootstrap (a truncation is folded
        into rew as gamma*V(s_end) by the caller, then marked done)."""
        T = rew.shape[0]
        adv = torch.zeros_like(rew)
        gae = torch.zeros_like(last_val)
        for t in reversed(range(T)):
            nxt = last_val if t == T - 1 else val[t + 1]
            alive = 1.0 - done[t].to(rew.dtype)
            delta = rew[t] + gamma * nxt * alive - val[t]
            gae = delta + gamma * lam * alive * gae
            adv[t] = gae
        return adv, adv + val
