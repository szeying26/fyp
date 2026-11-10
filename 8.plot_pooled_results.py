"""
Step 8 - Plots for the pooled tiny CNN-BiLSTM (output of step 7).

All figures use the 2025 test year only.

  1. summary_by_stock.png        correlation and error vs. "predict zero", per stock
  2. predicted_vs_actual_scatter.png   predicted vs. actual return, one panel per stock
  3. actual_by_prediction_bucket.png   average actual return when the model
                                       predicted low ... high
  4. timeseries/<stock>.png      actual and predicted returns over time

The two figure types from plotting.py are also produced for this model, in
the same style as that script:

  5. predicted_vs_actual_plots/<stock>_predicted_vs_actual.png
                                 actual and predicted returns on one axis
  6. figure_4_2_correlation_heatmap.png
                                 correlation matrix of the 12 stocks (train)

Daily returns move ~10x more than the model's predictions, so the time-series
figure draws them in two stacked panels with their own scales instead of on
one axis, where the prediction would look like a flat line.
"""

import os
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# =========================
# File paths
# =========================
MODEL_OUTPUT_FOLDER = "DATASET/model_output_pooled"
TRAIN_RETURNS_FILEPATH = "DATASET/train_log_returns.csv"
OUTPUT_FOLDER = "OUTPUT/pooled_model_plots"

STOCK_NAMES = {
    "1023.KL": "CIMB", "1155.KL": "Maybank", "1295.KL": "Public Bank",
    "4863.KL": "TM", "5183.KL": "PChem", "5211.KL": "Sunway",
    "5225.KL": "IHH Healthcare", "5347.KL": "Tenaga", "5819.KL": "Hong Leong Bank",
    "6012.KL": "Maxis", "6888.KL": "Axiata", "8869.KL": "Press Metal",
}

# =========================
# Style
# =========================
ACTUAL_COLOR = "#8a929d"     # neutral: what really happened
MODEL_COLOR = "#2a78d6"      # blue: the model
WORSE_COLOR = "#eb6834"      # orange: worse than the baseline
INK = "#101418"
INK_SOFT = "#4a525c"
GRID = "#dde1e7"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": GRID, "axes.labelcolor": INK_SOFT, "axes.titlecolor": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def label(stock):
    return STOCK_NAMES.get(stock, stock)


def as_percent(axis, decimals=1):
    axis.set_major_formatter(lambda value, _: f"{value * 100:.{decimals}f}%")


# =========================
# Load predictions
# =========================
def load_predictions():
    """Return {stock: DataFrame(Date, Actual, Predicted)} in pipeline column order."""
    columns = pd.read_csv(TRAIN_RETURNS_FILEPATH, nrows=0).columns
    stocks = [col for col in columns if col != "Date"]

    predictions = {}
    for stock in stocks:
        df = pd.read_csv(os.path.join(MODEL_OUTPUT_FOLDER, f"prediction_{stock}.csv"))
        # Keep the local calendar date; the time-of-day and timezone are not needed for plotting.
        df["Date"] = pd.to_datetime(df["Date"].str.slice(0, 10))
        predictions[stock] = df
    return predictions


def summarize(predictions):
    """Per-stock test metrics. 'error_vs_zero' < 1 means better than predicting 0."""
    rows = []
    for stock, df in predictions.items():
        actual, predicted = df["Actual"].to_numpy(), df["Predicted"].to_numpy()
        moved = actual != 0
        rows.append({
            "Stock": stock,
            "Name": label(stock),
            "correlation": np.corrcoef(actual, predicted)[0, 1],
            "error_vs_zero": np.mean((actual - predicted) ** 2) / np.mean(actual ** 2),
            "direction_hit_rate": np.mean(np.sign(actual[moved]) == np.sign(predicted[moved])),
        })
    return pd.DataFrame(rows)


# =========================
# 1. Summary by stock
# =========================
def plot_summary(summary):
    ordered = summary.sort_values("correlation")
    fig, (ax_corr, ax_err) = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)

    ax_corr.barh(ordered["Name"], ordered["correlation"], color=MODEL_COLOR, height=0.6)
    ax_corr.axvline(0, color=INK_SOFT, linewidth=0.8)
    ax_corr.set_title("Correlation of predicted with actual returns")
    ax_corr.set_xlabel("Correlation (higher is better)")
    for name, value in zip(ordered["Name"], ordered["correlation"]):
        ax_corr.annotate(f"{value:.3f}", (max(value, 0), name), xytext=(4, 0),
                         textcoords="offset points", va="center", fontsize=9, color=INK_SOFT)

    change = (ordered["error_vs_zero"] - 1) * 100
    colors = [MODEL_COLOR if value < 0 else WORSE_COLOR for value in change]
    ax_err.barh(ordered["Name"], change, color=colors, height=0.6)
    ax_err.axvline(0, color=INK_SOFT, linewidth=0.8)
    ax_err.set_title('Error compared with predicting "no change"')
    ax_err.set_xlabel("Change in squared error (left of 0 = model is better)")
    ax_err.xaxis.set_major_formatter(lambda value, _: f"{value:+.1f}%")
    for name, value in zip(ordered["Name"], change):
        ax_err.annotate(f"{value:+.1f}%", (value, name), xytext=(4 if value >= 0 else -4, 0),
                        textcoords="offset points", va="center",
                        ha="left" if value >= 0 else "right", fontsize=9, color=INK_SOFT)

    for ax in (ax_corr, ax_err):
        ax.grid(axis="y", visible=False)
        ax.margins(x=0.18)

    fig.suptitle("Pooled tiny CNN-BiLSTM: test results by stock (2025)", fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_FOLDER, "summary_by_stock.png"))
    plt.close(fig)


# =========================
# 2. Predicted vs. actual scatter
# =========================
def plot_scatter(predictions, summary):
    fig, axes = plt.subplots(3, 4, figsize=(14, 9.5))
    correlations = summary.set_index("Stock")["correlation"]

    for ax, (stock, df) in zip(axes.flat, predictions.items()):
        x, y = df["Predicted"].to_numpy(), df["Actual"].to_numpy()
        ax.scatter(x, y, s=10, color=ACTUAL_COLOR, alpha=0.55, linewidths=0)

        # Straight-line fit: an upward slope means higher predictions went
        # with higher actual returns.
        slope, intercept = np.polyfit(x, y, 1)
        line_x = np.array([x.min(), x.max()])
        ax.plot(line_x, slope * line_x + intercept, color=MODEL_COLOR, linewidth=2)

        ax.axhline(0, color=GRID, linewidth=0.8)
        ax.axvline(0, color=GRID, linewidth=0.8)
        ax.set_title(f"{label(stock)}   (correlation {correlations[stock]:.2f})")
        as_percent(ax.xaxis, decimals=2)   # predictions are much smaller than actual moves
        as_percent(ax.yaxis)
        ax.tick_params(labelsize=8)
        ax.locator_params(axis="x", nbins=4)

    fig.supxlabel("Predicted next-day return", color=INK_SOFT)
    fig.supylabel("Actual next-day return", color=INK_SOFT)
    fig.suptitle(
        "Predicted vs. actual daily returns, 2025 (each dot is one day; blue line = trend)",
        fontweight="bold", color=INK,
    )
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_FOLDER, "predicted_vs_actual_scatter.png"))
    plt.close(fig)


# =========================
# 3. Actual return by prediction bucket
# =========================
def plot_buckets(predictions, n_buckets=5):
    """
    Sort every stock's test days by the model's prediction, split them into
    equal-sized buckets (lowest to highest prediction) and average the actual
    return in each. If the model has skill, the bars rise from left to right.
    """
    frames = []
    for stock, df in predictions.items():
        ranked = df["Predicted"].rank(method="first")
        bucket = pd.qcut(ranked, n_buckets, labels=False) + 1
        frames.append(pd.DataFrame({"bucket": bucket, "Actual": df["Actual"]}))
    pooled = pd.concat(frames)

    grouped = pooled.groupby("bucket")["Actual"]
    mean = grouped.mean()
    standard_error = grouped.std() / np.sqrt(grouped.count())

    labels = ["Lowest\npredictions", "Low", "Middle", "High", "Highest\npredictions"]
    if n_buckets != 5:
        labels = [str(i) for i in mean.index]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.bar(labels, mean.values, color=MODEL_COLOR, width=0.6)
    ax.errorbar(labels, mean.values, yerr=standard_error.values, fmt="none",
                ecolor=INK_SOFT, elinewidth=1.2, capsize=4)
    ax.axhline(0, color=INK_SOFT, linewidth=0.8)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value * 100:+.2f}%")
    ax.set_ylabel("Average actual next-day return")
    ax.set_title("What actually happened, grouped by what the model predicted (2025)")
    ax.grid(axis="x", visible=False)

    offset = 0.15 * np.abs(mean.values).max()
    for x, (value, error) in enumerate(zip(mean.values, standard_error.values)):
        y = value + error + offset * 0.3 if value >= 0 else value - error - offset * 0.3
        ax.annotate(f"{value * 100:+.2f}%", (x, y), ha="center",
                    va="bottom" if value >= 0 else "top", fontsize=9, color=INK_SOFT)
    ax.margins(y=0.2)

    fig.text(0.01, -0.03,
             f"All 12 stocks pooled, {len(pooled):,} stock-days, {len(pooled) // n_buckets} per group. "
             "Thin lines show ±1 standard error.",
             fontsize=8.5, color=INK_SOFT)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_FOLDER, "actual_by_prediction_bucket.png"))
    plt.close(fig)


# =========================
# 4. Time series per stock
# =========================
def plot_timeseries(predictions, summary):
    folder = os.path.join(OUTPUT_FOLDER, "timeseries")
    os.makedirs(folder, exist_ok=True)
    correlations = summary.set_index("Stock")["correlation"]

    for stock, df in predictions.items():
        fig, (ax_actual, ax_pred) = plt.subplots(
            2, 1, figsize=(13, 6.5), sharex=True, gridspec_kw={"height_ratios": [1, 1]}
        )

        ax_actual.plot(df["Date"], df["Actual"], color=ACTUAL_COLOR, linewidth=1.2)
        ax_actual.axhline(0, color=INK_SOFT, linewidth=0.6)
        ax_actual.set_title("Actual daily log return", loc="left")
        as_percent(ax_actual.yaxis)

        ax_pred.plot(df["Date"], df["Predicted"], color=MODEL_COLOR, linewidth=1.2)
        ax_pred.axhline(0, color=INK_SOFT, linewidth=0.6)
        ax_pred.set_title("Predicted daily log return (note the smaller scale)", loc="left")
        as_percent(ax_pred.yaxis, decimals=2)
        ax_pred.xaxis.set_major_locator(mdates.MonthLocator())
        ax_pred.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax_pred.get_xticklabels(), rotation=30, ha="right")

        fig.suptitle(
            f"{label(stock)} ({stock}): actual vs. predicted returns, 2025   "
            f"(correlation {correlations[stock]:.2f})",
            fontweight="bold", color=INK,
        )
        fig.tight_layout()
        fig.savefig(os.path.join(folder, f"{stock}_actual_vs_predicted.png"))
        plt.close(fig)


# =========================
# 5. Predicted vs. actual on one axis (same figure as plotting.py)
# =========================
def plot_overlay(predictions):
    folder = os.path.join(OUTPUT_FOLDER, "predicted_vs_actual_plots")
    os.makedirs(folder, exist_ok=True)

    with plt.style.context("default"):
        for stock, df in predictions.items():
            plt.figure(figsize=(14, 6))
            plt.plot(df["Date"], df["Actual"], label="Actual Log Return", linewidth=1.5)
            plt.plot(df["Date"], df["Predicted"], label="Predicted Log Return", linewidth=1.5)

            plt.title(f"Predicted versus Actual Daily Log Returns ({stock})")
            plt.xlabel("Date")
            plt.ylabel("Daily Log Return")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            plt.savefig(os.path.join(folder, f"{stock}_predicted_vs_actual.png"), dpi=300)
            plt.close()


# =========================
# 6. Correlation heatmap of the 12 stocks (same figure as plotting.py)
# =========================
def plot_correlation_heatmap():
    train = pd.read_csv(TRAIN_RETURNS_FILEPATH)
    corr = train.drop(columns=["Date"]).corr()

    with plt.style.context("default"):
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", square=True,
                    cbar_kws={"label": "Correlation"})
        plt.title("Correlation Matrix of the 12 Stocks")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_FOLDER, "figure_4_2_correlation_heatmap.png"), dpi=300)
        plt.close()


# =========================
# Main
# =========================
def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    predictions = load_predictions()
    summary = summarize(predictions)

    plot_summary(summary)
    plot_scatter(predictions, summary)
    plot_buckets(predictions)
    plot_timeseries(predictions, summary)
    plot_overlay(predictions)
    plot_correlation_heatmap()

    summary.to_csv(os.path.join(OUTPUT_FOLDER, "summary_by_stock.csv"), index=False)

    print(summary.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(
        f"\nAverage: correlation {summary['correlation'].mean():.3f}, "
        f"error vs. zero {summary['error_vs_zero'].mean():.3f}, "
        f"direction hit rate {summary['direction_hit_rate'].mean():.1%}, "
        f"{(summary['error_vs_zero'] < 1).sum()} of {len(summary)} stocks beat predicting zero"
    )
    print(f"\nSaved plots to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
