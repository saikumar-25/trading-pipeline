"""Option-chain / Open-Interest agent (upgraded).

Reads the live Dhan option chain around ATM and derives:
  - PCR (Put/Call OI ratio): directional bias.
  - OI-PRICE QUADRANTS per strike: long/short buildup, covering/unwinding —
    this is how we tell *conviction* (e.g. PE short-buildup = put writing = support).
  - Strongest OI support / resistance strikes + where spot sits relative to them.
  - INTRADAY OI TREND: is positioning shifting bullish/bearish through the session.
  - ATM IV: premium richness / regime.
"""
from __future__ import annotations
from .base import AgentSignal, neutral

try:
    import oi_history
except Exception:                      # noqa: BLE001
    oi_history = None


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _quadrant(doi: float, dprice: float) -> str:
    """Classify an option leg by change in OI vs change in price."""
    if doi >= 0 and dprice >= 0:
        return "long_buildup"      # buyers adding
    if doi >= 0 and dprice < 0:
        return "short_buildup"     # writers adding (sellers)
    if doi < 0 and dprice >= 0:
        return "short_covering"    # sellers exiting
    return "long_unwinding"        # buyers exiting


def analyze(chain: dict, strike_step: int, symbol: str | None = None) -> AgentSignal:
    oc = (chain or {}).get("oc") or {}
    spot = _f(chain.get("last_price"))
    if not oc or not spot:
        return neutral("oi_chain", "no option chain")

    strikes = sorted(float(k) for k in oc.keys())
    atm = min(strikes, key=lambda s: abs(s - spot))
    lo, hi = atm - 10 * strike_step, atm + 10 * strike_step
    near = [s for s in strikes if lo <= s <= hi]

    tot_ce_oi = tot_pe_oi = 0.0
    max_ce_oi = max_pe_oi = -1.0
    oi_resistance = oi_support = atm
    atm_iv = 0.0
    # quadrant tallies (writing = bias-defining)
    pe_write = ce_write = ce_long = pe_long = 0.0

    for s in near:
        leg = oc[f"{s:.6f}"]
        ce, pe = leg.get("ce", {}), leg.get("pe", {})
        ce_oi, pe_oi = _f(ce.get("oi")), _f(pe.get("oi"))
        tot_ce_oi += ce_oi
        tot_pe_oi += pe_oi
        if ce_oi > max_ce_oi:
            max_ce_oi, oi_resistance = ce_oi, s
        if pe_oi > max_pe_oi:
            max_pe_oi, oi_support = pe_oi, s
        if s == atm:
            atm_iv = _f(ce.get("implied_volatility")) or _f(pe.get("implied_volatility"))

        # per-strike quadrant from OI change vs price change (day-over-day)
        ce_q = _quadrant(ce_oi - _f(ce.get("previous_oi")),
                         _f(ce.get("last_price")) - _f(ce.get("previous_close_price")))
        pe_q = _quadrant(pe_oi - _f(pe.get("previous_oi")),
                         _f(pe.get("last_price")) - _f(pe.get("previous_close_price")))
        w_ce = abs(ce_oi - _f(ce.get("previous_oi")))
        w_pe = abs(pe_oi - _f(pe.get("previous_oi")))
        if ce_q == "short_buildup":
            ce_write += w_ce         # call writing -> resistance/bearish
        elif ce_q == "long_buildup":
            ce_long += w_ce          # call buying  -> bullish
        if pe_q == "short_buildup":
            pe_write += w_pe         # put writing  -> support/bullish
        elif pe_q == "long_buildup":
            pe_long += w_pe          # put buying   -> bearish

    pcr = tot_pe_oi / tot_ce_oi if tot_ce_oi else 1.0
    notes, votes = [], []

    # 1) PCR level
    if pcr >= 1.3:
        votes.append(+0.4); notes.append(f"PCR {pcr:.2f} put-heavy")
    elif pcr <= 0.7:
        votes.append(-0.4); notes.append(f"PCR {pcr:.2f} call-heavy")
    else:
        notes.append(f"PCR {pcr:.2f}")

    # 2) writing pressure (the core OI read)
    writing_bias = (pe_write - ce_write)
    long_bias = (ce_long - pe_long)
    scale = max(pe_write + ce_write, 1.0)
    votes.append(max(-0.5, min(0.5, 0.5 * writing_bias / scale)))
    if pe_write > ce_write * 1.2:
        notes.append("PE writing > CE (support building)")
    elif ce_write > pe_write * 1.2:
        notes.append("CE writing > PE (resistance building)")
    scale2 = max(ce_long + pe_long, 1.0)
    votes.append(max(-0.3, min(0.3, 0.3 * long_bias / scale2)))

    # 3) spot proximity to OI walls (near support = bullish, near resistance = bearish)
    if abs(spot - oi_support) <= strike_step:
        votes.append(+0.2); notes.append(f"spot near OI support {oi_support:.0f}")
    if abs(spot - oi_resistance) <= strike_step:
        votes.append(-0.2); notes.append(f"spot near OI resistance {oi_resistance:.0f}")

    # 4) intraday OI trend (positioning drift through the session)
    pcr_delta = 0.0
    if oi_history and symbol:
        tr = oi_history.record_and_trend(symbol, tot_ce_oi, tot_pe_oi, pcr)
        pcr_delta = tr["pcr_delta"]
        if tr["n"] >= 3:
            if pcr_delta > 0.1:
                votes.append(+0.25); notes.append(f"PCR rising intraday (+{pcr_delta})")
            elif pcr_delta < -0.1:
                votes.append(-0.25); notes.append(f"PCR falling intraday ({pcr_delta})")

    score = sum(votes)
    confidence = min(0.85, 0.45 + 0.07 * len([v for v in votes if abs(v) > 0.05]))
    notes.append(f"support~{oi_support:.0f}, resistance~{oi_resistance:.0f}, ATM IV {atm_iv:.1f}")

    return AgentSignal("oi_chain", score, confidence, "; ".join(notes),
                       {"spot": spot, "atm": atm, "pcr": round(pcr, 2),
                        "oi_support": oi_support, "oi_resistance": oi_resistance,
                        "atm_iv": round(atm_iv, 1), "pcr_delta": pcr_delta}).clamp()
