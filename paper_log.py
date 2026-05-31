"""
Paper-trade logger & scorer.

- Every decision (including NO TRADE) is appended to signals_log.csv.
- Every BUY CE/PE opens a row in paper_positions.csv (status=open).
- On each scan, open positions are marked against the live option chain:
  premium >= target -> WIN, premium <= stop -> LOSS, else stay open.
- paper_report.py prints hit-rate, P/L, and expectancy.

This lets you judge the pipeline honestly for weeks BEFORE risking real money.
No real orders are ever placed.
"""
from __future__ import annotations
import csv
import os
import datetime as dt

from decision import Decision

DIR = os.path.dirname(os.path.abspath(__file__))
SIGNALS_CSV = os.path.join(DIR, "signals_log.csv")
POSITIONS_CSV = os.path.join(DIR, "paper_positions.csv")

SIG_COLS = ["time", "symbol", "action", "score", "confidence", "agreeing", "reason"]
POS_COLS = ["id", "open_time", "symbol", "action", "strike", "type", "security_id",
            "entry", "stop", "target", "lots", "qty", "status",
            "exit_time", "exit_price", "pnl_rs"]


def _append(path, cols, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in cols})


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write_all(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def record(d: Decision):
    now = dt.datetime.now().isoformat(timespec="seconds")
    _append(SIGNALS_CSV, SIG_COLS, {
        "time": now, "symbol": d.symbol, "action": d.action,
        "score": d.combined_score, "confidence": d.confidence,
        "agreeing": d.agreeing, "reason": d.reason})

    if d.action != "NO TRADE" and d.contract:
        c = d.contract
        _append(POSITIONS_CSV, POS_COLS, {
            "id": f"{d.symbol}-{now}", "open_time": now, "symbol": d.symbol,
            "action": d.action, "strike": c["strike"], "type": c["type"],
            "security_id": c["security_id"], "entry": c["entry"],
            "stop": c["stop"], "target": c["target"], "lots": c["lots"],
            "qty": c["qty"], "status": "open", "exit_time": "",
            "exit_price": "", "pnl_rs": ""})


def _chain_ltp_map(chain: dict) -> dict:
    out = {}
    for leg in (chain.get("oc") or {}).values():
        for side in ("ce", "pe"):
            o = leg.get(side) or {}
            if o.get("security_id") is not None:
                out[str(o["security_id"])] = float(o.get("last_price") or 0)
    return out


def mark_to_market(symbol: str, chain: dict):
    rows = _read(POSITIONS_CSV)
    if not rows:
        return
    ltp = _chain_ltp_map(chain)
    changed = False
    for r in rows:
        if r["status"] != "open" or r["symbol"] != symbol:
            continue
        cur = ltp.get(str(r["security_id"]))
        if not cur:
            continue
        entry, stop, target, qty = (float(r["entry"]), float(r["stop"]),
                                    float(r["target"]), float(r["qty"]))
        status = exit_px = None
        if cur >= target:
            status, exit_px = "WIN", cur
        elif cur <= stop:
            status, exit_px = "LOSS", cur
        if status:
            r["status"] = status
            r["exit_time"] = dt.datetime.now().isoformat(timespec="seconds")
            r["exit_price"] = round(exit_px, 2)
            r["pnl_rs"] = round((exit_px - entry) * qty, 0)
            changed = True
    if changed:
        _write_all(POSITIONS_CSV, POS_COLS, rows)


def stats() -> dict:
    rows = _read(POSITIONS_CSV)
    closed = [r for r in rows if r["status"] in ("WIN", "LOSS")]
    open_ = [r for r in rows if r["status"] == "open"]
    wins = [r for r in closed if r["status"] == "WIN"]
    losses = [r for r in closed if r["status"] == "LOSS"]
    pnl = sum(float(r["pnl_rs"]) for r in closed if r["pnl_rs"] != "")
    avg_win = (sum(float(r["pnl_rs"]) for r in wins) / len(wins)) if wins else 0
    avg_loss = (sum(float(r["pnl_rs"]) for r in losses) / len(losses)) if losses else 0
    n = len(closed)
    win_rate = (len(wins) / n * 100) if n else 0
    expectancy = (pnl / n) if n else 0
    return {"signals_logged": len(_read(SIGNALS_CSV)),
            "trades_taken": len(rows), "open": len(open_), "closed": n,
            "wins": len(wins), "losses": len(losses),
            "win_rate_%": round(win_rate, 1), "net_pnl_rs": round(pnl, 0),
            "avg_win_rs": round(avg_win, 0), "avg_loss_rs": round(avg_loss, 0),
            "expectancy_per_trade_rs": round(expectancy, 0)}
