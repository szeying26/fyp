import os
import random
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Bidirectional, LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping


# =========================
# Configuration
# =========================
WINDOWED_FOLDER = "DATASET/windowed_data"
OUTPUT_FOLDER = "DATASET/model_output"

EPOCHS = 30
BATCH_SIZE = 32
VALIDATION_SPLIT = 0.1
RANDOM_SEED = 42

# Daily log returns are ~0.01 in size, so the raw MSE loss is ~0.0001 and the
# network settles on a near-constant prediction. Standardizing the target
# (train statistics only) gives the loss a usable scale; predictions are
# converted back to log returns before metrics are computed and saved.
SCALE_TARGET = True


# =========================
# Reproducibility
# =========================
def set_seed(seed=RANDOM_SEED):
    np.random.seed(seed)
    random.seed(seed)
    tf.random.set_seed(seed)


# =========================
# Build CNN-BiLSTM model
# =========================
def build_cnn_bilstm_model(input_shape):
    """
    Build a CNN-BiLSTM model for one-step-ahead stock return prediction.

    Args:
        input_shape (tuple): (timesteps, features)

    Returns:
        tf.keras.Model
    """
    model = Sequential()

    # CNN layer to extract local temporal patterns
    model.add(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape))
    model.add(MaxPooling1D(pool_size=2))

    # BiLSTM to capture sequential dependencies
    model.add(Bidirectional(LSTM(50, return_sequences=False)))
    model.add(Dropout(0.2))

    # Dense layers for regression output
    model.add(Dense(32, activation='relu'))
    model.add(Dense(1, activation='linear'))

    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )

    return model


# =========================
# Load arrays for one stock
# =========================
def load_stock_arrays(stock_name):
    """
    Load train/test arrays for one stock.
    """
    X_train = np.load(os.path.join(WINDOWED_FOLDER, f"X_train_{stock_name}.npy"))
    y_train = np.load(os.path.join(WINDOWED_FOLDER, f"y_train_{stock_name}.npy"))
    X_test = np.load(os.path.join(WINDOWED_FOLDER, f"X_test_{stock_name}.npy"))
    y_test = np.load(os.path.join(WINDOWED_FOLDER, f"y_test_{stock_name}.npy"))

    date_test = pd.read_csv(
        os.path.join(WINDOWED_FOLDER, f"dates_test_{stock_name}.csv")
    )
    date_test["Date"] = pd.to_datetime(date_test["Date"])

    return X_train, y_train, X_test, y_test, date_test


# =========================
# Scale train/test features
# =========================
def scale_train_test(X_train, X_test):
    """
    Standardize X_train and X_test using training data only.
    This avoids data leakage.

    Input shapes:
        X_train: (samples, timesteps, features)
        X_test : (samples, timesteps, features)
    """
    n_train, t_train, f_train = X_train.shape
    n_test, t_test, f_test = X_test.shape

    scaler = StandardScaler()

    # reshape 3D -> 2D for scaling
    X_train_2d = X_train.reshape(-1, f_train)
    X_test_2d = X_test.reshape(-1, f_test)

    # fit on training only, transform both
    X_train_scaled = scaler.fit_transform(X_train_2d).reshape(n_train, t_train, f_train)
    X_test_scaled = scaler.transform(X_test_2d).reshape(n_test, t_test, f_test)

    return X_train_scaled, X_test_scaled


# =========================
# Detect stock names automatically
# =========================
def get_stock_names():
    """
    Detect all stock names from y_train_*.npy files.
    """
    stock_names = []
    for filename in os.listdir(WINDOWED_FOLDER):
        if filename.startswith("y_train_") and filename.endswith(".npy"):
            stock_name = filename.replace("y_train_", "").replace(".npy", "")
            stock_names.append(stock_name)

    stock_names.sort()
    return stock_names


# =========================
# Train model for one stock
# =========================
def train_one_stock(stock_name):
    """
    Train one CNN-BiLSTM model for a single stock and return predictions + metrics.
    """
    print(f"\nTraining stock: {stock_name}")

    # Load data
    X_train, y_train, X_test, y_test, date_test = load_stock_arrays(stock_name)

    # Scale input features
    X_train, X_test = scale_train_test(X_train, X_test)

    # Scale target (fit on training data only)
    y_scaler = StandardScaler()
    if SCALE_TARGET:
        y_train_fit = y_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
    else:
        y_train_fit = y_train

    # Build model
    model = build_cnn_bilstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))

    # Early stopping
    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    )

    # Train
    history = model.fit(
        X_train,
        y_train_fit,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=VALIDATION_SPLIT,
        verbose=0,
        callbacks=[early_stop]
    )

    # Predict
    y_pred = model.predict(X_test, verbose=0).flatten()
    if SCALE_TARGET:
        # back to log-return units
        y_pred = y_scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()

    # Metrics
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mse)

    print(f"{stock_name} -> X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"{stock_name} -> X_test : {X_test.shape}, y_test : {y_test.shape}")
    print(f"{stock_name} -> MSE: {mse:.6f}, MAE: {mae:.6f}, RMSE: {rmse:.6f}")

    # Save model
    model.save(os.path.join(OUTPUT_FOLDER, f"cnn_bilstm_{stock_name}.keras"))

    # Return results
    result_df = pd.DataFrame({
        "Date": date_test["Date"],
        "Actual": y_test,
        "Predicted": y_pred
    })

    result_df.to_csv(
        os.path.join(OUTPUT_FOLDER, f"prediction_{stock_name}.csv"),
        index=False
    )

    metrics = {
        "Stock": stock_name,
        "MSE": mse,
        "MAE": mae,
        "RMSE": rmse
    }

    return stock_name, result_df, metrics


# =========================
# Main
# =========================
def main():
    set_seed()
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    stock_names = get_stock_names()

    if not stock_names:
        raise FileNotFoundError(
            f"No windowed stock files found in {WINDOWED_FOLDER}. "
            f"Make sure your sliding-window script has already been run."
        )

    print("Stocks detected:")
    print(stock_names)

    all_metrics = []
    predicted_return_frames = []

    for stock in stock_names:
        stock_name, result_df, metrics = train_one_stock(stock)

        # keep only Date + Predicted for merged output
        temp_df = result_df[["Date", "Predicted"]].copy()
        temp_df = temp_df.rename(columns={"Predicted": stock_name})
        predicted_return_frames.append(temp_df)

        all_metrics.append(metrics)

    # Merge all predicted returns by Date
    predicted_returns_df = predicted_return_frames[0]
    for df in predicted_return_frames[1:]:
        predicted_returns_df = predicted_returns_df.merge(df, on="Date", how="inner")

    # Save merged predicted returns for QP
    predicted_returns_df.to_csv(
        os.path.join(OUTPUT_FOLDER, "predicted_returns_all_stocks.csv"),
        index=False
    )

    # Save metrics
    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(
        os.path.join(OUTPUT_FOLDER, "cnn_bilstm_metrics.csv"),
        index=False
    )

    print("\nAll stocks trained successfully.")
    print("\nMerged predicted return preview:")
    print(predicted_returns_df.head())

    print("\nMetrics preview:")
    print(metrics_df.head())

    print(f"\nSaved merged predicted returns to: {os.path.join(OUTPUT_FOLDER, 'predicted_returns_all_stocks.csv')}")
    print(f"Saved stock metrics to: {os.path.join(OUTPUT_FOLDER, 'cnn_bilstm_metrics.csv')}")


if __name__ == "__main__":
    main()