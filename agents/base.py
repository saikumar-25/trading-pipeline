"""Shared agent contract: every agent returns an AgentSignal."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class AgentSignal:
    name: str
    score: float          # -1.0 (bearish) .. +1.0 (bullish)
    confidence: float     # 0.0 .. 1.0
    notes: str            # human-readable one-liner(s)
    data: dict = field(default_factory=dict)

    def clamp(self) -> "AgentSignal":
        self.score = max(-1.0, min(1.0, self.score))
        self.confidence = max(0.0, min(1.0, self.confidence))
        return self


def neutral(name: str, notes: str = "no clear edge") -> AgentSignal:
    return AgentSignal(name=name, score=0.0, confidence=0.2, notes=notes)
