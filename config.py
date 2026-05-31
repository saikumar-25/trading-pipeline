"""
Configuration for the trading toolkit.

SECURITY: secrets are NOT stored here. They come from (in order):
  1. environment variables  (used in the cloud: GitHub Actions / Streamlit secrets)
  2. local_settings.py      (used on your machine; gitignored, never pushed)
This file is safe to commit to GitHub.
"""
import os

try:
    import local_settings as _ls       # your machine only (gitignored)
except Exception:                       # noqa: BLE001
    _ls = None


def _secret(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val:
        return val
    if _ls is not None and getattr(_ls, name, None):
        return getattr(_ls, name)
    return default


# --- Dhan API credentials (blank here on purpose; provided via env/local_settings) ---
DHAN_CLIENT_ID = _secret("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = _secret("DHAN_ACCESS_TOKEN")

# --- Auto token refresh (eliminates the 24h interruption) ---
# Setup TOTP on web.dhan.co, then provide DHAN_PIN + DHAN_TOTP_SECRET via
# env vars (cloud) or local_settings.py (your machine).
DHAN_PIN = _secret("DHAN_PIN")
DHAN_TOTP_SECRET = _secret("DHAN_TOTP_SECRET")

# --- Instruments to research (Dhan security IDs) ---
# Find security IDs in Dhan's instrument master CSV:
#   https://images.dhan.co/api-data/api-scrip-master.csv
# Example below uses placeholder IDs; replace with the ones you trade.
INSTRUMENTS = {
    "RELIANCE":  {"security_id": "2885",  "exchange_segment": "NSE_EQ"},
    "TCS":       {"security_id": "11536", "exchange_segment": "NSE_EQ"},
    "HDFCBANK":  {"security_id": "1333",  "exchange_segment": "NSE_EQ"},
    "INFY":      {"security_id": "1594",  "exchange_segment": "NSE_EQ"},
    "ICICIBANK": {"security_id": "4963",  "exchange_segment": "NSE_EQ"},
    "SBIN":      {"security_id": "3045",  "exchange_segment": "NSE_EQ"},
}

# --- Backtest settings ---
TIMEFRAME = "DAY"          # "DAY" or minutes: "1","5","15","25","60"
LOOKBACK_YEARS = 5         # Dhan provides up to 5 years
STARTING_CAPITAL = 100000  # rupees, for backtest sizing

# --- Realistic cost model (Indian equity delivery/intraday approx.) ---
# These are conservative defaults; tune to your actual broker plan.
BROKERAGE_PER_SIDE = 20.0      # flat Rs per order (Dhan-style discount)
SLIPPAGE_BPS = 5.0             # 5 basis points per side
STT_BPS = 25.0                # securities transaction tax, sell side (delivery ~0.1% = 10bps; intraday differs)
OTHER_CHARGES_BPS = 3.0       # exchange txn + gst + sebi + stamp, rough

# =====================================================================
#  MULTI-AGENT INTRADAY OPTIONS PIPELINE
# =====================================================================

# --- Telegram alerts (provided via env/local_settings; not stored here) ---
TELEGRAM_BOT_TOKEN = _secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _secret("TELEGRAM_CHAT_ID")

# --- F&O universe to watch (index options) ---
FNO_UNDERLYINGS = {
    "NIFTY":     {"under_security_id": 13, "under_exchange_segment": "IDX_I", "lot_size": 75,  "strike_step": 50},
    "BANKNIFTY": {"under_security_id": 25, "under_exchange_segment": "IDX_I", "lot_size": 35,  "strike_step": 100},
}

# --- Bar / scan cadence ---
SCAN_INTERVAL_MIN = 5          # evaluate on close of each 5-min bar
UNDERLYING_TF = "5"            # intraday minute timeframe for technical agent

# --- Decision-agent risk rules (deliberately conservative) ---
PAPER_MODE = True              # True = log only, never even hint at live orders
RISK_PER_TRADE_RS = 500.0      # max rupees risked per trade (set to YOUR comfort)
MAX_TRADES_PER_DAY = 2         # hard cap to prevent overtrading
MIN_EDGE = 0.30                # |combined score| must exceed this to act (0..1)
MIN_CONFIDENCE = 0.55          # aggregate confidence floor (0..1)
MIN_AGREEING_AGENTS = 3        # this many agents must agree on direction
REWARD_RISK = 1.5             # target = this multiple of risk
STOP_PREMIUM_PCT = 0.30        # stop-loss at 30% of option premium paid
MAX_ENTRY_SLIPPAGE_PCT = 0.08  # never pay more than +8% above the signal premium (anti-chase)

# --- Agent weights (how much each voice counts in the blend) ---
AGENT_WEIGHTS = {
    "technical":          1.0,
    "support_resistance": 1.0,
    "oi_chain":           1.2,   # OI is central for options
    "news":               0.7,
    "sentiment":          0.6,
    "fundamentals":       0.2,   # near-irrelevant for index intraday; kept low
}

# --- Optional LLM for news sentiment (leave blank = use built-in lexicon) ---
LLM_API_KEY = ""
LLM_MODEL = "claude-haiku-4-5-20251001"
