"""
Vectorized long-only backtester with a realistic Indian-equity cost model.
No look-ahead: today's signal is applied to tomorrow's return, and costs are
charged on every position change.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

import config


def _per_trade_cost_fraction() -> float:
    """Round-trip cost as a fraction of traded notional (rough but honest)."""
    bps = (config.SLIPPAGE_BPS + config.OTHER_CHARGES_BPS) * 2 + config.STT_BPS
    return bps / 10_000.0


def run(df: pd.DataFrame, position: pd.Series) -> dict:
    px = df["close"]
    daily_ret = px.pct_change().fillna(0)

    # apply yesterday's signal to today's return
    pos = position.shift(1).fillna(0)

    # cost when the position changes (enter/exit)
    turns = pos.diff().abs().fillna(0)
    trade_cost = turns * _per_trade_cost_fraction()
    # add a flat brokerage hit per change, expressed as fraction of capital
    flat = turns.apply(lambda t: config.BROKERAGE_PER_SIDE / config.STARTING_CAPITAL if t else 0)

    strat_ret = pos * daily_ret - trade_cost - flat
    equity = (1 + strat_ret).cumprod() * config.STARTING_CAPITAL
    bh_equity = (1 + daily_ret).cumprod() * config.STARTING_CAPITAL

    return {
        "equity": equity,
        "buy_hold": bh_equity,
        "strat_ret": strat_ret,
        "metrics": _metrics(strat_ret, equity, pos, turns),
        "bh_metrics": _metrics(daily_ret, bh_equity, pd.Series(1, index=df.index), pd.Series(0, index=df.index)),
    }


def _metrics(ret: pd.Series, equity: pd.Series, pos: pd.Series, turns: pd.Series) -> dict:
    n = len(ret)
    years = n / 252 if n else 1
    total = equity.iloc[-1] / equity.iloc[0] - 1 if n else 0
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 else 0
    vol = ret.std() * np.sqrt(252)
    sharpe = (ret.mean() * 252) / vol if vol > 0 else 0
    roll_max = equity.cummax()
    max_dd = ((equity - roll_max) / roll_max).min()
    exposure = pos.mean()
    n_trades = int(turns.sum())
    wins = (ret[ret != 0] > 0).mean() if (ret != 0).any() else 0
    return {
        "Total return %": round(total * 100, 1),
        "CAGR %": round(cagr * 100, 1),
        "Sharpe": round(sharpe, 2),
        "Max drawdown %": round(max_dd * 100, 1),
        "Time in market %": round(exposure * 100, 1),
        "Trades": n_trades,
        "Win rate %": round(wins * 100, 1),
    }
