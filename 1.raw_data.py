import os

import yfinance as yf


tickers_stock = [
    "1155.KL",   # MAYBANK
    "1295.KL",   # Public Bank
    "1023.KL",   # CIMB Bank
    "5347.KL",   # Tenaga Nasional
    "4863.KL",   # TM
    "5183.KL",   # PChem
    "6888.KL",   # Axiata
    "5225.KL",   # IHH Healthcare
    "5819.KL",   # Hong Leong Bank
    "6012.KL",   # Maxis
    "8869.KL",   # Press Metal
    "5211.KL",   # Sunway
]

"""tickers_klci = [
    "^KLSE"     #KLCI 
]"""

# All data starts in 2022, to keep the COVID period (2020-2021) out of every
# calculation, including the look-back history of the Alpha101 factors and the
# rolling z-score. The first weeks of 2022 are therefore used only as look-back
# history (see 4b.alpha_features.py and 5.feature_engineering.py).
SAMPLE_START = "2022-01-01"
END = "2026-01-01"

OHLCV_FILEPATH = "DATASET/ohlcv_malaysia_stocks.csv"

df = yf.download(tickers_stock, start=SAMPLE_START, end=END, auto_adjust=False)

#df = yf.download(tickers_klci, start="2025-01-01", end="2026-01-01", auto_adjust=False)

# yfinance occasionally returns an empty column for a ticker; fail loudly
# instead of silently producing a dataset with a missing stock.
empty = [t for t in tickers_stock if df["Close"][t].isna().all()]
if empty:
    raise RuntimeError(f"yfinance returned no data for {empty}; re-run the download.")

df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kuala_Lumpur")

# Adjusted close for the return pipeline.
adj_close = df["Adj Close"]
adj_close = adj_close[adj_close.index >= SAMPLE_START]

print(adj_close.tail())
adj_close.to_csv("malaysia_stocks.csv")

# Full OHLCV panel for the Alpha101 factors,
# in long format: Date, Ticker, Open, High, Low, Close, Adj Close, Volume.
os.makedirs(os.path.dirname(OHLCV_FILEPATH), exist_ok=True)
ohlcv = df.stack(level="Ticker", future_stack=True).reset_index()
ohlcv = ohlcv[["Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]]
ohlcv.to_csv(OHLCV_FILEPATH, index=False)
print(f"Saved OHLCV panel {ohlcv.shape} to: {OHLCV_FILEPATH}")
