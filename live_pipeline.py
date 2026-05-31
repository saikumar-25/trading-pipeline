"""
End-to-end multi-agent intraday options pipeline.

    python live_pipeline.py once     # evaluate every underlying right now
    python live_pipeline.py loop     # run continuously on each bar close (market hours)

Flow per underlying:
    data -> [technical, support/resistance, OI-chain, news, sentiment, fundamentals]
         -> decision agent (risk rules, NO-TRADE bias) -> Telegram alert

It NEVER places orders. Every alert is a proposal for you to act on manually.
"""
from __future__ import annotations
import sys
import time
import datetime as dt
from zoneinfo import ZoneInfo

import config
import netctx
import market
from agents import technical, support_resistance, oi_chain, news, sentiment, fundamentals
from decision import decide
import notifier
import paper_log

netctx.enable_global()      # trust OS cert store (corporate proxy / macOS fix)

IST = ZoneInfo("Asia/Kolkata")
_trades_today: dict[str, int] = {}
_day = None


def _market_open(now: dt.datetime) -> bool:
    if now.weekday() >= 5:                       # Sat/Sun
        return False
    t = now.time()
    return dt.time(9, 15) <= t <= dt.time(15, 30)


def _reset_if_new_day(now: dt.datetime):
    global _day, _trades_today
    if _day != now.date():
        _day, _trades_today = now.date(), {}


def evaluate(symbol: str, meta: dict):
    sid, seg = meta["under_security_id"], meta["under_exchange_segment"]
    step, lot = meta["strike_step"], meta["lot_size"]

    df = market.get_intraday_underlying(sid, seg, config.UNDERLYING_TF)
    expiries = market.get_expiries(sid, seg)
    chain = market.get_option_chain(sid, seg, expiries[0])

    sig_oi = oi_chain.analyze(chain, step)
    signals = [
        technical.analyze(df),
        support_resistance.analyze(df),
        sig_oi,
        news.analyze(symbol),
        sentiment.analyze(sig_oi.data),
        fundamentals.analyze(symbol, is_index=True),
    ]

    sr = next(s for s in signals if s.name == "support_resistance")
    levels = {"support": round(sr.data.get("nearest_support", 0)),
              "resistance": round(sr.data.get("nearest_resistance", 0)),
              "oi_support": sig_oi.data.get("oi_support"),
              "oi_resistance": sig_oi.data.get("oi_resistance")}

    d = decide(symbol, signals, chain, lot, step, levels,
               _trades_today.get(symbol, 0))

    # set invalidation level based on chosen side
    if d.action.endswith("CE"):
        d.levels["invalidation"] = levels["support"]
    elif d.action.endswith("PE"):
        d.levels["invalidation"] = levels["resistance"]

    if d.action != "NO TRADE":
        _trades_today[symbol] = _trades_today.get(symbol, 0) + 1

    # paper logging: score existing open positions, then record this decision
    paper_log.mark_to_market(symbol, chain)
    paper_log.record(d)

    notifier.send(notifier.format_message(d))
    return d


def run_once():
    now = dt.datetime.now(IST)
    _reset_if_new_day(now)
    for symbol, meta in config.FNO_UNDERLYINGS.items():
        try:
            evaluate(symbol, meta)
        except Exception as e:                   # noqa: BLE001
            print(f"[{symbol}] evaluation error: {e}")


def run_loop():
    print(f"Pipeline live. Scanning every {config.SCAN_INTERVAL_MIN} min during market hours. Ctrl-C to stop.")
    while True:
        now = dt.datetime.now(IST)
        if _market_open(now):
            run_once()
        # sleep to the next bar boundary
        step = config.SCAN_INTERVAL_MIN * 60
        sleep_s = step - (now.minute * 60 + now.second) % step + 2
        time.sleep(max(5, sleep_s))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    run_loop() if mode == "loop" else run_once()
