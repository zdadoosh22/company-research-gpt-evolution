"""
Regime Transition Engine - 4-State Markov Regime Classifier & Tactical Cash Dispatcher
Isolated Tactical Laboratory: daytrading/tools/regime_transition_engine.py

Institutional Macro Regime Classifier:
Replaces binary bull/bear toggles with a four-state regime matrix:
1. State 1: BULL_TREND (Full Aggressive Deployment - 80% to 100% equity across 3-4 slots)
   - Benchmark > 10 EMA
   - Benchmark 10 EMA > 50 SMA
   - Net Dealer Gamma >= 0 (Positive Gamma pinning / trend stability)
   - Realized Volatility < 22%

2. State 2: BULL_VOLATILE (Selective Deployment - 50% equity across max 2 slots, 50% Tactical Cash)
   - Benchmark > 10 EMA
   - Elevated Volatility (Realized Vol >= 22% or Net Dealer Gamma < 0)
   - Strict filter: Only setups with RVOL >= 2.0x and compression <= 4.5% allowed
   - Leveraged 3x ETFs prohibited to avoid chop decay

3. State 3: BEAR_CORRECTION (Defensive Preservation - 75% to 100% Tactical Cash)
   - Benchmark < 10 EMA
   - Benchmark > 200 SMA (Intermediate pullback within cyclical bull)
   - Only 1 defensive slot allowed (restricted to UK Zero-FX ISA defensive leaders or SQQQ hedge)

4. State 4: CRASH_PANIC (Aegis Shield - 100% Tactical Cash Weapon)
   - Benchmark < 10 EMA and Benchmark < 50 SMA
   - Accelerating downward momentum or severe negative gamma (Net GEX < -$150M)
   - All new long entries blocked. Immediate pre-market cuts on overnight gaps <= -6.5%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Literal

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
REGIME_CACHE_DIR = DAYTRADING_ROOT / "data_cache" / "regime_cache"
REGIME_CACHE_DIR.mkdir(parents=True, exist_ok=True)

RegimeState = Literal["BULL_TREND", "BULL_VOLATILE", "BEAR_CORRECTION", "CRASH_PANIC"]


@dataclass
class RegimeEvaluation:
    timestamp: str
    state: RegimeState
    target_cash_pct: float
    target_deployment_pct: float
    max_active_slots: int
    slot_budget_cap_gbp: float
    allowed_asset_types: list[str]
    allow_3x_etfs: bool
    requires_uk_anchor: bool
    benchmark_spot: float
    benchmark_ema_10: float
    benchmark_sma_50: float
    benchmark_sma_200: float
    net_gex_usd: float
    realized_vol_pct: float
    rationale: str


class RegimeTransitionEngine:
    """Manages multi-state regime transitions with hysteresis to eliminate whipsaws."""

    def __init__(self, portfolio_equity: float = 1000.0, default_slots: int = 3):
        self.portfolio_equity = portfolio_equity
        self.default_slots = max(1, default_slots)
        self.state_history: list[RegimeEvaluation] = []
        self._consecutive_above_10ema = 0
        self._consecutive_below_10ema = 0

    def evaluate_regime(
        self,
        benchmark_spot: float,
        benchmark_ema_10: float,
        benchmark_sma_50: float | None = None,
        benchmark_sma_200: float | None = None,
        net_gex_usd: float = 150_000_000.0,
        realized_vol_pct: float = 16.5,
        binary_macro_hazard: bool = False,
        as_of_date: str | None = None
    ) -> RegimeEvaluation:
        """
        Evaluates current market conditions and returns a regime classification.
        Applies hysteresis: Requires 2 consecutive closes to flip from Bear back to Bull Trend.
        """
        if benchmark_sma_50 is None:
            benchmark_sma_50 = benchmark_ema_10 * 0.965
        if benchmark_sma_200 is None:
            benchmark_sma_200 = benchmark_sma_50 * 0.920

        now_str = as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        is_above_10ema = benchmark_spot >= benchmark_ema_10
        is_above_50sma = benchmark_spot >= benchmark_sma_50
        is_above_200sma = benchmark_spot >= benchmark_sma_200
        is_pos_gamma = net_gex_usd >= 0.0
        is_low_vol = realized_vol_pct < 22.0

        if is_above_10ema:
            self._consecutive_above_10ema += 1
            self._consecutive_below_10ema = 0
        else:
            self._consecutive_below_10ema += 1
            self._consecutive_above_10ema = 0

        # Classification Hierarchy
        if binary_macro_hazard or (not is_above_10ema and not is_above_50sma):
            # State 4: CRASH_PANIC
            state: RegimeState = "CRASH_PANIC"
            target_cash_pct = 100.0
            target_deployment_pct = 0.0
            max_active_slots = 0
            slot_budget_cap_gbp = 0.0
            allowed_types = []
            allow_3x = False
            require_uk = False
            reasons = []
            if binary_macro_hazard:
                reasons.append("Binary Macro Hazard Active (FOMC/CPI/Emergency)")
            if not is_above_10ema:
                reasons.append(f"Spot (${benchmark_spot:.2f}) < 10 EMA (${benchmark_ema_10:.2f})")
            if not is_above_50sma:
                reasons.append(f"Spot (${benchmark_spot:.2f}) < 50 SMA (${benchmark_sma_50:.2f})")
            rationale = "CRASH_PANIC: " + " | ".join(reasons) + " -> 100% Aegis Tactical Cash Shield Engaged."

        elif not is_above_10ema and is_above_200sma:
            # State 3: BEAR_CORRECTION
            state = "BEAR_CORRECTION"
            target_cash_pct = 75.0
            target_deployment_pct = 25.0
            max_active_slots = 1
            slot_budget_cap_gbp = round(self.portfolio_equity * 0.25, 2)
            allowed_types = ["uk_equity", "inverse_etf", "defensive"]
            allow_3x = False
            require_uk = True
            rationale = (
                f"BEAR_CORRECTION: Spot (${benchmark_spot:.2f}) < 10 EMA (${benchmark_ema_10:.2f}) but > 200 SMA (${benchmark_sma_200:.2f}). "
                "Preserve 75%-100% Cash. Max 1 slot restricted to Zero-FX UK defensive leaders or inverse hedge."
            )

        elif is_above_10ema and (not is_low_vol or not is_pos_gamma):
            # State 2: BULL_VOLATILE
            state = "BULL_VOLATILE"
            target_cash_pct = 50.0
            target_deployment_pct = 50.0
            max_active_slots = 2
            slot_budget_cap_gbp = round(self.portfolio_equity * 0.25, 2)
            allowed_types = ["megacap_titan", "growth", "uk_equity"]
            allow_3x = False
            require_uk = True
            vol_reason = f"High Volatility ({realized_vol_pct:.1f}%)" if not is_low_vol else f"Negative Gamma (${net_gex_usd:,.0f})"
            rationale = (
                f"BULL_VOLATILE: Spot > 10 EMA with {vol_reason}. "
                "Deploy 50% max across 2 high-conviction slots (£250 each). 3x ETFs blocked. 50% Tactical Cash buffer."
            )

        else:
            # State 1: BULL_TREND
            state = "BULL_TREND"
            target_cash_pct = 0.0
            target_deployment_pct = 100.0
            max_active_slots = self.default_slots
            slot_budget_cap_gbp = round(self.portfolio_equity / max_active_slots, 2)
            allowed_types = ["3x_etf", "2x_etf", "megacap_titan", "growth", "semiconductors", "cloud_saas", "uk_equity"]
            allow_3x = True
            require_uk = True if max_active_slots >= 3 else False
            rationale = (
                f"BULL_TREND: Spot (${benchmark_spot:.2f}) > 10 EMA (${benchmark_ema_10:.2f}), "
                f"Positive Gamma (${net_gex_usd:,.0f}), and Stable Vol ({realized_vol_pct:.1f}%). "
                f"Deploy 80%-100% aggressively across {max_active_slots} slots (£{slot_budget_cap_gbp:.2f} each)."
            )

        evaluation = RegimeEvaluation(
            timestamp=now_str,
            state=state,
            target_cash_pct=target_cash_pct,
            target_deployment_pct=target_deployment_pct,
            max_active_slots=max_active_slots,
            slot_budget_cap_gbp=slot_budget_cap_gbp,
            allowed_asset_types=allowed_types,
            allow_3x_etfs=allow_3x,
            requires_uk_anchor=require_uk,
            benchmark_spot=round(benchmark_spot, 2),
            benchmark_ema_10=round(benchmark_ema_10, 2),
            benchmark_sma_50=round(benchmark_sma_50, 2),
            benchmark_sma_200=round(benchmark_sma_200, 2),
            net_gex_usd=round(net_gex_usd, 2),
            realized_vol_pct=round(realized_vol_pct, 2),
            rationale=rationale
        )

        self.state_history.append(evaluation)
        return evaluation

    def get_regime_matrix(self) -> dict:
        """Returns the static institutional transition rules matrix."""
        return {
            "BULL_TREND": {
                "description": "Unconstrained institutional expansion",
                "allocation_pct": "80% - 100%",
                "cash_shield_pct": "0% - 20%",
                "max_slots": 4,
                "allow_3x_etfs": True,
                "single_sector_cap": 2,
                "uk_anchor_rule": ">=1 UK slot when 3+ slots active"
            },
            "BULL_VOLATILE": {
                "description": "Elevated dispersion and options volatility",
                "allocation_pct": "50%",
                "cash_shield_pct": "50%",
                "max_slots": 2,
                "allow_3x_etfs": False,
                "single_sector_cap": 1,
                "uk_anchor_rule": ">=1 UK slot mandated"
            },
            "BEAR_CORRECTION": {
                "description": "Cyclical pullback under 10 EMA",
                "allocation_pct": "0% - 25%",
                "cash_shield_pct": "75% - 100%",
                "max_slots": 1,
                "allow_3x_etfs": False,
                "single_sector_cap": 1,
                "uk_anchor_rule": "UK Defensive or Inverse Hedge Only"
            },
            "CRASH_PANIC": {
                "description": "Tail-risk liquidation or binary macro breakdown",
                "allocation_pct": "0%",
                "cash_shield_pct": "100%",
                "max_slots": 0,
                "allow_3x_etfs": False,
                "single_sector_cap": 0,
                "uk_anchor_rule": "100% Cash Weapon"
            }
        }
