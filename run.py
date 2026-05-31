"""
Entry point. Runs every strategy on every configured instrument, prints a
comparison table, and writes today's signals to signals_report.md.

    python run.py

Works with no credentials (synthetic demo data). Add Dhan keys + real
security IDs in config.py to backtest your actual instruments.

This tool is RESEARCH ONLY. It never places orders. You review the signals
and trade manually.
"""
from __future__ import annotations
import datetime as dt
import pandas as pd

import config
import data
import strategies
import backtest


def main() -> None:
    rows, signals = [], []

    for name, meta in config.INSTRUMENTS.items():
        df, source = data.fetch_ohlcv(name, meta)
        print(f"\n=== {name}  [{source}]  {df.index[0].date()} -> {df.index[-1].date()}  ({len(df)} bars) ===")

        for strat_name, fn in strategies.REGISTRY.items():
            pos = fn(df)
            res = backtest.run(df, pos)
            m = res["metrics"]
            rows.append({"instrument": name, "strategy": strat_name, **m})

            today_pos = int(pos.iloc[-1])
            yday_pos = int(pos.iloc[-2]) if len(pos) > 1 else 0
            action = "HOLD/IN" if today_pos else "FLAT/OUT"
            if today_pos and not yday_pos:
                action = ">>> ENTER LONG"
            elif yday_pos and not today_pos:
                action = "<<< EXIT"
            signals.append({"instrument": name, "strategy": strat_name,
                            "signal": action, "last_close": round(df['close'].iloc[-1], 2)})

        # buy & hold benchmark row
        bh = backtest.run(df, strategies.momentum(df) * 0 + 1)["bh_metrics"]
        rows.append({"instrument": name, "strategy": "buy_hold", **bh})

    table = pd.DataFrame(rows)
    pd.set_option("display.width", 140)
    print("\n\n========== BACKTEST COMPARISON ==========")
    print(table.to_string(index=False))

    _write_signal_report(signals, table)
    print("\nWrote signals_report.md  (review before any manual trade)")


def _write_signal_report(signals: list[dict], table: pd.DataFrame) -> None:
    today = dt.date.today().isoformat()
    lines = [f"# Trading signals — {today}", "",
             "> Research output only. No orders are placed automatically. "
             "Review, paper-trade, and size positions yourself.", "",
             "## Today's actions", ""]
    actionable = [s for s in signals if s["signal"].startswith((">>>", "<<<"))]
    if actionable:
        for s in actionable:
            lines.append(f"- **{s['signal']}** {s['instrument']} "
                         f"({s['strategy']}) @ {s['last_close']}")
    else:
        lines.append("- No new entries/exits today. All strategies holding prior state.")
    lines += ["", "## Full state", "",
              "| Instrument | Strategy | Signal | Last close |",
              "|---|---|---|---|"]
    for s in signals:
        lines.append(f"| {s['instrument']} | {s['strategy']} | {s['signal']} | {s['last_close']} |")
    lines += ["", "## Backtest summary", "", table.to_markdown(index=False)]

    with open("signals_report.md", "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
