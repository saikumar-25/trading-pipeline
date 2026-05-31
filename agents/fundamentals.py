"""Fundamentals agent.

Honest note: for INDEX intraday options, company fundamentals are essentially
irrelevant on a 5-minute horizon. This agent therefore returns low-confidence,
near-neutral output for indices (and is weighted ~0.2 in config). It exists so
the pipeline is complete and ready if you later add single-stock options, where
fundamentals (earnings dates, results) actually matter.
"""
from __future__ import annotations
from .base import AgentSignal


def analyze(symbol: str, is_index: bool = True) -> AgentSignal:
    if is_index:
        return AgentSignal(
            "fundamentals", 0.0, 0.15,
            "fundamentals not material for index intraday (placeholder)", {})
    # Hook for single-stock: plug earnings surprise / valuation here later.
    return AgentSignal("fundamentals", 0.0, 0.2,
                       "single-stock fundamentals not yet wired", {})
