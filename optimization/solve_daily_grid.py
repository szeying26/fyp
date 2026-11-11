"""
Full grid for the daily strategy: every cardinality K = 4 ... 12 combined with every lambda
(0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1) = 81 settings. For each one the portfolio is re-optimised every day
from that day's predicted returns, and the static benchmark is solved once from historical average returns.

At lambda = 1 the objective ignores expected returns, so the daily portfolio equals the static one.
The 72 other settings are solved in parallel, one process per setting.

Usage: python solve_daily_grid.py <existing workbook> <predictions csv> <output .npy> [processes]
"""
import sys, itertools, time, multiprocessing as mp, numpy as np, pandas as pd, openpyxl
from scipy.optimize import minimize

SRC, PRED_CSV, OUT = sys.argv[1:4]
PROCS = int(sys.argv[4]) if len(sys.argv) > 4 else 8
LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]
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


def run(job):
    K, lam = job
    solve = make_solver(K, lam); st = solve(mu_hist)
    dy = np.tile(st, (len(P), 1)) if lam == 1 else np.array([solve(P[d]) for d in range(len(P))])
    return K, lam, st, dy


if __name__ == "__main__":
    t0 = time.time(); daily, static = {}, {}
    jobs = [(K, lam) for K in KS for lam in LAMS]
    with mp.Pool(PROCS) as pool:
        for K, lam, st, dy in pool.imap_unordered(run, jobs):
            static[(K, lam)] = st; daily[(K, lam)] = dy
            print(f"K={K} lam={lam} done ({len(daily)}/{len(jobs)}), {time.time() - t0:.0f}s", flush=True)
    np.save(OUT, {"daily": daily, "static": static, "dates": pred["Date"].tolist(), "KS": list(KS), "LAMS": LAMS}, allow_pickle=True)
