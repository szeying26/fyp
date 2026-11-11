"""
Step 7 - Pooled tiny CNN-BiLSTM: one small model trained on all stocks together.

6.cnn_bilstm_model.py trains a separate 54,321-weight network per stock on
~700 samples each. Here the samples of every stock are stacked, so a single
network learns from ~8,500 samples and the patterns it finds have to hold
across stocks. The network is also much smaller (509 weights) and only looks
at the last INPUT_WINDOW days: in testing, almost all of the predictable
signal sat in the most recent days, and the large network mostly fitted noise.

Neural networks start from random weights, so single runs differ. The model
is trained N_RUNS times with different seeds and the predictions are averaged.

To make samples from different stocks comparable:
  * inputs are standardized per stock (train statistics only),
  * the target stock's own return is added as an explicit first channel
    (in the per-stock arrays it is just one of the 12 return columns, and a
    shared model could not tell which one it is predicting),
  * the target is standardized per stock, and predictions are converted
    back to log returns before metrics are computed and saved.

Uses the windowed arrays from 5.feature_engineering.py and writes the same
output files as step 6, into DATASET/model_output_pooled.
"""

import os
import random
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, Conv1D, Bidirectional, LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping


# =========================
# Configuration
# =========================
WINDOWED_FOLDER = "DATASET/windowed_data"
TRAIN_RETURNS_FILEPATH = "DATASET/train_log_returns.csv"
OUTPUT_FOLDER = "DATASET/model_output_pooled"

EPOCHS = 30
BATCH_SIZE = 64
VALIDATION_FRACTION = 0.1   # most recent share of each stock's train windows
RANDOM_SEED = 42
N_RUNS = 5                  # seeds RANDOM_SEED, RANDOM_SEED + 1, ... are averaged
INPUT_WINDOW = 5            # use only the last 5 days of each 20-day window


def set_seed(seed=RANDOM_SEED):
    np.random.seed(seed)
    random.seed(seed)
    tf.random.set_seed(seed)


# =========================
# Model: tiny CNN-BiLSTM (477 weights for 22 input features)
# =========================
def build_cnn_bilstm_model(input_shape):
    model = Sequential()
    model.add(Input(shape=input_shape))
    # CNN: 4 filters looking at 2 days at a time
    model.add(Conv1D(filters=4, kernel_size=2, activation='relu'))
    # BiLSTM: 4 units forwards + 4 units backwards
    model.add(Bidirectional(LSTM(4, return_sequences=False)))
    model.add(Dense(1, activation='linear'))
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model


# =========================
# Data
# =========================
def get_stock_names():
    """Stock names in the same column order used to build the windows."""
    columns = pd.read_csv(TRAIN_RETURNS_FILEPATH, nrows=0).columns
    return [col for col in columns if col != "Date"]


def prepare_stock(stock_name, own_return_idx):
    """
    Load one stock's windows and put them on a stock-independent scale.

    Returns a dict with scaled X/y for train and test, the raw test target,
    the test dates and the fitted target scaler.
    """
    X_train = np.load(os.path.join(WINDOWED_FOLDER, f"X_train_{stock_name}.npy"))
    y_train = np.load(os.path.join(WINDOWED_FOLDER, f"y_train_{stock_name}.npy"))
    X_test = np.load(os.path.join(WINDOWED_FOLDER, f"X_test_{stock_name}.npy"))
    y_test = np.load(os.path.join(WINDOWED_FOLDER, f"y_test_{stock_name}.npy"))
    dates_test = pd.read_csv(os.path.join(WINDOWED_FOLDER, f"dates_test_{stock_name}.csv"))

    # Standardize features with this stock's training statistics.
    n_features = X_train.shape[2]
    x_scaler = StandardScaler().fit(X_train.reshape(-1, n_features))
    X_train = x_scaler.transform(X_train.reshape(-1, n_features)).reshape(X_train.shape)
    X_test = x_scaler.transform(X_test.reshape(-1, n_features)).reshape(X_test.shape)

    # Keep only the most recent days of each window.
    X_train = X_train[:, -INPUT_WINDOW:, :]
    X_test = X_test[:, -INPUT_WINDOW:, :]

    # Put the target stock's own return in channel 0.
    X_train = np.concatenate([X_train[:, :, [own_return_idx]], X_train], axis=2)
    X_test = np.concatenate([X_test[:, :, [own_return_idx]], X_test], axis=2)

    # Standardize the target with this stock's training statistics.
    y_scaler = StandardScaler().fit(y_train.reshape(-1, 1))
    y_train_scaled = y_scaler.transform(y_train.reshape(-1, 1)).flatten()

    return {
        "X_train": X_train, "y_train": y_train_scaled,
        "X_test": X_test, "y_test": y_test,
        "dates_test": pd.to_datetime(dates_test["Date"]),
        "y_scaler": y_scaler,
    }


def pool_training_data(stock_data):
    """
    Stack all stocks. The most recent VALIDATION_FRACTION of every stock's
    windows is held out for early stopping, so validation is always later in
    time than the data the model is fitted on.
    """
    X_fit, y_fit, X_val, y_val = [], [], [], []
    for data in stock_data.values():
        n_val = int(len(data["X_train"]) * VALIDATION_FRACTION)
        X_fit.append(data["X_train"][:-n_val])
        y_fit.append(data["y_train"][:-n_val])
        X_val.append(data["X_train"][-n_val:])
        y_val.append(data["y_train"][-n_val:])

    return (
        np.concatenate(X_fit), np.concatenate(y_fit),
        np.concatenate(X_val), np.concatenate(y_val),
    )


# =========================
# Main
# =========================
def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    stock_names = get_stock_names()
    print("Stocks pooled:")
    print(stock_names)

    stock_data = {
        stock: prepare_stock(stock, own_return_idx=idx)
        for idx, stock in enumerate(stock_names)
    }

    X_fit, y_fit, X_val, y_val = pool_training_data(stock_data)
    print(f"\nPooled train: {X_fit.shape}, validation: {X_val.shape}")

    # Train N_RUNS models from different random starts and average them.
    scaled_predictions = {stock: [] for stock in stock_names}
    for run in range(N_RUNS):
        seed = RANDOM_SEED + run
        set_seed(seed)

        model = build_cnn_bilstm_model(input_shape=X_fit.shape[1:])
        if run == 0:
            print(f"Model weights: {model.count_params():,}")
        early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

        history = model.fit(
            X_fit, y_fit,
            validation_data=(X_val, y_val),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            shuffle=True,
            verbose=0,
            callbacks=[early_stop],
        )
        print(f"Run {run + 1}/{N_RUNS} (seed {seed}): best val_loss {min(history.history['val_loss']):.4f}")
        model.save(os.path.join(OUTPUT_FOLDER, f"cnn_bilstm_pooled_seed{seed}.keras"))

        for stock, data in stock_data.items():
            scaled_predictions[stock].append(model.predict(data["X_test"], verbose=0))

    all_metrics = []
    predicted_returns_df = None

    for stock, data in stock_data.items():
        y_pred_scaled = np.mean(scaled_predictions[stock], axis=0)
        y_pred = data["y_scaler"].inverse_transform(y_pred_scaled).flatten()
        y_test = data["y_test"]

        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        print(f"{stock} -> MSE: {mse:.6f}, MAE: {mae:.6f}, RMSE: {np.sqrt(mse):.6f}")
        all_metrics.append({"Stock": stock, "MSE": mse, "MAE": mae, "RMSE": np.sqrt(mse)})

        result_df = pd.DataFrame({"Date": data["dates_test"], "Actual": y_test, "Predicted": y_pred})
        result_df.to_csv(os.path.join(OUTPUT_FOLDER, f"prediction_{stock}.csv"), index=False)

        column = result_df[["Date", "Predicted"]].rename(columns={"Predicted": stock})
        predicted_returns_df = (
            column if predicted_returns_df is None
            else predicted_returns_df.merge(column, on="Date", how="inner")
        )

    predicted_returns_df.to_csv(
        os.path.join(OUTPUT_FOLDER, "predicted_returns_all_stocks.csv"), index=False
    )
    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(os.path.join(OUTPUT_FOLDER, "cnn_bilstm_metrics.csv"), index=False)

    print("\nMetrics:")
    print(metrics_df)
    print(f"\nSaved outputs to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
