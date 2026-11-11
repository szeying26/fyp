"""
Cardinality loop for the daily strategy: for K = 4 ... 12 stocks held, re-optimise the portfolio every
day from that day's predicted returns, at one fixed lambda (default 0.9).

Mirrors the existing workbook's first stage (stock selection: loop K from 4 to the number of stocks),
but with the trade-off objective, because under pure risk minimisation the predictions do not enter.

Usage: python solve_daily_cardinality.py <existing workbook> <predictions csv> <output .npy> [lambda]
"""
import sys, itertools, time, numpy as np, pandas as pd, openpyxl
from scipy.optimize import minimize

SRC, PRED_CSV, OUT = sys.argv[1:4]
LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.9
LO, HI, KS = 0.05, 0.30, range(4, 13)

wv = openpyxl.load_workbook(SRC, data_only=True)
blk = lambda ws, r0, r1: np.array([[ws.cell(r, c).value for c in range(2, 14)] for r in range(r0, r1 + 1)], float)
hist = blk(wv["Historical data"], 2, 734); cov = np.cov(hist.T, ddof=0); mu_hist = hist.mean(0)
pred = pd.read_csv(PRED_CSV); P = pred.iloc[:, 1:].to_numpy()


def make_solver(K, lam):
    SUB = np.array(list(itertools.combinations(range(12), K)))
    CS = cov[SUB[:, :, None], SUB[:, None, :]] * 1e4
    EIG = np.linalg.eigvalsh(CS).max(1)

    def project(v):          # onto {sum = 1, LO <= w <= HI}, by bisection
        lo = (v - HI).min(1); hi = (v - LO).max(1)
        for _ in range(40):
            t = (lo + hi) / 2; s = np.clip(v - t[:, None], LO, HI).sum(1)
            lo = np.where(s > 1, t, lo); hi = np.where(s > 1, hi, t)
        return np.clip(v - ((lo + hi) / 2)[:, None], LO, HI)

    def batch(mu, iters=250):   # accelerated projected gradient on every K-stock subset at once
        m = mu[SUB] * 1e4
        w = project(np.full((len(SUB), K), 1 / K) + m * 1e-3); y = w.copy(); tk = 1.0
        step = np.minimum(1.0 / np.maximum(2 * lam * EIG, 1e-9), 50.0)[:, None]
        for _ in range(iters):
            g = 2 * lam * np.einsum("bij,bj->bi", CS, y) - (1 - lam) * m
            wn = project(y - step * g); tn = (1 + np.sqrt(1 + 4 * tk * tk)) / 2
            y = wn + ((tk - 1) / tn) * (wn - w); w, tk = wn, tn
        return w, lam * np.einsum("bi,bij,bj->b", w, CS, w) - (1 - lam) * (m * w).sum(1)

    def polish(b, mu, w0):      # exact refinement of one subset
        C = CS[b]; m = mu[SUB[b]] * 1e4
        f = lambda x: lam * x @ C @ x - (1 - lam) * m @ x; g = lambda x: 2 * lam * C @ x - (1 - lam) * m
        r = minimize(f, w0, jac=g, bounds=[(LO, HI)] * K, method="SLSQP", options={"ftol": 1e-15, "maxiter": 300},
                     constraints=[{"type": "eq", "fun": lambda x: x.sum() - 1, "jac": lambda x: np.ones(K)}])
        x = np.clip(r.x, LO, HI); x = x / x.sum()
        return (f(x), x) if (r.success and x.min() >= LO - 1e-9 and x.max() <= HI + 1e-9) else (f(w0), w0)

    def solve(mu, top=4):
        w, o = batch(mu); best = None
        for b in np.argsort(o)[:top]:
            fo, x = polish(b, mu, w[b])
            if best is None or fo < best[0] - 1e-12: best = (fo, b, x)
        full = np.zeros(12); full[SUB[best[1]]] = best[2]; return full
    return solve


t0 = time.time(); daily, static = {}, {}
for K in KS:
    solve = make_solver(K, LAM)
    static[K] = solve(mu_hist)
    daily[K] = np.array([solve(P[d]) for d in range(len(P))])
    print(f"K={K} done, {time.time() - t0:.0f}s", flush=True)
np.save(OUT, {"lam": LAM, "daily": daily, "static": static, "dates": pred["Date"].tolist()}, allow_pickle=True)
