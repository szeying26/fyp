# Stock return prediction and portfolio optimisation for 12 Bursa Malaysia stocks

This README records everything done on this project branch, from the first request ("the model is underfit, enrich the features") to the final daily-rebalanced portfolio workbook. It explains every file, every new spreadsheet sheet, every experiment and its result.

All results use the same split: **train 2022–2024, test 2025**. Nothing from 2025 was used to choose features or train models.

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
| Was the original model underfitting because it lacked features? | No. Adding 13 Alpha101 features did not help the original network. The network itself was the bottleneck. |
| What is actually predictable in this data? | A small next-day reversal: after a down day a stock is slightly more likely to rise, and the reverse. Lag-1 autocorrelation of returns is about −0.09. |
| What fixed the model? | Making it about 100 times smaller (509 weights instead of 54,321), looking at 5 days instead of 20, training one model on all 12 stocks, scaling the target, and averaging 5 runs. |
| How good is the final model? | On 2025: correlation 0.145 between predicted and actual returns, error 1.3% lower than predicting "no change", direction right 53.7% of the time, better than "no change" for all 12 stocks. |
| Is it the best possible model? | No. A one-variable straight-line model on yesterday's return is slightly better (correlation 0.170). |
| Does the existing optimisation workbook show that predictions help? | It cannot. Its design averages a year of predictions into one number and holds one portfolio, so predictions barely enter. |
| Do predictions help when used daily? | Yes, before trading costs. Daily re-optimisation returned 29–41% against about 14% for the static benchmark (Feb–Dec 2025), a statistically significant difference for λ up to 0.97 at K = 7, and for K = 4 to 8 at λ = 0.9. Across the full grid of 72 settings where the two portfolios can differ (K = 4 to 12, λ = 0.1 to 0.99), the daily portfolio is ahead in every one and significantly so in 47. The advantage shrinks as more stocks are held. |
| And after trading costs? | At an assumed 0.15% per unit traded the advantage disappears. The break-even cost is 0.13–0.17%. The final workbook excludes costs at the user's request (research setting). |

---

## 2. What was done, in order

1. **Researched Alpha101.** Read the Coriva overview (<https://coriva.eu.org/alpha101-overview/>) and its momentum/reversal detail page for the 23 factors in that category.
2. **Added the features.** Implemented 21 of the 23 momentum/reversal alphas (`alpha101.py`). Two were skipped: #56 needs market cap, #90 needs an industry classification.
3. **Ran a correlation check** (`4b.alpha_features.py`) on the training years only. 13 alphas were kept.
4. **Tested the original CNN-BiLSTM with and without the alphas.** No improvement; both were worse than predicting zero.
5. **Scaled the target and trained a pooled model.** Error fell closer to the "predict zero" level, but mostly because the network predicted less, not better.
6. **Analysed rolling z-score normalisation.** Safe and mildly helpful on the inputs; harmful on the target.
7. **Added the rolling z-score to the pipeline** (`5.feature_engineering.py`).
8. **Tried smaller networks.** A 509-weight CNN-BiLSTM on a 5-day window was the first network to beat predicting zero.
9. **Published an explainer report** on the tiny CNN-BiLSTM for a non-technical reader: <https://claude.ai/artifact/NwTXM5m9R5sDUyxncg57yh> (private to the account owner until shared; it describes single-run numbers, see section 4.8).
10. **Made the tiny model the pipeline default** (`7.pooled_cnn_bilstm_model.py`), averaged over 5 runs, and **plotted its results** (`8.plot_pooled_results.py`), including the two figure types from `plotting.py`.
11. **Diagnosed the "flat" predictions.** Not classic underfitting and not caused by log returns; the model is about 2.6 times too timid.
12. **Committed and pushed** the code to branch `alpha101-momentum-reversal-features`.
13. **Analysed the existing optimisation workbook** (`Copy ver MV model.xlsx`).
14. **Rebuilt the optimisation with tiny-model predictions** (`MV model - tiny CNN-BiLSTM.xlsx`) and compared it with the existing results.
15. **Explained why benchmark and prediction results match** in that design.
16. **Built a daily-rebalanced version** (`MV model - daily tiny CNN-BiLSTM.xlsx`), first with trading costs, then with costs removed.
17. **Added the cardinality loop to the daily version.** The first build fixed K = 7. The existing workbook's stock-selection stage loops K from 4 to 12, so the daily version now does the same.
18. **Computed the full grid.** Every K from 4 to 12 combined with every λ (81 settings), added to the daily workbook as a `Grid summary` sheet and nine `Grid K` sheets.

---

## 3. Files in this repository

### Pipeline scripts (run in this order)

| File | Status | What it does |
|---|---|---|
| `1.raw_data.py` | changed | Downloads the 12 stocks from Yahoo Finance. Still writes the adjusted-close file `malaysia_stocks.csv` for 2022 onwards. **New:** also writes `DATASET/ohlcv_malaysia_stocks.csv`, a full open/high/low/close/volume table from Oct 2020, because some alphas need up to 250 days of history. Stops with an error if Yahoo returns an empty column for any stock. |
| `2.data_preprocess.py` | unchanged | Cleans the adjusted-close file (dates, duplicates, missing rows). |
| `3.return_calculation.py` | unchanged | Turns prices into daily log returns, `DATASET/log_returns.csv`. |
| `4.train_test_split.py` | unchanged | Splits returns into train (2022–2024) and test (2025). |
| `alpha101.py` | **new** | Library of operators (`rank`, `ts_rank`, `delta`, `decay_linear`, …) and the 21 momentum/reversal alphas. Every alpha on day t uses data up to the close of day t only. |
| `4b.alpha_features.py` | **new** | Computes the alphas, runs the correlation check on the training years, and saves the features, the report and the selected list. Run after step 4 and before step 5. |
| `5.feature_engineering.py` | changed | Builds the 20-day input windows. **New options:** `USE_ALPHA_FEATURES` (append the target stock's 13 selected alphas) and `USE_ROLLING_ZSCORE` (replace input returns with a 60-day rolling z-score). The prediction target is always the plain log return. With both on, each window has 25 features instead of 12. |
| `6.cnn_bilstm_model.py` | changed | The original per-stock CNN-BiLSTM (54,321 weights). **New option:** `SCALE_TARGET` standardises the target using training data and converts predictions back to log returns. Kept for comparison; not the recommended model. |
| `7.pooled_cnn_bilstm_model.py` | **new** | The final model. One tiny CNN-BiLSTM (509 weights) trained on all 12 stocks together, using the last 5 days of each window, trained 5 times with different seeds and averaged. Writes to `DATASET/model_output_pooled/`. |
| `8.plot_pooled_results.py` | **new** | All result plots for the final model, written to `OUTPUT/pooled_model_plots/`. |
| `plotting.py` | unchanged | The original plotting script. It reads the step 6 output folder. Its two figure types are reproduced for the final model by step 8. |

### Optimisation scripts (`optimization/`)

These produced the two new workbooks. They were written as working scripts during the analysis and take their file paths as command-line arguments (see section 6).

| File | What it does |
|---|---|
| `optimization/solve_static_portfolios.py` | Solves the existing workbook's two portfolio problems exactly, by solving every K-stock combination and keeping the best. Does this for historical averages, the old predictions and the tiny-model predictions, and prints a check against the weights stored in the existing workbook. |
| `optimization/build_static_workbook.py` | Copies the existing workbook, swaps in the tiny-model predictions and the exact weights, and adds the `Comparison` sheet. Output: `MV model - tiny CNN-BiLSTM.xlsx`. |
| `optimization/solve_daily_portfolios.py` | For each of the 224 prediction days and each λ, finds the best 7-stock portfolio from that day's predictions. A fast batch method ranks all 792 combinations and the best few are refined exactly; it was checked against full enumeration on 16 cases with identical results. |
| `optimization/solve_daily_cardinality.py` | The cardinality loop for the daily strategy: the same daily optimisation for every K from 4 to 12 at one λ (0.9 by default). |
| `optimization/solve_daily_grid.py` | The full grid: the same daily optimisation for every K from 4 to 12 combined with every λ (81 settings), solved in parallel. About 5 minutes on 9 processes. |
| `optimization/build_daily_workbook.py` | Builds the daily workbook from scratch with live formulas, from the outputs of the three daily solvers (the grid file is an optional sixth argument). Output: `MV model - daily tiny CNN-BiLSTM.xlsx`. |

### Spreadsheets

| File | Status | What it is |
|---|---|---|
| `Copy ver MV model.xlsx` | existing (pulled from `main`) | The original mean-variance optimisation and backtest. |
| `MV model - tiny CNN-BiLSTM.xlsx` | **new** | Same design as the existing workbook, with tiny-model predictions and exact weights, plus a `Comparison` sheet. |
| `MV model - daily tiny CNN-BiLSTM.xlsx` | **new** | Daily re-optimisation using each day's prediction. No trading costs. |

### Generated data and outputs

| Path | Contents |
|---|---|
| `malaysia_stocks.csv` | Adjusted close prices from step 1. |
| `DATASET/ohlcv_malaysia_stocks.csv` | OHLCV table from Oct 2020 (step 1). |
| `DATASET/cleaned_malaysia_stocks.csv`, `log_returns.csv`, `train_log_returns.csv`, `test_log_returns.csv` | Outputs of steps 2–4. |
| `DATASET/alpha_features/alpha_features.csv` | All 21 alphas for every stock and day, cleaned. |
| `DATASET/alpha_features/alpha_ic_report.csv` | The correlation check table (section 4.2). |
| `DATASET/alpha_features/alpha_feature_correlation.csv` | Correlation between features on the training years. |
| `DATASET/alpha_features/selected_alpha_features.json` | The 13 selected alphas, read by step 5. |
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
- Before the check each alpha is winsorised at its training 1%/99% quantiles per stock; remaining gaps are forward-filled, then filled with the training median.

| Feature | Train IC | Train partial IC | Stocks with same sign | Test IC | Test partial IC | Decision |
|---|---|---|---|---|---|---|
| ret_1d (own day-t return) | -0.087 | n/a | 12/12 | -0.122 | n/a | base feature, already in the model |
| alpha038 | 0.110 | 0.071 | 12/12 | 0.126 | 0.061 | KEPT |
| alpha033 | 0.102 | 0.059 | 12/12 | 0.124 | 0.055 | dropped: correlation +0.85 with alpha038 |
| alpha039 | 0.068 | 0.052 | 12/12 | 0.062 | 0.039 | KEPT |
| alpha008 | 0.066 | 0.049 | 11/12 | 0.070 | 0.048 | KEPT |
| alpha019 | 0.066 | 0.048 | 12/12 | 0.039 | 0.011 | KEPT |
| alpha084 | 0.069 | 0.047 | 12/12 | 0.082 | 0.051 | KEPT |
| alpha035 | 0.091 | 0.043 | 12/12 | 0.107 | 0.030 | KEPT |
| alpha053 | 0.070 | 0.038 | 12/12 | 0.068 | 0.027 | KEPT |
| alpha046 | 0.063 | 0.037 | 12/12 | 0.070 | 0.030 | KEPT |
| alpha037 | 0.073 | 0.037 | 11/12 | 0.104 | 0.043 | KEPT |
| alpha052 | 0.040 | 0.034 | 10/12 | 0.024 | 0.013 | KEPT |
| alpha010 | 0.078 | 0.028 | 12/12 | 0.110 | 0.041 | KEPT |
| alpha030 | 0.054 | 0.025 | 11/12 | 0.057 | 0.016 | KEPT |
| alpha029 | 0.020 | 0.021 | 7/12 | 0.032 | 0.029 | KEPT |
| alpha024 | 0.036 | 0.018 | 10/12 | 0.054 | 0.035 | dropped: partial IC below 0.02 |
| alpha009 | 0.076 | -0.016 | 12/12 | 0.116 | 0.005 | dropped: partial IC below 0.02 |
| alpha023 | 0.010 | -0.014 | 7/12 | 0.032 | 0.001 | dropped: partial IC below 0.02 |
| alpha020 | 0.018 | 0.013 | 9/12 | 0.006 | 0.001 | dropped: partial IC below 0.02 |
| alpha049 | 0.082 | -0.013 | 12/12 | 0.126 | 0.031 | dropped: partial IC below 0.02 |
| alpha051 | 0.079 | 0.010 | 12/12 | 0.131 | 0.052 | dropped: partial IC below 0.02 |
| alpha004 | 0.003 | 0.000 | 8/12 | 0.000 | -0.005 | dropped: partial IC below 0.02 |

The test columns are an out-of-sample check and were not used for selection.

**Selected (13):** alpha038, 039, 008, 019, 084, 035, 053, 046, 037, 052, 010, 030, 029. The highest correlation between any two of them is 0.60.

**What the check revealed:** every alpha has a positive IC because they all partly measure the same thing, the next-day reversal. The per-stock lag-1 autocorrelation of returns in training ranges from +0.02 (CIMB) to −0.19 (Maxis).

### 4.3 Original CNN-BiLSTM, with and without the alphas

Per-stock models (Conv1D 64 filters → max pooling → BiLSTM 50 → dropout → dense 32 → 1), 12 stocks × 3 seeds.

| Inputs | MSE ÷ MSE of predicting zero | Correlation with actual | Stocks improved by alphas |
|---|---|---|---|
| Returns only | 1.054 | 0.027 | n/a |
| Returns + 13 alphas | 1.075 | −0.012 | 4 of 12 |

Both are worse than predicting zero. A ridge regression on yesterday's return alone reached a correlation of about 0.12 and beat zero, and adding the 13 alphas to that regression changed nothing (0.115). Conclusion: the features carry signal individually but add almost nothing jointly, and the network was failing to learn even the simple reversal.

### 4.4 Target scaling and pooling

Daily returns are about 0.01 in size, so the raw squared-error loss is tiny and the network settles near a constant. Scaling the target fixes the loss scale. Pooling trains one model on all stocks (about 8,500 samples instead of about 713 per stock).

| Model (3 seeds, 12 stocks) | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|
| Per-stock, raw target, returns only (original) | 1.054 | 0.027 | 3 of 12 |
| Per-stock, raw target, + alphas | 1.075 | −0.012 | 1 of 12 |
| Per-stock, scaled target, returns only | 1.022 | 0.020 | 1 of 12 |
| Per-stock, scaled target, + alphas | 1.014 | 0.014 | 1 of 12 |
| Pooled, scaled target, returns only | 1.007 | 0.000 | 0 of 12 |
| Pooled, scaled target, + alphas | 1.002 | 0.027 | 4 of 12 |

Error moved towards the "predict zero" level, but the predictions shrank (to 6–10% of the size of actual moves, from 16%) while correlation did not improve.

### 4.5 Rolling z-score analysis

The z-score for day t uses the mean and standard deviation of the **previous** W days only, so nothing leaks from the future.

Effect on the data (training years, average of 12 stocks):

| Property | Raw | z, 20-day | z, 60-day | z, 120-day |
|---|---|---|---|---|
| Test volatility ÷ train volatility | 1.20 | 1.03 | 1.04 | 1.00 |
| Range of that ratio across stocks | 0.88–2.03 | 0.96–1.16 | 0.95–1.14 | 0.86–1.15 |
| Volatility clustering (lag-1 autocorrelation of absolute returns) | 0.18 | 0.10 | 0.14 | 0.16 |
| Excess kurtosis | 4.4 | 5.0 | 5.2 | 5.9 |
| Correlation with next-day return, test | −0.115 | −0.111 | −0.118 | −0.120 |

Effect on the model (original architecture; pooled rows 5 seeds, per-stock rows 3 seeds):

| Model | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|
| Pooled, raw inputs | 1.009 | 0.007 | 1 of 12 |
| Pooled, z inputs 20-day | 1.011 | 0.009 | 1 of 12 |
| Pooled, z inputs 60-day | 1.006 | 0.018 | 1 of 12 |
| Pooled, z inputs 120-day | 1.005 | 0.024 | 2 of 12 |
| Pooled, z inputs and z target, 60-day | 1.018 | −0.030 | 0 of 12 |
| Pooled, raw inputs + alphas | 1.006 | 0.028 | 1 of 12 |
| Pooled, z inputs 60-day + alphas | 1.003 | 0.056 | 6 of 12 |
| Per-stock, raw inputs | 1.022 | 0.020 | 1 of 12 |
| Per-stock, z inputs 60-day | 1.020 | 0.016 | 3 of 12 |
| Per-stock, z inputs and z target, 60-day | 1.030 | −0.020 | 0 of 12 |
| Ridge on yesterday's return, raw | 0.976 | 0.17 | 10 of 12 |
| Ridge, z input and z target | 0.987 | 0.11 | 10 of 12 |

Decision: use a 60-day rolling z-score on the **inputs** and leave the target as a plain log return.

### 4.6 Smaller networks

Pooled setup, z-scored inputs plus 13 alphas (26 input features), 5 seeds each.

| Model | Weights | Window | MSE ÷ zero | Correlation | Stocks beating zero |
|---|---|---|---|---|---|
| Original CNN-BiLSTM (64 filters, LSTM 50, dense 32) | 54,321 | 20 days | 1.003 | 0.056 | 6 of 12 |
| Small CNN-BiLSTM (8 filters, LSTM 8, pooling, dropout) | 1,737 | 20 days | 1.006 | 0.021 | 1 of 12 |
| Small CNN-BiLSTM (same) | 1,737 | 10 days | 1.009 | 0.008 | 0 of 12 |
| Small LSTM (8 units) | 1,129 | 20 days | 0.998 | 0.079 | 6 of 12 |
| Small LSTM (8 units) | 1,129 | 5 days | 0.997 | 0.081 | 7 of 12 |
| Small dense (8 units) | 1,057 | 5 days | 1.058 | 0.057 | 0 of 12 |
| **Tiny CNN-BiLSTM (4 filters of width 2, LSTM 4 each way)** | **509** | **5 days** | **0.992** | **0.098** | **9 of 12** |
| Linear layer | 131 | 5 days | 1.013 | 0.093 | 3 of 12 |
| Linear layer | 27 | 1 day | 0.982 | 0.136 | 9 of 12 |
| Ridge on yesterday's z-scored return | 1 | 1 day | 0.976 | 0.170 | 10 of 12 |

- The tiny CNN-BiLSTM is the best neural network and the first to beat predicting zero.
- Size is not the whole story: the 1,737-weight version, which kept pooling and dropout, did worse than the original. Which of those differences matters was not isolated.
- More history hurts even a linear model (0.136 with 1 day, 0.093 with 5 days): the usable signal is in the most recent day.

### 4.7 The final model

`7.pooled_cnn_bilstm_model.py`:

- **Inputs:** last 5 trading days × 26 numbers: the target stock's own z-scored return, all 12 stocks' z-scored returns, and the target stock's 13 alphas. Inputs are standardised per stock on training data.
- **Network:** Conv1D (4 filters, kernel 2) → BiLSTM (4 units each way) → Dense(1). Weights: 212 + 288 + 9 = 509.
- **Target:** next-day log return, standardised per stock on training data; predictions are converted back.
- **Training:** all 12 stocks pooled; 7,704 fitting samples; the most recent 10% of each stock's training windows (852 samples) used for early stopping; batch 64, up to 30 epochs, patience 5.
- **Averaging:** 5 runs with seeds 42–46; predictions averaged.
- **Test:** 224 days × 12 stocks = 2,688 predictions (3 Feb to 31 Dec 2025).

Results on 2025:

| | Single run (average of 5) | 5 runs averaged (final) |
|---|---|---|
| Correlation with actual returns | 0.098 | 0.145 |
| MSE ÷ zero | 0.992 | 0.987 |
| Direction hit rate | 52.7% | 53.7% |
| Stocks beating zero | 9 of 12 | 12 of 12 |

Final model by stock:

| Stock | Correlation | MSE ÷ zero | Direction hit rate |
|---|---|---|---|
| CIMB (1023.KL) | 0.172 | 0.989 | 53.2% |
| Maybank (1155.KL) | 0.193 | 0.985 | 49.5% |
| Public Bank (1295.KL) | 0.230 | 0.977 | 59.5% |
| TM (4863.KL) | 0.204 | 0.974 | 57.5% |
| PChem (5183.KL) | 0.017 | 0.999 | 46.7% |
| Sunway (5211.KL) | 0.179 | 0.976 | 56.1% |
| IHH Healthcare (5225.KL) | 0.002 | 0.998 | 56.2% |
| Tenaga (5347.KL) | 0.200 | 0.982 | 56.8% |
| Hong Leong Bank (5819.KL) | 0.167 | 0.986 | 53.0% |
| Maxis (6012.KL) | 0.106 | 0.992 | 53.3% |
| Axiata (6888.KL) | 0.133 | 0.991 | 52.2% |
| Press Metal (8869.KL) | 0.136 | 0.996 | 51.0% |

Sorting all 2,688 test predictions into five equal groups by predicted value, the average actual next-day return rises steadily: −0.16%, 0.00%, +0.05%, +0.10%, +0.32%.

### 4.8 The explainer report

<https://claude.ai/artifact/NwTXM5m9R5sDUyxncg57yh>

A plain-language page on the tiny CNN-BiLSTM: what it predicts, what goes in, how the two layers work, how it was trained, how to read the scores, results, limits and a glossary. It was written before the 5-run averaging was added, so its numbers are the single-run figures (correlation 0.098, error 99.2%, hit rate 52.7%, 9 of 12 stocks), not the final averaged ones in section 4.7. The page was not previewed before publishing.

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

| Check | Train | Test |
|---|---|---|
| Correlation with actual returns | 0.184 | 0.145 |
| MSE ÷ zero | 0.977 | 0.987 |
| Size of predictions relative to actual moves | 6.5% | 5.6% |
| Size they should be, given that correlation | 18.4% | 14.5% |
| Average predicted return per day | 0.035% | 0.033% |
| Average actual return per day | 0.036% | 0.061% |

- A model that minimises squared error should move only as much as it is sure of. With a correlation of 0.145 the ideal predictions are about 14.5% the size of real moves, so even a perfect version would look nearly flat on a shared axis.
- Train and test results are close, so the model is neither memorising nor failing to learn.
- It is **under-confident** by a factor of about 2.6 (calibration slope 2.59 on test, 2.85 on train). Early stopping and averaging both pull predictions towards zero.
- Log returns are not the cause: log and simple returns differ by at most 0.32 percentage points on the most extreme day, and the average prediction is close to the average actual return.
- A possible improvement, **not implemented**: multiply predictions by about 2.85 (learned from training data). Correlation would be unchanged and error should fall to roughly 98% of the zero baseline.

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
| 0.1–0.7 | 6.61% / 0.31 | 9.22% / 0.49 | 6.61% / 0.31 | 8.19% / 0.40 |
| 0.9 | 8.79% / 0.49 | 9.22% / 0.49 | 8.80% / 0.49 | 8.39% / 0.45 |
| 0.95 | 9.99% / 0.66 | 8.53% / 0.48 | 9.94% / 0.64 | 9.07% / 0.54 |
| 0.97 | 10.82% / 0.76 | 9.03% / 0.55 | 10.88% / 0.74 | 10.37% / 0.69 |
| 0.99 | 9.32% / 0.63 | 12.52% / 0.90 | 11.59% / 0.84 | 11.53% / 0.84 |
| 1 | 13.96% / 1.02 | 13.96% / 1.02 | 9.83% / 0.67 | 9.83% / 0.67 |
| **Average** | 8.8% / 0.53 | 10.0% / 0.60 | 8.6% / 0.51 | 9.1% / 0.53 |

- Statistical test, λ=0.9, tiny model against rebuilt benchmark: z = −0.21, p = 0.83.
- The exact minimum-variance K=7 portfolio returned 9.8% in 2025 against 14.0% for Solver's non-optimal one, so the existing headline result partly reflects where Solver stopped.

### 4.13 Why benchmark and prediction results match in that design

- **Minimise risk:** the objective is variance, which depends only on the shared covariance matrix. Predictions enter only through the return floor (0.0237% a day), and the minimum-variance portfolios clear it comfortably under either set of expected returns (0.034–0.043% benchmark, 0.039–0.051% tiny model). A constraint that is not binding changes nothing, so the weights are identical for every K.
- **Trade-off:** averaging 224 days of predictions recreates the historical average. The tiny model's average predicted return per stock has a correlation of 0.93 with the historical average, with the same top five stocks. The model's skill is in day-to-day changes, which cancel out in a yearly average.

The comparison cannot show a difference whichever model supplies the predictions. That is a property of the design, not evidence about prediction.

### 4.14 Daily re-optimisation

`MV model - daily tiny CNN-BiLSTM.xlsx`. Before each trading day the optimiser receives that day's predicted returns and picks the best K-stock portfolio (5%–30% weights, same covariance matrix). The static benchmark solves the same problem once with historical average returns. Period: 3 Feb to 31 Dec 2025, 224 days. The 6.15% minimum-return floor is not applied, because on days when every prediction is low the problem would have no solution.

The workbook follows the existing workbook's two stages:

- **Stage A, stock selection (cardinality loop):** K = 4 to 12, at λ = 0.9.
- **Stage B, risk-return trade-off (λ loop):** λ = 0.1 to 1, at K = 7.

It also holds the **full grid** of every K with every λ (81 settings), reported after the two stages below.

The cardinality loop uses the trade-off objective, not pure risk minimisation as in the existing workbook. Under pure risk minimisation the predictions do not enter, so the daily and static portfolios would be identical for every K (this is what λ = 1 shows in stage B). λ = 0.9 was chosen because it is the setting the existing workbook's statistical test uses.

**Stage A results, cardinality loop at λ = 0.9, no trading costs:**

| K | Daily tiny model | Static benchmark | Difference (points) | Daily Sharpe | Static Sharpe | Daily max drawdown | Static max drawdown | Daily turnover | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 39.3% | 11.8% | +27.5 | 2.04 | 0.72 | 13.3% | 12.5% | 62% | 2.86 | 0.004 | Yes |
| 5 | 39.5% | 12.1% | +27.4 | 2.12 | 0.75 | 12.6% | 12.1% | 62% | 3.04 | 0.002 | Yes |
| 6 | 36.2% | 12.9% | +23.4 | 1.99 | 0.83 | 12.6% | 11.7% | 61% | 2.65 | 0.008 | Yes |
| 7 | 33.7% | 13.7% | +19.9 | 1.91 | 0.92 | 12.7% | 11.1% | 58% | 2.41 | 0.016 | Yes |
| 8 | 31.1% | 13.9% | +17.2 | 1.82 | 0.95 | 12.5% | 10.6% | 54% | 2.18 | 0.029 | Yes |
| 9 | 27.5% | 15.5% | +12.1 | 1.63 | 1.07 | 13.2% | 10.8% | 50% | 1.38 | 0.167 | No |
| 10 | 26.8% | 15.8% | +11.0 | 1.62 | 1.11 | 13.0% | 10.4% | 45% | 1.17 | 0.242 | No |
| 11 | 26.4% | 13.9% | +12.5 | 1.62 | 0.95 | 11.8% | 11.8% | 40% | 1.72 | 0.085 | No |
| 12 | 23.6% | 14.4% | +9.2 | 1.48 | 0.99 | 12.3% | 12.1% | 32% | 1.49 | 0.136 | No |

- The daily portfolio beats the static benchmark at every K, and the gap narrows steadily as K grows: holding more stocks forces the portfolio to spread out, which leaves less room to act on the forecast.
- The difference is statistically significant for K = 4 to 8 and not for K = 9 to 12.
- The best K for the daily strategy is 5 (highest return and Sharpe); for the static benchmark it is 10. K = 7, the existing workbook's choice, sits in the middle.
- Choosing K by its 2025 result and then reporting that result would overstate it; the whole table is the fair picture.

**Stage B results, λ loop at K = 7, no trading costs:**

| λ | Daily tiny model | Static benchmark | Difference (points) | Daily Sharpe | Static Sharpe | Daily max drawdown | Static max drawdown | Daily turnover | z | p-value | Different at 5%? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 38.9% | 14.0% | +25.0 | 1.92 | 0.83 | 16.0% | 13.2% | 57% | 2.15 | 0.031 | Yes |
| 0.3 | 39.2% | 14.0% | +25.3 | 1.94 | 0.83 | 15.7% | 13.2% | 57% | 2.18 | 0.029 | Yes |
| 0.5 | 40.4% | 14.0% | +26.4 | 2.01 | 0.83 | 14.9% | 13.2% | 57% | 2.36 | 0.018 | Yes |
| 0.7 | 40.6% | 14.0% | +26.7 | 2.07 | 0.83 | 14.1% | 13.2% | 58% | 2.61 | 0.009 | Yes |
| 0.9 | 33.7% | 13.7% | +19.9 | 1.91 | 0.92 | 12.7% | 11.1% | 58% | 2.41 | 0.016 | Yes |
| 0.95 | 31.8% | 13.6% | +18.2 | 1.97 | 1.01 | 11.3% | 10.0% | 50% | 2.44 | 0.015 | Yes |
| 0.97 | 29.3% | 13.9% | +15.4 | 1.99 | 1.07 | 10.4% | 9.8% | 40% | 2.52 | 0.012 | Yes |
| 0.99 | 19.5% | 14.1% | +5.4 | 1.52 | 1.14 | 9.7% | 9.5% | 16% | 1.82 | 0.069 | No |
| 1 | 12.3% | 12.3% | 0.0 | 0.96 | 0.96 | 10.6% | 10.6% | 0% | n/a | n/a | n/a |

Returns are cumulative; Sharpe ratios are annualised. Equal weight returned 13.8% (Sharpe 0.94, max drawdown 13.1%) and the KLCI 7.2% (Sharpe 0.48, max drawdown 12.9%) over the same days. At λ = 1 the objective ignores expected returns, so the two portfolios are identical, which confirms that the forecast is the only difference elsewhere. The K = 7 row of stage A and the λ = 0.9 row of stage B are the same portfolio.

**Full grid: every K with every λ, no trading costs.** The two stages above are one row and one column of this grid (the K = 7 row and the λ = 0.9 column), and the grid reproduces them exactly. Rows are K, columns are λ. At λ = 1 the daily and static portfolios are identical.

Daily tiny model, cumulative return:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 37.8% | 38.1% | 39.7% | 39.4% | 39.3% | 33.2% | 40.5% | 19.6% | 13.1% |
| 5 | 36.6% | 37.2% | 38.0% | 37.8% | 39.5% | 35.4% | 35.2% | 21.7% | 14.0% |
| 6 | 39.1% | 38.8% | 39.5% | 39.1% | 36.2% | 34.5% | 32.9% | 21.6% | 14.7% |
| 7 | 38.9% | 39.2% | 40.4% | 40.6% | 33.7% | 31.8% | 29.3% | 19.5% | 12.3% |
| 8 | 38.4% | 38.3% | 38.8% | 39.5% | 31.1% | 29.1% | 27.2% | 16.8% | 12.1% |
| 9 | 39.1% | 38.9% | 38.7% | 38.9% | 27.5% | 27.4% | 25.6% | 14.3% | 11.7% |
| 10 | 38.0% | 38.3% | 38.9% | 38.9% | 26.8% | 25.1% | 24.8% | 16.2% | 12.8% |
| 11 | 33.3% | 33.1% | 33.1% | 34.1% | 26.4% | 23.8% | 25.5% | 16.7% | 12.6% |
| 12 | 28.9% | 28.9% | 29.2% | 30.1% | 23.6% | 20.0% | 19.8% | 14.8% | 12.9% |

Static benchmark, cumulative return:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 12.5% | 12.5% | 12.5% | 12.5% | 11.8% | 12.0% | 16.4% | 12.7% | 13.1% |
| 5 | 13.5% | 13.5% | 13.5% | 13.5% | 12.1% | 13.5% | 13.6% | 13.8% | 14.0% |
| 6 | 13.6% | 13.6% | 13.6% | 13.8% | 12.9% | 13.0% | 14.2% | 14.4% | 14.7% |
| 7 | 14.0% | 14.0% | 14.0% | 14.0% | 13.7% | 13.6% | 13.9% | 14.1% | 12.3% |
| 8 | 14.8% | 14.8% | 14.8% | 14.8% | 13.9% | 13.5% | 13.6% | 11.8% | 12.1% |
| 9 | 15.1% | 15.1% | 15.1% | 16.6% | 15.5% | 14.8% | 11.4% | 11.5% | 11.7% |
| 10 | 16.8% | 16.8% | 16.8% | 17.1% | 15.8% | 12.5% | 12.6% | 12.8% | 12.8% |
| 11 | 17.6% | 17.6% | 17.6% | 17.7% | 13.9% | 12.5% | 12.5% | 12.6% | 12.6% |
| 12 | 15.9% | 15.9% | 15.9% | 15.9% | 14.4% | 12.9% | 12.7% | 12.5% | 12.9% |

Daily tiny model, annual Sharpe ratio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 1.81 | 1.83 | 1.91 | 1.94 | 2.04 | 1.91 | 2.57 | 1.59 | 1.05 |
| 5 | 1.76 | 1.80 | 1.85 | 1.88 | 2.12 | 2.09 | 2.32 | 1.73 | 1.16 |
| 6 | 1.91 | 1.90 | 1.94 | 1.97 | 1.99 | 2.09 | 2.18 | 1.69 | 1.20 |
| 7 | 1.92 | 1.93 | 2.01 | 2.07 | 1.91 | 1.97 | 1.99 | 1.52 | 0.96 |
| 8 | 1.93 | 1.93 | 1.96 | 2.04 | 1.82 | 1.83 | 1.86 | 1.30 | 0.94 |
| 9 | 1.99 | 1.98 | 1.98 | 2.04 | 1.63 | 1.74 | 1.76 | 1.08 | 0.88 |
| 10 | 1.97 | 1.98 | 2.03 | 2.08 | 1.62 | 1.62 | 1.72 | 1.22 | 0.96 |
| 11 | 1.80 | 1.79 | 1.80 | 1.88 | 1.62 | 1.56 | 1.80 | 1.26 | 0.95 |
| 12 | 1.64 | 1.64 | 1.66 | 1.73 | 1.48 | 1.33 | 1.41 | 1.11 | 0.96 |

Static benchmark, annual Sharpe ratio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.69 | 0.69 | 0.69 | 0.69 | 0.72 | 0.83 | 1.27 | 1.02 | 1.05 |
| 5 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 | 1.02 | 1.05 | 1.09 | 1.16 |
| 6 | 0.78 | 0.78 | 0.78 | 0.80 | 0.83 | 0.93 | 1.13 | 1.16 | 1.20 |
| 7 | 0.83 | 0.83 | 0.83 | 0.83 | 0.92 | 1.01 | 1.07 | 1.14 | 0.96 |
| 8 | 0.91 | 0.91 | 0.91 | 0.91 | 0.95 | 1.01 | 1.05 | 0.91 | 0.94 |
| 9 | 0.95 | 0.95 | 0.95 | 1.03 | 1.07 | 1.10 | 0.84 | 0.86 | 0.88 |
| 10 | 1.07 | 1.07 | 1.07 | 1.08 | 1.11 | 0.89 | 0.93 | 0.96 | 0.96 |
| 11 | 1.13 | 1.13 | 1.13 | 1.13 | 0.95 | 0.89 | 0.92 | 0.94 | 0.95 |
| 12 | 1.01 | 1.01 | 1.01 | 1.01 | 0.99 | 0.92 | 0.93 | 0.93 | 0.96 |

Jobson-Korkie-Memmel p-value, daily against static (bold = different at 5%):

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | **0.035** | **0.031** | **0.019** | **0.013** | **0.004** | 0.055 | **0.017** | **0.006** | n/a |
| 5 | **0.050** | **0.042** | **0.027** | **0.019** | **0.002** | **0.029** | **0.006** | **0.003** | n/a |
| 6 | **0.028** | **0.028** | **0.019** | **0.015** | **0.008** | **0.005** | **0.011** | **0.016** | n/a |
| 7 | **0.031** | **0.029** | **0.018** | **0.009** | **0.016** | **0.015** | **0.012** | 0.069 | n/a |
| 8 | **0.046** | **0.047** | **0.040** | **0.020** | **0.029** | **0.032** | **0.015** | 0.086 | n/a |
| 9 | 0.055 | 0.056 | 0.054 | **0.037** | 0.167 | 0.094 | **0.002** | 0.099 | n/a |
| 10 | 0.110 | 0.105 | 0.088 | **0.042** | 0.242 | **0.038** | **0.005** | **0.039** | n/a |
| 11 | 0.180 | 0.187 | 0.182 | 0.106 | 0.085 | 0.054 | **0.001** | **0.021** | n/a |
| 12 | 0.108 | 0.107 | 0.097 | 0.059 | 0.136 | 0.183 | **0.047** | **0.021** | n/a |

Average daily turnover of the daily portfolio:

| K \ λ | 0.1 | 0.3 | 0.5 | 0.7 | 0.9 | 0.95 | 0.97 | 0.99 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 61% | 62% | 63% | 64% | 62% | 54% | 49% | 16% | 0% |
| 5 | 61% | 61% | 62% | 63% | 62% | 54% | 46% | 16% | 0% |
| 6 | 59% | 59% | 60% | 61% | 61% | 52% | 42% | 17% | 0% |
| 7 | 57% | 57% | 57% | 58% | 58% | 50% | 40% | 16% | 0% |
| 8 | 54% | 54% | 54% | 55% | 54% | 48% | 36% | 14% | 0% |
| 9 | 50% | 49% | 50% | 51% | 50% | 44% | 33% | 10% | 0% |
| 10 | 46% | 45% | 46% | 46% | 45% | 41% | 31% | 10% | 0% |
| 11 | 39% | 39% | 39% | 40% | 40% | 37% | 28% | 10% | 0% |
| 12 | 31% | 30% | 31% | 31% | 32% | 30% | 21% | 6% | 0% |

- **The daily portfolio is ahead in all 72 settings with λ below 1.** Its cumulative return ranges from 14.3% to 40.6%; the static benchmark's ranges from 11.4% to 17.7%. The gap ranges from 2.3 to 27.5 points.
- **The difference is statistically significant in 47 of the 72 settings.** By K: 7, 8, 8, 7, 7 of 8 settings for K = 4 to 8, then 2, 4, 2, 2 of 8 for K = 9 to 12. So the stage A pattern (significant for small K, not for large K) holds across λ, not only at 0.9.
- **λ = 0.97 is significant at every K**, the only such column. The static benchmark's Sharpe ratio is low there for large K while the daily portfolio's stays high.
- **For λ from 0.1 to 0.7 the results barely change with λ.** The likely reason is that with so little weight on risk the optimiser mostly holds the stocks with the highest expected returns at the weight limits, whatever the exact λ.
- **Highest values:** cumulative return 40.6% at K = 7, λ = 0.7; Sharpe ratio 2.57 at K = 4, λ = 0.97. These are the best of 72 tries on one year, so they overstate what to expect; the tables as a whole are the fair picture.
- **Turnover falls as K rises and as λ approaches 1,** from about 62% a day (K = 4) to about 31% (K = 12) at low λ, and to 6–17% at λ = 0.99.
- With 72 tests at the 5% level, about 4 would appear significant by chance alone; 47 is far more than that, but the tests are not independent (the settings hold overlapping portfolios on the same days).

**Earlier version with trading costs (K = 7 only) (removed from the final workbook at the user's request):** at an assumed 0.15% per unit traded, results were:

| λ | Daily, before costs | Daily, after 0.15% costs | Static | Sharpe after costs | Static Sharpe | Break-even cost |
|---|---|---|---|---|---|---|
| 0.1 | 38.9% | 14.9% | 14.0% | 0.78 | 0.83 | 0.16% |
| 0.5 | 40.4% | 15.8% | 14.0% | 0.84 | 0.83 | 0.17% |
| 0.9 | 33.7% | 10.0% | 13.7% | 0.57 | 0.92 | 0.13% |
| 0.97 | 29.3% | 13.2% | 13.9% | 0.89 | 1.07 | 0.15% |
| 0.99 | 19.5% | 13.1% | 14.1% | 1.00 | 1.14 | 0.13% |

After costs no difference was statistically significant (p from 0.39 to 0.98). The 0.15% figure was an assumption, not a quoted fee.

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
| Predicted data | Values replaced with the tiny model's predictions for the same 224 dates. |
| Benchmark_MV model | Weights in rows 18–29 and 38–49 replaced with the exact optimum. K = 3 column cleared and marked infeasible. A note in A57 states where the weights came from. |
| Predicted_MV model | Same, using the tiny-model expected returns. |
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
| **Summary** | Table A, cardinality loop: one row per K = 4 to 12 at λ = 0.9. Table B, λ loop: one row per λ at K = 7. Both tables show cumulative return of the daily and static portfolios, the difference, annual Sharpe ratios, max drawdowns, average daily turnover, daily Sharpe ratios, correlation, Jobson-Korkie-Memmel z and p-value, and whether they differ at 5%. Below: equal weight and KLCI over the same days, then notes on method and assumptions. |
| **Grid summary** | The full grid. Seven tables with K = 4 to 12 down the side and λ = 0.1 to 1 across the top: daily cumulative return, static cumulative return, the difference, daily Sharpe, static Sharpe, p-value (yellow when below 0.05) and average daily turnover. Every cell links to the `Grid K` sheet for that K. |
| **Chart** | Wealth from RM100,000 for λ = 0.9: daily tiny model, static benchmark, equal weight, KLCI, with a line chart. |
| **Inputs** | Risk-free rate (ln(1.0288)/252), initial wealth (RM100,000), K = 7, weight limits 5% and 30%, colour key. |
| **Actual 2025** | Actual daily log returns for the 224 prediction days, plus the KLCI return. |
| **Predicted data** | The tiny model's predicted next-day return for each stock and day. |
| **Historical data** | 2022–2024 daily log returns. |
| **Covariance** | Average historical return per stock and the covariance matrix, as formulas on Historical data. |
| **Reference** | Equal-weight and KLCI daily returns, wealth, running peak and drawdown. |
| **K=4 … K=12** (nine sheets) | The cardinality loop at λ = 0.9. Row 4: the static benchmark's weights for that K. Rows 6–229: one row per day with the 12 daily weights (optimiser output), then formulas for sum of weights, stocks held, turnover, daily portfolio return, static benchmark return, wealth of each, running peak and drawdown of each. |
| **lam 0.1 … lam 1** (nine sheets) | The λ loop at K = 7, same layout. Sheet `lam 0.9` holds the same portfolio as sheet `K=7`. |
| **Grid K4 … Grid K12** (nine sheets) | The full grid, one sheet per K with nine λ blocks side by side (17 columns each). Rows 2–11: the block's statistics (cumulative returns, Sharpe ratios, turnover, correlation, z, p-value). Row 12: static benchmark weights. Rows 14–237: one row per day with the 12 daily weights (optimiser output), then formulas for turnover, daily return, static return and the wealth of each. |

Turnover is the sum of absolute weight changes from the previous day and is shown for information only. No trading costs are deducted for either portfolio.

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
python 7.pooled_cnn_bilstm_model.py
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
```

Yahoo Finance data can change slightly between downloads, and neural network training is not perfectly repeatable across machines, so re-running may give slightly different numbers.

---

## 7. Limitations

- **One test year.** Many model versions were compared on 2025; picking the best afterwards flatters the winner, so expect somewhat weaker results on a new year.
- **A simpler model is better at forecasting.** The one-variable straight-line model beats the tiny CNN-BiLSTM (correlation 0.170 against 0.145).
- **The predictable effect may not be tradable.** The next-day reversal may partly be the gap between buying and selling prices. This was not tested.
- **The grid results are 72 overlapping tests on one year.** They are not independent, and the best cell overstates what to expect. The `Grid K` sheets show returns, Sharpe ratios and turnover but not drawdowns; drawdowns are on the `K=` and `lam` sheets only.
- **The daily backtest is an upper bound.** It assumes trading at the previous day's close, the same price the prediction is computed from, and deducts no costs. The daily portfolio trades about 57% of its value each day; at an assumed 0.15% per unit traded its advantage disappeared.
- **Selection of alphas used multiple comparisons.** 21 features were screened with a threshold of about two standard errors.
- **The smaller-network result is not fully explained.** Which of size, pooling and dropout matters was not isolated.
- **KLCI comparison is not like for like.** Stock returns include dividends; the index does not.
- **Static rebuild keeps the existing design's look-ahead** (yearly average of predictions used from 2 January).
- **Workbook verification.** Excel could not be automated on this machine (it stopped responding and may still be open on a dialog). The static rebuild's numbers were confirmed by recomputing the workbook's formulas in Python, which reproduces the existing workbook's Summary to rounding error. The daily workbook's formulas were evaluated with the Python `formulas` engine: about 454,000 cells, no errors, with the Summary and all 81 grid results matching an independent calculation to rounding. Both files are set to calculate when opened in Excel.
- **The explainer report was not previewed** before publishing and shows single-run numbers.

---

## 8. State of the repository

- **Branch:** `alpha101-momentum-reversal-features`, pushed to `origin` (`szeying26/fyp`). It is not merged into `main`. Pull request link: <https://github.com/szeying26/fyp/pull/new/alpha101-momentum-reversal-features>
- **Committed and pushed (commit `7cfab2b`):** `alpha101.py`, `4b.alpha_features.py`, `7.pooled_cnn_bilstm_model.py`, `8.plot_pooled_results.py`, and the changes to `1.raw_data.py`, `5.feature_engineering.py`, `6.cnn_bilstm_model.py`.
- **Committed and pushed afterwards:** this `README.md`, the `optimization/` folder and the two new workbooks.
- **Also committed:** the generated files `DATASET/`, `OUTPUT/` and `malaysia_stocks.csv`, so results can be inspected without re-running the pipeline.

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
