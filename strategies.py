"""
Transparent ("white-box") rule-based strategies.
Each returns a position series in {0, 1}: 1 = long/in market, 0 = flat.
Long-only by design (simpler, and short-selling has extra constraints in India).

Signals are computed on data available *up to and including* each day, then
applied to the NEXT day's return in the backtest (no look-ahead).
"""
from __future__ import annotations
import pandas as pd


def ma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """Long when fast MA is above slow MA."""
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    return (f > s).astype(int).rename("ma_crossover")


def momentum(df: pd.DataFrame, lookback: int = 90) -> pd.Series:
    """Long when price is above its level `lookback` days ago (positive trend)."""
    mom = df["close"] / df["close"].shift(lookback) - 1
    return (mom > 0).astype(int).rename("momentum")


def rsi_mean_reversion(df: pd.DataFrame, period: int = 14,
                       buy: float = 30, exit_: float = 55) -> pd.Series:
    """Buy when RSI dips below `buy`, hold until RSI recovers above `exit_`."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - 100 / (1 + rs)

    pos, holding = [], False
    for r in rsi:
        if not holding and r < buy:
            holding = True
        elif holding and r > exit_:
            holding = False
        pos.append(1 if holding else 0)
    return pd.Series(pos, index=df.index, name="rsi_mean_reversion")


REGISTRY = {
    "ma_crossover": ma_crossover,
    "momentum": momentum,
    "rsi_mean_reversion": rsi_mean_reversion,
}
