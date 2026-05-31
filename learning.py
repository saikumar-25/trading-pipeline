"""
Lightweight 'learning' = honest measurement, not a magic optimizer.

Aggregates per-symbol paper performance from paper_positions.csv and, once a
symbol has enough closed trades, AUTO-MUTES names with negative expectancy so
the engine stops wasting attention on instruments that don't work for it.

Recomputed from the full log each time (idempotent — no double counting).
Caveat: intraday options data is noisy; MIN_SAMPLE is deliberately high so we
don't mute on a few unlucky trades.
"""
from __future__ import annotations
import csv
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))
POSITIONS = os.path.join(DIR, "paper_positions.csv")
PATH = os.path.join(DIR, "learning.json")
MIN_SAMPLE = 10           # need this many closed trades before muting a symbol


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compute() -> dict:
    stats = {}
    for r in _read(POSITIONS):
        if r.get("status") not in ("WIN", "LOSS"):
            continue
        s = stats.setdefault(r["symbol"], {"trades": 0, "wins": 0, "net_pnl": 0.0})
        s["trades"] += 1
        s["wins"] += 1 if r["status"] == "WIN" else 0
        try:
            s["net_pnl"] += float(r["pnl_rs"] or 0)
        except ValueError:
            pass
    for d in stats.values():
        d["win_rate"] = round(d["wins"] / d["trades"] * 100, 1) if d["trades"] else 0
        d["expectancy"] = round(d["net_pnl"] / d["trades"], 0) if d["trades"] else 0
    muted = sorted(s for s, d in stats.items()
                   if d["trades"] >= MIN_SAMPLE and d["expectancy"] < 0)
    out = {"symbols": stats, "muted": muted}
    try:
        json.dump(out, open(PATH, "w"), indent=1)
    except Exception:           # noqa: BLE001
        pass
    return out


def muted_symbols() -> set:
    if os.path.exists(PATH):
        try:
            return set(json.load(open(PATH)).get("muted", []))
        except Exception:       # noqa: BLE001
            pass
    return set()
