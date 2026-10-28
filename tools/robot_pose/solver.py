"""Levenberg-Marquardt with box bounds and a numeric Jacobian (numpy only: the
PC and the cloud need no scipy for this). Small problems: <= ~40 unknowns."""
import numpy as np


def least_squares(fun, x0, lo=None, hi=None, iters=60, step=1e-3, lam=1e-3, tol=1e-9):
    """Minimise sum(fun(x)**2). -> (x, cost). step: relative finite-difference step."""
    x = np.asarray(x0, float).copy()
    lo = np.full_like(x, -np.inf) if lo is None else np.asarray(lo, float)
    hi = np.full_like(x, np.inf) if hi is None else np.asarray(hi, float)
    x = np.clip(x, lo, hi)
    r = fun(x)
    cost = float(r @ r)
    for _ in range(iters):
        J = np.empty((r.size, x.size))
        for j in range(x.size):
            h = step * max(1.0, abs(x[j]))
            xj = x.copy()
            xj[j] += h
            if xj[j] > hi[j]:              # step inward at an upper bound
                xj[j] = x[j] - h
                h = -h
            J[:, j] = (fun(xj) - r) / h
        A, g = J.T @ J, J.T @ r
        improved = False
        while lam < 1e10:
            dx = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
            xn = np.clip(x + dx, lo, hi)
            rn = fun(xn)
            cn = float(rn @ rn)
            if cn < cost:
                done = cost - cn < tol * max(1.0, cost)
                x, r, cost, lam, improved = xn, rn, cn, max(lam / 3, 1e-9), True
                break
            lam *= 4
        if not improved or done:
            break
    return x, cost
