"""
Step 4b - Alpha101 momentum/reversal features + correlation check.

Run after 4.train_test_split.py and before 5.feature_engineering.py.

1. Compute the momentum/reversal alphas (alpha101.py) from the OHLCV panel.
2. Correlation check, using the TRAIN period only so the test year stays
   untouched by feature selection:
     a. relevance  - correlation of each alpha on day t with the stock's
                     log return on day t+1 (the "information coefficient", IC)
     b. added value - the same correlation after removing what the stock's
                     own day-t return already explains (partial IC). The
                     model already receives that return, so an alpha only
                     helps if it predicts something beyond it.
     c. redundancy - correlation between the alphas themselves, and with the
                     stock's own day-t return
3. Keep alphas that add value and are not redundant, and save them for
   5.feature_engineering.py.

The test-period IC is reported next to the train IC as an out-of-sample
sanity check. It is never used to choose features.
"""

import json
import os

import numpy as np
import pandas as pd

from alpha101 import compute_momentum_reversal_alphas

# =========================
# File paths
# =========================
OHLCV_FILEPATH = "DATASET/ohlcv_malaysia_stocks.csv"
LOG_RETURN_FILEPATH = "DATASET/log_returns.csv"
TRAIN_FILEPATH = "DATASET/train_log_returns.csv"
TEST_FILEPATH = "DATASET/test_log_returns.csv"

OUTPUT_FOLDER = "DATASET/alpha_features"
FEATURES_FILEPATH = os.path.join(OUTPUT_FOLDER, "alpha_features.csv")
IC_REPORT_FILEPATH = os.path.join(OUTPUT_FOLDER, "alpha_ic_report.csv")
CORRELATION_FILEPATH = os.path.join(OUTPUT_FOLDER, "alpha_feature_correlation.csv")
SELECTED_FILEPATH = os.path.join(OUTPUT_FOLDER, "selected_alpha_features.json")

# =========================
# Selection thresholds
# =========================
MIN_COVERAGE = 0.95      # share of non-missing train rows required
MIN_ABS_IC = 0.02        # on the partial IC; ~2 standard errors for ~8,800 pooled train rows
MAX_FEATURE_CORR = 0.70  # two features above this are treated as duplicates
WINSOR_QUANTILES = (0.01, 0.99)

BASE_FEATURE = "ret_1d"  # the stock's own day-t log return (already a model input)


# =========================
# 1. Load data
# =========================
def load_dates(filepath):
    df = pd.read_csv(filepath, usecols=["Date"])
    return pd.DatetimeIndex(pd.to_datetime(df["Date"]))


def load_price_panels(filepath=OHLCV_FILEPATH):
    """Return adjusted open/high/low/close and volume as dates x tickers frames."""
    df = pd.read_csv(filepath)
    df["Date"] = pd.to_datetime(df["Date"])

    panels = {
        column: df.pivot(index="Date", columns="Ticker", values=column).sort_index()
        for column in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    }

    # Same rule as 2.data_preprocess.py: drop dates where any stock is missing.
    complete = panels["Adj Close"].notna().all(axis=1) & panels["Close"].notna().all(axis=1)
    panels = {name: frame[complete] for name, frame in panels.items()}

    # Put O/H/L on the same dividend/split-adjusted basis as Adj Close so that
    # ex-dividend days do not look like price gaps.
    factor = panels["Adj Close"] / panels["Close"]
    return (
        panels["Open"] * factor,
        panels["High"] * factor,
        panels["Low"] * factor,
        panels["Adj Close"],
        panels["Volume"],
    )


# =========================
# 2. Clean features (train statistics only)
# =========================
def clean_feature(frame, train_dates):
    """
    Winsorize each stock's series at its train 1%/99% quantiles and fill the
    few remaining gaps (forward fill, then the train median). Only train-period
    statistics are used, so nothing leaks from the test year.
    """
    train = frame.loc[frame.index.isin(train_dates)]
    lower = train.quantile(WINSOR_QUANTILES[0])
    upper = train.quantile(WINSOR_QUANTILES[1])
    cleaned = frame.clip(lower=lower, upper=upper, axis=1)
    return cleaned.ffill().fillna(train.median())


# =========================
# 3. Correlation check
# =========================
def zscore_by_stock(frame, reference):
    """Standardize each stock's column with the mean/std of the reference rows."""
    std = reference.std().replace(0, np.nan)
    # A constant column carries no information; keep it at 0 instead of NaN.
    return ((frame - reference.mean()) / std).fillna(0.0).where(frame.notna())


def residual(y, x):
    """What is left of y after a linear fit on x."""
    slope = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
    return y - slope * x


def information_coefficient(feature, next_return, base, dates):
    """
    Correlation between a feature on day t and the return on day t+1.

    The model is trained per stock, so what matters is the time-series
    relationship inside each stock. Each stock's series is standardized and
    the rows are pooled. Spearman rank correlation is used because it is
    robust to outliers.

    Returns:
        pooled IC,
        partial IC (controlling for the base feature, i.e. the day-t return),
        per-stock ICs,
        number of pooled rows
    """
    in_period = lambda frame: frame.loc[frame.index.isin(dates)]
    f, r, b = in_period(feature), in_period(next_return), in_period(base)

    # A feature that never changes for a stock has no defined correlation.
    per_stock = pd.Series({
        ticker: f[ticker].corr(r[ticker], method="spearman") if f[ticker].nunique() > 1 else np.nan
        for ticker in f.columns
    })

    pooled = pd.DataFrame({
        "f": zscore_by_stock(f, f).stack(),
        "r": zscore_by_stock(r, r).stack(),
        "b": zscore_by_stock(b, b).stack(),
    }).dropna().rank()
    pooled_ic = pooled["f"].corr(pooled["r"])
    # (Undefined for the base feature itself: its residual is all zeros.)
    with np.errstate(invalid="ignore"):
        partial_ic = residual(pooled["f"], pooled["b"]).corr(residual(pooled["r"], pooled["b"]))

    return pooled_ic, partial_ic, per_stock, len(pooled)


def build_ic_report(features, raw_coverage, next_return, train_dates, test_dates):
    base = features[BASE_FEATURE]
    rows = []
    for name, frame in features.items():
        train_ic, train_partial, per_stock, n_obs = information_coefficient(
            frame, next_return, base, train_dates
        )
        test_ic, test_partial, _, _ = information_coefficient(
            frame, next_return, base, test_dates
        )
        if name == BASE_FEATURE:
            train_partial = test_partial = np.nan

        same_sign = int((np.sign(per_stock) == np.sign(train_ic)).sum())
        rows.append({
            "feature": name,
            "coverage": raw_coverage[name],
            "train_ic": train_ic,
            "train_partial_ic": train_partial,
            # Approximate: treats the pooled rows as independent.
            "partial_t_stat": train_partial * np.sqrt(n_obs - 3) / np.sqrt(1 - train_partial ** 2),
            "stocks_same_sign": same_sign,
            "n_stocks": len(per_stock),
            "test_ic": test_ic,
            "test_partial_ic": test_partial,
        })

    report = pd.DataFrame(rows).set_index("feature")
    report["abs_train_ic"] = report["train_partial_ic"].abs()
    return report.sort_values("abs_train_ic", ascending=False, na_position="first")


def feature_correlation_matrix(features, train_dates):
    """Pooled Spearman correlation between features over the train period."""
    stacked = pd.DataFrame({
        name: zscore_by_stock(
            frame.loc[frame.index.isin(train_dates)],
            frame.loc[frame.index.isin(train_dates)],
        ).stack()
        for name, frame in features.items()
    })
    return stacked.corr(method="spearman")


def select_features(report, correlation):
    """
    Greedy selection: walk the alphas from strongest to weakest train partial
    IC and keep one if it adds enough beyond the base return feature and is
    not a near-duplicate of it or of an alpha that was already kept.
    """
    selected = []
    decisions = {}

    for name, row in report.iterrows():
        if name == BASE_FEATURE:
            decisions[name] = "base feature (already in the model)"
            continue
        if row["coverage"] < MIN_COVERAGE:
            decisions[name] = f"dropped: coverage {row['coverage']:.0%} < {MIN_COVERAGE:.0%}"
            continue
        if row["abs_train_ic"] < MIN_ABS_IC:
            decisions[name] = f"dropped: |partial IC| {row['abs_train_ic']:.3f} < {MIN_ABS_IC}"
            continue

        rivals = correlation.loc[name, [BASE_FEATURE] + selected].abs()
        if rivals.max() > MAX_FEATURE_CORR:
            decisions[name] = (
                f"dropped: corr {correlation.loc[name, rivals.idxmax()]:+.2f} with {rivals.idxmax()}"
            )
            continue

        selected.append(name)
        decisions[name] = "KEPT"

    return selected, decisions


# =========================
# 4. Main
# =========================
def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    train_dates = load_dates(TRAIN_FILEPATH)
    test_dates = load_dates(TEST_FILEPATH)

    log_returns = pd.read_csv(LOG_RETURN_FILEPATH)
    log_returns["Date"] = pd.to_datetime(log_returns["Date"])
    log_returns = log_returns.set_index("Date").sort_index()

    # Target for the check: the return of the NEXT trading day.
    next_return = log_returns.shift(-1)
    # The last train day's "next return" belongs to the test year; exclude it.
    next_return.loc[train_dates.max()] = np.nan

    print("Computing momentum/reversal alphas...")
    open_, high, low, close, volume = load_price_panels()
    raw_alphas = compute_momentum_reversal_alphas(open_, high, low, close, volume)

    # Keep the modelling sample only (the warm-up history has done its job).
    sample_dates = log_returns.index
    missing = sample_dates.difference(close.index)
    if len(missing):
        raise ValueError(f"{len(missing)} log-return dates are missing from the OHLCV panel.")

    raw_alphas = {name: frame.loc[sample_dates, log_returns.columns] for name, frame in raw_alphas.items()}
    raw_coverage = {
        name: frame.loc[frame.index.isin(train_dates)].notna().mean().mean()
        for name, frame in raw_alphas.items()
    }
    alphas = {name: clean_feature(frame, train_dates) for name, frame in raw_alphas.items()}

    # Include the existing input (own day-t return) so redundancy with it is checked.
    check_set = {BASE_FEATURE: log_returns, **alphas}
    raw_coverage[BASE_FEATURE] = 1.0

    print("Running correlation check on the train period...")
    report = build_ic_report(check_set, raw_coverage, next_return, train_dates, test_dates)
    correlation = feature_correlation_matrix(check_set, train_dates)
    selected, decisions = select_features(report, correlation)
    report["decision"] = pd.Series(decisions)

    # ---------- save ----------
    long_features = pd.concat(
        {name: frame.stack() for name, frame in alphas.items()}, axis=1
    ).rename_axis(["Date", "Ticker"]).reset_index()
    long_features.to_csv(FEATURES_FILEPATH, index=False)

    report.drop(columns="abs_train_ic").to_csv(IC_REPORT_FILEPATH)
    correlation.to_csv(CORRELATION_FILEPATH)
    with open(SELECTED_FILEPATH, "w") as f:
        json.dump({"selected_features": selected}, f, indent=2)

    # ---------- print ----------
    pd.set_option("display.width", 200)
    print(f"\nTrain rows: {len(train_dates)} days x {log_returns.shape[1]} stocks")
    print("\nIC report (feature on day t vs. return on day t+1):")
    print(report.drop(columns="abs_train_ic").to_string(float_format=lambda v: f"{v:.3f}"))

    if selected:
        print("\nCorrelation between the selected features (train):")
        print(correlation.loc[selected, selected].round(2).to_string())

    print(f"\nSelected {len(selected)} of {len(alphas)} alphas: {selected}")
    print(f"Saved features to:           {FEATURES_FILEPATH}")
    print(f"Saved IC report to:          {IC_REPORT_FILEPATH}")
    print(f"Saved correlation matrix to: {CORRELATION_FILEPATH}")
    print(f"Saved selected list to:      {SELECTED_FILEPATH}")


if __name__ == "__main__":
    main()
