"""
Streamlit dashboard for the trading pipeline.

Local:   streamlit run dashboard.py
Cloud:   deploy on Streamlit Community Cloud (free) from your GitHub repo.

Reads the paper-trade logs the engine produces. When deployed, set
GITHUB_RAW_BASE in the app's Secrets to your repo's raw URL so it shows the
freshest committed data, e.g.:
  GITHUB_RAW_BASE = "https://raw.githubusercontent.com/<user>/<repo>/main"
If unset, it reads the local CSV files.
"""
from __future__ import annotations
import io
import os
import urllib.request

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Trading Pipeline", page_icon="📊", layout="wide")

RAW_BASE = os.getenv("GITHUB_RAW_BASE") or st.secrets.get("GITHUB_RAW_BASE", "") \
    if hasattr(st, "secrets") else os.getenv("GITHUB_RAW_BASE", "")


@st.cache_data(ttl=60)
def _load(name: str) -> pd.DataFrame:
    try:
        if RAW_BASE:
            url = f"{RAW_BASE}/{name}"
            data = urllib.request.urlopen(url, timeout=10).read()
            return pd.read_csv(io.BytesIO(data))
        if os.path.exists(name):
            return pd.read_csv(name)
    except Exception as e:                  # noqa: BLE001
        st.warning(f"Could not load {name}: {e}")
    return pd.DataFrame()


st.title("📊 Multi-Agent Trading Pipeline")
st.caption("LIVE Dhan market data (real prices, OI, scores). "
           "‘Paper’ only means outcomes are simulated on real prices — no orders are "
           "actually placed. Not investment advice.")

signals = _load("signals_log.csv")
positions = _load("paper_positions.csv")

# ---- scorecard ----
st.subheader("Paper-trading scorecard")
if positions.empty:
    st.info("No paper trades yet. The engine logs here once it proposes trades.")
else:
    closed = positions[positions["status"].isin(["WIN", "LOSS"])]
    wins = (closed["status"] == "WIN").sum()
    n = len(closed)
    pnl = pd.to_numeric(closed["pnl_rs"], errors="coerce").sum()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trades taken", len(positions))
    c2.metric("Closed", n)
    c3.metric("Win rate", f"{(wins/n*100):.0f}%" if n else "—")
    c4.metric("Net P/L (₹)", f"{pnl:,.0f}")
    c5.metric("Open", int((positions["status"] == "open").sum()))
    if n and pnl <= 0:
        st.error("Expectancy not positive yet — do NOT go live.")
    elif n >= 30 and pnl > 0:
        st.success("Positive expectancy over a meaningful sample.")

# ---- per-call results (what happened if you'd taken each call) ----
st.subheader("Calls & results")
if positions.empty:
    st.info("No calls generated yet. Each BUY call and its outcome will appear here.")
else:
    cols = [c for c in ["open_time", "symbol", "action", "strike", "type", "expiry",
                        "entry", "stop", "target", "status", "exit_price", "pnl_rs",
                        "reason"] if c in positions.columns]
    res = positions[cols].iloc[::-1]

    def _color_status(row):
        s = str(row.get("status", ""))
        bg = ("background-color: #1b3a1b" if s == "WIN"
              else "background-color: #3a1b1b" if s == "LOSS" else "")
        return [bg for _ in row]
    st.dataframe(res.style.apply(_color_status, axis=1), use_container_width=True)
    st.caption("WIN/LOSS = paper outcome at next-bar fill. 'pending'/'open' = still live. "
               "Entry is the realistic next-bar fill, not the signal price.")

# ---- latest signals (all decisions, incl. NO TRADE) ----
st.subheader("All decisions (incl. NO TRADE)")
if signals.empty:
    st.info("No signals logged yet.")
else:
    sig = signals.tail(20).iloc[::-1]
    def _color(row):
        a = str(row.get("action", ""))
        return ["background-color: #1b3a1b" if "BUY" in a else "" for _ in row]
    st.dataframe(sig.style.apply(_color, axis=1), use_container_width=True)

# ---- open positions ----
if not positions.empty:
    st.subheader("Open positions")
    op = positions[positions["status"] == "open"]
    st.dataframe(op if not op.empty else pd.DataFrame({"info": ["none open"]}),
                 use_container_width=True)

st.caption("Data refreshes ~every minute. Source: GitHub Actions engine.")
