"""
EXPERIENCE BANK & INSTITUTIONAL QUANTITATIVE MEMORY (experience_bank.py)
Autonomous Knowledge Store to Prevent Hypothesis Cycling & Enforce Historical Learning
========================================================================================
"""

from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BANK_FILE = SCRIPT_DIR / "experience_bank.json"


class ExperienceBank:
    def __init__(self, filepath: Path = BANK_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._initialize_defaults()

    def _initialize_defaults(self) -> dict:
        return {
            "version": "2.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trading_rules_invariants": [
                "£1,000 Trading 212 Stocks & Shares ISA capital constraint.",
                "Exact 0.15% FX conversion fee on USD-denominated tickers.",
                "Long-only cash equity; shorting prohibited; downside hedging via synthetic inverse ETFs (SQQQ/QID).",
                "Holding periods: Intraday to multi-day tactical swing (max 10-15 days).",
                "Quarantined Out-of-Sample: 2021 to 2026 is strictly blind evaluation data."
            ],
            "heuristic_guardrails": [
                "Fixed percentage stops trigger excessive stop-outs in high-volatility regimes; always use dynamic ATR-scaled stops >= 1.5x ATR.",
                "High-frequency breakout trading on low-beta assets generates excessive fee drag (>0.30% roundtrip); only trade breakouts in Top 3 RS sectors.",
                "Inverse ETFs (SQQQ/QID) suffer from -2.85x daily volatility decay drag; holding beyond 5 consecutive days during chop guarantees capital erosion.",
                "During Bear and Chop regimes, RSI dip-sniping must require both RSI <= 30 AND lower Bollinger Band touch to prevent catching falling knives."
            ],
            "validated_alphas": [
                {
                    "generation": 1,
                    "hypothesis": "Baseline Engine Freeze v3.0: 5-Pillar All-Weather Profit Architecture",
                    "oos_return_pct": 91.59,
                    "oos_sharpe": 2.65,
                    "stress_tested_return_pct": 55.83,
                    "status": "ACTIVE_PRODUCTION_BENCHMARK"
                }
            ],
            "falsified_hypotheses": []
        }

    def save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def record_validated_alpha(self, generation: int, hypothesis: str, oos_return: float, oos_sharpe: float, stress_return: float):
        entry = {
            "generation": generation,
            "hypothesis": hypothesis,
            "oos_return_pct": oos_return,
            "oos_sharpe": oos_sharpe,
            "stress_tested_return_pct": stress_return,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "VALIDATED"
        }
        self.data["validated_alphas"].append(entry)
        self.save()

    def record_falsified_hypothesis(self, generation: int, hypothesis: str, failure_reasons: list[str], autopsy_file: str):
        entry = {
            "generation": generation,
            "hypothesis": hypothesis,
            "failure_reasons": failure_reasons,
            "autopsy_file": autopsy_file,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "REJECTED_ROLLED_BACK"
        }
        self.data["falsified_hypotheses"].append(entry)
        self.save()

    def get_summary_for_prompt(self) -> dict:
        return {
            "trading_rules_invariants": self.data.get("trading_rules_invariants", []),
            "heuristic_guardrails": self.data.get("heuristic_guardrails", []),
            "recent_validated_alphas": self.data.get("validated_alphas", [])[-3:],
            "recent_falsified_hypotheses": self.data.get("falsified_hypotheses", [])[-3:]
        }
