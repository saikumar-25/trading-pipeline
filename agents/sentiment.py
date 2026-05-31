"""Market-sentiment agent (mood/regime), distinct from news headlines.

Uses option-chain internals as a fear/greed proxy:
  - PCR extremes (contrarian at the tails, trend-confirming in the middle).
  - ATM implied volatility level (rich IV = fear/uncertainty).
This intentionally reads the market's own positioning rather than text.
"""
from __future__ import annotations
from .base import AgentSignal, neutral


def analyze(oi_data: dict) -> AgentSignal:
    if not oi_data:
        return neutral("sentiment", "no chain data")
    pcr = oi_data.get("pcr", 1.0)
    iv = oi_data.get("atm_iv", 0.0)

    notes, votes = [], []
    # Mild trend-confirmation from PCR, but fade true extremes (capitulation).
    if pcr >= 1.8:
        votes.append(-0.3); notes.append(f"PCR {pcr} extreme (over-hedged, fade)")
    elif pcr <= 0.4:
        votes.append(+0.3); notes.append(f"PCR {pcr} extreme (over-bullish, fade)")
    elif pcr >= 1.2:
        votes.append(+0.3); notes.append("constructive positioning")
    elif pcr <= 0.8:
        votes.append(-0.3); notes.append("defensive positioning")

    # High IV lowers confidence (premiums rich, whipsaw risk)
    conf = 0.45
    if iv >= 20:
        conf = 0.3; notes.append(f"IV {iv} elevated (premiums rich)")
    elif iv and iv < 12:
        notes.append(f"IV {iv} calm")

    score = sum(votes)
    return AgentSignal("sentiment", score, conf,
                       "; ".join(notes) or "neutral mood", {}).clamp()
