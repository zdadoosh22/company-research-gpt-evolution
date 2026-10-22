"""
Adaptive Execution Engine - Dynamic Volatility Exits, Flexible Horizons & Extended-Hours Risk
Isolated Tactical Trading Lab: daytrading/tools/adaptive_execution_engine.py

Core Components:
1. Dynamic Volatility & GEX-Anchored Exits (ATR/Sigma normalized targets, Call Wall snapping).
2. Adaptive Holding Horizon (Intraday Scalp [1-4h], Standard Swing [2-5d], Extended Runner [5-10d]).
3. Extended-Hours & Overnight Gap Risk Management (Pre-market early execution, overnight catalyst fences).
4. Trading 212 ISA Optimization (0.30% USD FX vs 0.00% UK GBP Edge).
"""

import sys
import os
import math
import random
import json
import argparse
from datetime import datetime

# Import universe, profiles, and GEX engine
from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
from options_gex_tactical_engine import OptionsGEXTacticalEngine
from dual_factor_tactical_fused import FUNDAMENTAL_PROFILES


class AdaptiveExecutionEngine:
    def __init__(self, fx_fee_pct=0.0015):
        self.fx_fee_pct = fx_fee_pct
        self.gex_engine = OptionsGEXTacticalEngine()

    def calculate_dynamic_bracket(self, ticker, spot, budget=150.0, fx_rate=0.7465, gex_data=None):
        """
        Calculates volatility-normalized, structural targets and stops.
        Overhauled for Trading 212 ISA Architecture:
        - Default sizing: £150 (15% of £1,000 portfolio) to eliminate cash drag while keeping 55% reserve.
        - Strict FX Target Hurdle: USD assets require minimum +8.5% Stage 1 target to clear 0.30% FX.
        - UK Zero-FX ISA Edge: UK assets (0% FX) use nimble +5.0% to +6.5% targets.
        - Dynamic 10 EMA Trailing Runner on Stage 2 (4 to 12 days).
        - Snaps targets relative to Options GEX Call Wall.
        """
        prof = get_profile(ticker)
        daily_vol = prof["vol"]
        is_uk = prof["is_uk"]
        asset_type = prof["type"]
        
        # Calculate approximate 14-day ATR %
        atr_pct = daily_vol * 1.55 # Empirical relationship for US momentum equities
        
        # 1. Base Volatility-Normalized Multiples (Calibrated Hybrid: reachable Stage 1 + dynamic Stage 2 runner)
        if "3x" in asset_type:
            # High volatility leverage: Keep Stage 1 reachable (+8.5% to +10.0%) to lock in cash, scale Stage 2 wide
            stop_mult = 1.35
            t1_mult = 1.15
            t2_mult = 3.2
            min_t1 = 0.085 # Enforce minimum 8.5% hurdle for USD leveraged pairs
            min_t2 = 0.220
            max_stop = 0.080
            min_stop = 0.068
        elif "2x" in asset_type:
            stop_mult = 1.3
            t1_mult = 1.15
            t2_mult = 2.8
            min_t1 = 0.085
            min_t2 = 0.185
            max_stop = 0.075
            min_stop = 0.065
        elif asset_type == "uk_equity":
            # Lower volatility, 0% FX fee: nimble realistic targets without FX drag
            stop_mult = 1.35
            t1_mult = 1.35
            t2_mult = 2.6
            min_t1 = 0.050 # 0% FX allows nimble 5.0% take profit
            min_t2 = 0.110
            max_stop = 0.065
            min_stop = 0.055
        elif asset_type in ["growth", "crypto_proxy"]:
            stop_mult = 1.3
            t1_mult = 1.2
            t2_mult = 3.0
            min_t1 = 0.085
            min_t2 = 0.180
            max_stop = 0.075
            min_stop = 0.065
        else: # Standard equity / megacap
            stop_mult = 1.3
            t1_mult = 1.25
            t2_mult = 2.7
            min_t1 = 0.085 if not is_uk else 0.055
            min_t2 = 0.160
            max_stop = 0.070
            min_stop = 0.062

        # Raw calculated percentages
        stop_pct = min(max_stop, max(min_stop, atr_pct * stop_mult))
        t1_pct = min(0.110, max(min_t1, atr_pct * t1_mult))
        t2_pct = max(min_t2, atr_pct * t2_mult)

        raw_t1_price = spot * (1.0 + t1_pct)
        raw_t2_price = spot * (1.0 + t2_pct)
        raw_stop_price = spot * (1.0 - stop_pct)

        # 2. Options GEX Structural Snapping
        gex_snapped = False
        call_wall_note = "None"
        put_wall_note = "None"

        if not gex_data and not is_uk:
            # Generate GEX structure if not provided
            gex_data = self.gex_engine.simulate_strike_chain(spot, vol=daily_vol * math.sqrt(252), dte=3)

        if gex_data:
            cw = gex_data.get("call_wall", 0)
            pw = gex_data.get("put_wall", 0)
            
            # If Call Wall is between Spot and Stage 1 + 1.5%, snap Stage 1 just below Call Wall
            if spot < cw <= (raw_t1_price * 1.015):
                snapped_t1 = cw * 0.995 # Exit 0.5% below dealer resistance
                if (snapped_t1 - spot) / spot >= 0.045: # Ensure still at least 4.5%
                    raw_t1_price = snapped_t1
                    t1_pct = (raw_t1_price - spot) / spot
                    gex_snapped = True
                    call_wall_note = f"Snapped to Call Wall (${cw:.2f} - 0.5%)"
                    
            # If Put Wall is near stop, place stop directly below Put Wall to use dealer support
            if (raw_stop_price * 0.985) <= pw < spot:
                raw_stop_price = pw * 0.992 # 0.8% below put wall support
                stop_pct = (spot - raw_stop_price) / spot
                put_wall_note = f"Anchored below Put Wall (${pw:.2f} - 0.8%)"

        # Round values
        stop_price = round(raw_stop_price, 2)
        t1_price = round(raw_t1_price, 2)
        t2_price = round(raw_t2_price, 2)
        
        # Breakeven price covering T212 FX
        fx_roundtrip_pct = 0.0 if is_uk else (self.fx_fee_pct * 2.0)
        breakeven_price = round(spot * (1.0 + fx_roundtrip_pct + 0.001), 2)
        
        # Sizing in GBP
        unit_cost_gbp = spot if is_uk else (spot * fx_rate)
        shares = round(budget / unit_cost_gbp, 4)
        
        # Adaptive Horizon Classification
        horizon_plan = self.classify_adaptive_horizon(ticker, asset_type, daily_vol)

        return {
            "ticker": ticker,
            "spot": spot,
            "is_uk": is_uk,
            "asset_type": asset_type,
            "daily_vol_pct": round(daily_vol * 100, 2),
            "atr_14_pct": round(atr_pct * 100, 2),
            "commitment_gbp": budget,
            "shares": shares,
            "stop_loss_price": stop_price,
            "stop_loss_pct": round(-stop_pct * 100, 2),
            "stage_1_take_profit": t1_price,
            "stage_1_pct": round(t1_pct * 100, 2),
            "stage_2_take_profit": t2_price,
            "stage_2_pct": round(t2_pct * 100, 2),
            "breakeven_ratchet": breakeven_price,
            "call_wall_note": call_wall_note,
            "put_wall_note": put_wall_note,
            "horizon_plan": horizon_plan
        }

    def classify_adaptive_horizon(self, ticker, asset_type, daily_vol):
        """
        Determines the optimal adaptive holding horizon rather than a rigid 5-day cutoff.
        Includes exact 10 EMA / Swing-Low trailing rules for the Stage 2 runner.
        """
        if "inverse" in asset_type or ticker in ["SQQQ", "SOXS", "SPXU"]:
            return {
                "recommended_horizon": "1 to 3 Trading Days",
                "hard_limit": "4 Trading Days",
                "can_extend_past_5d": False,
                "runner_trail_rule": "Exit 100% at Stage 1 or Day 3. Never hold inverse runners into chop.",
                "rationale": "High 6.0*sigma^2 beta-slippage decay makes inverse multi-day holding toxic."
            }
        elif "3x_etf" in asset_type:
            return {
                "recommended_horizon": "2 to 4 Trading Days",
                "hard_limit": "5 Trading Days (Unless strong bull trend with Benchmark > 10 EMA)",
                "can_extend_past_5d": False,
                "runner_trail_rule": "Trail Stage 2 along prior-day low. Bank remaining 50% by Day 5.",
                "rationale": "Volatile compounding drag requires disciplined banking by Day 5."
            }
        elif asset_type == "uk_equity":
            return {
                "recommended_horizon": "3 to 10 Trading Days",
                "hard_limit": "15 Trading Days",
                "can_extend_past_5d": True,
                "runner_trail_rule": "Trail Stage 2 runner along daily 10 EMA for 4-12 days (0% FX advantage).",
                "rationale": "Zero FX drag and lower daily volatility permit patient multi-week swing compounding."
            }
        elif FUNDAMENTAL_PROFILES.get(ticker, {}).get("quality") == "HIGH_MOAT":
            return {
                "recommended_horizon": "3 to 8 Trading Days",
                "hard_limit": "12 Trading Days",
                "can_extend_past_5d": True,
                "runner_trail_rule": "Trail Stage 2 runner along daily 10 EMA / 2-day low for up to 12 days.",
                "rationale": "High-FCF moats exhibit multi-week institutional accumulation; extend runner if above 10 EMA."
            }
        else:
            return {
                "recommended_horizon": "2 to 6 Trading Days",
                "hard_limit": "8 Trading Days",
                "can_extend_past_5d": False,
                "runner_trail_rule": "Trail Stage 2 along 2-day low; close if momentum stalls below breakeven.",
                "rationale": "Standard momentum equity swing."
            }

    def evaluate_extended_hours_gap_risk(self, ticker, spot, pre_market_price=None, overnight_catalyst=False):
        """
        Evaluates pre-market and overnight risk in Trading 212:
        T212 provides extended-hours execution from 09:00 UK time (pre-market)
        and night market availability on major US equities.
        """
        prof = get_profile(ticker)
        daily_vol = prof["vol"]
        
        # If pre-market price provided, compute pre-market gap
        pre_market_gap_pct = 0.0
        if pre_market_price is not None and spot > 0:
            pre_market_gap_pct = (pre_market_price - spot) / spot
            
        gap_risk_score = 30 # Baseline normal overnight risk
        
        # Volatility penalty
        if daily_vol > 0.04:
            gap_risk_score += 25
        elif daily_vol > 0.03:
            gap_risk_score += 15
            
        # Overnight catalyst penalty (e.g. FOMC, CPI, mega-cap earnings peer)
        if overnight_catalyst:
            gap_risk_score += 35

        # Tactical recommendation
        if gap_risk_score >= 70:
            protocol = "TRIM_BEFORE_CLOSE_OR_USE_PREMARKET_STOP"
            action = "Bank 75% of profits before 21:00 UK close, or prepare pre-market stop in T212 app at 09:00 UK."
        elif gap_risk_score >= 45:
            protocol = "MONITOR_PREMARKET_AUCTION"
            action = "Standard overnight hold. Review 09:00 UK pre-market quotes on T212 for early gap breaches."
        else:
            protocol = "LOW_OVERNIGHT_RISK"
            action = "Safe overnight swing. Low likelihood of gapping past stop."

        # Extended hours early exit trigger
        early_cut_advisable = False
        if pre_market_price is not None and pre_market_gap_pct <= -0.055:
            early_cut_advisable = True
            action = "ACTIONABLE PRE-MARKET CUT: Stock gapping down heavily in pre-market. Execute sell in T212 extended hours (09:00 UK) to avoid regular-open panic dump."

        return {
            "ticker": ticker,
            "pre_market_gap_pct": round(pre_market_gap_pct * 100, 2),
            "gap_risk_score": gap_risk_score,
            "protocol": protocol,
            "early_cut_advisable": early_cut_advisable,
            "action_guidance": action
        }

    def run_dynamic_vs_fixed_backtest(self, num_runs=1500):
        """
        Backtests Dynamic Volatility/GEX Exits vs Fixed (+7.5% / +17%) Exits
        across 1,500 trades spanning High-Beta ETFs, Mega-Caps, and UK Moats.
        """
        print(f"[*] Running {num_runs} comparative backtests: Dynamic Volatility Exits vs Fixed Exits...")
        
        sample_tickers = ["SOXL", "TQQQ", "NVDA", "PLTR", "APP", "RR.L", "RIO.L", "MSFT"]
        
        fixed_results = []
        dynamic_results = []
        
        for _ in range(num_runs):
            ticker = random.choice(sample_tickers)
            prof = get_profile(ticker)
            daily_vol = prof["vol"]
            is_uk = prof["is_uk"]
            
            # Synthetic 5-day price movement path
            move_drift = random.gauss(0.015, daily_vol * math.sqrt(4.0)) # 4-day realized move
            max_favorable_excursion = abs(move_drift) * random.uniform(1.2, 1.8) if move_drift > 0 else abs(move_drift) * 0.4
            max_adverse_excursion = -abs(move_drift) * random.uniform(1.2, 1.8) if move_drift < 0 else -abs(move_drift) * 0.4
            
            fx_friction = 0.0 if is_uk else (self.fx_fee_pct * 2.0)
            slippage = 0.002
            total_friction = fx_friction + slippage

            # 1. FIXED EXIT MODEL (+7.5% Stage 1, +17% Stage 2, -7.0% Stop)
            fixed_stop = -0.070
            fixed_t1 = 0.075
            fixed_t2 = 0.170
            
            if max_adverse_excursion <= fixed_stop:
                fixed_ret = fixed_stop - total_friction
                fixed_win = False
            elif max_favorable_excursion >= fixed_t2:
                fixed_ret = ((fixed_t1 * 0.5) + (fixed_t2 * 0.5)) - total_friction
                fixed_win = True
            elif max_favorable_excursion >= fixed_t1:
                # Banked 50% at t1, remaining stopped at breakeven
                fixed_ret = (fixed_t1 * 0.5) - total_friction
                fixed_win = True
            else:
                # Expired or closed at end of 5 days
                fixed_ret = move_drift - total_friction
                fixed_win = fixed_ret > 0
                
            fixed_results.append(fixed_ret)

            # 2. DYNAMIC VOLATILITY-NORMALIZED MODEL
            bracket = self.calculate_dynamic_bracket(ticker, spot=100.0)
            dyn_stop = bracket["stop_loss_pct"] / 100.0
            dyn_t1 = bracket["stage_1_pct"] / 100.0
            dyn_t2 = bracket["stage_2_pct"] / 100.0
            
            if max_adverse_excursion <= dyn_stop:
                dyn_ret = dyn_stop - total_friction
                dyn_win = False
            elif max_favorable_excursion >= dyn_t2:
                dyn_ret = ((dyn_t1 * 0.5) + (dyn_t2 * 0.5)) - total_friction
                dyn_win = True
            elif max_favorable_excursion >= dyn_t1:
                dyn_ret = (dyn_t1 * 0.5) - total_friction
                dyn_win = True
            else:
                dyn_ret = move_drift - total_friction
                dyn_win = dyn_ret > 0
                
            dynamic_results.append(dyn_ret)

        def get_stats(rets):
            wins = [r for r in rets if r > 0]
            losses = [r for r in rets if r <= 0]
            wr = len(wins) / len(rets)
            avg_w = sum(wins) / max(1, len(wins))
            avg_l = sum(losses) / max(1, len(losses))
            exp = (wr * avg_w) + ((1.0 - wr) * avg_l)
            pf = abs(sum(wins)) / max(0.0001, abs(sum(losses)))
            return {
                "total_trades": len(rets),
                "win_rate_pct": round(wr * 100, 2),
                "profit_factor": round(pf, 3),
                "net_expectancy_pct": round(exp * 100, 3),
                "avg_win_pct": round(avg_w * 100, 3),
                "avg_loss_pct": round(avg_l * 100, 3)
            }

        summary = {
            "fixed_percentage_system": get_stats(fixed_results),
            "dynamic_volatility_gex_system": get_stats(dynamic_results)
        }
        return summary


def main():
    parser = argparse.ArgumentParser(description="Adaptive Execution Engine")
    parser.add_argument("--test", action="store_true", help="Run comparative backtest")
    parser.add_argument("--ticker", type=str, default="NVDA", help="Ticker for bracket")
    parser.add_argument("--spot", type=float, default=135.0, help="Spot price")
    parser.add_argument("--budget", type=float, default=75.0, help="GBP commitment")
    parser.add_argument("--pre-market", type=float, default=None, help="Pre-market quote")
    parser.add_argument("--overnight-catalyst", action="store_true", help="Overnight catalyst flag")
    parser.add_argument("--save-evidence", action="store_true", help="Save output to evidence directory")
    args = parser.parse_args()

    engine = AdaptiveExecutionEngine()

    if args.test:
        summary = engine.run_dynamic_vs_fixed_backtest(num_runs=1500)
        print("\n================ DYNAMIC VS FIXED EXITS COMPARISON ================")
        print(json.dumps(summary, indent=2))
        if args.save_evidence:
            ev_path = os.path.join(os.path.dirname(__file__), "..", "evidence", "dynamic_vs_fixed_exits_results.json")
            with open(ev_path, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"[+] Saved backtest results to {ev_path}")
        return

    # Calculate and display dynamic bracket
    bracket = engine.calculate_dynamic_bracket(args.ticker, spot=args.spot, budget=args.budget)
    gap_risk = engine.evaluate_extended_hours_gap_risk(
        args.ticker, spot=args.spot, pre_market_price=args.pre_market, overnight_catalyst=args.overnight_catalyst
    )

    print("\n" + "=" * 70)
    print(f"     ADAPTIVE DYNAMIC BRACKET & HORIZON PLAN: {args.ticker.upper()}")
    print("=" * 70)
    print(f"Current Spot Price   : ${bracket['spot']:.2f} ({'UK GBP Zero-FX' if bracket['is_uk'] else 'USD Pair'})")
    print(f"Daily Volatility (s) : {bracket['daily_vol_pct']}% | 14D ATR: {bracket['atr_14_pct']}%")
    print(f"Commitment Sizing    : £{bracket['commitment_gbp']:.2f} GBP (~{bracket['shares']} units)")
    print("-" * 70)
    print(f"Dynamic Hard Stop    : ${bracket['stop_loss_price']:.2f} ({bracket['stop_loss_pct']}%) [{bracket['put_wall_note']}]")
    print(f"Stage 1 Target (50%) : ${bracket['stage_1_take_profit']:.2f} (+{bracket['stage_1_pct']}%) [{bracket['call_wall_note']}]")
    print(f"Breakeven Ratchet    : ${bracket['breakeven_ratchet']:.2f} (Lock in upon Stage 1 hit)")
    print(f"Stage 2 Target (50%) : ${bracket['stage_2_take_profit']:.2f} (+{bracket['stage_2_pct']}%)")
    print("-" * 70)
    print(f"Adaptive Horizon     : {bracket['horizon_plan']['recommended_horizon']}")
    print(f"Soft Ceiling         : {bracket['horizon_plan']['hard_limit']}")
    print(f"Can Extend Past 5D?  : {'YES (Hold runner above 10 EMA)' if bracket['horizon_plan']['can_extend_past_5d'] else 'NO (Compounding decay limit)'}")
    print(f"Horizon Rationale    : {bracket['horizon_plan']['rationale']}")
    print("-" * 70)
    print(f"Overnight Gap Risk   : {gap_risk['gap_risk_score']}/100 [{gap_risk['protocol']}]")
    print(f"Extended-Hours Action: {gap_risk['action_guidance']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
