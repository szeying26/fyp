"""Solve the workbook's cardinality-constrained mean-variance problems by enumerating stock subsets."""
import sys, json, itertools, numpy as np, pandas as pd, openpyxl
from scipy.optimize import minimize
SRC, PRED_CSV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
wv = openpyxl.load_workbook(SRC, data_only=True)
def block(ws, r0, r1, c0=2, c1=13): return np.array([[ws.cell(r, c).value for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)], float)
hist = block(wv["Historical data"], 2, 734); actual = block(wv["Actual 2025"], 2, 245)
old_pred = block(wv["Predicted data"], 2, 225)
new_pred = pd.read_csv(PRED_CSV).iloc[:, 1:].to_numpy()
cov = np.cov(hist.T, ddof=0); mu_hist = hist.mean(0)
RSTAR, RF, WMAX, WMIN = np.log(1.0615) / 252, np.log(1.0288) / 252, 0.30, 0.05
LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]

def qp(idx, mu, lam=None):
    """lam=None: min variance. Otherwise max (1-lam)*mu'w - lam*w'Cw. Both with the return floor."""
    C, m, k = cov[np.ix_(idx, idx)], mu[list(idx)], len(idx)
    hi = np.sort(m)[::-1]; best_ret = WMIN * m.sum() + 0  # feasibility: max attainable return
    # greedy max return: all at WMIN, then fill up to WMAX in order of mu
    w = np.full(k, WMIN); left = 1 - k * WMIN
    for j in np.argsort(-m):
        add = min(WMAX - WMIN, left); w[j] += add; left -= add
    if left > 1e-12 or w @ m < RSTAR - 1e-12: return None
    if lam is None: f = lambda x: x @ C @ x * 1e4; g = lambda x: 2 * C @ x * 1e4
    else: f = lambda x: -((1 - lam) * (m @ x) - lam * (x @ C @ x)) * 1e4; g = lambda x: -((1 - lam) * m - 2 * lam * C @ x) * 1e4
    cons = [{"type": "eq", "fun": lambda x: x.sum() - 1, "jac": lambda x: np.ones(k)},
            {"type": "ineq", "fun": lambda x: (m @ x - RSTAR) * 1e4, "jac": lambda x: m * 1e4}]
    r = minimize(f, w, jac=g, bounds=[(WMIN, WMAX)] * k, constraints=cons, method="SLSQP", options={"ftol": 1e-14, "maxiter": 500})
    if not r.success: r = minimize(f, np.full(k, 1 / k) if k >= 4 else w, jac=g, bounds=[(WMIN, WMAX)] * k, constraints=cons, method="SLSQP", options={"ftol": 1e-14, "maxiter": 1000})
    x = r.x
    if abs(x.sum() - 1) > 1e-8 or m @ x < RSTAR - 1e-9: return None
    return r.fun, x

def solve(mu, K, lam=None):
    best = None
    for idx in itertools.combinations(range(12), K):
        s = qp(idx, mu, lam)
        if s and (best is None or s[0] < best[0] - 1e-12): best = (s[0], idx, s[1])
    if best is None: return None
    w = np.zeros(12); w[list(best[1])] = best[2]; return w

def all_portfolios(mu):
    out = {"minrisk": {K: solve(mu, K) for K in range(4, 13)}, "tradeoff": {l: solve(mu, 7, l) for l in LAMS}}
    return out

res = {"hist": all_portfolios(mu_hist), "old": all_portfolios(old_pred.mean(0)), "tiny": all_portfolios(new_pred.mean(0))}
np.save(OUT, res, allow_pickle=True)

# ---- validation against the workbook's stored Solver weights
cols_K = {12: "L", 11: "P", 10: "T", 9: "X", 8: "AB", 7: "AF", 6: "AJ", 5: "AN", 4: "AR"}
cols_L = dict(zip(LAMS, ["H", "L", "P", "T", "X", "AB", "AF", "AJ", "AN"]))
def stored(sheet, col, r0): return np.array([wv[sheet][f"{col}{r}"].value or 0 for r in range(r0, r0 + 12)], float)
for tag, sheet, mu in (("hist", "Benchmark_MV model", mu_hist), ("old", "Predicted_MV model", old_pred.mean(0))):
    print(f"== {sheet}: mine vs stored (variance x1e5; objective for trade-off)")
    for K, c in cols_K.items():
        s = stored(sheet, c, 18); m = res[tag]["minrisk"][K]
        print(f" K={K:2d} stored var {s@cov@s*1e5:.4f} ret_ok={s@mu>=RSTAR-1e-9} | mine", "infeasible" if m is None else f"var {m@cov@m*1e5:.4f} maxdiff {np.abs(m-s).max():.4f}")
    for l, c in cols_L.items():
        s = stored(sheet, c, 38); m = res[tag]["tradeoff"][l]; ob = lambda w: ((1-l)*(w@mu)-l*(w@cov@w))*1e4
        print(f" lam={l:<4} stored obj {ob(s):.5f} ret_ok={s@mu>=RSTAR-1e-9} | mine obj {ob(m):.5f} maxdiff {np.abs(m-s).max():.4f}")
print("tiny mu x1e4:", np.round(new_pred.mean(0)*1e4, 2))
for K in range(4, 13):
    m = res["tiny"]["minrisk"][K]; print(" tiny K", K, "infeasible" if m is None else np.round(m, 3))
for l in LAMS: print(" tiny lam", l, np.round(res["tiny"]["tradeoff"][l], 3))
