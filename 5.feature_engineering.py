import os
import numpy as np
import pandas as pd

# =========================
# File paths
# =========================
TRAIN_INPUT_FILEPATH = "DATASET/train_log_returns.csv"
TEST_INPUT_FILEPATH = "DATASET/test_log_returns.csv"
OUTPUT_FOLDER = "DATASET/windowed_data"

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
# 2. Create sliding windows for one target stock
# =========================
def create_sliding_windows(df, target_column, window_size=20):
    """
    Create sliding windows for one target stock.

    X -> past 'window_size' days of all stock returns
    y -> next-day return of one selected stock

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
    working_df = working_df.dropna().reset_index(drop=True)

    values = working_df[stock_columns].to_numpy()
    dates = working_df["Date"].to_numpy()

    target_idx = stock_columns.index(target_column)

    X_windows = []
    y_targets = []
    target_dates = []

    for i in range(window_size, len(values)):
        X_windows.append(values[i - window_size:i, :])   # all stock inputs
        y_targets.append(values[i, target_idx])          # one stock target
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

    # Loop through all stocks
    for stock in stock_columns:
        print(f"\nProcessing target stock: {stock}")

        # Create train windows
        X_train, y_train, train_dates, feature_columns = create_sliding_windows(
            train_df,
            target_column=stock,
            window_size=WINDOW_SIZE
        )

        # Create test windows
        X_test, y_test, test_dates, _ = create_sliding_windows(
            test_df,
            target_column=stock,
            window_size=WINDOW_SIZE
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