"""Decision agent: blends agent signals, applies hard risk rules, and either
proposes a single option trade or (by design, most of the time) says NO TRADE.

It NEVER places an order. It produces a structured proposal for you to act on.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from math import floor

import config
from agents.base import AgentSignal


@dataclass
class Decision:
    symbol: str
    action: str                      # "NO TRADE" | "BUY CE" | "BUY PE"
    reason: str
    combined_score: float = 0.0
    confidence: float = 0.0
    agreeing: int = 0
    contract: dict = field(default_factory=dict)   # strike, type, security_id, entry, stop, target, lots, qty
    levels: dict = field(default_factory=dict)      # invalidation/support/resistance
    signals: list = field(default_factory=list)


def _blend(signals: list[AgentSignal]) -> tuple[float, float, int]:
    w = config.AGENT_WEIGHTS
    num = den = cnum = cden = 0.0
    for s in signals:
        wt = w.get(s.name, 0.5)
        num += wt * s.score * s.confidence
        den += wt * s.confidence
        cnum += wt * s.confidence
        cden += wt
    combined = num / den if den else 0.0
    confidence = cnum / cden if cden else 0.0
    direction = 1 if combined > 0 else -1
    agreeing = sum(1 for s in signals
                   if s.score != 0 and (s.score > 0) == (direction > 0)
                   and abs(s.score) > 0.1)
    return combined, confidence, agreeing


def _pick_contract(chain: dict, side: str, strike_step: int) -> dict | None:
    oc = chain.get("oc", {})
    spot = float(chain.get("last_price", 0))
    if not oc or not spot:
        return None
    strikes = sorted(float(k) for k in oc.keys())
    atm = min(strikes, key=lambda s: abs(s - spot))
    leg = oc.get(f"{atm:.6f}", {})
    opt = leg.get("ce" if side == "CE" else "pe", {})
    entry = float(opt.get("last_price") or 0)
    if entry <= 0:
        return None
    return {"strike": atm, "type": side, "security_id": opt.get("security_id"),
            "entry": round(entry, 2), "iv": opt.get("implied_volatility"),
            "delta": opt.get("greeks", {}).get("delta")}


def decide(symbol: str, signals: list[AgentSignal], chain: dict,
           lot_size: int, strike_step: int, levels: dict,
           trades_done_today: int) -> Decision:
    combined, confidence, agreeing = _blend(signals)
    d = Decision(symbol=symbol, action="NO TRADE", reason="",
                 combined_score=round(combined, 3), confidence=round(confidence, 3),
                 agreeing=agreeing, levels=levels, signals=signals)

    # ---- hard gates (any failure => stay flat) ----
    if trades_done_today >= config.MAX_TRADES_PER_DAY:
        d.reason = f"daily trade cap reached ({config.MAX_TRADES_PER_DAY})"
        return d
    if abs(combined) < config.MIN_EDGE:
        d.reason = f"edge {combined:+.2f} below threshold {config.MIN_EDGE}"
        return d
    if confidence < config.MIN_CONFIDENCE:
        d.reason = f"confidence {confidence:.2f} below {config.MIN_CONFIDENCE}"
        return d
    if agreeing < config.MIN_AGREEING_AGENTS:
        d.reason = f"only {agreeing} agents agree (need {config.MIN_AGREEING_AGENTS})"
        return d

    side = "CE" if combined > 0 else "PE"
    c = _pick_contract(chain, side, strike_step)
    if not c:
        d.reason = "no tradable ATM contract / no premium"
        return d

    # ---- risk sizing ----
    entry = c["entry"]
    stop = round(entry * (1 - config.STOP_PREMIUM_PCT), 2)
    risk_per_unit = entry - stop
    target = round(entry + config.REWARD_RISK * risk_per_unit, 2)
    per_lot_risk = risk_per_unit * lot_size
    lots = floor(config.RISK_PER_TRADE_RS / per_lot_risk) if per_lot_risk > 0 else 0
    if lots < 1:
        d.reason = (f"risk budget Rs{config.RISK_PER_TRADE_RS:.0f} too small for 1 lot "
                    f"(needs ~Rs{per_lot_risk:.0f}) — stay flat")
        return d

    c.update({"stop": stop, "target": target, "lots": lots,
              "qty": lots * lot_size,
              "max_entry": round(entry * (1 + config.MAX_ENTRY_SLIPPAGE_PCT), 2),
              "max_loss_rs": round(per_lot_risk * lots, 0),
              "target_gain_rs": round(config.REWARD_RISK * per_lot_risk * lots, 0)})
    d.action = f"BUY {side}"
    d.contract = c
    d.reason = (f"{agreeing} agents agree, edge {combined:+.2f}, conf {confidence:.2f}")
    return d
