"""Daily re-optimisation: for each 2025 prediction day, solve the K=7 trade-off problem with that day's predicted returns."""
import sys, itertools, time, numpy as np, pandas as pd, openpyxl
from scipy.optimize import minimize
SRC, PRED_CSV, OUT = sys.argv[1:4]
wv = openpyxl.load_workbook(SRC, data_only=True)
blk = lambda ws, r0, r1: np.array([[ws.cell(r, c).value for c in range(2, 14)] for r in range(r0, r1 + 1)], float)
hist = blk(wv["Historical data"], 2, 734); cov = np.cov(hist.T, ddof=0); mu_hist = hist.mean(0)
pred = pd.read_csv(PRED_CSV); P = pred.iloc[:, 1:].to_numpy()
LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]; K, LO, HI = 7, 0.05, 0.30
SUB = np.array(list(itertools.combinations(range(12), K)))            # 792 x 7
CS = cov[SUB[:, :, None], SUB[:, None, :]] * 1e4                     # 792 x 7 x 7 (scaled)
EIG = np.linalg.eigvalsh(CS).max(1)

def project(v):
    lo = (v - HI).min(1); hi = (v - LO).max(1)
    for _ in range(40):
        t = (lo + hi) / 2; s = np.clip(v - t[:, None], LO, HI).sum(1)
        lo = np.where(s > 1, t, lo); hi = np.where(s > 1, hi, t)
    return np.clip(v - ((lo + hi) / 2)[:, None], LO, HI)

def obj(w, m, lam): return lam * np.einsum("bi,bij,bj->b", w, CS, w) - (1 - lam) * (m * w).sum(1)

def batch(mu, lam, iters=250):
    m = mu[SUB] * 1e4
    w = project(np.full((len(SUB), K), 1 / K) + m * 1e-3); y = w.copy(); tk = 1.0
    step = 1.0 / np.maximum(2 * lam * EIG, 1e-9)[:, None]
    if lam < 1: step = np.minimum(step, 50.0)
    for _ in range(iters):
        g = 2 * lam * np.einsum("bij,bj->bi", CS, y) - (1 - lam) * m
        wn = project(y - step * g); tn = (1 + np.sqrt(1 + 4 * tk * tk)) / 2
        y = wn + ((tk - 1) / tn) * (wn - w); w, tk = wn, tn
    return w, obj(w, m, lam)

def polish(b, mu, lam, w0):
    C = CS[b]; m = mu[SUB[b]] * 1e4
    f = lambda x: lam * x @ C @ x - (1 - lam) * m @ x; g = lambda x: 2 * lam * C @ x - (1 - lam) * m
    r = minimize(f, w0, jac=g, bounds=[(LO, HI)] * K, constraints=[{"type": "eq", "fun": lambda x: x.sum() - 1, "jac": lambda x: np.ones(K)}],
                 method="SLSQP", options={"ftol": 1e-15, "maxiter": 300})
    x = np.clip(r.x, LO, HI); x = x / x.sum()
    return (f(x), x) if (r.success and x.min() >= LO - 1e-9 and x.max() <= HI + 1e-9) else (f(w0), w0)

def solve(mu, lam, top=4):
    w, o = batch(mu, lam); best = None
    for b in np.argsort(o)[:top]:
        fo, x = polish(b, mu, lam, w[b])
        if best is None or fo < best[0] - 1e-12: best = (fo, b, x)
    full = np.zeros(12); full[SUB[best[1]]] = best[2]; return full, best[0]

def brute(mu, lam):
    best = None
    for b in range(len(SUB)):
        fo, x = polish(b, mu, lam, np.full(K, 1 / K))
        if best is None or fo < best[0] - 1e-12: best = (fo, b, x)
    return best[0]

if len(sys.argv) > 4:   # validation: fast method vs. full enumeration with SLSQP
    rng = np.random.default_rng(0)
    for d in rng.choice(len(P), 4, replace=False):
        for lam in (0.5, 0.9, 0.97, 0.99):
            _, fo = solve(P[d], lam); print(f"day {d} lam {lam}: fast {fo:.8f} brute {brute(P[d], lam):.8f}")
    sys.exit()

t0 = time.time(); daily = {}; static = {}
for lam in LAMS:
    static[lam] = solve(mu_hist, lam)[0]
    daily[lam] = np.array([solve(P[d], lam)[0] for d in range(len(P))]) if lam < 1 else np.tile(static[lam], (len(P), 1))
    print("lam", lam, "done", round(time.time() - t0), "s", flush=True)
np.save(OUT, {"daily": daily, "static": static, "dates": pred["Date"].tolist()}, allow_pickle=True)
