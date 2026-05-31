"""Telegram notifier + message formatting. No-ops gracefully if unconfigured."""
from __future__ import annotations
import datetime as dt
import json
import urllib.request

import config
import netctx
from decision import Decision


def format_message(d: Decision) -> str:
    t = dt.datetime.now().strftime("%H:%M")
    lines = [f"📊 {d.symbol}  ({t})  [{'PAPER' if config.PAPER_MODE else 'LIVE-SIGNAL'}]"]

    if d.action == "NO TRADE":
        lines.append(f"➖ NO TRADE — {d.reason}")
        lines.append(f"   score {d.combined_score:+.2f} | conf {d.confidence:.2f} | agree {d.agreeing}")
    else:
        c = d.contract
        arrow = "🟢" if "CE" in d.action else "🔴"
        side = "above" if "CE" in d.action else "below"
        inval = d.levels.get("invalidation")
        lines += [
            f"{arrow} {d.action}  {d.symbol} {c['strike']:.0f} {c['type']}  exp {c.get('expiry', '?')}",
            f"   Signal premium ~{c['entry']} (as of {t} bar)",
            f"   ➡️ Enter ONLY if premium ≤ {c.get('max_entry', c['entry'])}  (don't chase)",
            f"   Stop {c['stop']}  Target {c['target']}",
            f"   Size {c['lots']} lot(s) = {c['qty']} qty",
            f"   Max loss ≈ Rs{c['max_loss_rs']:.0f} | Target gain ≈ Rs{c['target_gain_rs']:.0f}",
        ]
        if inval:
            lines.append(f"   Thesis valid while {d.symbol} stays {side} {inval}")
        lines += [
            f"   Why: {d.reason}",
            "   ⚠️ You place the order. If price already ran past the max-entry, SKIP it.",
        ]

    # one-line agent breakdown
    brk = " | ".join(f"{s.name}:{s.score:+.1f}" for s in d.signals)
    lines.append(f"   Agents → {brk}")
    return "\n".join(lines)


def send(text: str) -> bool:
    token, chat = config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID
    if not token or not chat:
        print("[telegram not configured — message below]\n" + text)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with netctx.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:                       # noqa: BLE001
        print(f"[telegram send failed: {e}]\n{text}")
        return False
