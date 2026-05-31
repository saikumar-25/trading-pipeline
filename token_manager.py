"""
Dhan access-token auto-refresh via TOTP.

The manual token lasts 24h. This module mints a fresh one on demand using
Dhan's TOTP endpoint (no browser, no clicking), caches it in token_cache.json,
and refreshes automatically when it's missing or about to expire. A long-running
pipeline therefore never breaks at the 24h boundary.

Requirements:
  pip install pyotp
  Enable TOTP on web.dhan.co and set config.DHAN_PIN + config.DHAN_TOTP_SECRET
  (or env vars DHAN_PIN / DHAN_TOTP_SECRET).
"""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.request

import config
import netctx

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token_cache.json")
REFRESH_BEFORE_MIN = 30          # refresh when <30 min validity remains


def _secret() -> str | None:
    return os.getenv("DHAN_TOTP_SECRET") or config.DHAN_TOTP_SECRET or None


def _pin() -> str | None:
    return os.getenv("DHAN_PIN") or config.DHAN_PIN or None


def _load_cache():
    if os.path.exists(CACHE):
        try:
            d = json.load(open(CACHE))
            return d.get("access_token"), d.get("expiry")
        except Exception:           # noqa: BLE001
            pass
    return None, None


def _save_cache(token: str, expiry: str):
    json.dump({"access_token": token, "expiry": expiry}, open(CACHE, "w"))


def _expiring_soon(expiry: str | None) -> bool:
    if not expiry:
        return True
    try:
        exp = dt.datetime.fromisoformat(expiry.replace("Z", ""))
    except Exception:               # noqa: BLE001
        return True
    return dt.datetime.now() >= exp - dt.timedelta(minutes=REFRESH_BEFORE_MIN)


def _generate_via_totp() -> tuple[str, str]:
    import pyotp
    netctx.enable_global()
    totp = pyotp.TOTP(_secret()).now()
    url = ("https://auth.dhan.co/app/generateAccessToken"
           f"?dhanClientId={config.DHAN_CLIENT_ID}&pin={_pin()}&totp={totp}")
    req = urllib.request.Request(url, method="POST")
    resp = json.load(netctx.urlopen(req, timeout=15))
    token = resp.get("accessToken")
    if not token:
        raise RuntimeError(f"token generation failed: {resp}")
    return token, resp.get("expiryTime", "")


def get_valid_token() -> str:
    """Return a usable token, refreshing via TOTP if needed.
    Falls back to the static config token if TOTP isn't configured."""
    token, expiry = _load_cache()
    if token and not _expiring_soon(expiry):
        return token

    if _secret() and _pin():
        try:
            token, expiry = _generate_via_totp()
            _save_cache(token, expiry)
            print(f"[token] refreshed via TOTP, valid until {expiry}")
            return token
        except Exception as e:      # noqa: BLE001
            print(f"[token] TOTP refresh failed ({e}); using static config token")

    return config.DHAN_ACCESS_TOKEN


if __name__ == "__main__":
    t = get_valid_token()
    print("token (first 24 chars):", t[:24] + "...")
    _, exp = _load_cache()
    print("cached expiry:", exp or "(static config token, no cache)")
