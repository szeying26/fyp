import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CLEANED_FILEPATH = "DATASET/cleaned_malaysia_stocks.csv"
LOG_RETURN_FILEPATH = "DATASET/log_returns.csv"
LOG_RETURN_PLOT = "DATASET/log_returns_plot.png"


def get_cleaned_prices(cleaned_filepath=CLEANED_FILEPATH):
    """Load cleaned adjusted close prices from the preprocessing output."""
    df = pd.read_csv(cleaned_filepath)

    # Convert the Date column into datetime so the rows can be ordered by time.
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    # Treat every column except Date as a stock price column.
    price_columns = [column for column in df.columns if column != "Date"]
    df[price_columns] = df[price_columns].apply(pd.to_numeric, errors="coerce")

    # Set Date as the index so return calculations use time series format.
    price_df = df[["Date"] + price_columns].copy()
    return price_df.set_index("Date")


def calculate_log_returns(price_df):
    """Calculate log returns: ln(Pt / Pt-1)."""
    # Compute continuously compounded returns using the natural log ratio.
    return np.log(price_df / price_df.shift(1)).dropna()


def plot_returns(returns_df, title, output_filepath):
    """Plot return series for all stocks and save the figure."""
    plt.figure(figsize=(14, 7))

    # Draw one line per stock so their return movements can be compared.
    for column in returns_df.columns:
        plt.plot(returns_df.index, returns_df[column], label=column, linewidth=1)

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Return")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right", ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(output_filepath, dpi=300)
    plt.close()


def main():
    """Generate log return calculations and plots from cleaned adjusted close prices."""
    # Load the cleaned adjusted close prices prepared earlier.
    print("Loading cleaned prices...")
    price_df = get_cleaned_prices()

    # Calculate log returns for the cleaned price data.
    print("Calculating log returns...")
    log_returns = calculate_log_returns(price_df)

    # Save the calculated returns for later analysis or modeling.
    print("Saving log returns...")
    log_returns.to_csv(LOG_RETURN_FILEPATH)

    # Create and save the graph for log returns.
    print("Creating log return plot...")
    plot_returns(
        log_returns,
        "Log Returns of Cleaned Adjusted Close Prices",
        LOG_RETURN_PLOT,
    )

    print("Log return formula: ln(Pt / Pt-1)")
    print("\nCleaned adjusted close prices preview:")
    print(price_df.head())
    print("\nLog returns preview:")
    print(log_returns.head())
    print(f"\nUsed cleaned prices from: {CLEANED_FILEPATH}")
    print(f"Saved log returns to: {LOG_RETURN_FILEPATH}")
    print(f"Saved log return plot to: {LOG_RETURN_PLOT}")
    print(f"Dataset shape: {log_returns.shape}")

def desc_stat():
    """Calculate and print descriptive statistics for the log returns."""
    log_returns = pd.read_csv(LOG_RETURN_FILEPATH, index_col=0, parse_dates=True)
    print("\nDescriptive statistics for log returns:")
    print(log_returns.describe())
    "Save the output into a csv file"
    log_returns.describe().to_csv("DATASET/descriptive_statistics.csv")



if __name__ == "__main__":
    #main()
    desc_stat()
