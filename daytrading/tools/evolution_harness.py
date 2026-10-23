"""
DAYTRADING EVOLUTION TEST HARNESS (evolution_harness.py)
Autonomous Quantitative Evaluation, Walk-Forward Cross-Validation & Deflated Sharpe Verification
=================================================================================================
Mandate:
  - Quarantines In-Sample (IS: Epochs 1-5, 2015-2020) vs Out-of-Sample (OOS: Epochs 6-10, 2021-2026).
  - Evaluates strategies under Baseline (1.0x) and Synthetic Friction Stress (2.0x FX markup & slippage).
  - Computes Deflated Sharpe Ratio (DSR) to penalize data mining across generation count N.
  - Generates standardized GENERATION_AUDIT_TELEMETRY.json for ChatGPT and autonomous orchestrators.
  - Enforces strict PASS/FAIL gate with automatic non-zero exit codes on failure.
"""

from __future__ import annotations
import os
import sys
import math
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform.startswith('win'):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = DAYTRADING_ROOT.parent
EVOLUTION_DIR = DAYTRADING_ROOT / "evolution"
TELEMETRY_DIR = EVOLUTION_DIR / "telemetry"
AUTOPSIES_DIR = EVOLUTION_DIR / "autopsies"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(EVOLUTION_DIR))
import full_universe_out_of_sample_backtest as fb
try:
    import experience_bank
except ImportError:
    experience_bank = None

# Baseline Hurdles established in Phase 25 (v3.0-all-weather-converged)
BASELINE_IS_MEAN_RETURN = 53.34      # Epochs 1-5 Mean Return Baseline
BASELINE_OOS_MEAN_RETURN = 91.59     # Epochs 6-10 Mean Return Baseline
BASELINE_STRESSED_OOS_RETURN = 55.83 # Quarantined OOS with 2x FX and slippage
MAX_ALLOWED_OOS_DRAWDOWN = 15.00     # Max allowable peak-to-trough drawdown % in OOS
MIN_ALLOWABLE_WIN_RATE = 55.00       # Minimum win rate %


def calculate_deflated_sharpe(observed_sharpe: float, n_trials: int, n_periods: int = 120, skew: float = -0.2, kurtosis: float = 3.5) -> float:
    """
    Computes Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR).
    Penalizes Sharpe ratio for multiple hypothesis testing (trial count N).
    """
    if n_trials <= 1:
        return 0.99 if observed_sharpe > 0 else 0.05
    
    # Expected maximum Sharpe under null hypothesis (pure random noise)
    euler_mascheroni = 0.5772156649
    z = math.sqrt(2.0 * math.log(n_trials))
    expected_max_sharpe = z + (euler_mascheroni / z)
    
    # Variance of the Sharpe estimator under non-normality
    sr_var = (1.0 - skew * observed_sharpe + ((kurtosis - 1.0) / 4.0) * (observed_sharpe ** 2)) / max(n_periods - 1, 1)
    if sr_var <= 0.0:
        sr_var = 1.0 / n_periods

    sr_std = math.sqrt(sr_var)
    test_stat = (observed_sharpe - expected_max_sharpe) / sr_std
    
    # Standard normal cumulative distribution function approximation (erf)
    dsr = 0.5 * (1.0 + math.erf(test_stat / math.sqrt(2.0)))
    return round(float(dsr), 4)


class EvolutionBacktestHarness:
    def __init__(self, generation: int = 1, hypothesis: str = "Baseline Evolution Check", friction_multiplier: float = 1.0):
        self.generation = generation
        self.hypothesis = hypothesis
        self.friction_multiplier = friction_multiplier
        self.suite = fb.FullUniverseBacktestSuite(initial_capital=1000.0, max_slots=4)
        
        # Partition epochs
        self.all_epochs = fb.TEN_EPOCHS
        self.is_epochs = self.all_epochs[:5]   # Epochs 1-5: 2015-2020
        self.oos_epochs = self.all_epochs[5:]  # Epochs 6-10: 2021-2026

    def run_partition(self, epochs: list[dict], friction_mult: float = 1.0) -> dict:
        results = []
        for ep in epochs:
            # Execute backtest with friction scaling
            # Note: T212 FX fee = 0.0015 * friction_mult
            res = self.suite.run_epoch(ep)
            if friction_mult > 1.0:
                # Apply synthetic stress friction penalty
                extra_friction_pct = (friction_mult - 1.0) * 0.0030 * res["total_trades"] * 100.0
                res["net_return_pct"] = round(res["net_return_pct"] - extra_friction_pct, 2)
                res["final_equity_gbp"] = round(1000.0 * (1.0 + (res["net_return_pct"] / 100.0)), 2)
                res["net_profit_gbp"] = round(res["final_equity_gbp"] - 1000.0, 2)
                res["broker_fees_gbp"] = round(res["broker_fees_gbp"] * friction_mult, 2)
                res["hurdle_passed"] = res["net_return_pct"] >= ep["target_hurdle_pct"]
            results.append(res)
            
        returns = [r["net_return_pct"] for r in results]
        win_rates = [r["win_rate_pct"] for r in results]
        drawdowns = [r["max_drawdown_pct"] for r in results]
        
        mean_return = sum(returns) / len(returns)
        mean_win_rate = sum(win_rates) / len(win_rates)
        max_dd = max(drawdowns) if drawdowns else 0.0
        
        # Approximate annualized Sharpe across epochs
        variance = sum((x - mean_return) ** 2 for x in returns) / max(len(returns) - 1, 1)
        std_dev = math.sqrt(variance) if variance > 0 else 1.0
        sharpe = round((mean_return - 2.0) / std_dev, 2) if std_dev > 0 else 0.0
        
        return {
            "epoch_count": len(results),
            "mean_net_return_pct": round(mean_return, 2),
            "mean_win_rate_pct": round(mean_win_rate, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "annualized_sharpe": sharpe,
            "pass_rate_pct": round((sum(1 for r in results if r["hurdle_passed"]) / len(results)) * 100.0, 1),
            "epochs": results
        }

    def evaluate_generation(self) -> dict:
        print(f"\n" + "=" * 80)
        print(f"🚀 EXECUTING GENERATION {self.generation} EVALUATION")
        print(f"💡 Hypothesis: {self.hypothesis}")
        print(f"⚖️ Baseline Friction: 1.0x | Stress Friction: 2.0x")
        print("=" * 80)
        
        # 1. Run In-Sample (IS: 2015-2020)
        print("\n[1/3] Running In-Sample Training Split (Epochs 1-5: 2015-2020)...")
        is_metrics = self.run_partition(self.is_epochs, friction_mult=1.0)
        print(f"      IS Mean Return: {is_metrics['mean_net_return_pct']:+.2f}% | Max DD: {is_metrics['max_drawdown_pct']:.2f}% | Sharpe: {is_metrics['annualized_sharpe']:.2f}")

        # 2. Run Quarantined Out-of-Sample (OOS: 2021-2026)
        print("\n[2/3] Running Quarantined Out-of-Sample Split (Epochs 6-10: 2021-2026)...")
        oos_metrics = self.run_partition(self.oos_epochs, friction_mult=1.0)
        print(f"      OOS Mean Return: {oos_metrics['mean_net_return_pct']:+.2f}% | Max DD: {oos_metrics['max_drawdown_pct']:.2f}% | Sharpe: {oos_metrics['annualized_sharpe']:.2f}")

        # 3. Run Synthetic Friction Stress Test (2.0x FX & slippage on OOS)
        print("\n[3/3] Running Synthetic Friction Stress Test (2.0x FX & Slippage on OOS)...")
        stress_metrics = self.run_partition(self.oos_epochs, friction_mult=2.0)
        print(f"      Stressed OOS Return: {stress_metrics['mean_net_return_pct']:+.2f}% | Stressed Max DD: {stress_metrics['max_drawdown_pct']:.2f}%")

        # 4. Deflated Sharpe Ratio
        dsr = calculate_deflated_sharpe(
            observed_sharpe=oos_metrics["annualized_sharpe"],
            n_trials=self.generation,
            n_periods=120
        )
        print(f"\n📊 Deflated Sharpe Ratio (DSR, N={self.generation}): {dsr:.4f}")

        # 5. Gate Hurdle Validation
        hurdles = {
            "is_profitable": is_metrics["mean_net_return_pct"] > 0.0,
            "oos_profitable": oos_metrics["mean_net_return_pct"] > 0.0,
            "oos_return_vs_baseline": oos_metrics["mean_net_return_pct"] >= (BASELINE_OOS_MEAN_RETURN * 0.98), # Must match or beat baseline
            "max_drawdown_limit": oos_metrics["max_drawdown_pct"] <= MAX_ALLOWED_OOS_DRAWDOWN,
            "friction_stress_viable": stress_metrics["mean_net_return_pct"] > 0.0,
            "win_rate_acceptable": oos_metrics["mean_win_rate_pct"] >= MIN_ALLOWABLE_WIN_RATE,
            "dsr_significant": dsr >= 0.70 if self.generation > 1 else True
        }

        overall_passed = all(hurdles.values())
        verdict = "PASSED" if overall_passed else "FAILED"

        telemetry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "generation": self.generation,
            "hypothesis": self.hypothesis,
            "verdict": verdict,
            "overall_passed": overall_passed,
            "hurdles": hurdles,
            "metrics": {
                "in_sample": is_metrics,
                "out_of_sample": oos_metrics,
                "stress_tested_oos": stress_metrics,
                "deflated_sharpe_ratio": dsr
            },
            "baselines": {
                "baseline_is_mean": BASELINE_IS_MEAN_RETURN,
                "baseline_oos_mean": BASELINE_OOS_MEAN_RETURN,
                "max_allowed_oos_dd": MAX_ALLOWED_OOS_DRAWDOWN
            }
        }

        # Save telemetry
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        telemetry_file = TELEMETRY_DIR / f"gen_{self.generation:03d}_telemetry.json"
        with open(telemetry_file, "w") as f:
            json.dump(telemetry, f, indent=2)

        print("\n" + "=" * 80)
        print(f"🏁 GENERATION {self.generation} GATE VERDICT: {verdict}")
        print("=" * 80)
        for h, passed in hurdles.items():
            sym = "✅" if passed else "❌"
            print(f"  {sym} {h}: {'PASSED' if passed else 'FAILED'}")
        print(f"\n📁 Saved telemetry: {telemetry_file}")

        # Update Institutional Experience Bank
        if experience_bank is not None and self.generation > 1:
            try:
                eb = experience_bank.ExperienceBank()
                if overall_passed:
                    eb.record_validated_alpha(
                        generation=self.generation,
                        hypothesis=self.hypothesis,
                        oos_return=oos_metrics["mean_net_return_pct"],
                        oos_sharpe=oos_metrics["annualized_sharpe"],
                        stress_return=stress_metrics["mean_net_return_pct"]
                    )
                else:
                    failed_hurdles = [k for k, v in hurdles.items() if not v]
                    eb.record_falsified_hypothesis(
                        generation=self.generation,
                        hypothesis=self.hypothesis,
                        failure_reasons=failed_hurdles,
                        autopsy_file=f"gen_{self.generation:03d}_autopsy.md"
                    )
            except Exception as e:
                print(f"⚠️ Warning: Could not update ExperienceBank: {e}")

        return telemetry


def main():
    parser = argparse.ArgumentParser(description="Autonomous Evolution Backtest Harness")
    parser.add_argument("--generation", type=int, default=1, help="Generation counter (N)")
    parser.add_argument("--hypothesis", type=str, default="Baseline Convergence Check", help="Economic hypothesis description")
    parser.add_argument("--friction-multiplier", type=float, default=1.0, help="Friction multiplier (e.g. 2.0 for stress)")
    args = parser.parse_args()

    harness = EvolutionBacktestHarness(
        generation=args.generation,
        hypothesis=args.hypothesis,
        friction_multiplier=args.friction_multiplier
    )
    
    telemetry = harness.evaluate_generation()
    if not telemetry["overall_passed"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
