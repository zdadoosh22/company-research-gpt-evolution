"""
BASE EVOLUTION FACTOR INTERFACE (base_factor.py)
Modular, Pluggable Tactical Alpha Factor Protocol
=================================================
Allows autonomous generations to introduce independent, testable alpha sub-engines
without destructive modifications to core execution infrastructure.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Any


@dataclass
class FactorSignal:
    ticker: str
    action: Literal["BUY", "SELL", "HOLD", "SCALE_OUT"]
    conviction: float               # 0.0 to 1.0 confidence score
    target_pillar: str              # e.g., "PILLAR_6_MICROSTRUCTURE_ALPHA"
    entry_price: float
    stop_loss: float
    take_profit: float
    regime: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseEvolutionFactor(ABC):
    def __init__(self, factor_id: str, name: str, rationale: str):
        self.factor_id = factor_id
        self.name = name
        self.rationale = rationale
        self.enabled = True

    @abstractmethod
    def compute_signals(self, market_data: dict[str, list[dict]], current_date: str, regime_context: dict) -> list[FactorSignal]:
        """
        Evaluate market universe data up to current_date.
        Must strictly respect causal time boundaries (no lookahead bias).
        """
        pass

    @abstractmethod
    def evaluate_exit(self, position: dict, current_bar: dict, current_date: str) -> tuple[bool, str, float]:
        """
        Returns (should_exit: bool, exit_reason: str, exit_price: float).
        """
        pass
