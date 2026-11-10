import json
import os
import numpy as np
import pandas as pd

# =========================
# File paths
# =========================
TRAIN_INPUT_FILEPATH = "DATASET/train_log_returns.csv"
TEST_INPUT_FILEPATH = "DATASET/test_log_returns.csv"
OUTPUT_FOLDER = "DATASET/windowed_data"

# Alpha101 momentum/reversal features produced by 4b.alpha_features.py.
# Set USE_ALPHA_FEATURES = False to rebuild the original returns-only inputs.
USE_ALPHA_FEATURES = True
ALPHA_FEATURES_FILEPATH = "DATASET/alpha_features/alpha_features.csv"
SELECTED_ALPHAS_FILEPATH = "DATASET/alpha_features/selected_alpha_features.json"

# Rolling z-score of the INPUT returns: each day's return is expressed relative
# to the mean and standard deviation of that stock's previous ZSCORE_WINDOW
# days. This keeps the inputs on the same scale when volatility changes
# between the train and test periods. The prediction target stays a plain log
# return. Set USE_ROLLING_ZSCORE = False for the original raw-return inputs.
USE_ROLLING_ZSCORE = True
ZSCORE_WINDOW = 60
OHLCV_FILEPATH = "DATASET/ohlcv_malaysia_stocks.csv"

WINDOW_SIZE = 20


# =========================
# 1. Load dataset
# =========================
def load_dataset(filepath):
    """
    Load a split log return dataset and prepare the Date column.
    """
    df = pd.read_csv(filepath)

    # Convert Date to datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Remove invalid dates and sort chronologically
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    return df


# =========================
# 1a. Rolling z-score of returns
# =========================
def load_rolling_zscore_returns(stock_columns, window=ZSCORE_WINDOW):
    """
    Rolling z-score of every stock's daily log return.

        z_t = (r_t - mean(r_{t-window} .. r_{t-1})) / std(r_{t-window} .. r_{t-1})

    The mean and std come from the PREVIOUS `window` days only, so z_t never
    uses information from day t+1 onwards. Returns are rebuilt from the OHLCV
    file because it starts before 2022, which gives the first training days
    a full window of history.

    Returns:
        DataFrame with a Date column and one z-score column per stock.
    """
    ohlcv = pd.read_csv(OHLCV_FILEPATH, usecols=["Date", "Ticker", "Adj Close"])
    ohlcv["Date"] = pd.to_datetime(ohlcv["Date"], errors="coerce")

    prices = ohlcv.pivot(index="Date", columns="Ticker", values="Adj Close").sort_index().dropna()
    log_returns = np.log(prices / prices.shift(1)).dropna()[stock_columns]

    past = log_returns.shift(1).rolling(window)
    zscores = (log_returns - past.mean()) / past.std()

    return zscores.dropna().reset_index()


def replace_with_zscores(df, zscore_df):
    """
    Split one dataset into model inputs (z-scored returns) and targets (the
    original log returns), both aligned on the dataset's dates.
    """
    stock_columns = [col for col in df.columns if col != "Date"]
    input_df = df[["Date"]].merge(zscore_df, on="Date", how="left", validate="one_to_one")

    if input_df[stock_columns].isna().any().any():
        raise ValueError(
            "Rolling z-scores are missing for some dates. Re-run 1.raw_data.py "
            "so the OHLCV file covers the warm-up period."
        )

    return input_df, df


# =========================
# 1b. Alpha features
# =========================
def load_alpha_features():
    """
    Load the alphas that passed the correlation check in 4b.alpha_features.py.

    Returns:
        alpha_df         long table: Date, Ticker, <selected alpha columns>
        selected_alphas  list of selected alpha column names
    """
    with open(SELECTED_ALPHAS_FILEPATH) as f:
        selected_alphas = json.load(f)["selected_features"]

    alpha_df = pd.read_csv(ALPHA_FEATURES_FILEPATH, usecols=["Date", "Ticker"] + selected_alphas)
    alpha_df = alpha_df[["Date", "Ticker"] + selected_alphas]   # keep the selected order
    alpha_df["Date"] = pd.to_datetime(alpha_df["Date"], errors="coerce")

    return alpha_df, selected_alphas


def add_alpha_features(df, alpha_df, target_column):
    """
    Append the target stock's own alpha values as extra feature columns.

    Each alpha on date t only uses data up to the close of date t, the same
    information set as the date-t log returns, so the windows stay causal.
    """
    stock_alphas = alpha_df[alpha_df["Ticker"] == target_column].drop(columns="Ticker")
    merged = df.merge(stock_alphas, on="Date", how="left", validate="one_to_one")

    alpha_columns = [col for col in stock_alphas.columns if col != "Date"]
    if merged[alpha_columns].isna().any().any():
        raise ValueError(
            f"Alpha features are missing for some dates of {target_column}. "
            f"Re-run 4b.alpha_features.py."
        )

    return merged


# =========================
# 2. Create sliding windows for one target stock
# =========================
def create_sliding_windows(df, target_column, window_size=20, target_df=None):
    """
    Create sliding windows for one target stock.

    X -> past 'window_size' days of all stock returns (plus any extra
         feature columns in df, e.g. the target stock's alpha features)
    y -> next-day return of one selected stock, taken from target_df when
         given (same dates as df), otherwise from df itself

    Returns:
        X_windows     shape: (samples, timesteps, features)
        y_targets     shape: (samples,)
        target_dates  shape: (samples,)
        stock_columns list of feature columns
    """
    stock_columns = [col for col in df.columns if col != "Date"]

    if target_column not in stock_columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")

    working_df = df[["Date"] + stock_columns].copy()
    working_df[stock_columns] = working_df[stock_columns].apply(pd.to_numeric, errors="coerce")

    # Keep the target next to the inputs so both lose the same rows below.
    target_source = df if target_df is None else target_df
    if not target_source["Date"].equals(df["Date"]):
        raise ValueError("target_df must have the same dates as df.")
    working_df["__target__"] = pd.to_numeric(target_source[target_column], errors="coerce").to_numpy()

    working_df = working_df.dropna().reset_index(drop=True)

    values = working_df[stock_columns].to_numpy()
    targets = working_df["__target__"].to_numpy()
    dates = working_df["Date"].to_numpy()

    X_windows = []
    y_targets = []
    target_dates = []

    for i in range(window_size, len(values)):
        X_windows.append(values[i - window_size:i, :])   # all stock inputs
        y_targets.append(targets[i])                     # one stock target
        target_dates.append(dates[i])

    return (
        np.array(X_windows),
        np.array(y_targets),
        np.array(target_dates),
        stock_columns
    )


# =========================
# 3. Save arrays for one stock
# =========================
def save_arrays(X, y, dates, target_column, dataset_type, output_folder):
    """
    Save X, y, and dates for one stock.
    """
    np.save(os.path.join(output_folder, f"X_{dataset_type}_{target_column}.npy"), X)
    np.save(os.path.join(output_folder, f"y_{dataset_type}_{target_column}.npy"), y)

    pd.DataFrame({"Date": pd.to_datetime(dates)}).to_csv(
        os.path.join(output_folder, f"dates_{dataset_type}_{target_column}.csv"),
        index=False
    )


# =========================
# 4. Main loop for all stocks
# =========================
def main():
    # Create output folder if it does not exist
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Load train and test data once
    train_df = load_dataset(TRAIN_INPUT_FILEPATH)
    test_df = load_dataset(TEST_INPUT_FILEPATH)

    # Get all stock columns automatically
    stock_columns = [col for col in train_df.columns if col != "Date"]

    print("Stocks found:")
    print(stock_columns)
    print(f"\nWindow size: {WINDOW_SIZE} days")

    # Inputs: rolling z-scored returns. Targets: the original log returns.
    train_target_df, test_target_df = train_df, test_df
    if USE_ROLLING_ZSCORE:
        zscore_df = load_rolling_zscore_returns(stock_columns)
        train_df, train_target_df = replace_with_zscores(train_df, zscore_df)
        test_df, test_target_df = replace_with_zscores(test_df, zscore_df)
        print(f"Inputs: rolling z-score of returns ({ZSCORE_WINDOW}-day window)")

    if USE_ALPHA_FEATURES:
        alpha_df, selected_alphas = load_alpha_features()
        print(f"\nAlpha features per stock ({len(selected_alphas)}):")
        print(selected_alphas)

    # Loop through all stocks
    for stock in stock_columns:
        print(f"\nProcessing target stock: {stock}")

        if USE_ALPHA_FEATURES:
            stock_train_df = add_alpha_features(train_df, alpha_df, stock)
            stock_test_df = add_alpha_features(test_df, alpha_df, stock)
        else:
            stock_train_df, stock_test_df = train_df, test_df

        # Create train windows
        X_train, y_train, train_dates, feature_columns = create_sliding_windows(
            stock_train_df,
            target_column=stock,
            window_size=WINDOW_SIZE,
            target_df=train_target_df
        )

        # Create test windows
        X_test, y_test, test_dates, _ = create_sliding_windows(
            stock_test_df,
            target_column=stock,
            window_size=WINDOW_SIZE,
            target_df=test_target_df
        )

        # Save outputs
        save_arrays(X_train, y_train, train_dates, stock, "train", OUTPUT_FOLDER)
        save_arrays(X_test, y_test, test_dates, stock, "test", OUTPUT_FOLDER)

        # Print quick check
        print(f"X_train shape: {X_train.shape}")
        print(f"y_train shape: {y_train.shape}")
        print(f"X_test shape: {X_test.shape}")
        print(f"y_test shape: {y_test.shape}")

    print("\nAll stocks completed successfully.")
    print(f"Saved all windowed files in: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()