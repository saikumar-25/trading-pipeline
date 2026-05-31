# Trading toolkit (research only — never auto-trades)

## Run it now (no keys needed)
```bash
pip install pandas numpy tabulate
python run.py
```
Runs on synthetic demo data and writes `signals_report.md`.

## Switch to your real Dhan data
1. `pip install dhanhq`
2. In `config.py`, paste your `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN`
   (Dhan app → Profile → DhanHQ API → generate access token).
3. Find the **security IDs** for stocks you trade in Dhan's instrument master:
   https://images.dhan.co/api-data/api-scrip-master.csv
   Add them to `INSTRUMENTS` in `config.py`.
4. `python run.py` — it now backtests your instruments on up to 5 years of data.

## Files
- `config.py` — keys, instruments, costs, timeframe.
- `data.py` — fetches Dhan data (falls back to synthetic).
- `strategies.py` — MA crossover, momentum, RSI mean-reversion (white-box).
- `backtest.py` — vectorized backtest, realistic costs, no look-ahead.
- `run.py` — runs everything, prints comparison, writes `signals_report.md`.

## Important
- Output is **signals you act on manually**. Nothing is ordered for you.
- A good backtest is not future profit. Paper-trade first, size tiny, risk only what you can lose.
- For *live* personal algo trading, SEBI's April 2026 rules need static IP, OAuth+2FA, and an exchange Algo-ID via Dhan. Under 10 orders/sec with transparent rules = no separate registration.
