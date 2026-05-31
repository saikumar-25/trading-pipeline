"""Support/Resistance agent: classic pivots + recent swing levels.

Outputs a score based on where price sits relative to the day's pivot and
the nearest swing levels, plus the key levels themselves (used later as the
trade's invalidation reference).
"""
from __future__ import annotations
import pandas as pd
from .base import AgentSignal, neutral


def analyze(df: pd.DataFrame) -> AgentSignal:
    if df is None or len(df) < 30:
        return neutral("support_resistance", "not enough bars")

    # previous session range -> floor-trader pivots
    prev = df.tail(75)  # ~ last day of 5-min bars
    H, L, C = prev["high"].max(), prev["low"].min(), df["close"].iloc[-1]
    P = (H + L + C) / 3
    r1, s1 = 2 * P - L, 2 * P - H
    r2, s2 = P + (H - L), P - (H - L)

    price = df["close"].iloc[-1]
    notes = [f"P={P:.0f} R1={r1:.0f} S1={s1:.0f}"]

    # score: room to the upside vs downside within the pivot band
    up_room = (r1 - price)
    dn_room = (price - s1)
    span = max(r1 - s1, 1e-6)
    score = (up_room - dn_room) / span        # +ve = more room up
    # if price breaking above R1 / below S1, treat as breakout momentum
    if price > r1:
        score = 0.6; notes.append("above R1 (breakout up)")
    elif price < s1:
        score = -0.6; notes.append("below S1 (breakdown)")

    confidence = 0.5
    return AgentSignal("support_resistance", score, confidence, "; ".join(notes),
                       {"pivot": P, "r1": r1, "s1": s1, "r2": r2, "s2": s2,
                        "nearest_support": s1, "nearest_resistance": r1}).clamp()
