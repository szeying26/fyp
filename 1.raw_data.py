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

df = yf.download(tickers_stock, start="2022-01-01", end="2026-01-01", auto_adjust=False)

#df = yf.download(tickers_klci, start="2025-01-01", end="2026-01-01", auto_adjust=False)

adj_close = df["Adj Close"]
adj_close.index = adj_close.index.tz_localize("UTC").tz_convert("Asia/Kuala_Lumpur")

print(adj_close.tail())
adj_close.to_csv("malaysia_stocks.csv")
