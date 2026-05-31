"""Technical-analysis agent on the underlying's intraday bars."""
from __future__ import annotations
import pandas as pd
from .base import AgentSignal, neutral


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - 100 / (1 + rs)


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def analyze(df: pd.DataFrame) -> AgentSignal:
    if df is None or len(df) < 50:
        return neutral("technical", "not enough bars")

    close = df["close"]
    ema9, ema21 = _ema(close, 9), _ema(close, 21)
    rsi = _rsi(close)
    macd = _ema(close, 12) - _ema(close, 26)
    macd_sig = _ema(macd, 9)

    last = -1
    votes, notes = [], []

    # trend via EMA stack
    if ema9.iloc[last] > ema21.iloc[last]:
        votes.append(+1); notes.append("EMA9>EMA21 (up)")
    else:
        votes.append(-1); notes.append("EMA9<EMA21 (down)")

    # momentum via MACD
    if macd.iloc[last] > macd_sig.iloc[last]:
        votes.append(+1); notes.append("MACD bullish")
    else:
        votes.append(-1); notes.append("MACD bearish")

    # RSI regime (avoid chasing extremes)
    r = rsi.iloc[last]
    if r > 70:
        votes.append(-0.5); notes.append(f"RSI {r:.0f} overbought")
    elif r < 30:
        votes.append(+0.5); notes.append(f"RSI {r:.0f} oversold")
    elif r > 55:
        votes.append(+0.5); notes.append(f"RSI {r:.0f} firm")
    elif r < 45:
        votes.append(-0.5); notes.append(f"RSI {r:.0f} soft")

    score = sum(votes) / 2.5  # normalize to ~[-1,1]
    agree = abs(sum(1 if v > 0 else -1 for v in votes if v))
    confidence = min(0.85, 0.4 + 0.12 * agree)
    return AgentSignal("technical", score, confidence, "; ".join(notes),
                       {"rsi": round(r, 1)}).clamp()
