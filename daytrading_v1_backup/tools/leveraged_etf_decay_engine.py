"""
Leveraged ETF Decay & Inverse Rotation Engine
Isolated Tactical Trading Lab: daytrading/tools/leveraged_etf_decay_engine.py

Calculates:
- Discrete daily compounding and volatility beta-slippage decay
- Exact decay drag over 1-day, 3-day, 5-day, and 10-day horizons
- Compares 3x Bull, 2x Bull, and 3x Bear decay dynamics
- Dual-Directional Regime Rotation Strategy vs Buy & Hold
"""

import sys
import os
import math
import random
import json
import argparse

# 30 Leveraged & Inverse ETFs from the 200-Ticker Universe
LEVERAGED_BULL = [
    "TQQQ", "SOXL", "UPRO", "NVDL", "CONL", "TECL", "FNGU", "BULZ",
    "LABU", "TNA", "ERX", "DFEN", "DPST", "YINN", "CWEB"
]

LEVERAGED_BEAR = [
    "SQQQ", "SOXS", "SPXU", "TECS", "FNGD", "BERZ", "LABD", "TZA",
    "ERY", "SDOW", "FAZ", "YANG", "KOLD", "BOIL", "UVXY"
]

class LeveragedETFDecayEngine:
    def __init__(self, fx_fee_pct=0.0015):
        self.fx_fee_pct = fx_fee_pct # 0.15% each way on T212 (0.30% round-trip)

    def calculate_discrete_decay(self, beta, annual_vol, days, drift=0.0):
        """
        Calculates theoretical discrete compounding return and decay drag
        for a leveraged ETF vs beta * benchmark return over N trading days.
        """
        trading_days = 252.0
        daily_vol = annual_vol / math.sqrt(trading_days)
        daily_drift = drift / trading_days
        
        # Monte Carlo simulation of paths to compute expected decay
        num_paths = 5000
        benchmark_returns = []
        etf_returns = []
        
        for _ in range(num_paths):
            bench_price = 1.0
            etf_price = 1.0
            for d in range(days):
                daily_ret = random.gauss(daily_drift, daily_vol)
                bench_price *= (1.0 + daily_ret)
                etf_ret = beta * daily_ret
                etf_price *= max(0.0001, (1.0 + etf_ret))
                
            benchmark_returns.append(bench_price - 1.0)
            etf_returns.append(etf_price - 1.0)
            
        mean_bench = sum(benchmark_returns) / num_paths
        mean_etf = sum(etf_returns) / num_paths
        ideal_leveraged = beta * mean_bench
        decay_drag = ideal_leveraged - mean_etf # Positive means underperformance vs ideal leverage
        
        return {
            "beta": beta,
            "annual_vol_pct": round(annual_vol * 100, 1),
            "days": days,
            "mean_benchmark_ret_pct": round(mean_bench * 100, 3),
            "mean_etf_ret_pct": round(mean_etf * 100, 3),
            "ideal_leveraged_ret_pct": round(ideal_leveraged * 100, 3),
            "decay_drag_pct": round(decay_drag * 100, 3)
        }

    def run_decay_matrix(self):
        """
        Evaluates decay across 1, 3, 5, 10 days for:
        - 3x Bull (TQQQ, SOXL)
        - 2x Bull (NVDL, CONL)
        - 3x Bear (SQQQ, SOXS)
        across Low (15%), Medium (30%), High (60%), Extreme (90%) volatility.
        """
        days_list = [1, 3, 5, 10]
        vols = [0.15, 0.30, 0.60, 0.90]
        betas = [3.0, 2.0, -3.0]
        
        matrix_results = []
        print("[*] Computing Discrete Compounding Decay Matrix...")
        for beta in betas:
            for vol in vols:
                for days in days_list:
                    res = self.calculate_discrete_decay(beta, vol, days, drift=0.0)
                    matrix_results.append(res)
                    
        return matrix_results

    def simulate_regime_rotation(self, num_cycles=1000, cycle_length_days=20):
        """
        Backtests Dual-Directional Rotation vs Passive Buy & Hold over 20-day regimes.
        Regimes:
        - Strong Bull (40% of time): drift +20% ann, vol 20%
        - Strong Bear (25% of time): drift -30% ann, vol 35%
        - Volatile Chop (35% of time): drift 0% ann, vol 40% (high decay zone)
        """
        print(f"[*] Simulating Dual-Directional Rotation Strategy ({num_cycles} regimes)...")
        
        strategies = {
            "passive_3x_bull": [],
            "passive_3x_bear": [],
            "dual_directional_rotation": []
        }
        
        trading_days = 252.0
        fx_friction = self.fx_fee_pct * 2.0 # 0.30% round-trip on every switch
        
        for _ in range(num_cycles):
            regime_type = random.choices(["BULL", "BEAR", "CHOP"], weights=[0.40, 0.25, 0.35])[0]
            
            if regime_type == "BULL":
                drift, vol = 0.25, 0.20
            elif regime_type == "BEAR":
                drift, vol = -0.35, 0.35
            else: # CHOP
                drift, vol = 0.00, 0.45
                
            daily_drift = drift / trading_days
            daily_vol = vol / math.sqrt(trading_days)
            
            # Generate underlying path
            bench_prices = [100.0]
            for _ in range(cycle_length_days):
                ret = random.gauss(daily_drift, daily_vol)
                bench_prices.append(bench_prices[-1] * (1.0 + ret))
                
            # 1. Passive 3x Bull
            p_bull = 100.0
            for d in range(1, len(bench_prices)):
                b_ret = (bench_prices[d] - bench_prices[d-1]) / bench_prices[d-1]
                p_bull *= max(0.001, (1.0 + 3.0 * b_ret))
            # Subtract one roundtrip FX
            bull_ret = (p_bull / 100.0 - 1.0) - fx_friction
            strategies["passive_3x_bull"].append(bull_ret)
            
            # 2. Passive 3x Bear
            p_bear = 100.0
            for d in range(1, len(bench_prices)):
                b_ret = (bench_prices[d] - bench_prices[d-1]) / bench_prices[d-1]
                p_bear *= max(0.001, (1.0 - 3.0 * b_ret))
            bear_ret = (p_bear / 100.0 - 1.0) - fx_friction
            strategies["passive_3x_bear"].append(bear_ret)
            
            # 3. Dual-Directional Rotation (Regime Switched with 5-day hard limit)
            # Computes 5-day momentum & 20-day trend proxy
            p_rot = 100.0
            current_position = "CASH"
            etf_hold_days = 0
            
            for d in range(5, len(bench_prices)):
                momentum_5d = (bench_prices[d] - bench_prices[d-5]) / bench_prices[d-5]
                b_ret = (bench_prices[d] - bench_prices[d-1]) / bench_prices[d-1]
                
                # Rule 1: Signal Generation
                desired_pos = "CASH"
                if momentum_5d > 0.015:
                    desired_pos = "BULL_3X"
                elif momentum_5d < -0.015:
                    desired_pos = "BEAR_3X"
                else:
                    desired_pos = "CASH" # Avoid chop
                    
                # Rule 2: Hard 5-day Time Exit on Leveraged ETFs
                if etf_hold_days >= 5:
                    desired_pos = "CASH"
                    
                # Handle Position Switching and Frictions
                if desired_pos != current_position:
                    if current_position != "CASH":
                        p_rot *= (1.0 - self.fx_fee_pct) # Exit FX
                    if desired_pos != "CASH":
                        p_rot *= (1.0 - self.fx_fee_pct) # Entry FX
                    current_position = desired_pos
                    etf_hold_days = 0
                    
                # Apply daily return
                if current_position == "BULL_3X":
                    p_rot *= max(0.001, (1.0 + 3.0 * b_ret))
                    etf_hold_days += 1
                elif current_position == "BEAR_3X":
                    p_rot *= max(0.001, (1.0 - 3.0 * b_ret))
                    etf_hold_days += 1
                    
            # Close position at end of regime
            if current_position != "CASH":
                p_rot *= (1.0 - self.fx_fee_pct)
                
            rot_ret = (p_rot / 100.0) - 1.0
            strategies["dual_directional_rotation"].append(rot_ret)
            
        summary = {}
        for name, rets in strategies.items():
            wins = [r for r in rets if r > 0]
            losses = [r for r in rets if r <= 0]
            win_rate = len(wins) / len(rets)
            avg_win = sum(wins) / max(1, len(wins))
            avg_loss = sum(losses) / max(1, len(losses))
            expectancy = (win_rate * avg_win) + ((1.0 - win_rate) * avg_loss)
            cum_ret = sum(rets) / len(rets)
            
            summary[name] = {
                "total_cycles": len(rets),
                "win_rate_pct": round(win_rate * 100, 2),
                "avg_win_pct": round(avg_win * 100, 3),
                "avg_loss_pct": round(avg_loss * 100, 3),
                "cycle_expectancy_pct": round(expectancy * 100, 3)
            }
            
        return summary

def main():
    parser = argparse.ArgumentParser(description="Leveraged ETF Decay Engine")
    parser.add_argument("--matrix", action="store_true", help="Generate full decay matrix")
    parser.add_argument("--test-rotation", action="store_true", help="Run dual-directional rotation test")
    parser.add_argument("--save-evidence", action="store_true", help="Save output to evidence directory")
    args = parser.parse_args()

    engine = LeveragedETFDecayEngine()
    
    output_data = {}
    if args.matrix or not args.test_rotation:
        matrix = engine.run_decay_matrix()
        output_data["decay_matrix"] = matrix
        # Sample print
        print("\n=== SAMPLE DECAY VALUES (3x BULL vs 3x BEAR at 60% VOL) ===")
        for m in matrix:
            if m["annual_vol_pct"] == 60.0 and m["days"] in [1, 3, 5, 10]:
                print(f"Beta {m['beta']} | Days {m['days']} | ETF Ret: {m['mean_etf_ret_pct']}% | Ideal: {m['ideal_leveraged_ret_pct']}% | Decay Drag: {m['decay_drag_pct']}%")

    if args.test_rotation:
        rot_summary = engine.simulate_regime_rotation(num_cycles=1000)
        output_data["rotation_summary"] = rot_summary
        print("\n================ DUAL-DIRECTIONAL ROTATION SUMMARY ================")
        print(json.dumps(rot_summary, indent=2))

    if args.save_evidence:
        evidence_path = os.path.join(os.path.dirname(__file__), "..", "evidence", "leveraged_etf_decay_results.json")
        with open(evidence_path, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\n[+] Results saved cleanly to {evidence_path}")

if __name__ == "__main__":
    main()
