"""
End-of-day summary: how the universe moved today + today's paper-call results,
sent as one compact Telegram message. Also refreshes the learning stats.

Run by the eod GitHub Actions workflow at ~15:35 IST.
"""
from __future__ import annotations
import csv
import datetime as dt
import os

import config
import market
import learning
import notifier

POSITIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_positions.csv")


def _session_move(meta) -> float | None:
    """Today's intraday move %: first bar open -> last bar close."""
    try:
        df = market.get_intraday_underlying(
            meta["under_security_id"], meta["under_exchange_segment"],
            config.UNDERLYING_TF, days=2,
            instrument_type=meta.get("instrument_type", "INDEX"))
        last_day = df.index[-1].date()
        today = df[df.index.date == last_day]
        if today.empty:
            return None
        o, c = today["open"].iloc[0], today["close"].iloc[-1]
        return round((c - o) / o * 100, 2) if o else None
    except Exception:           # noqa: BLE001
        return None


def _todays_paper():
    today = dt.date.today().isoformat()
    n = w = 0
    pnl = 0.0
    if os.path.exists(POSITIONS):
        with open(POSITIONS, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("status") in ("WIN", "LOSS") and str(r.get("exit_time", "")).startswith(today):
                    n += 1
                    w += 1 if r["status"] == "WIN" else 0
                    try:
                        pnl += float(r["pnl_rs"] or 0)
                    except ValueError:
                        pass
    return n, w, n - w, pnl


def main():
    moves = {}
    for sym, meta in config.FNO_UNDERLYINGS.items():
        m = _session_move(meta)
        if m is not None:
            moves[sym] = m

    ranked = sorted(moves.items(), key=lambda kv: kv[1], reverse=True)
    gainers = ", ".join(f"{s} {v:+.1f}%" for s, v in ranked[:3])
    losers = ", ".join(f"{s} {v:+.1f}%" for s, v in ranked[-3:][::-1])
    up = sum(1 for v in moves.values() if v > 0)
    down = sum(1 for v in moves.values() if v < 0)

    n, w, l, pnl = _todays_paper()
    learn = learning.compute()
    muted = ", ".join(learn["muted"]) or "none"

    today = dt.date.today().isoformat()
    msg = (
        f"📊 EOD {today} — {len(moves)} instruments: {up} up / {down} down\n"
        f"Top: {gainers}\n"
        f"Bottom: {losers}\n"
        f"Paper today: {n} call(s), {w}W/{l}L, net ₹{pnl:+,.0f}\n"
        f"Auto-muted (persistent losers): {muted}"
    )
    notifier.send(msg)
    print(msg)


if __name__ == "__main__":
    main()
