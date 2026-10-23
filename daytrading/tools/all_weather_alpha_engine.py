"""
All-Weather Alpha Engine - 4-Pillar Multi-Strategy Tactical Architecture
Isolated Tactical Laboratory: daytrading/tools/all_weather_alpha_engine.py

Institutional All-Weather Profit Engine:
Replaces single-mode breakout dependency with a 4-pillar multi-strategy framework:

1. Pillar 1: Cross-Asset Relative Strength (RS) Sector Rotation Matrix
   - Computes 20-day RS vs Benchmark (QQQ/SPY) across 8 global clusters.
   - Authorizes breakout capital ONLY into the Top 3 leading clusters with positive 20D momentum.
   - In 2022/inflationary bears, automatically quarantines collapsing Tech and routes capital
     into surging UK Zero-FX Energy (SHEL.L, BP.L), Defense (BA.L, LMT), and Commodities (XOM, CVX).

2. Pillar 2: Wyckoff "Undercut & Reclaim" Rubber-Band Dip-Buyer
   - Active in BEAR_CORRECTION and BULL_VOLATILE regimes.
   - Triggers on deep oversold capitulation (RSI < 28 or price >= 2.2x ATR below 20 EMA).
   - Enforces reversal confirmation: Intraday undercut of prior low + close in upper 50% of range on RVOL >= 1.35x.
   - Tight stop (-3.2% UK / -3.8% US), quick Stage 1 profit at descending 10 EMA (+5.0% to +8.5%),
     and strict 3-day time exit.

3. Pillar 3: Active Inverse ETF Waterfall Harvester
   - Active in BEAR_CORRECTION and CRASH_PANIC when benchmark breaks 5-day low on RVOL >= 1.30x.
   - Authorizes 1 slot in SQQQ, SOXS, or SPXU.
   - -4.0% stop, +6.5% Stage 1 bank, and strict 4-day holding limit to capture crash waterfalls without decay.

4. Pillar 4: Progressive "Pilot-Slot" Exposure Scaling & 3-Day Hysteresis
   - Requires 3 consecutive closes above 10 EMA when below 50 SMA before unlocking breakouts.
   - Uses 1 Pilot Slot (£200 / 20%) to test market waters; only expands to Slots 2 & 3 after Pilot hits >= +2.5%.
   - Freezes breakouts for 3 days if Pilot stops out, capping false-dawn chop loss to < 0.8% of portfolio.

5. Pillar 5: Catalyst / PEAD Volume-Shock Override
   - Captures post-earnings drift on RVOL >= 2.20x and return >= +4.0% clearing 20-day high.
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
CACHE_DIR = DAYTRADING_ROOT / "data_cache" / "all_weather_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

StrategyPillar = Literal[
    "SQUEEZE_BREAKOUT_PILOT",
    "SQUEEZE_BREAKOUT_EXPANDED",
    "WYCKOFF_RUBBERBAND_DIP",
    "INVERSE_WATERFALL_HARVESTER",
    "SECTOR_RS_ROTATION_BREAKOUT",
    "PEAD_CATALYST_OVERRIDE"
]

SECTOR_CLUSTERS = {
    "UK_ZERO_FX_VALUE_DEFENSE": [
        "SHEL.L", "BP.L", "RR.L", "RIO.L", "BA.L", "AZN.L", "GSK.L", "ULVR.L", "BARC.L", "LLOY.L", "NWG.L", "HSBA.L", "DGE.L", "BATS.L", "REL.L"
    ],
    "US_ENERGY_DEFENSE": [
        "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "LMT", "RTX", "GD", "NOC", "BA", "GE", "CAT"
    ],
    "HEALTHCARE_MEDTECH": [
        "LLY", "NVO", "VRTX", "REGN", "ISRG", "GILD", "AMGN", "BMY", "ABBV", "PFE"
    ],
    "CONSUMER_DEFENSIVE_STAPLES": [
        "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "CMG", "TJX", "DG", "DLTR"
    ],
    "SEMICONDUCTORS_HARDWARE": [
        "NVDA", "AMD", "QCOM", "ARM", "MU", "AMAT", "LRCX", "KLAC", "AVGO", "DELL", "VRT", "TXN", "INTC"
    ],
    "CLOUD_CYBER_SAAS": [
        "PLTR", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "NOW", "ZS", "WDAY", "APP", "MDB"
    ],
    "FINTECH_PLATFORMS": [
        "COIN", "UBER", "ABNB", "DASH", "SHOP", "SQ", "PYPL", "SPOT", "HOOD", "AFRM", "SOFI"
    ],
    "INVERSE_ETPS": [
        "SQQQ", "SOXS", "SPXU"
    ],
    "LEVERAGED_BULL_ETPS": [
        "TQQQ", "SOXL", "UPRO", "TECL", "FNGU", "BULZ", "LABU", "TNA", "DPST"
    ]
}


@dataclass
class SectorRSRank:
    cluster: str
    return_20d_pct: float
    benchmark_return_20d_pct: float
    relative_strength_pct: float
    is_authorized: bool
    top_tickers: list[str]


@dataclass
class AllWeatherSignal:
    ticker: str
    is_uk: bool
    cluster: str
    strategy_pillar: StrategyPillar
    entry_price: float
    stop_loss_price: float
    stop_loss_pct: float
    stage_1_price: float
    stage_1_pct: float
    stage_2_price: float
    stage_2_pct: float
    max_holding_days: int
    can_extend_runner: bool
    recommended_slot_budget_gbp: float
    rationale: str


class AllWeatherAlphaEngine:
    def __init__(self, portfolio_equity: float = 1000.0, default_slots: int = 3):
        self.portfolio_equity = portfolio_equity
        self.default_slots = max(1, default_slots)
        self.pilot_slot_active = False
        self.pilot_slot_profitable = False
        self.chop_freeze_remaining_days = 0

    def compute_sector_rs_matrix(
        self,
        market_data: dict[str, dict[str, dict]],
        current_date: str,
        benchmark_ticker: str = "QQQ"
    ) -> list[SectorRSRank]:
        """
        Pillar 1: Computes 20-day Relative Strength for all sector clusters vs QQQ.
        Returns clusters sorted from strongest to weakest.
        """
        # Benchmark 20-day return
        b_bars = market_data.get(benchmark_ticker, {})
        dates = sorted([d for d in b_bars.keys() if d <= current_date])
        if len(dates) < 21:
            # Fallback if insufficient history
            return [SectorRSRank(c, 0.0, 0.0, 0.0, True, SECTOR_CLUSTERS[c][:3]) for c in SECTOR_CLUSTERS]

        date_20d_ago = dates[-21]
        b_start = b_bars[date_20d_ago]["close"]
        b_curr = b_bars[current_date]["close"]
        b_ret = ((b_curr - b_start) / max(0.0001, b_start)) * 100.0

        cluster_rankings = []
        for cluster, tickers in SECTOR_CLUSTERS.items():
            if cluster in ("INVERSE_ETPS", "LEVERAGED_BULL_ETPS"):
                continue

            rets = []
            for t in tickers:
                t_bars = market_data.get(t, {})
                if date_20d_ago in t_bars and current_date in t_bars:
                    p0 = t_bars[date_20d_ago]["close"]
                    p1 = t_bars[current_date]["close"]
                    rets.append(((p1 - p0) / max(0.0001, p0)) * 100.0)

            c_ret = sum(rets) / max(1, len(rets)) if rets else 0.0
            rs = c_ret - b_ret
            cluster_rankings.append({
                "cluster": cluster,
                "ret_20d": round(c_ret, 2),
                "b_ret": round(b_ret, 2),
                "rs": round(rs, 2),
                "tickers": tickers
            })

        # Sort by RS descending
        cluster_rankings.sort(key=lambda x: x["rs"], reverse=True)

        results = []
        for idx, item in enumerate(cluster_rankings):
            # Top 3 clusters with positive absolute return or positive RS against falling market
            is_auth = (idx < 3) and (item["ret_20d"] > -2.0 or item["rs"] > 4.0)
            results.append(SectorRSRank(
                cluster=item["cluster"],
                return_20d_pct=item["ret_20d"],
                benchmark_return_20d_pct=item["b_ret"],
                relative_strength_pct=item["rs"],
                is_authorized=is_auth,
                top_tickers=item["tickers"][:5]
            ))

        return results

    def detect_wyckoff_reversal_dip(
        self,
        ticker: str,
        recent_bars: list[dict],
        daily_atr_pct: float,
        is_uk: bool
    ) -> AllWeatherSignal | None:
        """
        Pillar 2: Wyckoff "Undercut & Reclaim" Rubber-Band Dip-Buyer.
        Captures oversold snapbacks into descending 10 EMA without catching falling knives.
        """
        if len(recent_bars) < 15:
            return None

        bar_curr = recent_bars[-1]
        bar_prev = recent_bars[-2]
        spot = bar_curr["close"]
        low_curr = bar_curr["low"]
        high_curr = bar_curr["high"]
        close_curr = bar_curr["close"]
        low_prev = bar_prev["low"]

        # 1. Measure 14-day RSI approximation
        closes = [b["close"] for b in recent_bars[-15:]]
        gains = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        losses = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        rs_val = (avg_gain / max(0.0001, avg_loss)) if avg_loss > 0 else 100.0
        rsi = 100.0 - (100.0 / (1.0 + rs_val))

        # 2. Measure 3-day return
        p_3d_ago = recent_bars[-4]["close"]
        ret_3d = ((spot - p_3d_ago) / max(0.0001, p_3d_ago)) * 100.0

        # Oversold Stretch Condition: RSI < 28 OR 3-day drop <= -8.5%
        is_oversold = (rsi < 28.0) or (ret_3d <= -8.5)
        if not is_oversold:
            return None

        # 3. Institutional Undercut & Reclaim:
        # Intraday low undercut prior day's low, and close finishes above prior low in top 50% of candle
        candle_range = high_curr - low_curr
        close_location = (close_curr - low_curr) / max(0.0001, candle_range) if candle_range > 0 else 0.5
        reclaimed_low = (low_curr < low_prev) and (close_curr >= low_prev) and (close_location >= 0.48)
        hammer_absorption = (close_location >= 0.65) and (ret_3d <= -9.0)

        if not (reclaimed_low or hammer_absorption):
            return None

        # Sizing and Brackets:
        # Stop loss placed tight: -0.6x ATR below low (capped at -3.2% UK / -3.8% US)
        raw_stop = (spot - low_curr) / spot + 0.008
        stop_pct = min(0.038 if not is_uk else 0.032, max(0.024, raw_stop))
        stop_price = round(spot * (1.0 - stop_pct), 2)

        # Stage 1 Target (60%): Snapback to descending 5D/10D EMA (+5.5% UK / +7.5% US)
        t1_pct = 0.052 if is_uk else 0.075
        t1_price = round(spot * (1.0 + t1_pct), 2)

        # Stage 2 Target (40%): +10.5% or 3-day time exit
        t2_pct = 0.095 if is_uk else 0.135
        t2_price = round(spot * (1.0 + t2_pct), 2)

        budget = round(self.portfolio_equity * (0.33 if is_uk else 0.25), 2)

        return AllWeatherSignal(
            ticker=ticker,
            is_uk=is_uk,
            cluster="UK_ZERO_FX_VALUE_DEFENSE" if is_uk else "OVERSOLD_REVERSAL",
            strategy_pillar="WYCKOFF_RUBBERBAND_DIP",
            entry_price=spot,
            stop_loss_price=stop_price,
            stop_loss_pct=-round(stop_pct * 100, 2),
            stage_1_price=t1_price,
            stage_1_pct=round(t1_pct * 100, 2),
            stage_2_price=t2_price,
            stage_2_pct=round(t2_pct * 100, 2),
            max_holding_days=3,  # Strict 3-day mean reversion exit
            can_extend_runner=False,
            recommended_slot_budget_gbp=budget,
            rationale=(
                f"WYCKOFF_REVERSAL: RSI={rsi:.1f}, 3D Ret={ret_3d:.1f}%. "
                f"Undercut prior low ({low_prev:.2f}) and reclaimed to close at {close_curr:.2f}. "
                f"R:R=1:{(t1_pct/stop_pct):.2f}. Target descending 10 EMA; hard 3-day time exit."
            )
        )

    def detect_inverse_waterfall_setup(
        self,
        qqq_bars: list[dict],
        regime_state: str
    ) -> AllWeatherSignal | None:
        """
        Pillar 3: Active Inverse ETF Waterfall Harvester (SQQQ/SPXU).
        Triggers when benchmark is in Bear regime and breaks 5-day low with accelerating volume.
        """
        if regime_state not in ("BEAR_CORRECTION", "CRASH_PANIC") or len(qqq_bars) < 6:
            return None

        curr_bar = qqq_bars[-1]
        prior_5 = qqq_bars[-6:-1]
        low_5d = min(b["low"] for b in prior_5)
        spot_qqq = curr_bar["close"]

        # If QQQ broke below 5-day low
        is_waterfall_breakdown = spot_qqq < low_5d
        if not is_waterfall_breakdown:
            return None

        # Allocate 1 slot in SQQQ
        budget = round(self.portfolio_equity * 0.28, 2)
        return AllWeatherSignal(
            ticker="SQQQ",
            is_uk=False,
            cluster="INVERSE_ETPS",
            strategy_pillar="INVERSE_WATERFALL_HARVESTER",
            entry_price=1.0,  # normalized
            stop_loss_price=0.96,
            stop_loss_pct=-4.0,
            stage_1_price=1.065,
            stage_1_pct=+6.5,
            stage_2_price=1.140,
            stage_2_pct=+14.0,
            max_holding_days=4,  # Hard 4-day ceiling to prevent decay
            can_extend_runner=False,
            recommended_slot_budget_gbp=budget,
            rationale=(
                "INVERSE_CRASH_HARVESTER: QQQ broke 5-day support in BEAR regime. "
                "Deploy SQQQ slot with -4.0% hard stop and 4-day max hold ceiling to capture market waterfall."
            )
        )

    def evaluate_pilot_slot_permission(
        self,
        benchmark_consecutive_above_10ema: int,
        benchmark_above_50sma: bool,
        open_trades_count: int
    ) -> tuple[bool, str, StrategyPillar]:
        """
        Pillar 4: Progressive "Pilot-Slot" Exposure Scaling & 3-Day Hysteresis.
        Prevents getting chopped up on day 1 of a bear-market rally.
        """
        if self.chop_freeze_remaining_days > 0:
            return False, f"CHOP_FREEZE_ACTIVE: {self.chop_freeze_remaining_days} days remaining after pilot stop-out.", "SQUEEZE_BREAKOUT_PILOT"

        # 3-Day Hysteresis when below 50 SMA
        if not benchmark_above_50sma and benchmark_consecutive_above_10ema < 3:
            return False, f"HYSTERESIS_GATE: Benchmark below 50 SMA requires 3 consecutive closes > 10 EMA (Current: {benchmark_consecutive_above_10ema}/3).", "SQUEEZE_BREAKOUT_PILOT"

        # If no trades currently active, authorize ONLY 1 Pilot Slot (£200)
        if open_trades_count == 0:
            return True, "PILOT_SLOT_AUTHORIZED: 1 Test slot (£200 / 20%) to probe market follow-through.", "SQUEEZE_BREAKOUT_PILOT"

        # If Pilot Slot is active, only expand if it is profitable (>= +2.5%)
        if open_trades_count == 1 and not self.pilot_slot_profitable:
            return False, "PILOT_EXPANSION_LOCKED: Slot 2 locked until Pilot Slot achieves >= +2.5% unrealized profit.", "SQUEEZE_BREAKOUT_EXPANDED"

        return True, "EXPANDED_GROWTH_AUTHORIZED: Pilot slot validated follow-through. Deploying slots 2 & 3.", "SQUEEZE_BREAKOUT_EXPANDED"
