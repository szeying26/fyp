import os
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# FILE PATHS
# =====================================================

ACTUAL_FILE = "DATASET/test_log_returns.csv"
PREDICTED_FILE = "DATASET/model_output/predicted_returns_all_stocks.csv"

OUTPUT_FOLDER = "OUTPUT/predicted_vs_actual_plots"

# =====================================================
# CREATE OUTPUT FOLDER
# =====================================================

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =====================================================
# LOAD DATA
# =====================================================

actual_df = pd.read_csv(
    ACTUAL_FILE,
    index_col=0,
    parse_dates=True
)

predicted_df = pd.read_csv(
    PREDICTED_FILE,
    index_col=0,
    parse_dates=True
)

# =====================================================
# LOOP THROUGH ALL STOCKS
# =====================================================

for stock in actual_df.columns:

    if stock not in predicted_df.columns:
        print(f"Skipping {stock} (not found in predicted file)")
        continue

    comparison_df = pd.DataFrame({
        "Actual": actual_df[stock],
        "Predicted": predicted_df[stock]
    }).dropna()

    if len(comparison_df) == 0:
        print(f"No data available for {stock}")
        continue

    plt.figure(figsize=(14, 6))

    plt.plot(
        comparison_df.index,
        comparison_df["Actual"],
        label="Actual Log Return",
        linewidth=1.5
    )

    plt.plot(
        comparison_df.index,
        comparison_df["Predicted"],
        label="Predicted Log Return",
        linewidth=1.5
    )

    plt.title(
        f"Predicted versus Actual Daily Log Returns ({stock})"
    )

    plt.xlabel("Date")
    plt.ylabel("Daily Log Return")

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    save_path = os.path.join(
        OUTPUT_FOLDER,
        f"{stock}_predicted_vs_actual.png"
    )

    plt.savefig(save_path, dpi=300)

    plt.close()

    print(f"Saved: {save_path}")

print("\nAll plots generated successfully.")



import seaborn as sns

train = pd.read_csv(f"DATASET/train_log_returns.csv")
corr = train.drop(columns=["Date"]).corr()
plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", square=True,
            cbar_kws={"label": "Correlation"})
plt.title("Correlation Matrix of the 12 Stocks")
plt.tight_layout()
plt.savefig(f"DATASET/figure_4_2_correlation_heatmap.png", dpi=300)
plt.close()

print("\nFigures saved to:", "DATASET/")