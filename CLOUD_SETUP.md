# Run the pipeline online (free) — setup guide

Two free pieces, no server to manage and nothing tied to your Mac:

```
GitHub Actions (engine)  ──► scans every 5 min in market hours
        │                     sends Telegram alerts
        │                     commits paper logs back to the repo
        ▼
Streamlit Community Cloud (dashboard)  ──► reads those logs, view from any phone
```

Your secrets never go into the repo — they live as GitHub/Streamlit **secrets**.
Files that must never be pushed are already in `.gitignore`:
`local_settings.py`, `token_cache.json`, `*.log`.

---

## Part A — Put the code on GitHub (public repo)

A public repo gives unlimited free Actions minutes. It's safe because it has **no secrets**.

1. Create a GitHub account (if needed) and a **new public repo**, e.g. `trading-pipeline`. Don't add a README.
2. On your Mac, push the `trading_toolkit` folder as the repo root:

```bash
cd "/Users/anvi/Documents/Claude/Projects/Trade app/trading_toolkit"
git init
git add .
git commit -m "trading pipeline"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/trading-pipeline.git
git push -u origin main
```

3. **Sanity check:** open the repo on github.com and confirm `local_settings.py` and `token_cache.json` are **NOT** there. If you see them, stop and tell me.

## Part B — Add your secrets to GitHub

Repo → **Settings → Secrets and variables → Actions → New repository secret**. Add these five:

| Name | Value |
|---|---|
| `DHAN_CLIENT_ID` | your Dhan client id |
| `DHAN_PIN` | your 6-digit Dhan PIN |
| `DHAN_TOTP_SECRET` | your base32 TOTP secret |
| `TELEGRAM_BOT_TOKEN` | your bot token |
| `TELEGRAM_CHAT_ID` | your group id (the negative number) |

## Part C — Turn the engine on

1. Repo → **Actions** tab → enable workflows if prompted.
2. Open **trading-pipeline** → **Run workflow** (the `workflow_dispatch` button) to test it once now. Check your Telegram group for a message and the **signals_log.csv** updating in the repo.
3. After that it runs automatically every 5 minutes during market hours.

## Part D — Deploy the dashboard

1. Go to **share.streamlit.io**, sign in with GitHub.
2. **Create app** → pick your repo, branch `main`, main file `dashboard.py`.
3. In the app's **Settings → Secrets**, add:

```
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/<YOUR_USERNAME>/trading-pipeline/main"
```

4. Deploy. You'll get a public URL (open it on your phone) showing latest signals + the paper scorecard, refreshing every minute.

---

## Good to know
- **Free:** public-repo Actions = unlimited minutes; Streamlit Community Cloud = free.
- **Token:** the engine mints its own Dhan token via TOTP and caches it between runs — no daily login.
- **Static IP:** not required, because this only reads data and sends alerts (no order placement).
- **Paper mode stays ON** until you change `PAPER_MODE` in `config.py`. Keep it on while you judge the scorecard.
- **Schedule note:** GitHub cron can occasionally lag a few minutes under load — fine for 5-min bars, not for split-second trades.
- **If you ever rotate your PIN/token:** update the GitHub secrets (and `local_settings.py` locally), then delete `token_cache.json` / clear the Actions cache.
