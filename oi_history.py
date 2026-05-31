"""
Lightweight intraday OI snapshot store, so the OI agent can see how Open
Interest is *trending through the session* (not just a single snapshot).
Resets each day. Persisted to oi_history.json (committed in the cloud run).
"""
from __future__ import annotations
import json
import os
import datetime as dt

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oi_history.json")


def _load() -> dict:
    if os.path.exists(PATH):
        try:
            return json.load(open(PATH))
        except Exception:           # noqa: BLE001
            pass
    return {}


def record_and_trend(symbol: str, ce_oi: float, pe_oi: float, pcr: float) -> dict:
    """Append today's snapshot and return the intraday trend vs session open."""
    data = _load()
    today = dt.date.today().isoformat()
    if data.get("date") != today:
        data = {"date": today, "symbols": {}}

    snaps = data.setdefault("symbols", {}).setdefault(symbol, [])
    snaps.append({"t": dt.datetime.now().strftime("%H:%M"),
                  "ce": round(ce_oi, 1), "pe": round(pe_oi, 1), "pcr": round(pcr, 3)})
    data["symbols"][symbol] = snaps[-120:]
    try:
        json.dump(data, open(PATH, "w"))
    except Exception:               # noqa: BLE001
        pass

    if len(snaps) >= 2:
        first = snaps[0]
        return {"pcr_open": first["pcr"], "pcr_delta": round(pcr - first["pcr"], 3),
                "ce_delta": round(ce_oi - first["ce"], 1),
                "pe_delta": round(pe_oi - first["pe"], 1), "n": len(snaps)}
    return {"pcr_open": round(pcr, 3), "pcr_delta": 0.0,
            "ce_delta": 0.0, "pe_delta": 0.0, "n": len(snaps)}
