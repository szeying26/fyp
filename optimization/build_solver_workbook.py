"""
Build the workbook that Excel Solver (not Python) solves, for consistency with 'Copy ver MV model.xlsx'.

The 'Solver model' sheet holds the same optimisation model as the original workbook: 12 weights and 12 binary
selection cells, upper/lower link constraints, sum of weights = 1, number of stocks = K. The 'Jobs' sheet lists every
problem to solve; the VBA macro in DailySolver.bas goes down that list, calls Solver for each row and writes the weights.

Jobs, in order:
  1. static, minimise risk, historical average returns, K = 4..12       (the original workbook's stage 1)
  2. static, trade-off at K = 7, historical average returns, each lambda (the original workbook's stage 2)
  3. daily (every trading day of 2025), trade-off at K = 7, that day's predicted returns, each lambda below 1
  4. daily, trade-off at lambda = 0.9, that day's predicted returns, K = 4..12 except 7

The macro works in the original workbook's order: stage 1 finds the best cardinality at lambda = 1 (minimise risk) from a
2025 backtest, stage 2 runs the trade-off at that K, stage 3 is the lambda = 0.9 sensitivity check for the other K. If the
best K is not 7 the macro adds the stage 2 jobs for it to the Jobs sheet. The actual 2025 returns the backtest needs are
written to a second VBA module, Data2025.bas, by this script, together with the predictions for every day of 2025
(the macro adds any day that an older copy of the workbook is missing).

Usage: python build_solver_workbook.py <original workbook> <predictions csv> <output .xlsx> [<test returns csv> <output Data2025.bas>]
"""
import sys, pandas as pd, openpyxl
from openpyxl.utils import get_column_letter as L
from openpyxl.styles import Font, Alignment, PatternFill
SRC, PRED_CSV, OUT = sys.argv[1:4]
TEST_CSV, BAS_OUT = (sys.argv[4:6] if len(sys.argv) >= 6 else (None, None))
old = openpyxl.load_workbook(SRC, data_only=True); pred = pd.read_csv(PRED_CSV); N = len(pred)
NAMES = ["CIMB", "MAYBANK", "PUBLIC BANK", "TELEKOM", "PETRONAS", "SUNWAY", "IHH HEALTHCARE", "TNB",
         "HONG LEONG BANK", "MAXIS", "AXIATA", "PRESS METAL"]
KS = list(range(4, 13)); LAMS = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.97, 0.99, 1]; K0, LAM0 = 7, 0.9

F = "Arial"; base = Font(name=F, size=10); bold = Font(name=F, size=10, bold=True); title = Font(name=F, size=14, bold=True)
blue = Font(name=F, size=10, color="0000FF"); green = Font(name=F, size=10, color="008000")
head = PatternFill("solid", start_color="DDEBF7"); key = PatternFill("solid", start_color="FFFF00")
def put(ws, ref, value, font=base, fmt=None, fill=None):
    c = ws[ref]; c.value = value; c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    return c
def header(ws, row, labels, col0=1):
    for i, t in enumerate(labels):
        c = put(ws, f"{L(col0 + i)}{row}", t, bold, fill=head); c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 40

wb = openpyxl.Workbook()
# ------------------------------------------------------------ instructions
ins = wb.active; ins.title = "Instructions"
put(ins, "A1", "Daily portfolio optimisation solved by Excel Solver", title)
steps = [
    "Purpose: solve the daily portfolios with Excel Solver, using the same Solver model and options as 'Copy ver MV model.xlsx', so the daily results are consistent with the original workbook.",
    "",
    "Which workbook: everything below is done in THIS workbook, 'MV model - daily Excel Solver.xlsx' (the file you are reading now).",
    "Do not run the macro in 'Copy ver MV model.xlsx' or in the other 'MV model - ...' workbooks. They are not changed by this process.",
    "Keep only this workbook open in Excel while the macro runs.",
    "",
    "How to run (Excel for Mac):",
    "1. With this workbook open, save it as a macro-enabled workbook: File > Save As > File Format: Excel Macro-Enabled Workbook (.xlsm). Keep the name, so the file becomes 'MV model - daily Excel Solver.xlsm', in the same folder. Continue in that .xlsm file.",
    "2. Make sure Solver is installed: Tools > Excel Add-ins > tick 'Solver Add-In'.",
    "3. Open the VBA editor: Tools > Macro > Visual Basic Editor.",
    "4. In the editor, click 'VBAProject (MV model - daily Excel Solver.xlsm)' in the project list on the left so the macros go into this workbook. Then File > Import File... and choose DailySolver.bas, and again for Data2025.bas. Both are in the 'optimization' folder next to this workbook.",
    "5. In the editor: Tools > References... tick 'Solver' and press OK. (If 'Solver' is not listed, press Browse and choose Solver.xlam.)",
    "6. Back in this workbook, first run stage 1: Tools > Macro > Macros... > RunStage1BestCardinality > Run. It solves the 9 minimise-risk jobs and reports the best cardinality at lambda = 1 on the sheet 'Stage 1 best K'.",
    "   Then run everything: Tools > Macro > Macros... > RunAllStages > Run.",
    "7. Progress is shown in the status bar at the bottom of the window. Each job writes its result on the 'Jobs' sheet as soon as it is solved.",
    "8. To stop early, press Esc (or Cmd + .) and choose End. Run the macro again later and it continues with the unsolved jobs.",
    "9. When it finishes, save this workbook (Cmd + S). The results are on the 'Jobs' and 'Stage 1 best K' sheets of 'MV model - daily Excel Solver.xlsm'.",
    "",
    "The stages, in the same order as 'Copy ver MV model.xlsx':",
    "Stage 1: minimise risk (lambda = 1) for K = 4 to 12 with historical average returns. Each portfolio is held through 2025; the K with the highest cumulative return is the best cardinality.",
    "Stage 2: risk-return trade-off at the best K from stage 1, for each lambda: static (historical average returns) and daily (that day's predicted returns).",
    "Stage 3: sensitivity check, daily trade-off at lambda = 0.9 for every other K. The slow daily jobs (lambda 0.97 and 0.99) are solved last.",
    "The 'Jobs' sheet is built with stage 2 at K = 7. If stage 1 finds a different best K, the macro adds the stage 2 jobs for that K at the bottom of the 'Jobs' sheet and skips the K = 7 ones.",
    "",
    "What the macro does for each row of the 'Jobs' sheet: writes K, lambda and the expected returns into 'Solver model', starts from equal weights with every stock selected,",
    "sets up the Solver model (GRG Nonlinear, binary selection cells), solves it, and copies the weights, objective value and Solver's result code back to the row.",
    "",
    "Solver result codes: 0, 1 or 2 = Solver found a solution. 14 = integer solution found within tolerance. 5 = no feasible solution. 3 = iteration limit. 10 = time limit (100 seconds per job).",
    "",
    "Solver options are the ones stored in the original workbook: GRG Nonlinear, precision 0.000001, convergence 0.0001, central derivatives, integer optimality 0%, automatic scaling off, multistart off.",
    "One addition: a time limit of 100 seconds per job, so a single difficult day cannot stop the whole run. The original workbook had no time limit.",
    "All portfolios are backtested over the whole of 2025. A copy of this workbook made before the predictions covered January has only 224 days on 'Predicted data'; the macro adds the missing days and their jobs at the bottom of the two sheets and keeps the finished jobs.",
    "Keep the computer plugged in and awake while the macro runs; a sleeping computer pauses Solver.",
]
for i, t in enumerate(steps): put(ins, f"A{3 + i}", t, bold if t.endswith(":") else base)
ins.column_dimensions["A"].width = 160

# ------------------------------------------------------------ data
prd = wb.create_sheet("Predicted data"); header(prd, 1, ["Date"] + NAMES)
for i in range(N):
    put(prd, f"A{2 + i}", pred["Date"].iloc[i])
    for j in range(12): put(prd, f"{L(2 + j)}{2 + i}", float(pred.iloc[i, 1 + j]), blue, "0.0000%")
prd.column_dimensions["A"].width = 26; prd.freeze_panes = "B2"
put(prd, "O1", "Tiny CNN-BiLSTM predicted next-day log return. Source: DATASET/model_output_pooled/predicted_returns_all_stocks.csv")

oh = old["Historical data"]; his = wb.create_sheet("Historical data"); header(his, 1, ["Date"] + NAMES)
for r in range(2, 735):
    put(his, f"A{r}", oh.cell(r, 1).value)
    for c in range(2, 14): put(his, f"{L(c)}{r}", float(oh.cell(r, c).value), blue, "0.0000%")
his.column_dimensions["A"].width = 26; his.freeze_panes = "B2"
put(his, "O1", "Daily log returns 2022-2024. Source: 'Copy ver MV model.xlsx', sheet 'Historical data'.")

cv = wb.create_sheet("Covariance")
put(cv, "A1", "Historical average returns and covariance matrix (2022-2024), same formulas as the original workbook", title)
header(cv, 3, ["Stock", "Average daily return"]); header(cv, 3, NAMES, col0=4)
for i, n in enumerate(NAMES):
    r = 4 + i; ci = L(2 + i)
    put(cv, f"A{r}", n, bold); put(cv, f"C{r}", n, bold)
    put(cv, f"B{r}", f"=AVERAGE('Historical data'!{ci}2:{ci}734)", green, "0.0000%")
    for j in range(12):
        cj = L(2 + j)
        put(cv, f"{L(4 + j)}{r}", f"=COVAR('Historical data'!{ci}2:{ci}734,'Historical data'!{cj}2:{cj}734)", green, "0.000000")
cv.column_dimensions["A"].width = 18; cv.column_dimensions["B"].width = 20; cv.column_dimensions["C"].width = 18

# ------------------------------------------------------------ solver model (cell addresses are used by the macro)
m = wb.create_sheet("Solver model", 1)
put(m, "A1", "Solver model (the macro fills the blue cells and calls Solver)", title)
for r, (lab, v, fmt) in enumerate([("Cardinality constraint, K", 7, "0"), ("Lambda", 0.9, "0.00"), ("Max weight for each asset", 0.30, "0%"),
                                   ("Min weight for each asset", 0.05, "0%"), ("Min return of portfolio, daily (minimise-risk jobs only)", "=LN(1.0615)/252", "0.000000")], start=3):
    put(m, f"A{r}", lab); put(m, f"B{r}", v, blue, fmt)
header(m, 10, ["Asset", "Expected return", "Weight", "Binary", "Upper link", "Lower link"])
for i, n in enumerate(NAMES):
    r = 11 + i
    put(m, f"A{r}", n, bold); put(m, f"B{r}", f"=Covariance!B{4 + i}", blue, "0.0000%")
    put(m, f"C{r}", 1 / 12, blue, "0.0000", key); put(m, f"D{r}", 1, blue, "0", key)
    put(m, f"E{r}", f"=C{r}-$B$5*D{r}", base, "0.0000"); put(m, f"F{r}", f"=$B$6*D{r}-C{r}", base, "0.0000")
put(m, "A23", "Total", bold); put(m, "C23", "=SUM(C11:C22)", base, "0.0000"); put(m, "D23", "=SUM(D11:D22)", base, "0")
put(m, "A25", "Portfolio expected return"); put(m, "B25", "=SUMPRODUCT(B11:B22,C11:C22)", base, "0.000000%")
put(m, "A26", "Portfolio variance"); put(m, "B26", "=SUMPRODUCT(MMULT(Covariance!D4:O15,C11:C22),C11:C22)", base, "0.00000000")
put(m, "A27", "Trade-off objective (1 - lambda) x return - lambda x variance"); put(m, "B27", "=(1-B4)*B25-B4*B26", base, "0.00000000")
notes = ["Variables (yellow): C11:D22, the 12 weights and 12 binary selection cells.",
         "Constraints: C23 = 1; D11:D22 binary; D23 = B3; E11:E22 <= 0; F11:F22 <= 0. Minimise-risk jobs also require B25 >= B7.",
         "Objective: minimise B26 (minimise-risk jobs) or maximise B27 (trade-off jobs).",
         "This is the same model as 'Copy ver MV model.xlsx' (sheets 'Benchmark_MV model' and 'Predicted_MV model'), with the cells laid out in one block."]
for i, t in enumerate(notes): put(m, f"A{29 + i}", t)
m.column_dimensions["A"].width = 58
for c in "BCDEF": m.column_dimensions[c].width = 16

# ------------------------------------------------------------ jobs
jb = wb.create_sheet("Jobs", 2)
header(jb, 1, ["Job", "Mode", "K", "Lambda", "Day (0 = static, historical average)", "Date"] + [f"{n} weight" for n in NAMES]
       + ["Objective value", "Solver result code", "Seconds", "Portfolio expected return", "Portfolio variance", "Sum of weights", "Stocks held"])
jobs = [("minrisk", K, 1, 0) for K in KS] + [("tradeoff", K0, lam, 0) for lam in LAMS]
jobs += [("tradeoff", K0, lam, d) for lam in LAMS if lam < 1 for d in range(1, N + 1)]
jobs += [("tradeoff", K, LAM0, d) for K in KS if K != K0 for d in range(1, N + 1)]
for i, (mode, K, lam, d) in enumerate(jobs):
    r = 2 + i
    put(jb, f"A{r}", i + 1); put(jb, f"B{r}", mode); put(jb, f"C{r}", K, blue); put(jb, f"D{r}", lam, blue); put(jb, f"E{r}", d, blue)
    put(jb, f"F{r}", "static" if d == 0 else pred["Date"].iloc[d - 1])
jb.column_dimensions["F"].width = 26; jb.freeze_panes = "G2"
for c in range(7, 26): jb.column_dimensions[L(c)].width = 13
wb.save(OUT); print("saved", OUT, "jobs:", len(jobs))

# ------------------------------------------------------------ 2025 data as a VBA module (stage 1 backtest; full-year predictions)
if TEST_CSV:
    act = pd.read_csv(TEST_CSV)
    assert list(act["Date"]) == list(pred["Date"]), "predictions must cover every day of the test returns"
    line = lambda d, vals, full: (str(d) if full else str(d)[:10]) + "|" + ",".join(f"{float(v):.10f}" for v in vals)
    sets = [("LoadActual", "A", [line(d, v, False) for d, v in zip(act["Date"], act.iloc[:, 1:13].to_numpy())]),
            ("LoadPredicted", "P", [line(d, v, True) for d, v in zip(pred["Date"], pred.iloc[:, 1:13].to_numpy())])]
    out = ['Attribute VB_Name = "Data2025"', "Option Explicit", "",
           "' 2025 data for DailySolver.bas, one text line per trading day:",
           "'   date|CIMB,MAYBANK,PUBLIC BANK,TELEKOM,PETRONAS,SUNWAY,IHH HEALTHCARE,TNB,HONG LEONG BANK,MAXIS,AXIATA,PRESS METAL",
           "' LoadActual:    actual daily log returns (source: DATASET/test_log_returns.csv), for the stage 1 backtest.",
           "' LoadPredicted: tiny CNN-BiLSTM predicted returns (source: DATASET/model_output_pooled/predicted_returns_all_stocks.csv),",
           "'                used to add days that an older copy of the workbook does not have on its 'Predicted data' sheet.",
           "' Generated by build_solver_workbook.py."]
    PER = 60
    for name, tag, rows in sets:
        parts = [rows[i:i + PER] for i in range(0, len(rows), PER)]
        out += ["", f"Public Sub {name}(ByRef a() As String)", f"    ReDim a(1 To {len(rows)})"]
        out += [f"    {tag}{k + 1} a" for k in range(len(parts))] + ["End Sub"]
        n = 0
        for k, part in enumerate(parts):
            out += ["", f"Private Sub {tag}{k + 1}(ByRef a() As String)"]
            for t in part:
                n += 1; out.append(f'    a({n}) = "{t}"')
            out.append("End Sub")
    open(BAS_OUT, "w").write("\n".join(out) + "\n"); print("saved", BAS_OUT, "days:", len(act))
