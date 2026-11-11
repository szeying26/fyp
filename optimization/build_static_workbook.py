import sys, numpy as np, pandas as pd, openpyxl
from openpyxl.utils import get_column_letter as L, column_index_from_string as CI
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
SRC, PRED_CSV, SOL, OUT = sys.argv[1:5]
res = np.load(SOL, allow_pickle=True).item()
wb = openpyxl.load_workbook(SRC); old = openpyxl.load_workbook(SRC, data_only=True)
LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]
COLS_K = {12: "L", 11: "P", 10: "T", 9: "X", 8: "AB", 7: "AF", 6: "AJ", 5: "AN", 4: "AR"}
COLS_L = dict(zip(LAMS, ["H", "L", "P", "T", "X", "AB", "AF", "AJ", "AN"]))

def clean(w):
    w = np.where(np.abs(w) < 1e-7, 0, w)
    for t in (0.05, 0.3): w = np.where(np.abs(w - t) < 1e-7, t, w)
    return w / w.sum()

def put(ws, col, r0, w):
    c = CI(col); w = clean(w)
    for i in range(12):
        ws.cell(r0 + i, c).value = float(w[i]); ws.cell(r0 + i, c + 1).value = int(w[i] > 0)

# 1. tiny-model predictions
pred = pd.read_csv(PRED_CSV); ws = wb["Predicted data"]
assert [ws.cell(r, 1).value for r in range(2, 226)] == pred["Date"].tolist(), "dates differ"
for i, row in enumerate(pred.iloc[:, 1:].to_numpy()):
    for j, v in enumerate(row): ws.cell(2 + i, 2 + j).value = float(v)

# 2. optimal weights (exact search) for both models
for sheet, tag in (("Benchmark_MV model", "hist"), ("Predicted_MV model", "tiny")):
    ws = wb[sheet]
    for K, col in COLS_K.items(): put(ws, col, 18, res[tag]["minrisk"][K])
    for lam, col in COLS_L.items(): put(ws, col, 38, res[tag]["tradeoff"][lam])
    # K=3 cannot satisfy the constraints (3 x 30% < 100%): clear the stale numbers
    c = CI("AV")
    for r in range(18, 30): ws.cell(r, c).value = 0; ws.cell(r, c + 1).value = 0
    ws["AV35"] = "K=3 is infeasible: 3 stocks x 30% max weight < 100%"
    ws["A57"] = "Weights in rows 18-29 and 38-49 are the exact optimum, found in Python by solving every K-stock subset (see Comparison sheet notes)."

# 3. labels
wb["Backtest"]["M1"] = "Tiny CNN-BiLSTM model"
wb["Summary"]["M2"] = "Tiny CNN-BiLSTM model"; wb["Summary"]["L13"] = "Tiny CNN-BiLSTM model"
bt2 = wb["Backtest (2)"]
for c in range(13, 22): bt2.cell(2, c).value = str(bt2.cell(2, c).value).replace("Predicted", "Tiny model")
wb["Stat_Test"]["B4"] = "r_A (Tiny CNN-BiLSTM)"

# 4. comparison sheet
cs = wb.create_sheet("Comparison", 0)
F = "Calibri"; bold = Font(name=F, bold=True); blue = Font(name=F, color="0000FF"); green = Font(name=F, color="008000")
head_fill = PatternFill("solid", start_color="DDEBF7"); thin = Side(style="thin", color="BFBFBF")
def cell(ref, v, font=None, fmt=None, fill=None, align=None):
    c = cs[ref]; c.value = v; c.font = font or Font(name=F)
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if align: c.alignment = Alignment(horizontal=align, wrap_text=True, vertical="center")
    return c
cell("A1", "Comparison: existing workbook vs. rebuild with the tiny CNN-BiLSTM predictions", Font(name=F, bold=True, size=14))
cell("A2", "Blue = values copied from 'Copy ver MV model.xlsx' (Summary and Stat_Test sheets). Green = live links to this workbook's Summary and Stat_Test sheets.")
osum = old["Summary"]; ost = old["Stat_Test"]
GROUPS = ["Existing: Benchmark", "Existing: CNN-BiLSTM", "Rebuild: Benchmark", "Rebuild: Tiny CNN-BiLSTM"]
def table(top, title, labels, metrics, bench_cols, pred_cols):
    cell(f"A{top}", title, Font(name=F, bold=True, size=12))
    r = top + 1
    for name, row, fmt in metrics:
        cell(f"A{r}", name, bold, fill=head_fill)
        for g, text in enumerate(GROUPS): cell(f"{L(2+g)}{r}", text, bold, fill=head_fill, align="center")
        cell(f"F{r}", "Tiny minus existing CNN-BiLSTM", bold, fill=head_fill, align="center")
        cell(f"G{r}", "Tiny minus rebuilt benchmark", bold, fill=head_fill, align="center")
        for i, lab in enumerate(labels):
            rr = r + 1 + i; b, p = bench_cols[i], pred_cols[i]
            cell(f"A{rr}", lab)
            cell(f"B{rr}", osum[f"{b}{row}"].value, blue, fmt); cell(f"C{rr}", osum[f"{p}{row}"].value, blue, fmt)
            cell(f"D{rr}", f"=Summary!{b}{row}", green, fmt); cell(f"E{rr}", f"=Summary!{p}{row}", green, fmt)
            cell(f"F{rr}", f"=E{rr}-C{rr}", None, fmt); cell(f"G{rr}", f"=E{rr}-D{rr}", None, fmt)
        rr = r + 1 + len(labels)
        cell(f"A{rr}", "Average", bold)
        for c in "BCDEFG": cell(f"{c}{rr}", f"=AVERAGE({c}{r+1}:{c}{rr-1})", bold, fmt)
        r = rr + 2
    return r
kl = [f"K={k}" for k in range(4, 13)]
nxt = table(4, "1. Minimise risk (rows = number of stocks held, K)", kl,
            [("Realized cumulative return, 2025", 4, "0.00%"), ("Sharpe ratio (annual)", 6, "0.000"), ("Max drawdown", 7, "0.00%")],
            list("CDEFGHIJK"), list("MNOPQRSTU"))
nxt = table(nxt + 1, "2. Risk-return trade-off, K=7 (rows = lambda)", [f"lambda={l}" for l in LAMS],
            [("Realized cumulative return, 2025", 15, "0.00%"), ("Sharpe ratio (annual)", 18, "0.000"), ("Max drawdown", 19, "0.00%")],
            list("CDEFGHIJK"), list("LMNOPQRST"))
r = nxt + 1
cell(f"A{r}", "3. Reference portfolios (same in both workbooks)", Font(name=F, bold=True, size=12))
for g, text in enumerate(["Equal weight", "KLCI index"]): cell(f"{L(2+g)}{r+1}", text, bold, fill=head_fill, align="center")
for i, (name, row, fmt) in enumerate([("Realized cumulative return, 2025", 4, "0.00%"), ("Sharpe ratio (annual)", 6, "0.000"), ("Max drawdown", 7, "0.00%")]):
    cell(f"A{r+2+i}", name); cell(f"B{r+2+i}", f"=Summary!L{row}", green, fmt); cell(f"C{r+2+i}", f"=Summary!W{row}", green, fmt)
r += 7
cell(f"A{r}", "4. Are the Sharpe ratios different? (Jobson-Korkie test with Memmel correction, lambda=0.9 portfolios, predicted vs. benchmark)", Font(name=F, bold=True, size=12))
for g, text in enumerate(["Existing workbook", "Rebuild (tiny model)"]): cell(f"{L(2+g)}{r+1}", text, bold, fill=head_fill, align="center")
for i, (name, ref, fmt) in enumerate([("Sharpe ratio, predicted portfolio (daily)", "K8", "0.0000"), ("Sharpe ratio, benchmark portfolio (daily)", "K9", "0.0000"),
                                      ("z statistic", "K19", "0.000"), ("p-value", "K20", "0.000"), ("Decision at 5%", "K21", None)]):
    cell(f"A{r+2+i}", name); cell(f"B{r+2+i}", ost[ref].value, blue, fmt); cell(f"C{r+2+i}", f"=Stat_Test!{ref}", green, fmt)
r += 9
cell(f"A{r}", "Notes", Font(name=F, bold=True, size=12))
notes = [
    "Predicted data: replaced with the pooled tiny CNN-BiLSTM predictions (509 weights, 5-day window, average of 5 runs), 3 Feb - 31 Dec 2025. Source: DATASET/model_output_pooled/predicted_returns_all_stocks.csv from 7.pooled_cnn_bilstm_model.py.",
    "Method is unchanged from the existing workbook: same covariance matrix (2022-2024), same constraints (5%-30% per held stock, exactly K stocks, minimum return ln(1.0615)/252 per day), same backtest and test formulas.",
    "Weights: the existing workbook's weights came from Excel Solver. Here every K-stock subset was solved in Python (scipy SLSQP) and the best kept, so the weights are the true optimum. This was done for BOTH the benchmark and the tiny-model sheets so they are compared on equal terms.",
    "Because of that, 'Rebuild: Benchmark' differs from 'Existing: Benchmark' wherever Solver had stopped at a non-optimal portfolio (K=6,7,8,9,11 and lambda >= 0.95).",
    "Existing K=12 CNN-BiLSTM portfolio: its expected return was below the required minimum, i.e. it did not satisfy its own constraint.",
    "Caveat carried over from the existing design: the predicted expected return is the average of all 2025 predictions, but the portfolio is held from 2 Jan 2025. That average was not knowable at the start of the year.",
    "Caveat: KLCI is a price index (no dividends) while the stock returns are dividend-adjusted, and no trading costs are deducted.",
]
for i, t in enumerate(notes): cell(f"A{r+1+i}", t)
cs.column_dimensions["A"].width = 38
for c in "BCDEFG": cs.column_dimensions[c].width = 21
cs.freeze_panes = "B4"
wb.active = 0
wb.calculation.fullCalcOnLoad = True   # no cached values in an openpyxl file: make Excel compute on open
wb.save(OUT); print("saved", OUT, wb.sheetnames)
