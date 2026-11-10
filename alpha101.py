"""
WorldQuant "101 Formulaic Alphas" (Kakushadze, 2016) - momentum & reversal family.

Reference used for the classification and operator definitions:
https://coriva.eu.org/alpha101-overview/  (section "动量与反转类（23 个因子）")

That page assigns 23 alphas to the momentum/reversal category:
    #4 #8 #9 #10 #19 #20 #23 #24 #29 #30 #33 #35 #37 #38 #39
    #46 #49 #51 #52 #53 #56 #84 #90
21 of them are implemented here. Two are skipped because the inputs are not
available from yfinance OHLCV data:
    #56 needs market cap, #90 needs a sub-industry classification.

Every input is a DataFrame with rows = dates and columns = tickers, so
cross-sectional operators (rank, scale) work along axis=1 and time-series
operators work down each column. All operators only look backwards in time,
so the value on date t uses information up to the close of date t only.

Where the article and the original paper disagree (#9, #30) the paper's
formula is used. Fractional windows from the paper (e.g. 9.99922) are rounded
to integers, as the article recommends.
"""

import numpy as np
import pandas as pd


# =========================
# Operators
# =========================
def rank(df):
    """Cross-sectional percentile rank on each date (0-1]."""
    return df.rank(axis=1, pct=True)


def delay(df, d):
    return df.shift(d)


def delta(df, d):
    return df - df.shift(d)


def ts_sum(df, d):
    return df.rolling(d).sum()


def sma(df, d):
    return df.rolling(d).mean()


def ts_min(df, d):
    return df.rolling(d).min()


def ts_max(df, d):
    return df.rolling(d).max()


def ts_rank(df, d):
    """Percentile rank of today's value within its own last d days."""
    return df.rolling(d).rank(pct=True)


def ts_corr(x, y, d):
    return x.rolling(d).corr(y)


def decay_linear(df, d):
    """Linearly weighted moving average, most recent day weighted highest."""
    weights = np.arange(1, d + 1, dtype=float)
    weights /= weights.sum()
    return df.rolling(d).apply(lambda x: np.dot(x, weights), raw=True)


def scale(df, a=1):
    """Rescale each date's cross-section so that sum(|x|) = a."""
    return df.mul(a).div(df.abs().sum(axis=1), axis=0)


def signedpower(base, exponent):
    return np.sign(base) * base.abs().pow(exponent)


def _where(cond, a, b):
    """Element-wise cond ? a : b that keeps the DataFrame shape and labels."""
    a = a if isinstance(a, pd.DataFrame) else pd.DataFrame(a, index=cond.index, columns=cond.columns)
    return a.where(cond, b)


# =========================
# Momentum & reversal alphas
# =========================
def compute_momentum_reversal_alphas(open_, high, low, close, volume):
    """
    Compute the 21 momentum/reversal alphas.

    Args (all DataFrames, dates x tickers, same shape):
        open_, high, low, close: dividend/split-adjusted prices
        volume: traded shares

    Returns:
        dict {alpha_name: DataFrame(dates x tickers)}
    """
    returns = close.pct_change()
    # The paper defines vwap from intraday trades; with daily bars the usual
    # approximation is the typical price.
    vwap = (high + low + close) / 3.0
    # Share-volume average (keeps volume / adv20 dimensionless).
    adv20 = sma(volume, 20)

    d1 = delta(close, 1)
    alphas = {}

    # #4  short-term reversal on the cross-sectional rank of the low
    alphas["alpha004"] = -1 * ts_rank(rank(low), 9)

    # #8  change in (5d open sum x 5d return sum) versus 10 days ago
    x8 = ts_sum(open_, 5) * ts_sum(returns, 5)
    alphas["alpha008"] = -1 * rank(x8 - delay(x8, 10))

    # #9  conditional reversal: follow the move in a 5-day one-way trend,
    #     fade it otherwise
    trend9 = (ts_min(d1, 5) > 0) | (ts_max(d1, 5) < 0)
    alphas["alpha009"] = _where(trend9, d1, -d1)

    # #10 same idea with a 4-day window, cross-sectionally ranked
    trend10 = (ts_min(d1, 4) > 0) | (ts_max(d1, 4) < 0)
    alphas["alpha010"] = rank(_where(trend10, d1, -d1))

    # #19 7-day reversal, scaled up for stocks with strong 1-year momentum
    alphas["alpha019"] = (
        -1 * np.sign((close - delay(close, 7)) + delta(close, 7))
        * (1 + rank(1 + ts_sum(returns, 250)))
    )

    # #20 gap fill: today's open versus yesterday's high / close / low
    alphas["alpha020"] = (
        -1 * rank(open_ - delay(high, 1))
        * rank(open_ - delay(close, 1))
        * rank(open_ - delay(low, 1))
    )

    # #23 fade the 2-day move in the high when the high is above its 20d mean
    alphas["alpha023"] = _where(sma(high, 20) < high, -1 * delta(high, 2), 0.0)

    # #24 flat 100-day trend -> distance from the 100d low, else 3-day reversal
    slow_trend = delta(sma(close, 100), 100) / delay(close, 100)
    alphas["alpha024"] = _where(
        slow_trend <= 0.05,
        -1 * (close - ts_min(close, 100)),
        -1 * delta(close, 3),
    )

    # #29 ranked 5-day reversal + time-series rank of the lagged reversal
    inner29 = ts_min(rank(rank(-1 * rank(delta(close - 1, 5)))), 2)
    alphas["alpha029"] = (
        ts_min(rank(rank(scale(np.log(inner29)))), 5)
        + ts_rank(delay(-1 * returns, 6), 5)
    )

    # #30 3-day direction signature x short/long volume ratio
    sign_sum = (
        np.sign(close - delay(close, 1))
        + np.sign(delay(close, 1) - delay(close, 2))
        + np.sign(delay(close, 2) - delay(close, 3))
    )
    alphas["alpha030"] = (1.0 - rank(sign_sum)) * ts_sum(volume, 5) / ts_sum(volume, 20)

    # #33 intraday (open -> close) move, ranked
    alphas["alpha033"] = rank(-1 * (1 - (open_ / close)))

    # #35 "volume expanding at the bottom": three time scales multiplied
    alphas["alpha035"] = (
        ts_rank(volume, 32)
        * (1 - ts_rank(close + high - low, 16))
        * (1 - ts_rank(returns, 32))
    )

    # #37 200d correlation of yesterday's intraday move with close + today's move
    alphas["alpha037"] = (
        rank(ts_corr(delay(open_ - close, 1), close, 200)) + rank(open_ - close)
    )

    # #38 fade stocks at a 10-day high that also closed strong intraday
    alphas["alpha038"] = -1 * rank(ts_rank(close, 10)) * rank(close / open_)

    # #39 volume-weighted 7-day reversal, scaled by 1-year momentum
    alphas["alpha039"] = (
        -1 * rank(delta(close, 7) * (1 - rank(decay_linear(volume / adv20, 9))))
        * (1 + rank(ts_sum(returns, 250)))
    )

    # #46 / #49 / #51 trend acceleration: slope of days -20..-10 minus slope
    #     of days -10..0. Thresholds are in price units, as in the paper.
    accel = (delay(close, 20) - delay(close, 10)) / 10 - (delay(close, 10) - close) / 10
    ones = pd.DataFrame(1.0, index=close.index, columns=close.columns)
    alphas["alpha046"] = _where(accel > 0.25, -1 * ones, _where(accel < 0, ones, -d1))
    alphas["alpha049"] = _where(accel < -0.1, ones, -d1)
    alphas["alpha051"] = _where(accel < -0.05, ones, -d1)
    # The rolling inputs are NaN during warm-up; do not let the comparisons
    # turn that into a real-looking value.
    for name in ("alpha046", "alpha049", "alpha051"):
        alphas[name] = alphas[name].where(accel.notna())

    # #52 rising 5-day lows x long-minus-short momentum x volume rank
    low5 = ts_min(low, 5)
    alphas["alpha052"] = (
        (-1 * low5 + delay(low5, 5))
        * rank((ts_sum(returns, 240) - ts_sum(returns, 20)) / 220)
        * ts_rank(volume, 5)
    )

    # #53 9-day change in where the close sits inside the day's range.
    #     close == low happens on ~10% of days for these stocks, so the
    #     denominator is floored (common convention) to avoid dividing by 0.
    denom = (close - low).where((close - low) > 1e-4, 1e-4)
    alphas["alpha053"] = -1 * delta(((close - low) - (high - close)) / denom, 9)

    # #84 vwap relative to its 15-day high, raised to the 5-day price change
    alphas["alpha084"] = signedpower(
        ts_rank(vwap - ts_max(vwap, 15), 21), delta(close, 5)
    )

    # Rolling comparisons above (e.g. sma(high, 20) < high) evaluate to False
    # on warm-up rows; blank those so they are not mistaken for real values.
    alphas["alpha023"] = alphas["alpha023"].where(sma(high, 20).notna())
    alphas["alpha024"] = alphas["alpha024"].where(slow_trend.notna())
    alphas["alpha009"] = alphas["alpha009"].where(ts_min(d1, 5).notna())
    alphas["alpha010"] = alphas["alpha010"].where(ts_min(d1, 4).notna())

    return {
        name: frame.replace([np.inf, -np.inf], np.nan)
        for name, frame in alphas.items()
    }
