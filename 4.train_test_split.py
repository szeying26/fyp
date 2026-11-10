import pandas as pd


# File paths for the input log returns data and the split outputs.
INPUT_FILEPATH = "DATASET/log_returns.csv"
TRAIN_OUTPUT_FILEPATH = "DATASET/train_log_returns.csv"
TEST_OUTPUT_FILEPATH = "DATASET/test_log_returns.csv"


def load_log_returns(filepath=INPUT_FILEPATH):
    """Load the log return dataset and prepare Date for time-based splitting."""
    # Read the CSV file produced by return_calculation.py.
    df = pd.read_csv(filepath)

    # Convert Date into datetime format so rows can be filtered by date range.
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Remove rows with invalid dates, then sort the dataset in time order.
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df


def split_train_test(df):
    """Split log returns into train data for 2022-2024 and test data for 2025."""
    # Define the train period requested by the user.
    train_start = pd.Timestamp("2022-01-01", tz="Asia/Kuala_Lumpur")
    train_end = pd.Timestamp("2024-12-31 23:59:59", tz="Asia/Kuala_Lumpur")

    # Define the test period requested by the user.
    test_start = pd.Timestamp("2025-01-01", tz="Asia/Kuala_Lumpur")
    test_end = pd.Timestamp("2025-12-31 23:59:59", tz="Asia/Kuala_Lumpur")

    # Keep only rows whose dates fall inside the train period.
    train_df = df[(df["Date"] >= train_start) & (df["Date"] <= train_end)].copy()

    # Keep only rows whose dates fall inside the test period.
    test_df = df[(df["Date"] >= test_start) & (df["Date"] <= test_end)].copy()

    return train_df, test_df


def save_splits(train_df, test_df):
    """Save the train and test datasets into separate CSV files."""
    # Write the training set to disk.
    train_df.to_csv(TRAIN_OUTPUT_FILEPATH, index=False)

    # Write the testing set to disk.
    test_df.to_csv(TEST_OUTPUT_FILEPATH, index=False)


def main():
    """Load log returns, split them by date, and save the results."""
    # Load the full log return dataset.
    df = load_log_returns()

    # Split the dataset into training and testing periods.
    train_df, test_df = split_train_test(df)

    # Save both datasets for later modeling steps.
    save_splits(train_df, test_df)

    # Show a short summary so the user can confirm the split worked.
    print("Train period: 2022-01-01 to 2024-12-31")
    print("Test period: 2025-01-01 to 2025-12-31")
    print(f"Train dataset shape: {train_df.shape}")
    print(f"Test dataset shape: {test_df.shape}")
    print(f"Saved train data to: {TRAIN_OUTPUT_FILEPATH}")
    print(f"Saved test data to: {TEST_OUTPUT_FILEPATH}")


if __name__ == "__main__":
    main()
