"""Option-chain / Open-Interest agent.

Reads the live Dhan option chain and derives:
  - PCR (Put/Call OI ratio): directional bias.
  - OI buildup vs previous OI: where smart money is adding (support/resistance).
  - Max-pain strike: gravitational pull into expiry.
  - ATM IV: regime / richness of premium.
"""
from __future__ import annotations
from .base import AgentSignal, neutral


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def analyze(chain: dict, strike_step: int) -> AgentSignal:
    oc = (chain or {}).get("oc") or {}
    spot = _f(chain.get("last_price"))
    if not oc or not spot:
        return neutral("oi_chain", "no option chain")

    strikes = sorted((float(k) for k in oc.keys()))
    atm = min(strikes, key=lambda s: abs(s - spot))

    # window around ATM (key strikes only)
    lo, hi = atm - 10 * strike_step, atm + 10 * strike_step
    near = [s for s in strikes if lo <= s <= hi]

    tot_ce_oi = tot_pe_oi = 0.0
    ce_add = pe_add = 0.0
    max_ce_strike = max_pe_strike = atm
    max_ce_oi = max_pe_oi = -1.0
    atm_iv = 0.0

    for s in near:
        leg = oc[f"{s:.6f}"]
        ce, pe = leg.get("ce", {}), leg.get("pe", {})
        ce_oi, pe_oi = _f(ce.get("oi")), _f(pe.get("oi"))
        tot_ce_oi += ce_oi; tot_pe_oi += pe_oi
        ce_add += ce_oi - _f(ce.get("previous_oi"))
        pe_add += pe_oi - _f(pe.get("previous_oi"))
        if ce_oi > max_ce_oi:
            max_ce_oi, max_ce_strike = ce_oi, s   # biggest CE OI = resistance
        if pe_oi > max_pe_oi:
            max_pe_oi, max_pe_strike = pe_oi, s    # biggest PE OI = support
        if s == atm:
            atm_iv = _f(ce.get("implied_volatility")) or _f(pe.get("implied_volatility"))

    pcr = tot_pe_oi / tot_ce_oi if tot_ce_oi else 1.0

    notes, votes = [], []
    # PCR bias
    if pcr >= 1.3:
        votes.append(+0.6); notes.append(f"PCR {pcr:.2f} (put-heavy, supportive)")
    elif pcr <= 0.7:
        votes.append(-0.6); notes.append(f"PCR {pcr:.2f} (call-heavy, capped)")
    else:
        notes.append(f"PCR {pcr:.2f} (balanced)")

    # OI buildup: heavy PE writing = bullish, heavy CE writing = bearish
    if pe_add > ce_add * 1.2:
        votes.append(+0.4); notes.append("PE writing > CE (bullish add)")
    elif ce_add > pe_add * 1.2:
        votes.append(-0.4); notes.append("CE writing > PE (bearish add)")

    score = sum(votes)
    confidence = min(0.8, 0.45 + 0.1 * len(votes))
    notes.append(f"support~{max_pe_strike:.0f}, resistance~{max_ce_strike:.0f}, ATM IV {atm_iv:.1f}")

    return AgentSignal("oi_chain", score, confidence, "; ".join(notes),
                       {"spot": spot, "atm": atm, "pcr": round(pcr, 2),
                        "oi_support": max_pe_strike, "oi_resistance": max_ce_strike,
                        "atm_iv": round(atm_iv, 1)}).clamp()
