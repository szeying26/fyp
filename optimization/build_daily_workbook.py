"""Build the daily-rebalanced mean-variance workbook. Weights are solver output (values); everything else is live formulas."""
import sys, numpy as np, pandas as pd, openpyxl
from openpyxl.utils import get_column_letter as L
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
SRC, PRED_CSV, SOL, OUT, SOL_K = sys.argv[1:6]
SOL_G = sys.argv[6] if len(sys.argv) > 6 else None   # optional: full K x lambda grid

sol = np.load(SOL, allow_pickle=True).item()        # lambda loop at K = 7
sol_k = np.load(SOL_K, allow_pickle=True).item()    # cardinality loop K = 4..12 at one lambda
KS = sorted(sol_k["daily"]); LAM_K = sol_k["lam"]
old = openpyxl.load_workbook(SRC, data_only=True)
pred = pd.read_csv(PRED_CSV)
LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]
NAMES = ["CIMB", "MAYBANK", "PUBLIC BANK", "TELEKOM", "PETRONAS", "SUNWAY", "IHH HEALTHCARE", "TNB",
         "HONG LEONG BANK", "MAXIS", "AXIATA", "PRESS METAL"]
N = len(pred)                    # 224 trading days
FIRST, LAST = 6, 6 + N - 1       # data rows on the lambda sheets
AR0, AR1 = 2, 2 + N - 1          # data rows on the data sheets

F = "Arial"
base = Font(name=F, size=10); bold = Font(name=F, size=10, bold=True); title = Font(name=F, size=14, bold=True)
blue = Font(name=F, size=10, color="0000FF"); green = Font(name=F, size=10, color="008000")
head = PatternFill("solid", start_color="DDEBF7"); key = PatternFill("solid", start_color="FFFF00")
PCT, PCT4, NUM = "0.00%;(0.00%);-", "0.0000%", "0.000"

wb = openpyxl.Workbook()

def put(ws, ref, value, font=base, fmt=None, fill=None, wrap=False, align=None):
    c = ws[ref]; c.value = value; c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if wrap or align: c.alignment = Alignment(wrap_text=wrap, horizontal=align, vertical="center")
    return c

def header(ws, row, labels, col0=1):
    for i, text in enumerate(labels):
        put(ws, f"{L(col0 + i)}{row}", text, bold, fill=head, wrap=True, align="center")
    ws.row_dimensions[row].height = 44

# ---------------------------------------------------------------- Inputs
inp = wb.active; inp.title = "Inputs"
put(inp, "A1", "Daily-rebalanced portfolio: inputs and assumptions", title)
rows = [
    ("Risk-free rate, daily", "=LN(1.0288)/252", "0.000000", False, "Same as the existing workbook (2.88% a year)."),
    ("Initial wealth (RM)", 100000, "#,##0", False, "Same as the existing workbook."),
    ("Stocks held each day, K", 7, "0", False, "Same as the existing trade-off model."),
    ("Minimum weight of a held stock", 0.05, "0%", False, "Same as the existing workbook."),
    ("Maximum weight of a held stock", 0.30, "0%", False, "Same as the existing workbook."),
]
for i, (label, value, fmt, is_key, note) in enumerate(rows):
    r = 3 + i
    put(inp, f"A{r}", label); put(inp, f"B{r}", value, blue, fmt, fill=key if is_key else None); put(inp, f"C{r}", note)
put(inp, "A10", "Colour key", bold)
put(inp, "A11", "Blue text = typed-in input or optimiser output (not a formula)", blue)
put(inp, "A12", "Black text = formula", base)
put(inp, "A13", "Green text = link to another sheet", green)
put(inp, "A14", "Trading costs are not deducted anywhere in this workbook (research setting).", base)
inp.column_dimensions["A"].width = 44; inp.column_dimensions["B"].width = 14; inp.column_dimensions["C"].width = 110
RF, W0 = "Inputs!$B$3", "Inputs!$B$4"

# ---------------------------------------------------------------- data sheets
oa, ok = old["Actual 2025"], old["KLSE_data"]
actual_by_date = {oa.cell(r, 1).value: [oa.cell(r, c).value for c in range(2, 14)] for r in range(2, 246)}
klci_by_date = {ok.cell(r, 1).value: (ok.cell(r, 3).value or 0) for r in range(2, 246)}

act = wb.create_sheet("Actual 2025")
header(act, 1, ["Date"] + NAMES + ["KLCI"])
prd = wb.create_sheet("Predicted data")
header(prd, 1, ["Date"] + NAMES)
for i, date in enumerate(pred["Date"]):
    r = AR0 + i
    assert date in actual_by_date, date
    put(act, f"A{r}", date); put(prd, f"A{r}", date)
    for j in range(12):
        put(act, f"{L(2 + j)}{r}", float(actual_by_date[date][j]), blue, "0.0000%")
        put(prd, f"{L(2 + j)}{r}", float(pred.iloc[i, 1 + j]), blue, "0.0000%")
    put(act, f"N{r}", float(klci_by_date.get(date, 0)), blue, "0.0000%")
put(act, "P1", "Actual daily log returns. Source: 'Copy ver MV model.xlsx', sheets 'Actual 2025' and 'KLSE_data', restricted to the days that have a prediction.")
put(prd, "O1", "Tiny CNN-BiLSTM predicted next-day log return. Each row was produced from data up to the previous trading day. Source: DATASET/model_output_pooled/predicted_returns_all_stocks.csv (7.pooled_cnn_bilstm_model.py).")
for ws in (act, prd):
    ws.column_dimensions["A"].width = 26; ws.freeze_panes = "B2"
    for c in range(2, 15): ws.column_dimensions[L(c)].width = 12

# ---------------------------------------------------------------- historical inputs
oh = old["Historical data"]
his = wb.create_sheet("Historical data")
header(his, 1, ["Date"] + NAMES)
for r in range(2, 735):
    put(his, f"A{r}", oh.cell(r, 1).value)
    for c in range(2, 14): put(his, f"{L(c)}{r}", float(oh.cell(r, c).value), blue, "0.0000%")
his.column_dimensions["A"].width = 26; his.freeze_panes = "B2"
put(his, "O1", "Daily log returns 2022-2024. Source: 'Copy ver MV model.xlsx', sheet 'Historical data'.")

cv = wb.create_sheet("Covariance")
put(cv, "A1", "Inputs to the optimiser, from 2022-2024 history", title)
header(cv, 3, ["Stock", "Average daily return (benchmark expected return)"])
header(cv, 3, NAMES, col0=4)
for i, name in enumerate(NAMES):
    r = 4 + i; ci = L(2 + i)
    put(cv, f"A{r}", name, bold); put(cv, f"C{r}", name, bold)
    put(cv, f"B{r}", f"=AVERAGE('Historical data'!{ci}2:{ci}734)", green, "0.0000%")
    for j in range(12):
        cj = L(2 + j)
        put(cv, f"{L(4 + j)}{r}", f"=COVAR('Historical data'!{ci}2:{ci}734,'Historical data'!{cj}2:{cj}734)", green, "0.000000")
put(cv, "A18", "The covariance matrix is the same one the existing workbook uses and is held fixed all year. Only the expected returns change from day to day.")
cv.column_dimensions["A"].width = 18; cv.column_dimensions["B"].width = 26; cv.column_dimensions["C"].width = 18
for c in range(4, 16): cv.column_dimensions[L(c)].width = 12

# ---------------------------------------------------------------- reference portfolios
ref = wb.create_sheet("Reference")
put(ref, "A1", "Reference portfolios over the same days", title)
header(ref, 5, ["Date", "Equal weight return", "KLCI return", "Wealth: equal weight", "Wealth: KLCI",
                "Peak: equal weight", "Drawdown: equal weight", "Peak: KLCI", "Drawdown: KLCI"])
for i in range(N):
    r, a = FIRST + i, AR0 + i
    put(ref, f"A{r}", f"='Actual 2025'!A{a}", green)
    put(ref, f"B{r}", f"=AVERAGE('Actual 2025'!B{a}:M{a})", green, PCT4)
    put(ref, f"C{r}", f"='Actual 2025'!N{a}", green, PCT4)
    for ret, w, pk, dd in (("B", "D", "F", "G"), ("C", "E", "H", "I")):
        put(ref, f"{w}{r}", f"={W0}*(1+{ret}{r})" if i == 0 else f"={w}{r-1}*(1+{ret}{r})", base, "#,##0")
        put(ref, f"{pk}{r}", f"={w}{r}" if i == 0 else f"=MAX({pk}{r-1},{w}{r})", base, "#,##0")
        put(ref, f"{dd}{r}", f"=({pk}{r}-{w}{r})/{pk}{r}", base, PCT)
ref.column_dimensions["A"].width = 26; ref.freeze_panes = "B6"
for c in range(2, 10): ref.column_dimensions[L(c)].width = 15

# ---------------------------------------------------------------- one sheet per strategy
def sheet_name(lam): return f"lam {lam}"
def k_sheet_name(K): return f"K={K}"
COLS = ["Sum of weights", "Stocks held", "Turnover", "Daily tiny model return", "Static benchmark return",
        "Wealth: daily tiny model", "Wealth: static benchmark",
        "Peak: daily", "Drawdown: daily", "Peak: static", "Drawdown: static"]

def strategy_sheet(name, heading, static_w, daily_w):
    ws = wb.create_sheet(name)
    put(ws, "A1", heading, title)
    put(ws, "A2", "Static benchmark weights (historical average returns, held all year)", bold)
    header(ws, 3, NAMES, col0=2)
    for j in range(12): put(ws, f"{L(2 + j)}4", float(round(static_w[j], 10)), blue, "0.0%")
    put(ws, "N4", "=SUM(B4:M4)", base, "0.0%")
    header(ws, 5, ["Date"] + [f"{n} weight" for n in NAMES] + COLS)
    W = np.round(daily_w, 10)
    for i in range(N):
        r, a = FIRST + i, AR0 + i
        put(ws, f"A{r}", f"='Actual 2025'!A{a}", green)
        for j in range(12): put(ws, f"{L(2 + j)}{r}", float(W[i, j]), blue, "0.0%")
        put(ws, f"N{r}", f"=SUM(B{r}:M{r})", base, "0.0%")
        put(ws, f"O{r}", f'=COUNTIF(B{r}:M{r},">0")', base, "0")
        put(ws, f"P{r}", 0 if i == 0 else f"=SUMPRODUCT(ABS(B{r}:M{r}-B{r-1}:M{r-1}))", base, "0.0%")
        put(ws, f"Q{r}", f"=SUMPRODUCT(B{r}:M{r},'Actual 2025'!B{a}:M{a})", green, PCT4)
        put(ws, f"R{r}", f"=SUMPRODUCT($B$4:$M$4,'Actual 2025'!B{a}:M{a})", green, PCT4)
        for ret, w in (("Q", "S"), ("R", "T")):
            put(ws, f"{w}{r}", f"={W0}*(1+{ret}{r})" if i == 0 else f"={w}{r-1}*(1+{ret}{r})", base, "#,##0")
        for w, pk, dd in (("S", "U", "V"), ("T", "W", "X")):
            put(ws, f"{pk}{r}", f"={w}{r}" if i == 0 else f"=MAX({pk}{r-1},{w}{r})", base, "#,##0")
            put(ws, f"{dd}{r}", f"=({pk}{r}-{w}{r})/{pk}{r}", base, PCT)
    ws.column_dimensions["A"].width = 26; ws.freeze_panes = "B6"
    for c in range(2, 25): ws.column_dimensions[L(c)].width = 13

# stage 1: cardinality loop (stock selection), K = 4 ... 12 at one lambda
for K in KS:
    strategy_sheet(k_sheet_name(K), f"K = {K} stocks held, lambda = {LAM_K}: each day maximise (1 - lambda) x expected return - lambda x variance",
                   sol_k["static"][K], sol_k["daily"][K])
# stage 2: lambda loop at K = 7
for lam in LAMS:
    strategy_sheet(sheet_name(lam), f"lambda = {lam}, K = 7 stocks held: each day maximise (1 - lambda) x expected return - lambda x variance",
                   sol["static"][lam], sol["daily"][lam])

# ---------------------------------------------------------------- summary
sm = wb.create_sheet("Summary", 0)
put(sm, "A1", "Daily re-optimisation with tiny CNN-BiLSTM predictions vs. a static historical-average portfolio", title)
put(sm, "A2", f"Backtest: {pred['Date'].iloc[0][:10]} to {pred['Date'].iloc[-1][:10]} ({N} trading days). Both portfolios hold K stocks with 5%-30% weights and use the same 2022-2024 covariance matrix; "
              "the only difference is the expected return fed to the optimiser.")
put(sm, "A3", "No trading costs are deducted (research setting).", bold)
H = ["Daily tiny model: cumulative return", "Static benchmark: cumulative return", "Daily minus static",
     "Daily: Sharpe (annual)", "Static: Sharpe (annual)",
     "Daily: max drawdown", "Static: max drawdown", "Average daily turnover",
     "Daily Sharpe (daily)", "Static Sharpe (daily)", "Correlation of the two return series",
     "JK-Memmel z statistic", "p-value", "Different at 5%?"]

def summary_row(r, label, label_fmt, sheet, test=True):
    s = f"'{sheet}'!"
    q, t, p = (f"{s}{c}{FIRST}:{c}{LAST}" for c in "QRP")
    put(sm, f"A{r}", label, bold, label_fmt)
    put(sm, f"B{r}", f"={s}S{LAST}/{W0}-1", green, PCT)
    put(sm, f"C{r}", f"={s}T{LAST}/{W0}-1", green, PCT)
    put(sm, f"D{r}", f"=B{r}-C{r}", base, PCT)
    put(sm, f"E{r}", f"=(AVERAGE({q})-{RF})/STDEV({q})*SQRT(252)", green, NUM)
    put(sm, f"F{r}", f"=(AVERAGE({t})-{RF})/STDEV({t})*SQRT(252)", green, NUM)
    put(sm, f"G{r}", f"=MAX({s}V{FIRST}:V{LAST})", green, PCT)
    put(sm, f"H{r}", f"=MAX({s}X{FIRST}:X{LAST})", green, PCT)
    put(sm, f"I{r}", f"=AVERAGE({p})", green, "0.0%")
    put(sm, f"J{r}", f"=(AVERAGE({q})-{RF})/STDEV({q})", green, "0.0000")
    put(sm, f"K{r}", f"=(AVERAGE({t})-{RF})/STDEV({t})", green, "0.0000")
    if not test:   # identical portfolios: nothing to test
        for c in "LMNO": put(sm, f"{c}{r}", "n/a")
    else:
        put(sm, f"L{r}", f"=CORREL({q},{t})", green, NUM)
        put(sm, f"M{r}", f"=(J{r}-K{r})/SQRT((1/{N})*(2-2*L{r}+0.5*(J{r}^2+K{r}^2-2*J{r}*K{r}*L{r}^2)))", base, NUM)
        put(sm, f"N{r}", f"=2*(1-NORMSDIST(ABS(M{r})))", base, NUM)
        put(sm, f"O{r}", f'=IF(N{r}<0.05,"Yes","No")')

# table A: cardinality loop
put(sm, "A4", f"A. Stock selection: cardinality loop K = {KS[0]} to {KS[-1]}, lambda = {LAM_K}", Font(name=F, size=12, bold=True))
header(sm, 5, ["K (stocks held)"] + H)
for i, K in enumerate(KS): summary_row(6 + i, K, "0", k_sheet_name(K))
# table B: lambda loop at K = 7
RB = 6 + len(KS) + 1
put(sm, f"A{RB}", "B. Risk-return trade-off: lambda loop, K = 7", Font(name=F, size=12, bold=True))
header(sm, RB + 1, ["lambda"] + H)
for i, lam in enumerate(LAMS): summary_row(RB + 2 + i, lam, "0.00", sheet_name(lam), test=(lam != 1))
r0 = RB + 2 + len(LAMS) + 1
put(sm, f"A{r0}", "Reference portfolios (same days)", bold)
header(sm, r0 + 1, ["Portfolio", "Cumulative return", "Sharpe (annual)", "Max drawdown"])
for i, (name, ret, w, dd) in enumerate([("Equal weight (12 stocks)", "B", "D", "G"), ("KLCI index", "C", "E", "I")]):
    r = r0 + 2 + i
    put(sm, f"A{r}", name)
    put(sm, f"B{r}", f"=Reference!{w}{LAST}/{W0}-1", green, PCT)
    put(sm, f"C{r}", f"=(AVERAGE(Reference!{ret}{FIRST}:{ret}{LAST})-{RF})/STDEV(Reference!{ret}{FIRST}:{ret}{LAST})*SQRT(252)", green, NUM)
    put(sm, f"D{r}", f"=MAX(Reference!{dd}{FIRST}:{dd}{LAST})", green, PCT)
rn = r0 + 6
put(sm, f"A{rn}", "Notes", bold)
notes = [
    "How it works: before each trading day the optimiser is given that day's predicted return for the 12 stocks and picks the best K-stock portfolio. The realised return is those weights times what actually happened that day.",
    "No look-ahead: each prediction uses prices only up to the previous trading day, and the covariance matrix uses 2022-2024 only.",
    "Static benchmark: the same optimisation with historical average returns, solved once and held all year. At lambda = 1 the objective ignores expected returns, so the daily and static portfolios are identical.",
    "Full grid: sheet 'Grid summary' shows every K from 4 to 12 combined with every lambda (81 settings); the daily weights behind it are on sheets 'Grid K4' to 'Grid K12'.",
    "Comparison with the original workbook: sheet 'vs Original' backtests the original workbook's own portfolios over the same days and compares them with the daily tiny model.",
    "Two loops, as in the existing workbook: table A varies the number of stocks held (K = 4 to 12) at a fixed lambda; table B fixes K = 7 and varies lambda. Sheet 'K=7' and sheet 'lam 0.9' are the same portfolio.",
    "The cardinality loop uses the trade-off objective rather than pure risk minimisation, because when only risk is minimised the predictions do not enter and the daily and static portfolios are identical.",
    "Weights (blue cells on the 'K=' and 'lam' sheets) were found in Python by solving every K-stock combination each day and keeping the best. All other numbers are live formulas.",
    "No minimum-return floor: the existing workbook requires an expected return of ln(1.0615)/252 per day. It is dropped here because on days when every prediction is low the problem would have no solution.",
    "Turnover = sum of absolute weight changes from the previous day (2.0 would mean selling everything and buying a different portfolio). It is shown for information only.",
    "No trading costs are deducted, for either portfolio (research setting). The daily portfolio trades far more than the static one, so real-world results would be lower.",
    "Execution assumption: each day's weights are assumed to be traded at the previous day's closing price, the same price the prediction is computed from.",
    "KLCI is a price index (no dividends) while stock returns are dividend-adjusted, as in the existing workbook.",
    "Statistical test: Jobson-Korkie with Memmel correction, same formula as the existing workbook's Stat_Test sheet, comparing the daily portfolio with the static benchmark.",
]
for i, text in enumerate(notes): put(sm, f"A{rn + 1 + i}", text)
sm.column_dimensions["A"].width = 26
for c in range(2, 16): sm.column_dimensions[L(c)].width = 15
sm.freeze_panes = "B4"

# ---------------------------------------------------------------- full K x lambda grid (optional)
# One sheet per K, holding nine lambda blocks side by side (weights, turnover, daily and static return, statistics),
# and one 'Grid summary' sheet with a K-by-lambda table for each statistic.
if SOL_G:
    grid = np.load(SOL_G, allow_pickle=True).item()
    GK, GL = grid["KS"], grid["LAMS"]
    BW = 17                                   # columns per lambda block: 12 weights, turnover, daily and static return, daily and static wealth
    GS, GF = 12, 14; GE = GF + N - 1          # static-weight row, first and last data row
    STATS = ["Daily: cumulative return", "Static: cumulative return", "Daily: Sharpe (annual)", "Static: Sharpe (annual)",
             "Average daily turnover", "Daily Sharpe (daily)", "Static Sharpe (daily)", "Correlation of the two series",
             "JK-Memmel z statistic", "p-value"]          # rows 2 .. 11, in each block's first column
    def grid_name(K): return f"Grid K{K}"
    for K in GK:
        ws = wb.create_sheet(grid_name(K))
        put(ws, "A1", f"K = {K} stocks held, every lambda: daily re-optimised weights, static benchmark weights and statistics", title)
        for i, text in enumerate(STATS): put(ws, f"A{2 + i}", text, bold)
        put(ws, f"A{GS}", "Static benchmark weights", bold)
        put(ws, f"A{GF - 1}", "Date", bold, fill=head, align="center")
        for i in range(N): put(ws, f"A{GF + i}", f"='Actual 2025'!A{AR0 + i}", green)
        for b, lam in enumerate(GL):
            c0 = 2 + b * BW; c = lambda k: L(c0 + k)        # c(0..11) weights, c(12) turnover, c(13) daily, c(14) static
            w0, w1, tn, dr, sr, dw, sw = c(0), c(11), c(12), c(13), c(14), c(15), c(16)
            q, t = f"{dr}{GF}:{dr}{GE}", f"{sr}{GF}:{sr}{GE}"
            put(ws, f"{w0}2", f"={dw}{GE}/{W0}-1", base, PCT)
            put(ws, f"{w0}3", f"={sw}{GE}/{W0}-1", base, PCT)
            put(ws, f"{w0}4", f"={w0}7*SQRT(252)", base, NUM)
            put(ws, f"{w0}5", f"={w0}8*SQRT(252)", base, NUM)
            put(ws, f"{w0}6", f"=AVERAGE({tn}{GF}:{tn}{GE})", base, "0.0%")
            put(ws, f"{w0}7", f"=(AVERAGE({q})-{RF})/STDEV({q})", green, "0.0000")
            put(ws, f"{w0}8", f"=(AVERAGE({t})-{RF})/STDEV({t})", green, "0.0000")
            if lam == 1:      # identical portfolios: nothing to test
                for r in (9, 10, 11): put(ws, f"{w0}{r}", "n/a")
            else:
                put(ws, f"{w0}9", f"=CORREL({q},{t})", base, NUM)
                put(ws, f"{w0}10", f"=({w0}7-{w0}8)/SQRT((1/{N})*(2-2*{w0}9+0.5*({w0}7^2+{w0}8^2-2*{w0}7*{w0}8*{w0}9^2)))", base, NUM)
                put(ws, f"{w0}11", f"=2*(1-NORMSDIST(ABS({w0}10)))", base, NUM)
            put(ws, f"{c(1)}2", f"<- lambda = {lam}", bold)
            for j in range(12): put(ws, f"{c(j)}{GS}", float(round(grid["static"][(K, lam)][j], 10)), blue, "0.0%")
            header(ws, GF - 1, [f"{n} weight" for n in NAMES] + ["Turnover", f"Daily return (lambda {lam})", f"Static return (lambda {lam})", "Wealth: daily", "Wealth: static"], col0=c0)
            W = np.round(grid["daily"][(K, lam)], 10)
            for i in range(N):
                r, a = GF + i, AR0 + i
                for j in range(12): put(ws, f"{c(j)}{r}", float(W[i, j]), blue, "0.0%")
                put(ws, f"{tn}{r}", 0 if i == 0 else f"=SUMPRODUCT(ABS({w0}{r}:{w1}{r}-{w0}{r-1}:{w1}{r-1}))", base, "0.0%")
                put(ws, f"{dr}{r}", f"=SUMPRODUCT({w0}{r}:{w1}{r},'Actual 2025'!$B{a}:$M{a})", green, PCT4)
                put(ws, f"{sr}{r}", f"=SUMPRODUCT({w0}${GS}:{w1}${GS},'Actual 2025'!$B{a}:$M{a})", green, PCT4)
                for ret, wl in ((dr, dw), (sr, sw)):
                    put(ws, f"{wl}{r}", f"={W0}*(1+{ret}{r})" if i == 0 else f"={wl}{r-1}*(1+{ret}{r})", base, "#,##0")
        ws.column_dimensions["A"].width = 30; ws.freeze_panes = f"B{GF}"
        for cc in range(2, 2 + BW * len(GL)): ws.column_dimensions[L(cc)].width = 12

    gs = wb.create_sheet("Grid summary", 1)
    put(gs, "A1", "Full grid: every cardinality K = 4 to 12 with every lambda (81 settings)", title)
    put(gs, "A2", "Rows are K (stocks held), columns are lambda. Every cell links to the 'Grid K' sheet for that K (Grid K4 ... Grid K12). No trading costs are deducted. "
                  "At lambda = 1 the daily and static portfolios are identical, so there is nothing to test.")
    TABLES = [("Daily tiny model: cumulative return", 2, PCT), ("Static benchmark: cumulative return", 3, PCT), ("Daily minus static: cumulative return", None, PCT),
              ("Daily tiny model: Sharpe ratio (annual)", 4, NUM), ("Static benchmark: Sharpe ratio (annual)", 5, NUM),
              ("JK-Memmel p-value, daily vs. static (yellow = different at 5%)", 11, NUM), ("Average daily turnover of the daily portfolio", 6, "0.0%")]
    r = 4; first_row = {}
    for name, srow, fmt in TABLES:
        put(gs, f"A{r}", name, Font(name=F, size=12, bold=True))
        header(gs, r + 1, ["K \\ lambda"] + GL)
        first_row[name] = r + 2
        for i, K in enumerate(GK):
            rr = r + 2 + i; put(gs, f"A{rr}", K, bold, "0")
            for b, lam in enumerate(GL):
                cell = f"{L(2 + b)}{rr}"
                if srow is None:
                    d0, s0 = first_row[TABLES[0][0]] + i, first_row[TABLES[1][0]] + i
                    put(gs, cell, f"={L(2 + b)}{d0}-{L(2 + b)}{s0}", base, fmt)
                else:
                    put(gs, cell, f"='{grid_name(K)}'!{L(2 + b * BW)}{srow}", green, fmt)
        if srow == 11:
            gs.conditional_formatting.add(f"B{r + 2}:{L(1 + len(GL))}{r + 1 + len(GK)}", CellIsRule(operator="lessThan", formula=["0.05"], fill=key))
        r += len(GK) + 4
    gs.column_dimensions["A"].width = 14
    for cc in range(2, 2 + len(GL)): gs.column_dimensions[L(cc)].width = 12
    gs.freeze_panes = "B4"

# ---------------------------------------------------------------- comparison with the original workbook
# The original workbook's own portfolios (its stored Solver weights), backtested over the same days as the daily strategy.
OCOLS_K = {4: "AR", 5: "AN", 6: "AJ", 7: "AF", 8: "AB", 9: "X", 10: "T", 11: "P", 12: "L"}
OCOLS_L = dict(zip(LAMS, ["H", "L", "P", "T", "X", "AB", "AF", "AJ", "AN"]))
def orig_w(sheet, col, r0): return [float(old[sheet][f"{col}{r}"].value or 0) for r in range(r0, r0 + 12)]
ORIG = []     # (set label, K or lambda, weights)
for label, sheet in (("Original benchmark, minimise risk", "Benchmark_MV model"), ("Original CNN-BiLSTM, minimise risk", "Predicted_MV model")):
    ORIG += [(label, K, orig_w(sheet, OCOLS_K[K], 18)) for K in KS]
for label, sheet in (("Original benchmark, trade-off K = 7", "Benchmark_MV model"), ("Original CNN-BiLSTM, trade-off K = 7", "Predicted_MV model")):
    ORIG += [(label, lam, orig_w(sheet, OCOLS_L[lam], 38)) for lam in LAMS]

vo = wb.create_sheet("vs Original", 1)
orr = wb.create_sheet("Original returns")
put(vo, "A1", "Daily tiny CNN-BiLSTM strategy compared with the original workbook's portfolios", title)
put(vo, "A2", f"The original portfolios use the weights stored in 'Copy ver MV model.xlsx' (found by Excel Solver) and are held fixed. All portfolios are measured over the same {N} days "
              f"({pred['Date'].iloc[0][:10]} to {pred['Date'].iloc[-1][:10]}), so the original figures differ from that workbook's own Summary, which covers all of 2025. No trading costs.")
WR0 = 30                                    # first row of the stored original weights
put(vo, f"A{WR0 - 2}", "Original workbook weights (values copied from 'Copy ver MV model.xlsx', sheets 'Benchmark_MV model' and 'Predicted_MV model')", Font(name=F, size=12, bold=True))
header(vo, WR0 - 1, ["Portfolio", "K or lambda"] + NAMES + ["Sum of weights"])
header(orr, 1, ["Date"] + [f"{lab}, {v}" for lab, v, _ in ORIG])
for k, (lab, v, w) in enumerate(ORIG):
    r = WR0 + k
    put(vo, f"A{r}", lab); put(vo, f"B{r}", v, blue, "0.00" if k >= 2 * len(KS) else "0")
    for j in range(12): put(vo, f"{L(3 + j)}{r}", w[j], blue, "0.0%")
    put(vo, f"O{r}", f"=SUM(C{r}:N{r})", base, "0.0%")
for i in range(N):
    a = AR0 + i
    put(orr, f"A{a}", f"='Actual 2025'!A{a}", green)
    for k in range(len(ORIG)):
        put(orr, f"{L(2 + k)}{a}", f"=SUMPRODUCT('vs Original'!$C${WR0 + k}:$N${WR0 + k},'Actual 2025'!$B{a}:$M{a})", green, PCT4)
orr.column_dimensions["A"].width = 26; orr.freeze_panes = "B2"
for c in range(2, 2 + len(ORIG)): orr.column_dimensions[L(c)].width = 16
put(orr, f"{L(3 + len(ORIG))}1", "Daily return of each original-workbook portfolio: stored weights x actual returns.")

VH = ["Original benchmark: cumulative return", "Original CNN-BiLSTM: cumulative return", "Daily tiny model: cumulative return", "Daily tiny minus original CNN-BiLSTM",
      "Original benchmark: Sharpe (annual)", "Original CNN-BiLSTM: Sharpe (annual)", "Daily tiny: Sharpe (annual)",
      "Daily tiny Sharpe (daily)", "Original CNN-BiLSTM Sharpe (daily)", "Correlation of the two series", "JK-Memmel z statistic", "p-value", "Different at 5%?"]
def vs_row(r, label, fmt, k_bench, k_pred, sheet):
    ob, op = (f"'Original returns'!{L(2 + k)}{AR0}:{L(2 + k)}{AR1}" for k in (k_bench, k_pred))
    q = f"'{sheet}'!Q{FIRST}:Q{LAST}"
    put(vo, f"A{r}", label, bold, fmt)
    put(vo, f"B{r}", f"=EXP(SUMPRODUCT(LN(1+{ob})))-1", green, PCT)
    put(vo, f"C{r}", f"=EXP(SUMPRODUCT(LN(1+{op})))-1", green, PCT)
    put(vo, f"D{r}", f"='{sheet}'!S{LAST}/{W0}-1", green, PCT)
    put(vo, f"E{r}", f"=D{r}-C{r}", base, PCT)
    put(vo, f"F{r}", f"=(AVERAGE({ob})-{RF})/STDEV({ob})*SQRT(252)", green, NUM)
    put(vo, f"G{r}", f"=J{r}*SQRT(252)", base, NUM)
    put(vo, f"H{r}", f"=I{r}*SQRT(252)", base, NUM)
    put(vo, f"I{r}", f"=(AVERAGE({q})-{RF})/STDEV({q})", green, "0.0000")
    put(vo, f"J{r}", f"=(AVERAGE({op})-{RF})/STDEV({op})", green, "0.0000")
    put(vo, f"K{r}", f"=CORREL({q},{op})", green, NUM)
    put(vo, f"L{r}", f"=(I{r}-J{r})/SQRT((1/{N})*(2-2*K{r}+0.5*(I{r}^2+J{r}^2-2*I{r}*J{r}*K{r}^2)))", base, NUM)
    put(vo, f"M{r}", f"=2*(1-NORMSDIST(ABS(L{r})))", base, NUM)
    put(vo, f"N{r}", f'=IF(M{r}<0.05,"Yes","No")')
nK = len(KS)
put(vo, "A4", f"A. By number of stocks held. Original: minimise risk. Daily tiny model: trade-off at lambda = {LAM_K} (sheets 'K=')", Font(name=F, size=12, bold=True))
header(vo, 5, ["K (stocks held)"] + VH)
for i, K in enumerate(KS): vs_row(6 + i, K, "0", i, nK + i, k_sheet_name(K))
put(vo, "A16", "B. By lambda, K = 7. Original: trade-off portfolios. Daily tiny model: sheets 'lam'", Font(name=F, size=12, bold=True))
header(vo, 17, ["lambda"] + VH)
for i, lam in enumerate(LAMS): vs_row(18 + i, lam, "0.00", 2 * nK + i, 2 * nK + len(LAMS) + i, sheet_name(lam))
put(vo, "A27", "The statistical test compares the daily tiny model with the original CNN-BiLSTM portfolio (Jobson-Korkie with Memmel correction).")
vo.column_dimensions["A"].width = 36; vo.freeze_panes = "B4"
for c in range(2, 16): vo.column_dimensions[L(c)].width = 15

# ---------------------------------------------------------------- chart
ch = wb.create_sheet("Chart", 1)
put(ch, "A1", "Wealth from RM100,000, lambda = 0.9", title)
header(ch, 3, ["Date", "Daily tiny model", "Static benchmark", "Equal weight", "KLCI"])
s9 = f"'{sheet_name(0.9)}'!"
for i in range(N):
    r, d = 4 + i, FIRST + i
    put(ch, f"A{r}", f"=LEFT('Actual 2025'!A{AR0 + i},10)", green)
    for c, src in zip("BCDE", [f"{s9}S{d}", f"{s9}T{d}", f"Reference!D{d}", f"Reference!E{d}"]):
        put(ch, f"{c}{r}", f"={src}", green, "#,##0")
line = LineChart(); line.title = "Cumulative wealth (RM), 2025 out-of-sample, lambda = 0.9"
line.y_axis.title = "Wealth (RM)"; line.x_axis.title = "Date"; line.height = 11; line.width = 26
line.add_data(Reference(ch, min_col=2, max_col=5, min_row=3, max_row=3 + N), titles_from_data=True)
line.set_categories(Reference(ch, min_col=1, min_row=4, max_row=3 + N))
line.x_axis.tickLblSkip = 20; line.y_axis.scaling.min = 85000
for s in line.series: s.smooth = False; s.graphicalProperties.line.width = 15000
ch.add_chart(line, "G3")
ch.column_dimensions["A"].width = 14
for c in "BCDE": ch.column_dimensions[c].width = 16

wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
print("saved", OUT, wb.sheetnames)
