# Stock return prediction and portfolio optimisation for 12 Bursa Malaysia stocks

This README records everything done on this project branch, from the first request ("the model is underfit, enrich the features") to the final daily-rebalanced portfolio workbook. It explains every file, every new spreadsheet sheet, every experiment and its result.

All results use the same split: **train 2022–2024, test 2025**. Nothing from 2025 was used to choose features or train models.

> **Status note (15 Nov 2026).** The pooled model has since been retrained on 5-day windows built directly in step 5 (`WINDOW_SIZE = 5`; the 20-day window and `INPUT_WINDOW` are removed), which adds 15 training days per stock. The files in `DATASET/windowed_data` and `DATASET/model_output_pooled` are from this retrained model: average correlation 0.129, error relative to predicting zero 0.989, direction right 52.9%, 12 of 12 stocks beat zero (full year 2025). **Everything below this note — the plots, the workbooks, `optimization/Data2025.bas` and all portfolio results — still describes the previous model** (20-day windows cut to the last 5 days; correlation 0.132) and has not been re-run. The two sets of predictions correlate 0.99 for every stock.

## Contents

1. [Headline findings](#1-headline-findings)
2. [What was done, in order](#2-what-was-done-in-order)
3. [Files in this repository](#3-files-in-this-repository)
4. [Step-by-step details and results](#4-step-by-step-details-and-results)
5. [The spreadsheets, sheet by sheet](#5-the-spreadsheets-sheet-by-sheet)
6. [How to run everything](#6-how-to-run-everything)
7. [Limitations](#7-limitations)
8. [State of the repository](#8-state-of-the-repository)
9. [Glossary](#9-glossary)

---

## 1. Headline findings

| Question | Answer |
|---|---|
| Was the original model underfitting because it lacked features? | No. Adding the selected Alpha101 features did not help the original network. The network itself was the bottleneck. |
| What is actually predictable in this data? | A small next-day reversal: after a down day a stock is slightly more likely to rise, and the reverse. Lag-1 autocorrelation of returns is about −0.09. |
| What fixed the model? | Making it about 100 times smaller (477 weights instead of about 54,000), looking at 5 days instead of 20, training one model on all 12 stocks, scaling the target, and averaging 5 runs. |
| How good is the final model? | Over all of 2025: correlation 0.132 between predicted and actual returns, error 1.1% lower than predicting "no change", direction right 52.5% of the time, better than "no change" for 11 of the 12 stocks. |
| Is it the best possible model? | No. A one-variable straight-line model on yesterday's return is slightly better (correlation 0.170 against 0.137 on the 224 days where both were tested, section 4.7). |
| Does the existing optimisation workbook show that predictions help? | It cannot. Its design averages a year of predictions into one number and holds one portfolio, so predictions barely enter. |
| Do predictions help when used daily? | Yes, before trading costs. Daily re-optimisation returned 26–37% against 6–11% for the static benchmark (all of 2025), a statistically significant difference for λ up to 0.97 at K = 7, and for every K from 4 to 12 at λ = 0.9. Across the full grid of 72 settings where the two portfolios can differ (K = 4 to 12, λ = 0.1 to 0.99), the daily portfolio is ahead in every one and significantly so in 58. |
| And after trading costs? | At an assumed 0.15% per unit traded the advantage disappears. The break-even cost is 0.12–0.14%. The workbook excludes costs at the user's request (research setting). |
| How does the daily strategy compare with the original workbook? | Over the whole of 2025 the original workbook's portfolios returned 7–14%; the daily tiny model returned 26–37% for λ up to 0.97. The gap in Sharpe ratio is statistically significant in 5 of the 18 comparisons (section 4.15). |
| Which period are the portfolios tested on? | Every portfolio in every workbook is backtested over the whole of 2025, 2 January to 31 December (244 trading days), so all comparisons are like for like. |
| What period does the data cover? | 3 January 2022 to 31 December 2025 only. Nothing from 2020–2021 is used anywhere, to keep the COVID period out. |

---

## 2. What was done, in order

1. **Researched Alpha101.** Read the Coriva overview (<https://coriva.eu.org/alpha101-overview/>) and its momentum/reversal detail page for the 23 factors in that category.
2. **Added the features.** Implemented 21 of the 23 momentum/reversal alphas (`alpha101.py`). Two were skipped: #56 needs market cap, #90 needs an industry classification.
3. **Ran a correlation check** (`4b.alpha_features.py`) on the training years only. 9 alphas were kept.
4. **Tested the original CNN-BiLSTM with and without the alphas.** No improvement; both were worse than predicting zero.
5. **Scaled the target and trained a pooled model.** Error fell closer to the "predict zero" level, but mostly because the network predicted less, not better.
6. **Analysed rolling z-score normalisation.** Safe and mildly helpful on the inputs; harmful on the target.
7. **Added the rolling z-score to the pipeline** (`5.feature_engineering.py`).
8. **Tried smaller networks.** A tiny CNN-BiLSTM (about 500 weights) on a 5-day window was the first network to beat predicting zero.
9. **Published an explainer report** on the tiny CNN-BiLSTM for a non-technical reader: <https://claude.ai/artifact/NwTXM5m9R5sDUyxncg57yh> (private to the account owner until shared; it describes single-run numbers, see section 4.8).
10. **Made the tiny model the pipeline default** (`7.pooled_cnn_bilstm_model.py`), averaged over 5 runs, and **plotted its results** (`8.plot_pooled_results.py`), including the two figure types from `plotting.py`.
11. **Diagnosed the "flat" predictions.** Not classic underfitting and not caused by log returns; the model is more than twice too timid.
12. **Committed and pushed** the code to branch `alpha101-momentum-reversal-features`.
13. **Analysed the existing optimisation workbook** (`Copy ver MV model.xlsx`).
14. **Rebuilt the optimisation with tiny-model predictions** (`MV model - tiny CNN-BiLSTM.xlsx`) and compared it with the existing results.
15. **Explained why benchmark and prediction results match** in that design.
16. **Built a daily-rebalanced version** (`MV model - daily tiny CNN-BiLSTM.xlsx`), first with trading costs, then with costs removed.
17. **Added the cardinality loop to the daily version.** The first build fixed K = 7. The existing workbook's stock-selection stage loops K from 4 to 12, so the daily version now does the same.
18. **Computed the full grid.** Every K from 4 to 12 combined with every λ (81 settings), added to the daily workbook as a `Grid summary` sheet and nine `Grid K` sheets.
19. **Set all data to start in 2022.** The price download begins on 3 January 2022, to keep the COVID period (2020–2021) out of every calculation, including look-back history. Every step, every experiment in section 4 and both workbooks were run on this data; all numbers in this README come from it. Alphas that need 200–250 days of history are excluded by the coverage rule, and the first 60 trading days of 2022 serve only as look-back history.
20. **Compared the daily strategy with the original workbook.** The original workbook's own portfolios were backtested over the same days and compared with the daily tiny model (sheet `vs Original`, section 4.15).
21. **Extended the backtest to the whole of 2025.** The daily version first covered 3 Feb to 31 Dec (224 days), because the test windows were built from 2025 data alone and the first 20 days had no prediction. The windows now take their look-back days from the end of 2024, so the same trained model (the 5 saved networks, not retrained) predicts every trading day from 2 January. The 224 existing predictions are unchanged to the last digit; 20 January days were added. Every portfolio in every workbook is now backtested over the same 244 days.
22. **Set up an Excel Solver version** (`MV model - daily Excel Solver.xlsx`, section 4.16), so the daily portfolios can be solved with the same tool and settings as the original workbook. Its first stage finds the best cardinality at λ = 1, as the original workbook does.

---

## 3. Files in this repository

### Pipeline scripts (run in this order)

| File | Status | What it does |
|---|---|---|
| `1.raw_data.py` | changed | Downloads the 12 stocks from Yahoo Finance. Still writes the adjusted-close file `malaysia_stocks.csv` for 2022 onwards. **New:** also writes `DATASET/ohlcv_malaysia_stocks.csv`, a full open/high/low/close/volume table for the same period (3 Jan 2022 onwards; nothing earlier is downloaded). Stops with an error if Yahoo returns an empty column for any stock. |
| `2.data_preprocess.py` | unchanged | Cleans the adjusted-close file (dates, duplicates, missing rows). |
| `3.return_calculation.py` | unchanged | Turns prices into daily log returns, `DATASET/log_returns.csv`. |
| `4.train_test_split.py` | unchanged | Splits returns into train (2022–2024) and test (2025). |
| `alpha101.py` | **new** | Library of operators (`rank`, `ts_rank`, `delta`, `decay_linear`, …) and the 21 momentum/reversal alphas. Every alpha on day t uses data up to the close of day t only. |
| `4b.alpha_features.py` | **new** | Computes the alphas, runs the correlation check on the training years, and saves the features, the report and the selected list. Run after step 4 and before step 5. |
| `5.feature_engineering.py` | changed | Builds the 20-day input windows. **New options:** `USE_ALPHA_FEATURES` (append the target stock's 9 selected alphas) and `USE_ROLLING_ZSCORE` (replace input returns with a 60-day rolling z-score). The prediction target is always the plain log return. With both on, each window has 21 features instead of 12. Days at the start of 2022 that lack look-back history are left out of the training sample. **Test windows take their look-back days from the end of 2024** (`TEST_LOOKBACK_FROM_TRAIN`), so every trading day of 2025 gets a prediction, starting on 2 January. |
| `6.cnn_bilstm_model.py` | changed | The original per-stock CNN-BiLSTM (54,321 weights). **New option:** `SCALE_TARGET` standardises the target using training data and converts predictions back to log returns. Kept for comparison; not the recommended model. |
| `7.pooled_cnn_bilstm_model.py` | **new** | The final model. One tiny CNN-BiLSTM (477 weights) trained on all 12 stocks together, using the last 5 days of each window, trained 5 times with different seeds and averaged. Writes to `DATASET/model_output_pooled/`. Run with `REUSE_SAVED_MODELS=1` to load the 5 saved networks and only predict, without training. |
| `8.plot_pooled_results.py` | **new** | All result plots for the final model, written to `OUTPUT/pooled_model_plots/`. |
| `plotting.py` | unchanged | The original plotting script. It reads the step 6 output folder. Its two figure types are reproduced for the final model by step 8. |

### Optimisation scripts (`optimization/`)

These produced the two new workbooks. They were written as working scripts during the analysis and take their file paths as command-line arguments (see section 6).

| File | What it does |
|---|---|
| `optimization/solve_static_portfolios.py` | Solves the existing workbook's two portfolio problems exactly, by solving every K-stock combination and keeping the best. Does this for historical averages, the old predictions and the tiny-model predictions, and prints a check against the weights stored in the existing workbook. |
| `optimization/build_static_workbook.py` | Copies the existing workbook, swaps in the tiny-model predictions and the exact weights, and adds the `Comparison` sheet. Output: `MV model - tiny CNN-BiLSTM.xlsx`. |
| `optimization/solve_daily_portfolios.py` | For each of the 244 prediction days (every trading day of 2025) and each λ, finds the best 7-stock portfolio from that day's predictions. A fast batch method ranks all 792 combinations and the best few are refined exactly; it was checked against full enumeration on 16 cases with identical results. |
| `optimization/solve_daily_cardinality.py` | The cardinality loop for the daily strategy: the same daily optimisation for every K from 4 to 12 at one λ (0.9 by default). |
| `optimization/solve_daily_grid.py` | The full grid: the same daily optimisation for every K from 4 to 12 combined with every λ (81 settings), solved in parallel. About 5 minutes on 9 processes. |
| `optimization/build_daily_workbook.py` | Builds the daily workbook from scratch with live formulas, from the outputs of the three daily solvers (the grid file is an optional sixth argument). Output: `MV model - daily tiny CNN-BiLSTM.xlsx`. |
| `optimization/build_solver_workbook.py` | Builds `MV model - daily Excel Solver.xlsx`, the workbook that Excel Solver itself solves (section 4.16), and the data module `optimization/Data2025.bas`. |
| `optimization/DailySolver.bas`, `optimization/Data2025.bas` | The VBA macro that runs Excel Solver over every job, and the 2025 data it needs. Imported into the Solver workbook by hand. |

### Spreadsheets

| File | Status | What it is |
|---|---|---|
| `Copy ver MV model.xlsx` | existing (pulled from `main`) | The original mean-variance optimisation and backtest. |
| `MV model - tiny CNN-BiLSTM.xlsx` | **new** | Same design as the existing workbook, with tiny-model predictions and exact weights, plus a `Comparison` sheet. |
| `MV model - daily tiny CNN-BiLSTM.xlsx` | **new** | Daily re-optimisation using each day's prediction. No trading costs. |
| `MV model - daily Excel Solver.xlsx` | **new** | The same optimisation problems set up for Excel Solver, for consistency with the original workbook. Solved by a macro inside Excel (section 4.16). |

### Generated data and outputs

| Path | Contents |
|---|---|
| `malaysia_stocks.csv` | Adjusted close prices from step 1. |
| `DATASET/ohlcv_malaysia_stocks.csv` | OHLCV table from 3 Jan 2022 (step 1). |
| `DATASET/cleaned_malaysia_stocks.csv`, `log_returns.csv`, `train_log_returns.csv`, `test_log_returns.csv` | Outputs of steps 2–4. |
| `DATASET/alpha_features/alpha_features.csv` | All 21 alphas for every stock and day, cleaned. |
| `DATASET/alpha_features/alpha_ic_report.csv` | The correlation check table (section 4.2). |
| `DATASET/alpha_features/alpha_feature_correlation.csv` | Correlation between features on the training years. |
| `DATASET/alpha_features/selected_alpha_features.json` | The 9 selected alphas, read by step 5. |
| `DATASET/windowed_data/` | Model inputs and targets per stock (step 5). |
| `DATASET/model_output_pooled/` | Final model: 5 saved networks, per-stock predictions, `predicted_returns_all_stocks.csv`, metrics. |
| `OUTPUT/pooled_model_plots/` | All figures (section 4.9). |

---

## 4. Step-by-step details and results

### 4.1 The Alpha101 features

"101 Formulaic Alphas" (Kakushadze, 2016) is a published list of formulas that turn price and volume history into signals. The Coriva article groups them into five categories; this work used the **momentum and reversal** group:

`#4 #8 #9 #10 #19 #20 #23 #24 #29 #30 #33 #35 #37 #38 #39 #46 #49 #51 #52 #53 #56 #84 #90`

Implementation choices:

- **Skipped:** #56 (needs market cap) and #90 (needs sub-industry classification).
- **Prices:** open, high and low are put on the same dividend-adjusted basis as the adjusted close, so ex-dividend days do not look like price gaps.
- **VWAP** (#84) is approximated by (high + low + close) / 3, as the article suggests for daily data.
- **Fractional windows** in the paper (for example 9.99922) are rounded to whole numbers.
- **#9 and #30** follow the original paper where the article's formula differs.
- **#53** divides by (close − low), which is zero on about 10% of days for these stocks; the denominator is floored at 0.0001.
- **#46, #49, #51** use price-unit thresholds designed for US stocks; for these lower-priced stocks they rarely trigger and mostly reduce to "minus yesterday's price change".
- Cross-sectional ranks are over only 12 stocks, so they are coarse.

### 4.2 The correlation check

Run on 2022–2024 only (733 days × 12 stocks). Each alpha on day t was compared with the stock's return on day t+1.

- **IC** (information coefficient): Spearman correlation between the alpha and the next-day return, after standardising each stock's series.
- **Partial IC**: the same after removing what the stock's own day-t return already explains. The model already receives that return, so an alpha only adds value if it predicts something beyond it.
- **Selection rule:** coverage ≥ 95%, |partial IC| ≥ 0.02 (about two standard errors), and correlation below 0.70 with the day-t return and with any alpha already kept.
- **Coverage** is the share of training days on which the alpha has a value. Because the data starts in 2022, an alpha with a long look-back has no value for its first days. The five alphas that need 200–250 days of history (#19, #24, #37, #39, #52) cover only 66–73% of the training days and are dropped by this rule. The others need at most 34 days.
- Before the check each alpha is winsorised at its training 1%/99% quantiles per stock; gaps after an alpha's first value are forward-filled, then filled with the training median. The days before its first value are left empty.

| Feature | Coverage | Train IC | Train partial IC | Stocks with same sign | Test IC | Test partial IC | Decision |
|---|---|---|---|---|---|---|---|
| ret_1d (own day-t return) | 100% | −0.087 | n/a | 12/12 | −0.122 | n/a | base feature, already in the model |
| alpha038 | 99% | 0.112 | 0.074 | 12/12 | 0.126 | 0.061 | KEPT |
| alpha033 | 100% | 0.102 | 0.059 | 12/12 | 0.124 | 0.055 | dropped: correlation +0.85 with alpha038 |
| alpha039 | 66% | 0.073 | 0.055 | 12/12 | 0.062 | 0.040 | dropped: coverage 66% below 95% (needs more history than 2022 provides) |
| alpha008 | 98% | 0.068 | 0.051 | 11/12 | 0.070 | 0.048 | KEPT |
| alpha084 | 95% | 0.073 | 0.050 | 12/12 | 0.082 | 0.051 | KEPT |
| alpha019 | 66% | 0.066 | 0.045 | 12/12 | 0.038 | 0.010 | dropped: coverage 66% below 95% (needs more history than 2022 provides) |
| alpha035 | 96% | 0.095 | 0.044 | 12/12 | 0.106 | 0.030 | KEPT |
| alpha053 | 99% | 0.070 | 0.039 | 12/12 | 0.068 | 0.027 | KEPT |
| alpha046 | 97% | 0.065 | 0.038 | 12/12 | 0.067 | 0.026 | KEPT |
| alpha052 | 67% | 0.043 | 0.036 | 9/12 | 0.024 | 0.012 | dropped: coverage 67% below 95% (needs more history than 2022 provides) |
| alpha037 | 73% | 0.080 | 0.033 | 12/12 | 0.104 | 0.044 | dropped: coverage 73% below 95% (needs more history than 2022 provides) |
| alpha024 | 73% | 0.050 | 0.029 | 11/12 | 0.052 | 0.033 | dropped: coverage 73% below 95% (needs more history than 2022 provides) |
| alpha010 | 100% | 0.078 | 0.029 | 12/12 | 0.110 | 0.041 | KEPT |
| alpha030 | 98% | 0.058 | 0.028 | 11/12 | 0.057 | 0.016 | KEPT |
| alpha029 | 99% | 0.020 | 0.021 | 7/12 | 0.032 | 0.029 | KEPT |
| alpha049 | 97% | 0.083 | −0.018 | 11/12 | 0.126 | 0.031 | dropped: partial IC below 0.02 |
| alpha009 | 99% | 0.076 | −0.015 | 12/12 | 0.115 | 0.005 | dropped: partial IC below 0.02 |
| alpha020 | 100% | 0.018 | 0.013 | 8/12 | 0.009 | 0.003 | dropped: partial IC below 0.02 |
| alpha023 | 98% | 0.014 | −0.011 | 9/12 | 0.031 | 0.000 | dropped: partial IC below 0.02 |
| alpha051 | 97% | 0.081 | 0.010 | 11/12 | 0.131 | 0.052 | dropped: partial IC below 0.02 |
| alpha004 | 99% | 0.004 | 0.001 | 8/12 | 0.000 | −0.005 | dropped: partial IC below 0.02 |

The test columns are an out-of-sample check and were not used for selection.

**Selected (9):** alpha038, 008, 084, 035, 053, 046, 010, 030, 029. The highest correlation between any two of them is 0.61.

**What the check revealed:** every alpha has a positive IC because they all partly measure the same thing, the next-day reversal. The per-stock lag-1 autocorrelation of returns in training ranges from +0.02 (CIMB) to −0.19 (Maxis).

### 4.3 Original CNN-BiLSTM, with and without the alphas

Per-stock models (Conv1D 64 filters → max pooling → BiLSTM 50 → dropout → dense 32 → 1), raw returns as inputs, 12 stocks × 3 seeds.

| Inputs | MSE ÷ MSE of predicting zero | Correlation with actual | Stocks improved by alphas |
|---|---|---|---|
| Returns only | 1.054 | 0.026 | n/a |
| Returns + 9 alphas | 1.293 (median run 1.010) | 0.024 | 5 of 12 |

Both are worse than predicting zero. The average with alphas is pulled up by Maybank, where the network's error was 3.7 times the zero baseline; the median run is 1.010. A ridge regression on yesterday's return alone reached a correlation of 0.17 and beat zero, and giving that regression all the features did not improve it (0.16). Conclusion: the features carry signal individually but add almost nothing jointly, and the network was failing to learn even the simple reversal.

### 4.4 Target scaling and pooling

Daily returns are about 0.01 in size, so the raw squared-error loss is tiny and the network settles near a constant. Scaling the target fixes the loss scale. Pooling trains one model on all stocks (about 8,000 samples instead of about 700 per stock).

| Model (3 seeds, 12 stocks) | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|
| Per-stock, raw target, returns only (original) | 1.054 | 0.026 | 2 of 12 |
| Per-stock, raw target, + alphas | 1.293 | 0.024 | 0 of 12 |
| Per-stock, scaled target, returns only | 1.019 | 0.020 | 1 of 12 |
| Per-stock, scaled target, + alphas | 1.009 | 0.013 | 1 of 12 |
| Pooled, scaled target, returns only | 1.003 | 0.019 | 4 of 12 |
| Pooled, scaled target, + alphas | 1.002 | 0.019 | 4 of 12 |

Error moved towards the "predict zero" level, but the predictions shrank (to 5–10% of the size of actual moves, from 16%) while correlation did not improve.

### 4.5 Rolling z-score analysis

The z-score for day t uses the mean and standard deviation of the **previous** W days only, so nothing leaks from the future. With data from 2022 only, the first W days of returns have no z-score and drop out of training, so a longer window costs more training days (20, 60 or 120).

Effect on the data (average of 12 stocks):

| Property | Raw | z, 20-day | z, 60-day | z, 120-day |
|---|---|---|---|---|
| Test volatility ÷ train volatility | 1.20 | 1.03 | 1.05 | 1.00 |
| Range of that ratio across stocks | 0.88–2.03 | 0.96–1.17 | 0.95–1.15 | 0.88–1.12 |
| Volatility clustering (lag-1 autocorrelation of absolute returns) | 0.18 | 0.10 | 0.14 | 0.16 |
| Excess kurtosis | 4.4 | 5.0 | 5.5 | 6.9 |
| Correlation with next-day return, test | −0.115 | −0.111 | −0.118 | −0.120 |

Effect on the model (original architecture; pooled rows 5 seeds, per-stock rows 3 seeds):

| Model | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|
| Pooled, raw inputs | 1.007 | 0.014 | 1 of 12 |
| Pooled, z inputs 20-day | 1.018 | 0.001 | 1 of 12 |
| Pooled, z inputs 60-day | 1.004 | 0.034 | 4 of 12 |
| Pooled, z inputs 120-day | 1.031 | 0.024 | 0 of 12 |
| Pooled, z inputs and z target, 60-day | 1.014 | −0.005 | 0 of 12 |
| Pooled, raw inputs + alphas | 1.002 | 0.027 | 4 of 12 |
| Pooled, z inputs 60-day + alphas | 1.002 | 0.050 | 6 of 12 |
| Per-stock, raw inputs | 1.019 | 0.020 | 1 of 12 |
| Per-stock, z inputs 60-day | 1.024 | 0.015 | 2 of 12 |
| Per-stock, z inputs and z target, 60-day | 1.032 | −0.023 | 0 of 12 |
| Ridge on yesterday's return, raw | 0.976 | 0.17 | 10 of 12 |
| Ridge, z input and z target | 0.986 | 0.12 | 10 of 12 |

Decision: use a 60-day rolling z-score on the **inputs** and leave the target as a plain log return.

### 4.6 Smaller networks

Pooled setup, z-scored inputs plus 9 alphas (22 input features), 5 seeds each.

| Model | Weights | Window | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|---|---|
| Original CNN-BiLSTM (64 filters, LSTM 50, dense 32) | 53,553 | 20 days | 1.002 | 0.050 | 6 of 12 |
| Small CNN-BiLSTM (8 filters, LSTM 8, pooling, dropout) | 1,641 | 20 days | 1.005 | 0.034 | 2 of 12 |
| Small CNN-BiLSTM (same) | 1,641 | 10 days | 1.007 | 0.011 | 3 of 12 |
| Small LSTM (8 units) | 1,001 | 20 days | 0.996 | 0.089 | 6 of 12 |
| Small LSTM (8 units) | 1,001 | 5 days | 0.994 | 0.095 | 6 of 12 |
| Small dense (8 units) | 897 | 5 days | 1.050 | 0.071 | 1 of 12 |
| **Tiny CNN-BiLSTM (4 filters of width 2, LSTM 4 each way)** | **477** | **5 days** | **0.992** | **0.085** | **10 of 12** |
| Linear layer | 111 | 5 days | 1.005 | 0.101 | 4 of 12 |
| Linear layer | 23 | 1 day | 0.979 | 0.141 | 9 of 12 |
| Ridge on yesterday's z-scored return | 1 | 1 day | 0.976 | 0.170 | 10 of 12 |

- The tiny CNN-BiLSTM beats predicting zero for the most stocks of any neural network with a hidden layer (10 of 12). The small LSTMs also get below 1.0 on average, with slightly higher correlation, but for only 6 stocks.
- Size is not the whole story: the 1,641-weight version, which kept pooling and dropout, did no better than the original. Which of those differences matters was not isolated.
- More history hurts even a linear model (0.141 with 1 day, 0.101 with 5 days): the usable signal is in the most recent day.

### 4.7 The final model

`7.pooled_cnn_bilstm_model.py`:

- **Inputs:** last 5 trading days × 22 numbers: the target stock's own z-scored return, all 12 stocks' z-scored returns, and the target stock's 9 alphas. Inputs are standardised per stock on training data.
- **Network:** Conv1D (4 filters, kernel 2) → BiLSTM (4 units each way) → Dense(1). Weights: 180 + 288 + 9 = 477.
- **Target:** next-day log return, standardised per stock on training data; predictions are converted back.
- **Training:** all 12 stocks pooled; 653 windows per stock (1 April 2022 is the earliest input day, after 60 days of look-back); 7,056 fitting samples; the most recent 10% of each stock's training windows (780 samples) used for early stopping; batch 64, up to 30 epochs, patience 5.
- **Averaging:** 5 runs with seeds 42–46; predictions averaged.
- **Test:** 244 days × 12 stocks = 2,928 predictions, every trading day of 2025 (2 Jan to 31 Dec). The look-back days for the first test days come from the end of 2024.

Results on 2025 (all 244 days):

| | Single run (average of 5) | 5 runs averaged (final) |
|---|---|---|
| Correlation with actual returns | 0.082 | 0.132 |
| MSE ÷ zero | 0.994 | 0.989 |
| Direction hit rate | 51.8% | 52.5% |
| Stocks beating zero | 8 of 12 | 11 of 12 |

The model comparisons in sections 4.3 to 4.6 and the checks in section 4.10 were run before the predictions were extended to January, on 3 Feb to 31 Dec 2025 (224 days). On those days the final model scores 0.137, 0.986, 52.7% and 12 of 12 (single run: 0.085, 0.992, 52.1%, 10 of 12). The model is the same; only the number of test days differs.

Final model by stock:

| Stock | Correlation | MSE ÷ zero | Direction hit rate |
|---|---|---|---|
| CIMB (1023.KL) | 0.081 | 0.997 | 52.9% |
| Maybank (1155.KL) | 0.241 | 0.979 | 50.5% |
| Public Bank (1295.KL) | 0.139 | 0.986 | 47.2% |
| TM (4863.KL) | 0.140 | 0.981 | 53.3% |
| PChem (5183.KL) | 0.039 | 0.997 | 49.6% |
| Sunway (5211.KL) | 0.113 | 0.992 | 54.4% |
| IHH Healthcare (5225.KL) | 0.048 | 0.993 | 56.6% |
| Tenaga (5347.KL) | 0.133 | 1.000 | 52.5% |
| Hong Leong Bank (5819.KL) | 0.217 | 0.981 | 56.1% |
| Maxis (6012.KL) | 0.159 | 0.981 | 52.3% |
| Axiata (6888.KL) | 0.097 | 0.992 | 55.9% |
| Press Metal (8869.KL) | 0.176 | 0.982 | 48.9% |

Sorting all 2,928 test predictions into five equal groups by predicted value, the average actual next-day return rises steadily: −0.17%, −0.03%, +0.02%, +0.12%, +0.25%.

### 4.8 The explainer report

<https://claude.ai/artifact/NwTXM5m9R5sDUyxncg57yh>

A plain-language page on the tiny CNN-BiLSTM: what it predicts, what goes in, how the two layers work, how it was trained, how to read the scores, results, limits and a glossary. **It has not been updated since the model was finalised,** so its description and figures do not match the current model. The current numbers are in section 4.7. The page was not previewed before publishing.

### 4.9 Plots

Written by `8.plot_pooled_results.py` to `OUTPUT/pooled_model_plots/`:

| File | What it shows |
|---|---|
| `summary_by_stock.png` | Per stock: correlation, and error compared with predicting "no change". |
| `predicted_vs_actual_scatter.png` | One panel per stock; each dot is a day; a trend line shows whether higher predictions went with higher actual returns. |
| `actual_by_prediction_bucket.png` | Average actual return in five groups sorted by predicted return. The clearest single picture of the model's skill. |
| `timeseries/<stock>_actual_vs_predicted.png` | Actual and predicted returns over time in two stacked panels with separate scales. |
| `predicted_vs_actual_plots/<stock>_predicted_vs_actual.png` | Same figure as `plotting.py`: both lines on one axis. The predicted line looks nearly flat because predictions are about a tenth the size of real moves. |
| `figure_4_2_correlation_heatmap.png` | Same figure as `plotting.py`: correlation of the 12 stocks' training returns. The three big banks are the most correlated group (0.48–0.54). |
| `summary_by_stock.csv` | Numbers behind the first figure. |

### 4.10 Why the predictions look flat

The test column covers 3 Feb to 31 Dec 2025 (224 days); see the note in section 4.7.

| Check | Train | Test |
|---|---|---|
| Correlation with actual returns | 0.187 | 0.137 |
| MSE ÷ zero | 0.976 | 0.986 |
| Size of predictions relative to actual moves | 6.8% | 6.0% |
| Size they should be, given that correlation | 18.7% | 13.7% |
| Average predicted return per day | 0.051% | 0.049% |
| Average actual return per day | 0.034% | 0.061% |

- A model that minimises squared error should move only as much as it is sure of. With a correlation of 0.137 the ideal predictions are about 13.7% the size of real moves, so even a perfect version would look nearly flat on a shared axis.
- Train and test results are close, so the model is neither memorising nor failing to learn.
- It is **under-confident** by a factor of about 2.3 (calibration slope 2.34 on test, 2.77 on train). Early stopping and averaging both pull predictions towards zero.
- Log returns are not the cause: log and simple returns differ by at most 0.32 percentage points on the most extreme day, and the average prediction is close to the average actual return.
- A possible improvement, **not implemented**: multiply predictions by about 2.8 (learned from training data). Correlation would be unchanged and error should fall to roughly 98% of the zero baseline.

### 4.11 The existing optimisation workbook

`Copy ver MV model.xlsx` is a mean-variance portfolio optimiser with a 2025 backtest (sheet-by-sheet description in section 5.1).

The optimisation:

- Covariance matrix from 2022–2024 returns, shared by both models.
- Expected returns: historical average (benchmark) or the average of the CNN-BiLSTM's 2025 predictions (predicted model).
- Constraints: weights sum to 1, no short selling, each held stock between 5% and 30%, exactly K stocks held, expected return at least ln(1.0615)/252 per day.
- Problem 1, **minimise risk**: lowest variance for K = 4 to 12.
- Problem 2, **risk-return trade-off**: K = 7, maximise (1−λ)·return − λ·variance for λ = 0.1 to 1.
- Backtest: fixed weights applied to actual 2025 returns, starting from RM100,000.

Its stored results:

| Portfolio | Cumulative return | Annual Sharpe | Max drawdown |
|---|---|---|---|
| Benchmark, min risk, K=7 | 14.0% | 1.02 | 10.1% |
| CNN-BiLSTM, min risk, K=7 | 14.0% | 1.02 | 10.1% |
| Equal weight | 8.4% | 0.48 | 14.9% |
| KLCI | 2.2% | 0.01 | 14.5% |
| Benchmark, λ=0.9 | 8.8% | 0.49 | 11.1% |
| CNN-BiLSTM, λ=0.9 | 9.2% | 0.49 | 12.3% |

Its statistical test (Jobson-Korkie with Memmel correction, λ=0.9): z = −0.02, p = 0.99, no difference.

Problems found:

1. **Predictions barely enter the minimum-risk results.** Variance does not depend on expected returns; they only appear in the return floor.
2. **The old predictions look broken for some stocks.** CIMB's prediction is the same number on essentially every day, Sunway has only 15 distinct values, and PChem averages −0.51% per day.
3. **Look-ahead.** The predicted expected return is the average over all of 2025, but the portfolio is held from 2 January; predictions only begin on 3 February.
4. **λ does almost nothing below 0.9**, because returns (about 0.001) dominate variances (about 0.00005).
5. **KLCI is not like for like:** stock returns include dividends, the index does not; no trading costs.
6. **Two errors:** the predicted K=12 portfolio is below its own return floor; K=3 is infeasible (3 × 30% < 100%).
7. **Excel Solver stopped at non-optimal portfolios** for K = 6, 7, 8, 9, 11 and λ ≥ 0.95 (found when re-solving exactly).
8. **Unfinished Wilcoxon test:** signed ranks are computed but no test statistic.

### 4.12 Static rebuild with tiny-model predictions

`MV model - tiny CNN-BiLSTM.xlsx` keeps the existing design. Changes: tiny-model predictions, exact weights for both the benchmark and predicted sheets, and a `Comparison` sheet.

Minimise risk (cumulative return 2025 / annual Sharpe):

| K | Existing benchmark | Existing CNN-BiLSTM | Rebuilt benchmark | Rebuilt tiny model |
|---|---|---|---|---|
| 4 | 10.88% / 0.78 | 10.88% / 0.78 | 10.88% / 0.78 | 10.88% / 0.78 |
| 5 | 12.16% / 0.91 | 11.44% / 0.82 | 12.16% / 0.91 | 12.16% / 0.91 |
| 6 | 13.55% / 1.01 | 13.05% / 0.97 | 12.52% / 0.92 | 12.52% / 0.92 |
| 7 | 13.96% / 1.02 | 13.96% / 1.02 | 9.83% / 0.67 | 9.83% / 0.67 |
| 8 | 13.52% / 0.99 | 13.15% / 0.96 | 9.48% / 0.64 | 9.48% / 0.64 |
| 9 | 10.72% / 0.74 | 12.74% / 0.90 | 9.05% / 0.59 | 9.05% / 0.59 |
| 10 | 10.29% / 0.68 | 12.19% / 0.85 | 10.29% / 0.68 | 10.29% / 0.68 |
| 11 | 9.79% / 0.64 | 11.87% / 0.82 | 9.91% / 0.65 | 9.91% / 0.65 |
| 12 | 9.53% / 0.62 | 7.73% / 0.45 | 9.53% / 0.62 | 9.53% / 0.62 |
| **Average** | 11.6% / 0.82 | 11.9% / 0.84 | 10.4% / 0.72 | 10.4% / 0.72 |

Risk-return trade-off, K=7 (cumulative return 2025 / annual Sharpe):

| λ | Existing benchmark | Existing CNN-BiLSTM | Rebuilt benchmark | Rebuilt tiny model |
|---|---|---|---|---|
| 0.1 | 6.61% / 0.31 | 9.22% / 0.49 | 6.61% / 0.31 | 7.26% / 0.35 |
| 0.3 | 6.61% / 0.31 | 9.22% / 0.49 | 6.61% / 0.31 | 7.04% / 0.34 |
| 0.5 | 6.61% / 0.31 | 9.22% / 0.49 | 6.61% / 0.31 | 7.04% / 0.34 |
| 0.7 | 6.61% / 0.31 | 9.22% / 0.49 | 6.61% / 0.31 | 7.04% / 0.34 |
| 0.9 | 8.79% / 0.49 | 9.22% / 0.49 | 8.80% / 0.49 | 7.38% / 0.36 |
| 0.95 | 9.99% / 0.66 | 8.53% / 0.48 | 9.94% / 0.64 | 9.11% / 0.55 |
| 0.97 | 10.82% / 0.76 | 9.03% / 0.55 | 10.88% / 0.74 | 10.51% / 0.70 |
| 0.99 | 9.32% / 0.63 | 12.52% / 0.90 | 11.59% / 0.84 | 11.59% / 0.84 |
| 1 | 13.96% / 1.02 | 13.96% / 1.02 | 9.83% / 0.67 | 9.83% / 0.67 |
| **Average** | 8.8% / 0.53 | 10.0% / 0.60 | 8.6% / 0.51 | 8.5% / 0.50 |

- Statistical test, λ=0.9, tiny model against rebuilt benchmark: z = −0.62, p = 0.54.
- The tiny model's expected returns are the average of its predictions over all 244 days of 2025.
- The exact minimum-variance K=7 portfolio returned 9.8% in 2025 against 14.0% for Solver's non-optimal one, so the existing headline result partly reflects where Solver stopped.

### 4.13 Why benchmark and prediction results match in that design

- **Minimise risk:** the objective is variance, which depends only on the shared covariance matrix. Predictions enter only through the return floor (0.0237% a day), and the minimum-variance portfolios clear it comfortably under either set of expected returns (0.034–0.043% benchmark, 0.046–0.052% tiny model). A constraint that is not binding changes nothing, so the weights are identical for every K.
- **Trade-off:** averaging 244 days of predictions recreates the historical average. The tiny model's average predicted return per stock has a correlation of 0.95 with the historical average, with the same top five stocks. The model's skill is in day-to-day changes, which cancel out in a yearly average.

The comparison cannot show a difference whichever model supplies the predictions. That is a property of the design, not evidence about prediction.

### 4.14 Daily re-optimisation

`MV model - daily tiny CNN-BiLSTM.xlsx`. Before each trading day the optimiser receives that day's predicted returns and picks the best K-stock portfolio (5%–30% weights, same covariance matrix). The static benchmark solves the same problem once with historical average returns. Period: the whole of 2025, 2 Jan to 31 Dec, 244 trading days. The 6.15% minimum-return floor is not applied, because on days when every prediction is low the problem would have no solution.

The workbook follows the existing workbook's two stages:

- **Stage A, stock selection (cardinality loop):** K = 4 to 12, at λ = 0.9.
- **Stage B, risk-return trade-off (λ loop):** λ = 0.1 to 1, at K = 7.

It also holds the **full grid** of every K with every λ (81 settings), reported after the two stages below.

The cardinality loop uses the trade-off objective, not pure risk minimisation as in the existing workbook. Under pure risk minimisation the predictions do not enter, so the daily and static portfolios would be identical for every K (this is what λ = 1 shows in stage B). λ = 0.9 was chosen because it is the setting the existing workbook's statistical test uses.

**Stage A results, cardinality loop at λ = 0.9, no trading costs:**

| K | Daily tiny model | Static benchmark | Difference (points) | Daily Sharpe | Static Sharpe | Daily max drawdown | Static max drawdown | Daily turnover | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 34.3% | 6.2% | +28.1 | 1.71 | 0.29 | 13.8% | 12.5% | 60% | 3.14 | 0.002 | Yes |
| 5 | 37.0% | 6.7% | +30.4 | 1.87 | 0.33 | 13.2% | 12.1% | 59% | 3.48 | <0.001 | Yes |
| 6 | 33.3% | 7.6% | +25.6 | 1.72 | 0.40 | 13.3% | 11.7% | 57% | 3.05 | 0.002 | Yes |
| 7 | 31.5% | 8.8% | +22.7 | 1.65 | 0.49 | 13.6% | 11.1% | 54% | 2.74 | 0.006 | Yes |
| 8 | 29.0% | 8.9% | +20.2 | 1.55 | 0.51 | 13.7% | 10.6% | 51% | 2.48 | 0.013 | Yes |
| 9 | 29.0% | 10.8% | +18.2 | 1.56 | 0.64 | 13.4% | 10.8% | 47% | 2.17 | 0.030 | Yes |
| 10 | 29.9% | 11.1% | +18.8 | 1.62 | 0.68 | 13.1% | 10.4% | 43% | 2.16 | 0.030 | Yes |
| 11 | 29.2% | 8.9% | +20.3 | 1.61 | 0.51 | 12.7% | 12.1% | 39% | 2.79 | 0.005 | Yes |
| 12 | 25.5% | 9.0% | +16.5 | 1.44 | 0.52 | 12.9% | 13.0% | 32% | 2.69 | 0.007 | Yes |

- The daily portfolio beats the static benchmark at every K. The gap is largest at K = 5 (30 points) and smallest at K = 12 (17 points).
- The difference is statistically significant at every K from 4 to 12.
- The best K for the daily strategy is 5 (highest return and Sharpe); for the static benchmark it is 10. K = 7, the existing workbook's choice, sits in the middle.
- Choosing K by its 2025 result and then reporting that result would overstate it; the whole table is the fair picture.

**Stage B results, λ loop at K = 7, no trading costs:**

| λ | Daily tiny model | Static benchmark | Difference (points) | Daily Sharpe | Static Sharpe | Daily max drawdown | Static max drawdown | Daily turnover | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 28.2% | 6.6% | +21.6 | 1.38 | 0.31 | 15.0% | 13.7% | 55% | 2.31 | 0.021 | Yes |
| 0.3 | 29.5% | 6.6% | +22.8 | 1.44 | 0.31 | 15.1% | 13.7% | 55% | 2.47 | 0.014 | Yes |
| 0.5 | 29.4% | 6.6% | +22.8 | 1.44 | 0.31 | 15.7% | 13.7% | 56% | 2.51 | 0.012 | Yes |
| 0.7 | 30.1% | 6.6% | +23.5 | 1.49 | 0.31 | 15.6% | 13.7% | 56% | 2.73 | 0.006 | Yes |
| 0.9 | 31.5% | 8.8% | +22.7 | 1.65 | 0.49 | 13.6% | 11.1% | 54% | 2.74 | 0.006 | Yes |
| 0.95 | 29.8% | 9.9% | +19.9 | 1.71 | 0.64 | 12.7% | 10.0% | 50% | 2.44 | 0.015 | Yes |
| 0.97 | 25.9% | 10.9% | +15.1 | 1.67 | 0.74 | 11.2% | 9.8% | 39% | 2.33 | 0.020 | Yes |
| 0.99 | 16.1% | 11.6% | +4.5 | 1.16 | 0.84 | 10.4% | 9.5% | 14% | 1.45 | 0.148 | No |
| 1 | 9.8% | 9.8% | 0.0 | 0.67 | 0.67 | 10.6% | 10.6% | 0% | n/a | n/a | n/a |

Returns are cumulative; Sharpe ratios are annualised. Equal weight returned 8.4% (Sharpe 0.48, max drawdown 14.9%) and the KLCI 2.2% (Sharpe 0.01, max drawdown 14.5%) over the same days, the same figures as the original workbook's Summary. At λ = 1 the objective ignores expected returns, so the two portfolios are identical, which confirms that the forecast is the only difference elsewhere. The K = 7 row of stage A and the λ = 0.9 row of stage B are the same portfolio.

**Full grid: every K with every λ, no trading costs.** The two stages above are one row and one column of this grid (the K = 7 row and the λ = 0.9 column), and the grid reproduces them exactly. Rows are K, columns are λ. At λ = 1 the daily and static portfolios are identical.

Daily tiny model, cumulative return:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 34.1% | 34.5% | 35.2% | 34.5% | 34.3% | 31.1% | 30.6% | 19.2% | 10.9% |
| 5 | 30.4% | 30.3% | 31.0% | 30.8% | 37.0% | 34.0% | 32.8% | 19.5% | 12.2% |
| 6 | 29.9% | 30.4% | 30.3% | 31.0% | 33.3% | 30.6% | 27.9% | 16.8% | 12.5% |
| 7 | 28.2% | 29.5% | 29.4% | 30.1% | 31.5% | 29.8% | 25.9% | 16.1% | 9.8% |
| 8 | 28.8% | 30.1% | 30.3% | 30.5% | 29.0% | 24.9% | 23.7% | 15.6% | 9.5% |
| 9 | 27.7% | 28.6% | 27.7% | 29.6% | 29.0% | 23.6% | 22.2% | 14.8% | 9.1% |
| 10 | 26.4% | 27.5% | 27.7% | 29.2% | 29.9% | 23.7% | 19.7% | 13.9% | 10.3% |
| 11 | 23.8% | 24.7% | 24.7% | 26.5% | 29.2% | 22.1% | 20.9% | 13.7% | 9.9% |
| 12 | 20.8% | 22.1% | 21.8% | 23.5% | 25.5% | 20.2% | 16.8% | 12.0% | 9.5% |

Static benchmark, cumulative return:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 5.5% | 5.5% | 5.5% | 5.5% | 6.2% | 7.5% | 13.9% | 10.3% | 10.9% |
| 5 | 6.3% | 6.3% | 6.3% | 6.3% | 6.7% | 9.5% | 10.4% | 11.1% | 12.2% |
| 6 | 6.3% | 6.3% | 6.3% | 6.7% | 7.6% | 9.1% | 11.1% | 12.0% | 12.5% |
| 7 | 6.6% | 6.6% | 6.6% | 6.6% | 8.8% | 9.9% | 10.9% | 11.6% | 9.8% |
| 8 | 7.4% | 7.4% | 7.4% | 7.4% | 8.9% | 9.7% | 10.6% | 9.0% | 9.5% |
| 9 | 7.5% | 7.5% | 7.5% | 9.4% | 10.8% | 11.2% | 8.0% | 8.7% | 9.1% |
| 10 | 9.3% | 9.3% | 9.3% | 9.9% | 11.1% | 8.6% | 9.4% | 10.3% | 10.3% |
| 11 | 9.9% | 9.9% | 9.9% | 10.3% | 8.9% | 8.6% | 9.4% | 9.8% | 9.9% |
| 12 | 8.3% | 8.3% | 8.3% | 8.3% | 9.0% | 8.7% | 9.3% | 9.3% | 9.5% |

Daily tiny model, annual Sharpe ratio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 1.57 | 1.59 | 1.63 | 1.62 | 1.71 | 1.71 | 1.89 | 1.42 | 0.78 |
| 5 | 1.42 | 1.42 | 1.47 | 1.47 | 1.87 | 1.86 | 2.06 | 1.40 | 0.91 |
| 6 | 1.43 | 1.46 | 1.47 | 1.51 | 1.72 | 1.73 | 1.77 | 1.24 | 0.92 |
| 7 | 1.38 | 1.44 | 1.44 | 1.49 | 1.65 | 1.71 | 1.67 | 1.16 | 0.67 |
| 8 | 1.42 | 1.49 | 1.51 | 1.53 | 1.55 | 1.44 | 1.52 | 1.12 | 0.64 |
| 9 | 1.40 | 1.45 | 1.41 | 1.51 | 1.56 | 1.38 | 1.44 | 1.05 | 0.59 |
| 10 | 1.36 | 1.41 | 1.42 | 1.50 | 1.62 | 1.40 | 1.27 | 0.96 | 0.68 |
| 11 | 1.27 | 1.32 | 1.32 | 1.42 | 1.61 | 1.31 | 1.34 | 0.94 | 0.65 |
| 12 | 1.15 | 1.22 | 1.20 | 1.30 | 1.44 | 1.22 | 1.08 | 0.81 | 0.62 |

Static benchmark, annual Sharpe ratio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.24 | 0.24 | 0.24 | 0.24 | 0.29 | 0.42 | 0.98 | 0.73 | 0.78 |
| 5 | 0.29 | 0.29 | 0.29 | 0.29 | 0.33 | 0.61 | 0.70 | 0.78 | 0.91 |
| 6 | 0.29 | 0.29 | 0.29 | 0.31 | 0.40 | 0.56 | 0.78 | 0.87 | 0.92 |
| 7 | 0.31 | 0.31 | 0.31 | 0.31 | 0.49 | 0.64 | 0.74 | 0.84 | 0.67 |
| 8 | 0.37 | 0.37 | 0.37 | 0.37 | 0.51 | 0.63 | 0.72 | 0.60 | 0.64 |
| 9 | 0.38 | 0.38 | 0.38 | 0.49 | 0.64 | 0.73 | 0.49 | 0.57 | 0.59 |
| 10 | 0.49 | 0.49 | 0.49 | 0.53 | 0.68 | 0.52 | 0.60 | 0.68 | 0.68 |
| 11 | 0.54 | 0.54 | 0.54 | 0.56 | 0.51 | 0.52 | 0.60 | 0.65 | 0.65 |
| 12 | 0.43 | 0.43 | 0.43 | 0.44 | 0.52 | 0.53 | 0.59 | 0.60 | 0.62 |

Jobson-Korkie-Memmel p-value, daily against static (bold = different at 5%):

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | **0.006** | **0.005** | **0.003** | **0.002** | **0.002** | **0.025** | 0.137 | **0.003** | n/a |
| 5 | **0.015** | **0.014** | **0.009** | **0.005** | **<0.001** | **0.017** | **0.003** | **0.003** | n/a |
| 6 | **0.013** | **0.010** | **0.008** | **0.005** | **0.002** | **0.011** | **0.026** | 0.062 | n/a |
| 7 | **0.021** | **0.014** | **0.012** | **0.006** | **0.006** | **0.015** | **0.020** | 0.148 | n/a |
| 8 | **0.021** | **0.014** | **0.012** | **0.008** | **0.013** | 0.053 | **0.032** | **0.026** | n/a |
| 9 | **0.032** | **0.025** | **0.027** | **0.020** | **0.030** | 0.130 | **0.008** | **0.006** | n/a |
| 10 | 0.075 | 0.059 | 0.053 | **0.029** | **0.030** | **0.031** | **0.048** | 0.066 | n/a |
| 11 | 0.089 | 0.069 | 0.068 | **0.037** | **0.005** | **0.039** | **0.025** | **0.034** | n/a |
| 12 | 0.050 | **0.032** | **0.035** | **0.019** | **0.007** | **0.045** | 0.101 | **0.012** | n/a |

Average daily turnover of the daily portfolio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 59% | 60% | 60% | 60% | 60% | 58% | 52% | 15% | 0% |
| 5 | 58% | 58% | 58% | 58% | 59% | 55% | 46% | 15% | 0% |
| 6 | 56% | 57% | 57% | 57% | 57% | 53% | 42% | 13% | 0% |
| 7 | 55% | 55% | 56% | 56% | 54% | 50% | 39% | 14% | 0% |
| 8 | 53% | 53% | 53% | 53% | 51% | 48% | 37% | 13% | 0% |
| 9 | 48% | 48% | 49% | 49% | 47% | 45% | 34% | 12% | 0% |
| 10 | 45% | 45% | 45% | 45% | 43% | 41% | 32% | 11% | 0% |
| 11 | 39% | 39% | 39% | 39% | 39% | 37% | 30% | 10% | 0% |
| 12 | 32% | 32% | 32% | 32% | 32% | 31% | 24% | 6% | 0% |

- **The daily portfolio is ahead in all 72 settings with λ below 1.** Its cumulative return ranges from 12.0% to 37.0%; the static benchmark's ranges from 5.5% to 13.9%. The gap ranges from 2.7 to 30.4 points.
- **The difference is statistically significant in 58 of the 72 settings.** By K: 7, 8, 7, 7, 7, 7 of 8 settings for K = 4 to 9, then 4, 5, 6 of 8 for K = 10 to 12.
- **λ = 0.7 and λ = 0.9 are significant at every K**, the only such columns. Of the 14 settings that are not significant, 7 are at K = 10 to 12 with λ of 0.5 or below; the other 7 are single cells at λ = 0.95 to 0.99.
- **For λ from 0.1 to 0.7 the results barely change with λ.** The likely reason is that with so little weight on risk the optimiser mostly holds the stocks with the highest expected returns at the weight limits, whatever the exact λ.
- **Highest values:** cumulative return 37.0% at K = 5, λ = 0.9; Sharpe ratio 2.06 at K = 5, λ = 0.97. These are the best of 72 tries on one year, so they overstate what to expect; the tables as a whole are the fair picture.
- **Turnover falls as K rises and as λ approaches 1,** from about 60% a day (K = 4) to about 32% (K = 12) at low λ, and to 6–15% at λ = 0.99.
- With 72 tests at the 5% level, about 4 would appear significant by chance alone; 58 is far more than that, but the tests are not independent (the settings hold overlapping portfolios on the same days).

**With trading costs (K = 7 only; not in the workbook, which excludes costs at the user's request).** Deducting an assumed 0.15% per unit traded from the daily portfolio:

| λ | Daily, before costs | Daily, after 0.15% costs | Static | Sharpe after costs | Static Sharpe | Break-even cost |
|---|---|---|---|---|---|---|
| 0.1 | 28.2% | 5.0% | 6.6% | 0.21 | 0.31 | 0.14% |
| 0.5 | 29.4% | 5.6% | 6.6% | 0.24 | 0.31 | 0.14% |
| 0.9 | 31.5% | 7.8% | 8.8% | 0.38 | 0.49 | 0.14% |
| 0.97 | 25.9% | 9.4% | 10.9% | 0.55 | 0.74 | 0.14% |
| 0.99 | 16.1% | 10.5% | 11.6% | 0.71 | 0.84 | 0.12% |

After costs the daily portfolio is slightly behind the static benchmark at every λ shown, and no difference is statistically significant (p from 0.57 to 0.88). The 0.15% figure is an assumption, not a quoted fee.

### 4.15 Comparison with the original workbook

Sheet `vs Original` of the daily workbook. The original workbook's own portfolios (the weights stored in `Copy ver MV model.xlsx`, found by Excel Solver, held fixed all year) are backtested over the whole of 2025 (2 Jan to 31 Dec, 244 days), the same days as the daily strategy, with no trading costs. This is also the period of the original workbook's own Summary, so the original figures here match it (section 4.11). Returns are cumulative; Sharpe ratios are annualised. The test compares the daily tiny model with the original CNN-BiLSTM portfolio.

**By number of stocks held.** Original: minimise-risk portfolios. Daily tiny model: trade-off at λ = 0.9.

| K | Original benchmark | Original CNN-BiLSTM | Daily tiny model | Daily tiny minus original CNN-BiLSTM (points) | Original benchmark Sharpe | Original CNN-BiLSTM Sharpe | Daily tiny Sharpe | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 10.9% | 10.9% | 34.3% | +23.4 | 0.78 | 0.78 | 1.71 | 1.18 | 0.238 | No |
| 5 | 12.2% | 11.4% | 37.0% | +25.6 | 0.91 | 0.82 | 1.87 | 1.48 | 0.140 | No |
| 6 | 13.5% | 13.0% | 33.3% | +20.2 | 1.01 | 0.97 | 1.72 | 1.03 | 0.301 | No |
| 7 | 14.0% | 14.0% | 31.5% | +17.6 | 1.02 | 1.02 | 1.65 | 0.90 | 0.366 | No |
| 8 | 13.5% | 13.1% | 29.0% | +15.9 | 0.99 | 0.96 | 1.55 | 0.90 | 0.366 | No |
| 9 | 10.7% | 12.7% | 29.0% | +16.2 | 0.74 | 0.90 | 1.56 | 1.09 | 0.275 | No |
| 10 | 10.3% | 12.2% | 29.9% | +17.7 | 0.68 | 0.85 | 1.62 | 1.35 | 0.176 | No |
| 11 | 9.8% | 11.9% | 29.2% | +17.3 | 0.64 | 0.82 | 1.61 | 1.42 | 0.155 | No |
| 12 | 9.5% | 7.7% | 25.5% | +17.8 | 0.62 | 0.45 | 1.44 | 2.32 | 0.020 | Yes |

**By λ, K = 7.** Original: trade-off portfolios.

| λ | Original benchmark | Original CNN-BiLSTM | Daily tiny model | Daily tiny minus original CNN-BiLSTM (points) | Original benchmark Sharpe | Original CNN-BiLSTM Sharpe | Daily tiny Sharpe | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 6.6% | 9.2% | 28.2% | +19.0 | 0.31 | 0.49 | 1.38 | 1.67 | 0.095 | No |
| 0.3 | 6.6% | 9.2% | 29.5% | +20.2 | 0.31 | 0.49 | 1.44 | 1.79 | 0.074 | No |
| 0.5 | 6.6% | 9.2% | 29.4% | +20.2 | 0.31 | 0.49 | 1.44 | 1.82 | 0.069 | No |
| 0.7 | 6.6% | 9.2% | 30.1% | +20.9 | 0.31 | 0.49 | 1.49 | 1.96 | 0.050 | Yes |
| 0.9 | 8.8% | 9.2% | 31.5% | +22.3 | 0.49 | 0.49 | 1.65 | 2.26 | 0.024 | Yes |
| 0.95 | 10.0% | 8.5% | 29.8% | +21.3 | 0.66 | 0.48 | 1.71 | 2.36 | 0.018 | Yes |
| 0.97 | 10.8% | 9.0% | 25.9% | +16.9 | 0.76 | 0.55 | 1.67 | 2.53 | 0.011 | Yes |
| 0.99 | 9.3% | 12.5% | 16.1% | +3.6 | 0.63 | 0.90 | 1.16 | 1.07 | 0.286 | No |
| 1 | 14.0% | 14.0% | 9.8% | −4.1 | 1.02 | 1.02 | 0.67 | −1.49 | 0.135 | No |

- **Return:** the daily tiny model is ahead of both original portfolios in every row except λ = 1, by 16 to 26 points for K = 4 to 12 and by 17 to 22 points for λ up to 0.97.
- **Sharpe ratio:** the daily tiny model's is about 1.4 to 1.9 against about 0.3 to 1.0 for the original portfolios (λ up to 0.97).
- **Statistical test:** the Sharpe difference from the original CNN-BiLSTM portfolio is significant at 5% in 5 of the 18 comparisons (K = 12, and λ = 0.7, 0.9, 0.95 and 0.97 at K = 7). Against the original minimise-risk portfolios (the K table) it is significant only at K = 12: those portfolios did well in 2025, so the gap, although large, is not statistically reliable on one year of data.
- **λ = 1:** the daily strategy ignores predictions there and holds the exact minimum-variance portfolio (9.8%), which did worse than the portfolio Excel Solver stopped at in the original workbook (14.0%).
- **The original benchmark and original CNN-BiLSTM columns are close to each other** in most rows, for the reason given in section 4.13.
- These results exclude trading costs. The daily portfolio trades about 55% of its value a day and the original portfolios do not trade, so at an assumed 0.15% cost the advantage would disappear, as in section 4.14.

### 4.16 Excel Solver version

`MV model - daily Excel Solver.xlsx`, with the macro `optimization/DailySolver.bas` and the data module `optimization/Data2025.bas`. The daily workbook in section 4.14 was solved in Python by checking every K-stock combination. This version sets up the same problems for Excel Solver, with the model and options stored in `Copy ver MV model.xlsx` (GRG Nonlinear, binary selection cells, precision 0.000001, convergence 0.0001, central derivatives, integer optimality 0%, multistart off), so the daily results can be produced with the same tool as the original. Solver cannot be started from outside Excel on this machine, so the macro is run by hand inside Excel.

The macro works in the original workbook's order:

- **Stage 1, best cardinality at λ = 1:** minimise risk for K = 4 to 12 with historical average returns. Each portfolio is held through the whole of 2025 and the K with the highest cumulative return is taken as the best cardinality (sheet `Stage 1 best K`).
- **Stage 2, risk-return trade-off at that K:** each λ, static (historical average returns) and daily (each day's predicted returns, all 244 days).
- **Stage 3, sensitivity check:** daily trade-off at λ = 0.9 for every other K.

Each job starts from equal weights with every stock selected and has a 100-second time limit, which the original workbook did not have.

**Stage 1 result** (Excel Solver's minimise-risk portfolios, held through all of 2025):

| K | Cumulative return | Same as the original workbook? |
|---|---|---|
| 4 | 10.88% | Yes |
| 5 | 12.16% | Yes |
| 6 | 13.55% | Yes |
| **7** | **13.96%** | Yes |
| 8 | 13.52% | Yes |
| 9 | 10.72% | Yes |
| 10 | 10.29% | Yes |
| 11 | 9.79% | Yes |
| 12 | 9.53% | Yes |

- **The best cardinality at λ = 1 is K = 7,** the same as in the original workbook, so stage 2 runs at K = 7.
- **Excel Solver reproduces the original benchmark results at every K.** For K = 6, 7, 8, 9 and 11 these are not the exact minimum-variance portfolios (section 4.11, problem 7), which is why the Python-solved static figures in sections 4.12 and 4.14 differ at those K.
- **The best K is chosen with actual 2025 returns,** the year the strategy is tested on. This follows the original workbook, but it is a look-ahead choice.
- **Status:** the daily jobs are still being solved in Excel. When this section was written 1,488 jobs were finished, all with Solver result code 0 and all constraints met; the workbook with the results is not in the repository yet, and no daily Solver results are reported here.

---

## 5. The spreadsheets, sheet by sheet

### 5.1 `Copy ver MV model.xlsx` (existing, unchanged)

| Sheet | Contents |
|---|---|
| Historical data | Daily log returns of the 12 stocks, 2022–2024 (733 days). |
| Predicted data | The original CNN-BiLSTM's predicted returns, 3 Feb to 31 Dec 2025 (224 days). |
| Benchmark_MV model | Expected return = historical average; covariance matrix; Solver weights for K = 3 to 12 (rows 18–29) and for λ = 0.1 to 1 with K = 7 (rows 38–49); portfolio return, variance and Sharpe. |
| Predicted_MV model | Same layout, with expected return = average of the predictions. |
| Actual 2025 | Actual daily log returns for 2025 (244 days). |
| KLSE_data | KLCI index level and log return. |
| Backtest | Daily return, wealth and running peak for the minimum-risk portfolios. |
| Backtest (2) | The same for the trade-off portfolios. |
| Summary | Cumulative return, Sharpe, max drawdown; efficient-frontier chart. |
| Chart | Wealth curves and frontier charts. |
| Stat_Test | Jobson-Korkie test with Memmel correction (λ = 0.9), plus unfinished signed-rank columns. |

### 5.2 `MV model - tiny CNN-BiLSTM.xlsx` (new)

Same sheets as above, with these changes:

| Sheet | What changed |
|---|---|
| **Comparison** (new, first tab) | Described below. |
| Predicted data | Replaced with the tiny model's predictions for every trading day of 2025 (244 rows; the original sheet has 224). |
| Benchmark_MV model | Weights in rows 18–29 and 38–49 replaced with the exact optimum. K = 3 column cleared and marked infeasible. A note in A57 states where the weights came from. |
| Predicted_MV model | Same, using the tiny-model expected returns. The yearly-average formulas in B3:B14 now cover all 244 rows. |
| Backtest, Backtest (2), Summary, Stat_Test | Formulas untouched; headers renamed to "Tiny CNN-BiLSTM model" / "Tiny model". |
| Historical data, Actual 2025, KLSE_data, Chart | Unchanged. |

**The `Comparison` sheet:**

- **Section 1, Minimise risk:** three tables (cumulative return, annual Sharpe, max drawdown), rows K = 4 to 12 plus an average. Columns: Existing: Benchmark, Existing: CNN-BiLSTM, Rebuild: Benchmark, Rebuild: Tiny CNN-BiLSTM, Tiny minus existing CNN-BiLSTM, Tiny minus rebuilt benchmark.
- **Section 2, Risk-return trade-off:** the same three tables with rows λ = 0.1 to 1.
- **Section 3, Reference portfolios:** equal weight and KLCI.
- **Section 4, Sharpe ratio test:** daily Sharpe ratios, z, p-value and decision for the existing workbook and the rebuild.
- **Notes:** what was replaced, how the weights were found, and the caveats carried over from the existing design.
- **Colours:** blue = values copied from `Copy ver MV model.xlsx`; green = live links to this workbook's Summary and Stat_Test sheets.

### 5.3 `MV model - daily tiny CNN-BiLSTM.xlsx` (new)

Built from scratch. Blue cells are inputs or optimiser output; black cells are formulas; green cells link to another sheet.

| Sheet | Contents |
|---|---|
| **Summary** | Table A, cardinality loop: one row per K = 4 to 12 at λ = 0.9. Table B, λ loop: one row per λ at K = 7. Both tables show cumulative return of the daily and static portfolios, the difference, annual Sharpe ratios, max drawdowns, average daily turnover, daily Sharpe ratios, correlation, Jobson-Korkie-Memmel z and p-value, and whether they differ at 5%. Below: equal weight and KLCI over the same period, then notes on method and assumptions. |
| **vs Original** | Comparison with the original workbook. Table A by K and table B by λ: cumulative return and Sharpe ratio of the original benchmark, the original CNN-BiLSTM and the daily tiny model over the whole of 2025, with the Jobson-Korkie-Memmel test of the daily tiny model against the original CNN-BiLSTM. Below: the 36 original weight sets, copied from `Copy ver MV model.xlsx`. |
| **Grid summary** | The full grid. Seven tables with K = 4 to 12 down the side and λ = 0.1 to 1 across the top: daily cumulative return, static cumulative return, the difference, daily Sharpe, static Sharpe, p-value (yellow when below 0.05) and average daily turnover. Every cell links to the `Grid K` sheet for that K. |
| **Chart** | Wealth from RM100,000 for λ = 0.9: daily tiny model, static benchmark, equal weight, KLCI, with a line chart. |
| **Inputs** | Risk-free rate (ln(1.0288)/252), initial wealth (RM100,000), K = 7, weight limits 5% and 30%, colour key. |
| **Actual 2025** | Actual daily log returns for every trading day of 2025 (244 days), plus the KLCI return. |
| **Predicted data** | The tiny model's predicted next-day return for each stock and day. |
| **Historical data** | 2022–2024 daily log returns. |
| **Covariance** | Average historical return per stock and the covariance matrix, as formulas on Historical data. |
| **Reference** | Equal-weight and KLCI daily returns, wealth, running peak and drawdown. |
| **K=4 … K=12** (nine sheets) | The cardinality loop at λ = 0.9. Row 4: the static benchmark's weights for that K. Rows 6–249: one row per day with the 12 daily weights (optimiser output), then formulas for sum of weights, stocks held, turnover, daily portfolio return, static benchmark return, wealth of each, running peak and drawdown of each. |
| **lam 0.1 … lam 1** (nine sheets) | The λ loop at K = 7, same layout. Sheet `lam 0.9` holds the same portfolio as sheet `K=7`. |
| **Original returns** | Daily return of each of the 36 original-workbook portfolios (stored weights × actual returns), used by `vs Original`. |
| **Grid K4 … Grid K12** (nine sheets) | The full grid, one sheet per K with nine λ blocks side by side (17 columns each). Rows 2–11: the block's statistics (cumulative returns, Sharpe ratios, turnover, correlation, z, p-value). Row 12: static benchmark weights. Rows 14–257: one row per day with the 12 daily weights (optimiser output), then formulas for turnover, daily return, static return and the wealth of each. |

Turnover is the sum of absolute weight changes from the previous day and is shown for information only. No trading costs are deducted for either portfolio.

### 5.4 `MV model - daily Excel Solver.xlsx` (new)

The workbook Excel Solver works in (section 4.16). It is saved as `.xlsm` once the macro is imported.

| Sheet | Contents |
|---|---|
| **Instructions** | How to import the two macro files and run them, what each stage does, and the Solver options used. |
| **Solver model** | The optimisation model in one block: K, λ, weight limits and return floor (B3:B7); for each stock the expected return, weight, binary selection cell and the two linking constraints (rows 11–22); totals; portfolio return, variance and the trade-off objective (B25:B27). The macro fills the inputs and calls Solver. |
| **Jobs** | One row per problem to solve: mode (minimise risk or trade-off), K, λ and day (0 = static, historical average returns). The macro writes the 12 weights, objective value, Solver result code, seconds taken, portfolio return and variance, sum of weights and number of stocks held. A row with a result code is finished and is skipped on the next run. |
| **Predicted data** | The tiny model's predicted returns for every trading day of 2025. |
| **Historical data**, **Covariance** | 2022–2024 returns, their averages and the covariance matrix, as in the original workbook. |
| **Actual 2025**, **Stage 1 best K** | Created by the macro: actual 2025 returns with the daily return of each minimise-risk portfolio, and the table that picks the best cardinality at λ = 1. |

---

## 6. How to run everything

Requirements: Python 3.9+, `pandas`, `numpy`, `yfinance`, `scipy`, `scikit-learn`, `tensorflow`, `matplotlib`, `seaborn`, `openpyxl`.

```bash
python 1.raw_data.py
python 2.data_preprocess.py
mv cleaned_malaysia_stocks.csv DATASET/      # see note below
python 3.return_calculation.py               # see note below
python 4.train_test_split.py
python 4b.alpha_features.py
python 5.feature_engineering.py
python 7.pooled_cnn_bilstm_model.py          # REUSE_SAVED_MODELS=1 python ... predicts with the saved networks, no training
python 8.plot_pooled_results.py
```

Notes on the existing scripts, which were not changed:

- `2.data_preprocess.py` writes `cleaned_malaysia_stocks.csv` to the project root, but `3.return_calculation.py` reads it from `DATASET/`. Move the file by hand.
- `3.return_calculation.py` has `main()` commented out and only runs `desc_stat()`. Uncomment `main()` to regenerate `DATASET/log_returns.csv`.

The workbooks:

```bash
PRED=DATASET/model_output_pooled/predicted_returns_all_stocks.csv

# static rebuild
python optimization/solve_static_portfolios.py "Copy ver MV model.xlsx" $PRED solutions.npy
python optimization/build_static_workbook.py   "Copy ver MV model.xlsx" $PRED solutions.npy "MV model - tiny CNN-BiLSTM.xlsx"

# daily version (each solve takes about 5 minutes)
python optimization/solve_daily_portfolios.py  "Copy ver MV model.xlsx" $PRED daily.npy            # lambda loop, K = 7
python optimization/solve_daily_cardinality.py "Copy ver MV model.xlsx" $PRED daily_k.npy 0.9      # K loop 4..12
python optimization/solve_daily_grid.py        "Copy ver MV model.xlsx" $PRED grid.npy 9             # full grid, 9 processes
python optimization/build_daily_workbook.py    "Copy ver MV model.xlsx" $PRED daily.npy "MV model - daily tiny CNN-BiLSTM.xlsx" daily_k.npy grid.npy

# Excel Solver version (section 4.16): builds the workbook and the data module; the macro is then run inside Excel
python optimization/build_solver_workbook.py   "Copy ver MV model.xlsx" $PRED "MV model - daily Excel Solver.xlsx" DATASET/test_log_returns.csv optimization/Data2025.bas
```

Yahoo Finance data can change slightly between downloads, and neural network training is not perfectly repeatable across machines, so re-running may give slightly different numbers.

---

## 7. Limitations

- **Shorter training history.** Starting in 2022 leaves three training years, and the first 60 trading days of 2022 are used only as look-back history. Alphas that need 200–250 days of history cannot be used without giving up most of the first training year.
- **One test year.** Many model versions were compared on 2025; picking the best afterwards flatters the winner, so expect somewhat weaker results on a new year.
- **A simpler model is better at forecasting.** The one-variable straight-line model beats the tiny CNN-BiLSTM (correlation 0.170 against 0.137, both on 3 Feb to 31 Dec 2025).
- **Model comparisons cover 224 days, backtests 244.** The model experiments in sections 4.3 to 4.6 and 4.10 were evaluated on 3 Feb to 31 Dec 2025 and were not repeated when the predictions were extended to January. The final model's own scores are given for both periods in section 4.7.
- **The predictable effect may not be tradable.** The next-day reversal may partly be the gap between buying and selling prices. This was not tested.
- **The grid results are 72 overlapping tests on one year.** They are not independent, and the best cell overstates what to expect. The `Grid K` sheets show returns, Sharpe ratios and turnover but not drawdowns; drawdowns are on the `K=` and `lam` sheets only.
- **The daily backtest is an upper bound.** It assumes trading at the previous day's close, the same price the prediction is computed from, and deducts no costs. The daily portfolio trades about 55% of its value each day at K = 7; at an assumed 0.15% per unit traded its advantage disappears.
- **Selection of alphas used multiple comparisons.** 21 features were screened with a threshold of about two standard errors.
- **The smaller-network result is not fully explained.** Which of size, pooling and dropout matters was not isolated.
- **KLCI comparison is not like for like.** Stock returns include dividends; the index does not.
- **Static rebuild keeps the existing design's look-ahead** (yearly average of predictions used from 2 January).
- **Workbook verification.** Excel could not be automated on this machine (it stopped responding and may still be open on a dialog). The static rebuild's numbers were confirmed by recomputing the workbook's formulas in Python, which reproduces the existing workbook's Summary to rounding error. The daily workbook's formulas were evaluated with the Python `formulas` engine after the full-year rebuild: no errors, with the Summary tables (both loops: cumulative returns, Sharpe ratios, drawdowns and p-values) matching an independent calculation to rounding. The grid and `vs Original` tables in this README come from that independent calculation; their workbook formulas are built the same way as before but were not individually compared again. The static rebuild was not recalculated after its `Predicted data` sheet was extended to 244 rows. The Excel Solver macro has not been run by its author; it is tested only when run in Excel. Both files are set to calculate when opened in Excel.
- **The explainer report is out of date.** Its figures do not match the current model, and it was not previewed before publishing.

---

## 8. State of the repository

- **Branch:** `alpha101-momentum-reversal-features`, pushed to `origin` (`szeying26/fyp`).
- **Pull request #1 (merged into `main`):** the model code.
- **Pull request #2 (merged into `main`):** the optimisation scripts, workbooks, this README and the generated data.
- **Pull request #3:** all data starting in 2022, everything re-run, and the comparison with the original workbook: <https://github.com/szeying26/fyp/pull/3>
- **Generated files are in the repository** (`DATASET/`, `OUTPUT/`, `malaysia_stocks.csv`), so results can be inspected without re-running the pipeline.

---

## 9. Glossary

| Term | Meaning |
|---|---|
| Return / log return | A stock's price change from one day's close to the next; the log return is ln(today ÷ yesterday), almost identical to the percentage change at daily scale. |
| Alpha | A formula that turns price and volume history into a signal meant to hint at future returns. |
| IC (information coefficient) | Correlation between a signal today and the return tomorrow. |
| Partial IC | The IC after removing what yesterday's return already explains. |
| Rolling z-score | How unusual today's value is compared with the previous 60 days. |
| CNN | A layer that slides a small window over the data to detect short patterns. |
| BiLSTM | A layer that reads a sequence forwards and backwards and remembers what matters. |
| Weights (of a network) | The adjustable numbers inside a neural network. |
| Pooled model | One model trained on all stocks together. |
| MSE ÷ zero | The model's squared error as a share of the error from always predicting "no change". Below 1 is better than that baseline. |
| Mean-variance optimisation | Choosing portfolio weights to balance expected return against variance. |
| K (cardinality) | The number of stocks the portfolio must hold. |
| λ (lambda) | The trade-off setting: low values favour return, high values favour low risk; 1 means minimise risk only. |
| Sharpe ratio | Average return above the risk-free rate, divided by its variability. |
| Max drawdown | The largest fall from a previous peak in portfolio value. |
| Turnover | How much of the portfolio is traded from one day to the next. |
| Jobson-Korkie test (Memmel correction) | A test of whether two portfolios' Sharpe ratios are really different. |
