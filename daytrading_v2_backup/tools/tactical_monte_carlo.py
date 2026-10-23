"""
Tactical Monte Carlo Engine - Portfolio Sleeve Stress & Friction Rigor
Isolated Tactical Trading Lab: daytrading/tools/tactical_monte_carlo.py

Simulates 2,500 independent annual portfolio trajectories under real-world
Trading 212 Stocks ISA frictions:
- 0.15% FX each way (0.30% round-trip) on non-GBP pairs
- Manual iPhone execution lag (15 to 45 mins, lognormal slippage)
- Overnight gap jump risk (gapping past stop loss)
- £75 vs £100 trade commitments
- Measures Max Drawdown, Max Consecutive Losses, and Probability of Sleeve Ruin
"""

import sys
import os
import math
import random
import json
import argparse

class TacticalMonteCarloEngine:
    def __init__(self, fx_fee_pct=0.0015):
        self.fx_fee_pct = fx_fee_pct

    def simulate_single_trade(self, trade_size=75.0, is_uk=False):
        """
        Simulates a single dual-factor tactical trade including iPhone execution delay,
        T212 FX fees, spread, and overnight gap risk.
        Based on Phase 6 empirical distributions:
        - High-Moat Dual-Factor: Win Rate 59.2%
        - Avg Win: +7.78% (Two-stage blended)
        - Avg Loss: -7.57% (Stop Loss)
        - Overnight gap slippage occurs in 15% of losses (stop gap expansion)
        """
        # 1. Base Win/Loss Probability
        is_winner = random.random() < 0.592
        
        # 2. Friction Drag
        fx_drag = 0.0 if is_uk else (self.fx_fee_pct * 2.0) # 0.30% round-trip
        # Manual iPhone delay slippage (lognormal)
        manual_slippage = random.lognormvariate(-6.8, 0.4) # Mean ~0.13%
        total_friction_pct = fx_drag + (manual_slippage * 2.0)
        
        if is_winner:
            # Stage 1 banked (+7.5%), evaluating Stage 2 runner (+17%)
            hit_runner = random.random() < 0.52
            if hit_runner:
                gross_pct = (0.075 * 0.5) + (0.170 * 0.5) # +12.25% blended gross
            else:
                gross_pct = (0.075 * 0.5) + (0.003 * 0.5) # +3.90% blended gross
            net_pct = gross_pct - total_friction_pct
        else:
            # Loss scenario: Standard stop is -7.0%
            # In 15% of cases, overnight gap jumps past the stop
            if random.random() < 0.15:
                gap_multiplier = random.uniform(1.15, 1.40) # e.g. -8.0% to -9.8%
                gross_pct = -0.070 * gap_multiplier
            else:
                gross_pct = -0.070
            net_pct = gross_pct - total_friction_pct
            
        pnl_gbp = trade_size * net_pct
        return pnl_gbp, net_pct, is_winner

    def simulate_annual_trajectory(self, starting_capital=1000.0, trade_size=75.0, num_trades=150, uk_ratio=0.15):
        """
        Simulates one full annual trajectory (150 trades).
        Returns final capital, peak-to-trough drawdown %, max consecutive losses, ruined flag.
        """
        capital = starting_capital
        peak_capital = starting_capital
        max_drawdown_pct = 0.0
        
        current_loss_streak = 0
        max_loss_streak = 0
        
        trade_pnls = []
        
        for _ in range(num_trades):
            is_uk = random.random() < uk_ratio # 15% UK names (0% FX)
            pnl_gbp, net_pct, is_winner = self.simulate_single_trade(trade_size=trade_size, is_uk=is_uk)
            
            capital += pnl_gbp
            trade_pnls.append(pnl_gbp)
            
            if capital > peak_capital:
                peak_capital = capital
            drawdown = (peak_capital - capital) / peak_capital
            if drawdown > max_drawdown_pct:
                max_drawdown_pct = drawdown
                
            if not is_winner:
                current_loss_streak += 1
                if current_loss_streak > max_loss_streak:
                    max_loss_streak = current_loss_streak
            else:
                current_loss_streak = 0
                
            # If capital drops below 30% of starting capital, severe distress
            if capital <= 0:
                capital = 0
                break

        is_ruined = (max_drawdown_pct >= 0.50) # 50% drawdown definition of ruin
        total_return_pct = (capital - starting_capital) / starting_capital

        return {
            "ending_capital": round(capital, 2),
            "total_return_pct": round(total_return_pct * 100, 2),
            "max_drawdown_pct": round(max_drawdown_pct * 100, 2),
            "max_consecutive_losses": max_loss_streak,
            "is_ruined": is_ruined
        }

    def run_monte_carlo(self, num_trajectories=2500, starting_capital=1000.0, trade_sizes=[75.0, 100.0]):
        print(f"[*] Executing {num_trajectories} Monte Carlo trajectories per trade size...")
        
        results = {}
        for size in trade_sizes:
            trajectories = []
            ruined_count = 0
            
            for _ in range(num_trajectories):
                traj = self.simulate_annual_trajectory(starting_capital=starting_capital, trade_size=size, num_trades=150)
                trajectories.append(traj)
                if traj["is_ruined"]:
                    ruined_count += 1
                    
            # Sort metrics
            end_caps = sorted([t["ending_capital"] for t in trajectories])
            returns = sorted([t["total_return_pct"] for t in trajectories])
            drawdowns = sorted([t["max_drawdown_pct"] for t in trajectories])
            loss_streaks = sorted([t["max_consecutive_losses"] for t in trajectories])
            
            n = len(trajectories)
            p5_idx = int(0.05 * n)
            p50_idx = int(0.50 * n)
            p95_idx = int(0.95 * n)
            
            results[f"trade_size_£{int(size)}"] = {
                "starting_capital_gbp": starting_capital,
                "trade_commitment_gbp": size,
                "total_annual_trajectories": n,
                "ending_capital_median_gbp": round(end_caps[p50_idx], 2),
                "ending_capital_5th_pct_gbp": round(end_caps[p5_idx], 2),
                "ending_capital_95th_pct_gbp": round(end_caps[p95_idx], 2),
                "annual_return_median_pct": round(returns[p50_idx], 2),
                "annual_return_5th_pct": round(returns[p5_idx], 2),
                "annual_return_95th_pct": round(returns[p95_idx], 2),
                "max_drawdown_median_pct": round(drawdowns[p50_idx], 2),
                "max_drawdown_95th_pct": round(drawdowns[p95_idx], 2),
                "worst_case_drawdown_pct": round(max(drawdowns), 2),
                "max_consecutive_losses_median": loss_streaks[p50_idx],
                "max_consecutive_losses_95th_pct": loss_streaks[p95_idx],
                "probability_of_ruin_pct": round((ruined_count / n) * 100, 3)
            }
            
        return results

def main():
    parser = argparse.ArgumentParser(description="Tactical Monte Carlo Risk Engine")
    parser.add_argument("--runs", type=int, default=2500, help="Number of annual trajectories")
    parser.add_argument("--capital", type=float, default=1000.0, help="Starting tactical cash in GBP")
    parser.add_argument("--save-evidence", action="store_true", help="Save output to evidence directory")
    args = parser.parse_args()

    engine = TacticalMonteCarloEngine()
    results = engine.run_monte_carlo(num_trajectories=args.runs, starting_capital=args.capital)
    
    print("\n================ TACTICAL MONTE CARLO RISK REPORT ================")
    print(json.dumps(results, indent=2))
    
    if args.save_evidence:
        evidence_path = os.path.join(os.path.dirname(__file__), "..", "evidence", "tactical_monte_carlo_results.json")
        with open(evidence_path, "w") as f:
            json.dump({"monte_carlo_summary": results}, f, indent=2)
        print(f"\n[+] Results saved cleanly to {evidence_path}")

if __name__ == "__main__":
    main()
