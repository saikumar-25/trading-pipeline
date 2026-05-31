"""News agent: pull recent headlines for the underlying and score sentiment.

Default scorer is a transparent finance lexicon (no API key needed). If
config.LLM_API_KEY is set, you can swap in an LLM scorer (hook provided).
News fetch uses Google News RSS at runtime on the user's machine.
"""
from __future__ import annotations
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import netctx
from .base import AgentSignal, neutral

_POS = {"surge", "rally", "gain", "jump", "rise", "beat", "upgrade", "bullish",
        "record", "strong", "boost", "outperform", "buy", "soars", "rebound",
        "recovery", "optimism", "inflows", "cuts rate", "stimulus"}
_NEG = {"fall", "drop", "plunge", "slump", "crash", "miss", "downgrade",
        "bearish", "weak", "loss", "selloff", "fear", "cut", "warning",
        "slowdown", "outflows", "tariff", "war", "hike", "default", "fraud"}


def _fetch_headlines(query: str, limit: int = 15) -> list[str]:
    q = urllib.parse.quote(f"{query} stock market India")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with netctx.urlopen(req, timeout=8) as r:
            root = ET.fromstring(r.read())
        return [it.findtext("title", "") for it in root.iter("item")][:limit]
    except Exception:
        return []


def _lexicon_score(titles: list[str]) -> tuple[float, int]:
    pos = neg = 0
    for t in titles:
        tl = t.lower()
        pos += sum(w in tl for w in _POS)
        neg += sum(w in tl for w in _NEG)
    total = pos + neg
    if total == 0:
        return 0.0, 0
    return (pos - neg) / total, total


def analyze(query: str, headlines: list[str] | None = None) -> AgentSignal:
    titles = headlines if headlines is not None else _fetch_headlines(query)
    if not titles:
        return neutral("news", "no headlines fetched")
    score, hits = _lexicon_score(titles)
    confidence = min(0.65, 0.25 + 0.04 * hits)
    top = titles[0][:80]
    return AgentSignal("news", score, confidence,
                       f"{len(titles)} headlines, net tone {score:+.2f}; e.g. '{top}'",
                       {"headline_count": len(titles)}).clamp()
