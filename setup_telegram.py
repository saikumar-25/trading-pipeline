"""
One-time Telegram setup.

For a PRIVATE chat: open your bot, press Start, send 'hi', then run this.
For a GROUP: create the group, add the bot, make it an ADMIN (so it can see
messages), post any message in the group, then run this. Groups have negative
IDs and this script prefers them automatically.

    python setup_telegram.py
"""
import json
import os
import re
import urllib.parse

import config
import netctx

TOKEN = config.TELEGRAM_BOT_TOKEN


def _api(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return json.load(netctx.urlopen(url, timeout=10))


def _set_local(key: str, value: str):
    """Insert/replace a KEY = "value" line in local_settings.py."""
    path = "local_settings.py"
    src = open(path).read() if os.path.exists(path) else ""
    line = f'{key} = "{value}"'
    if re.search(rf'^{key}\s*=', src, flags=re.M):
        src = re.sub(rf'^{key}\s*=.*$', line, src, count=1, flags=re.M)
    else:
        src = (src.rstrip() + "\n" + line + "\n") if src else line + "\n"
    open(path, "w").write(src)


def main():
    netctx.enable_global()
    if not TOKEN:
        print("No TELEGRAM_BOT_TOKEN in config.py"); return
    r = _api("getUpdates")
    chats = {}      # id -> (name, type)
    for u in r.get("result", []):
        m = (u.get("message") or u.get("channel_post")
             or u.get("my_chat_member", {}).get("chat") and u["my_chat_member"] or {})
        ch = (m.get("chat") if isinstance(m, dict) else None) or {}
        if ch.get("id"):
            chats[ch["id"]] = (ch.get("title") or ch.get("first_name") or "?",
                               ch.get("type", "?"))
    if not chats:
        print("No chats found yet.\n"
              " - Private: open the bot, press Start, send 'hi'.\n"
              " - Group: add the bot as ADMIN and post a message in the group.\n"
              "Then re-run this script.")
        return

    print("Chats the bot can see:")
    for cid, (name, ctype) in chats.items():
        print(f"  {cid}  [{ctype}]  {name}")

    # prefer a group/supergroup (negative id) if present, else first chat
    groups = {cid: v for cid, v in chats.items()
              if v[1] in ("group", "supergroup") or int(cid) < 0}
    chat_id, (name, ctype) = (next(iter(groups.items())) if groups
                              else next(iter(chats.items())))
    print(f"\nSelected: {name} (id {chat_id}, {ctype})")

    _set_local("TELEGRAM_CHAT_ID", str(chat_id))
    print("Wrote TELEGRAM_CHAT_ID to local_settings.py")

    _api("sendMessage", {"chat_id": chat_id,
                         "text": "✅ Trading pipeline connected. Alerts will arrive here."})
    print("Sent a test message — check Telegram.")


if __name__ == "__main__":
    main()
