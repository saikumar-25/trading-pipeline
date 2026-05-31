"""Shared SSL handling.

Fixes 'CERTIFICATE_VERIFY_FAILED' on python.org macOS builds AND on networks
with a TLS-inspecting proxy/antivirus (self-signed root injected into the chain)
by using the operating-system trust store via `truststore` when available,
then falling back to certifi, then the default context.

    pip install truststore certifi
"""
import ssl
import urllib.request

_injected = False


def enable_global() -> str:
    """Patch ssl so requests/dhanhq (not just urllib) trust the OS store.
    Safe to call repeatedly. Returns which backend is active."""
    global _injected
    if _injected:
        return "truststore"
    try:
        import truststore
        truststore.inject_into_ssl()
        _injected = True
        return "truststore"
    except Exception:                       # noqa: BLE001
        return "default"


def make_context() -> ssl.SSLContext:
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:                       # noqa: BLE001
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:                       # noqa: BLE001
        return ssl.create_default_context()


def urlopen(req_or_url, data=None, timeout=10):
    """Drop-in urllib.request.urlopen that trusts the OS/certifi store."""
    return urllib.request.urlopen(req_or_url, data=data, timeout=timeout,
                                  context=make_context())
