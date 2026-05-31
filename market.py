"""
Live market-data helpers for the options pipeline (Dhan v2).
All functions degrade gracefully and raise clear errors on bad responses.
"""
from __future__ import annotations
import datetime as dt
import time
import pandas as pd

import config

_client = None
_client_token = None
_last_oc_call = 0.0          # option_chain is rate-limited (~1 req / 3s)


def client(force_token: bool = False):
    """Return a dhanhq client, rebuilding it if the access token has rotated
    (so a multi-day loop keeps working across the 24h token refresh)."""
    global _client, _client_token
    import netctx
    import token_manager
    token = token_manager.force_refresh() if force_token else token_manager.get_valid_token()
    if _client is None or token != _client_token:
        netctx.enable_global()      # make dhanhq/requests trust OS store too
        from dhanhq import DhanContext, dhanhq
        _client = dhanhq(DhanContext(config.DHAN_CLIENT_ID, token))
        _client_token = token
    return _client


def _with_auth_retry(fn):
    """Run a client call; if it fails (often a stale/invalidated token that the
    cached expiry can't detect), force-refresh the token once and retry."""
    try:
        return fn(client())
    except Exception:               # noqa: BLE001
        return fn(client(force_token=True))


def get_expiries(under_security_id: int, segment: str) -> list[str]:
    def call(c):
        r = c.expiry_list(under_security_id=under_security_id,
                          under_exchange_segment=segment)
        if r.get("status") != "success":
            raise RuntimeError(f"expiry_list failed: {r}")
        data = r["data"]
        return data.get("data", data) if isinstance(data, dict) else data
    return _with_auth_retry(call)


def get_option_chain(under_security_id: int, segment: str, expiry: str) -> dict:
    """Returns {'last_price': float, 'oc': {strike: {ce:{...}, pe:{...}}}}."""
    global _last_oc_call
    wait = 3.1 - (time.time() - _last_oc_call)
    if wait > 0:
        time.sleep(wait)

    def call(c):
        r = c.option_chain(under_security_id=under_security_id,
                           under_exchange_segment=segment, expiry=expiry)
        if r.get("status") != "success":
            raise RuntimeError(f"option_chain failed: {r}")
        return r["data"]["data"]
    result = _with_auth_retry(call)
    _last_oc_call = time.time()
    return result


def detect_strike_step(chain: dict) -> float | None:
    """Smallest positive gap between adjacent strikes = the strike step."""
    ks = sorted(float(k) for k in (chain.get("oc") or {}).keys())
    diffs = sorted({round(b - a, 2) for a, b in zip(ks, ks[1:]) if b > a})
    return diffs[0] if diffs else None


def get_intraday_underlying(under_security_id: int, segment: str,
                            interval: str = "5", days: int = 5,
                            instrument_type: str = "INDEX") -> pd.DataFrame:
    to_date = dt.date.today()
    from_date = to_date - dt.timedelta(days=days)

    def call(c):
        r = c.intraday_minute_data(
            security_id=str(under_security_id),
            exchange_segment=segment,
            instrument_type=instrument_type,
            from_date=str(from_date),
            to_date=str(to_date),
            interval=int(interval),
        )
        if r.get("status") != "success":
            raise RuntimeError(f"intraday failed: {r}")
        return r["data"]
    d = _with_auth_retry(call)
    df = pd.DataFrame(d)
    df.index = pd.to_datetime(df["timestamp"], unit="s")
    return df[["open", "high", "low", "close", "volume"]].astype(float)
