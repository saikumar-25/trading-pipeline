# Multi-agent intraday options pipeline

Live data in → six specialist agents → decision agent (risk-gated) → Telegram alert.
**It never places orders.** Every alert is a proposal you act on manually.

```
                 ┌─────────────────────────────────────────────┐
  Dhan API ─────▶│  technical   support/resistance   oi_chain   │
 (intraday +     │  news        sentiment            fundamentals│
  option chain)  └───────────────────┬─────────────────────────┘
                                      ▼  each → {score -1..+1, confidence, notes}
                            ┌──────────────────┐
                            │  DECISION AGENT   │  weighted blend + hard risk gates
                            │  default: NO TRADE│
                            └─────────┬─────────┘
                                      ▼
                          Telegram message (you place the trade)
```

## The agents
| Agent | What it reads | Output |
|---|---|---|
| `technical` | underlying 5-min bars | EMA stack, MACD, RSI → trend/momentum score |
| `support_resistance` | underlying bars | floor pivots + swing levels → room up/down + invalidation levels |
| `oi_chain` | live option chain | PCR, OI buildup (support/resistance), ATM IV → directional bias |
| `news` | Google News headlines | finance-lexicon sentiment (LLM hook optional) |
| `sentiment` | option-chain internals | PCR/IV fear-greed regime |
| `fundamentals` | — | near-neutral for index intraday (honest placeholder; ready for single-stock) |

The decision agent multiplies each agent's score by its confidence and a config weight, then **only proposes a trade if ALL gates pass**: edge ≥ `MIN_EDGE`, confidence ≥ `MIN_CONFIDENCE`, at least `MIN_AGREEING_AGENTS` agree, daily trade cap not hit, and the risk budget covers ≥1 lot. Otherwise it stays flat. Given that ~91% of F&O traders lose, staying flat is the common — and correct — answer.

## Setup (one time)
1. **Telegram bot:** message `@BotFather` → `/newbot` → copy the token. Message `@userinfobot` to get your numeric chat ID. Put both in `config.py` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`), then send your bot any message once so it can reply to you.
2. **Risk knobs** in `config.py`: `RISK_PER_TRADE_RS`, `MAX_TRADES_PER_DAY`, `MIN_EDGE`, `MIN_CONFIDENCE`, `STOP_PREMIUM_PCT`, `REWARD_RISK`. Defaults are deliberately tight.
3. Keep `PAPER_MODE = True` until you've watched it for weeks.

## Run
```bash
cd trading_toolkit
python live_pipeline.py once    # one evaluation now (any time)
python live_pipeline.py loop    # continuous, every 5 min during market hours
```

## Hard limits & honesty
- **No auto-execution, ever.** The tool messages you; you decide and click.
- A green signal is *not* a prediction — it's a risk-bounded suggestion with a stop. Most days it will say NO TRADE.
- Index fundamentals don't matter intraday; that agent is intentionally low-weight.
- Your Dhan token expires (~24h) — regenerate and update `config.py` when fetches fail with auth errors.
- Live automated order placement (not used here) needs SEBI's static-IP + Algo-ID setup via Dhan.
- **Paper-trade first. Risk only money you can afford to lose. This is not income.**
