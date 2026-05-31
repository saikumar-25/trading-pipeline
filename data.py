"""
Data layer: fetch OHLCV from Dhan if credentials exist, else generate
realistic synthetic data so the whole toolkit runs out-of-the-box.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd

import config


def _synthetic_ohlcv(years: int, seed: int = 42) -> pd.DataFrame:
    """Geometric-Brownian-motion daily candles. For demo/testing only."""
    rng = np.random.default_rng(seed)
    n = years * 252
    dates = pd.bdate_range(end=dt.date.today(), periods=n)
    mu, sigma = 0.08 / 252, 0.018          # mild upward drift, ~1.8% daily vol
    rets = rng.normal(mu, sigma, n)
    close = 1000 * np.exp(np.cumsum(rets))
    # build OHLC around the close path
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = rng.integers(1_00_000, 50_00_000, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=dates,
    )


def fetch_ohlcv(name: str, meta: dict) -> tuple[pd.DataFrame, str]:
    """
    Returns (dataframe, source_label).
    Uses Dhan if config has credentials AND a real security_id, else synthetic.
    """
    have_creds = bool(config.DHAN_CLIENT_ID and config.DHAN_ACCESS_TOKEN)
    real_id = meta.get("security_id", "0000") not in ("0000", "", None)

    if have_creds and real_id:
        import time
        for attempt in range(3):
            try:
                return _fetch_dhan(name, meta), "DHAN (live)"
            except Exception as e:                 # noqa: BLE001
                if attempt < 2:
                    time.sleep(1.0)                # transient hiccup / pacing
                    continue
                print(f"  ! Dhan fetch failed for {name}: {e}\n    -> using synthetic data")

    return _synthetic_ohlcv(config.LOOKBACK_YEARS), "SYNTHETIC (demo)"


def _fetch_dhan(name: str, meta: dict) -> pd.DataFrame:
    """Pull historical candles via the official dhanhq client."""
    from dhanhq import DhanContext, dhanhq  # pip install dhanhq (v2.x)

    ctx = DhanContext(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
    client = dhanhq(ctx)
    to_date = dt.date.today()
    from_date = to_date - dt.timedelta(days=int(config.LOOKBACK_YEARS * 365))

    if config.TIMEFRAME.upper() == "DAY":
        resp = client.historical_daily_data(
            security_id=meta["security_id"],
            exchange_segment=meta["exchange_segment"],
            instrument_type="EQUITY",
            from_date=str(from_date),
            to_date=str(to_date),
        )
    else:
        resp = client.intraday_minute_data(
            security_id=meta["security_id"],
            exchange_segment=meta["exchange_segment"],
            instrument_type="EQUITY",
            from_date=str(from_date),
            to_date=str(to_date),
            interval=int(config.TIMEFRAME),
        )

    if isinstance(resp, dict) and resp.get("status") not in (None, "success"):
        raise RuntimeError(resp.get("remarks") or resp)
    data = resp.get("data", resp)
    if not (isinstance(data, dict) and "close" in data):
        raise RuntimeError(f"unexpected response shape: {str(data)[:120]}")
    df = pd.DataFrame(data)
    # Dhan returns 'timestamp' (epoch) + open/high/low/close/volume
    ts_col = "timestamp" if "timestamp" in df else "start_Time"
    df.index = pd.to_datetime(df[ts_col], unit="s")
    return df[["open", "high", "low", "close", "volume"]].astype(float)
