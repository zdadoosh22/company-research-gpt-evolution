"""
AUTONOMOUS EVOLUTION ORCHESTRATOR (evolution_orchestrator.py)
Closed-Loop Generational Controller, Telemetry Dispatcher & Fail-Safe Commit/Rollback Engine
=============================================================================================
Modes:
  --mode status   : Display generational scoreboard across all historical iterations.
  --mode dispatch : Generate the structured prompt input packet for ChatGPT.
  --mode verify   : Run harness for Generation N; auto-commit on PASS, auto-restore on FAIL.
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
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

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = DAYTRADING_ROOT.parent
TELEMETRY_DIR = SCRIPT_DIR / "telemetry"
AUTOPSIES_DIR = SCRIPT_DIR / "autopsies"
HARNESS_PATH = DAYTRADING_ROOT / "tools" / "evolution_harness.py"

try:
    import experience_bank
except ImportError:
    experience_bank = None


def get_latest_generation() -> tuple[int, dict | None]:
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    telemetry_files = sorted(TELEMETRY_DIR.glob("gen_*_telemetry.json"))
    if not telemetry_files:
        return 0, None
    latest_file = telemetry_files[-1]
    with open(latest_file, "r") as f:
        data = json.load(f)
    return data.get("generation", 0), data


def show_scoreboard():
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(TELEMETRY_DIR.glob("gen_*_telemetry.json"))
    print("\n" + "=" * 95)
    print("🏆 AUTONOMOUS TRADING ENGINE: GENERATIONAL EVOLUTION SCOREBOARD")
    print("=" * 95)
    print(f"{'GEN':<5} | {'VERDICT':<7} | {'IS RETURN':<10} | {'OOS RETURN':<11} | {'STRESS RET':<11} | {'MAX DD':<8} | {'DSR':<6} | {'HYPOTHESIS'}")
    print("-" * 95)
    
    if not files:
        print("No generation telemetry found yet.")
        print("=" * 95)
        return

    for f in files:
        with open(f, "r") as jf:
            d = json.load(jf)
        gen = d.get("generation", 0)
        verdict = d.get("verdict", "UNKNOWN")
        m = d.get("metrics", {})
        is_ret = f"{m.get('in_sample', {}).get('mean_net_return_pct', 0.0):+.1f}%"
        oos_ret = f"{m.get('out_of_sample', {}).get('mean_net_return_pct', 0.0):+.1f}%"
        stress_ret = f"{m.get('stress_tested_oos', {}).get('mean_net_return_pct', 0.0):+.1f}%"
        max_dd = f"{m.get('out_of_sample', {}).get('max_drawdown_pct', 0.0):.1f}%"
        dsr = f"{m.get('deflated_sharpe_ratio', 0.0):.2f}"
        hyp = d.get("hypothesis", "N/A")[:30]
        
        status_sym = "✅" if verdict == "PASSED" else "❌"
        print(f"G{gen:<4} | {status_sym} {verdict:<4} | {is_ret:<10} | {oos_ret:<11} | {stress_ret:<11} | {max_dd:<8} | {dsr:<6} | {hyp}")
    print("=" * 95 + "\n")


def dispatch_packet_for_chatgpt():
    gen, telemetry = get_latest_generation()
    next_gen = gen + 1
    
    eb_summary = {}
    if experience_bank is not None:
        try:
            eb_summary = experience_bank.ExperienceBank().get_summary_for_prompt()
        except Exception:
            pass

    # Dynamic Archetype Diagnosis
    recommendation = "ARCH-EXPLORE"
    rec_reason = "Generation 2 kickoff: Explore novel alpha factors or outside-the-box microstructure mechanisms."
    if telemetry:
        m = telemetry.get("metrics", {})
        oos = m.get("out_of_sample", {})
        max_dd = oos.get("max_drawdown_pct", 0.0)
        stress_ret = m.get("stress_tested_oos", {}).get("mean_net_return_pct", 0.0)
        
        if next_gen % 4 == 0:
            recommendation = "ARCH-VISUAL"
            rec_reason = "Milestone generation: Upgrade Cyber War Room UI, visual scrubber, and aesthetic dashboards."
        elif max_dd > 13.0:
            recommendation = "ARCH-SHIELD"
            rec_reason = f"Max Drawdown is {max_dd:.1f}%; prioritize tail-risk fortification and cash shield ratchets."
        elif stress_ret < 50.0:
            recommendation = "ARCH-MICRO"
            rec_reason = f"Synthetic friction stress return ({stress_ret:.1f}%) indicates broker fee drag; prioritize intraday execution and slippage eradication."
        elif next_gen % 2 == 0:
            recommendation = "ARCH-MACRO"
            rec_reason = "Optimize cross-asset Relative Strength sector rotation or introduce new asset clusters (UK dividend leaders / defense)."
        else:
            recommendation = "ARCH-MATH"
            rec_reason = "Formulate stochastic calculus models (Kalman filter / Hurst exponent / Ornstein-Uhlenbeck drift)."

    packet = {
        "current_generation": gen,
        "next_generation": next_gen,
        "active_architecture": "5-Pillar All-Weather Alpha Architecture (RS Sector Rotation, ATR Volatility Bracket, RSI Dip Sniper, SQQQ Inverse Hedge, Cash Shield)",
        "diagnostic_recommendation": {
            "suggested_archetype": recommendation,
            "rationale": rec_reason,
            "allowed_archetypes": [
                "ARCH-MACRO (Structural Regime & Cross-Asset Expansion)",
                "ARCH-MICRO (Intraday Microstructure & Slippage Eradication)",
                "ARCH-SHIELD (Anti-Fragility & Crisis Tail-Risk Fortress)",
                "ARCH-MATH (Stochastic Calculus & Signal Theory)",
                "ARCH-VISUAL (Cyber War Room & High-Aesthetic Terminal)",
                "ARCH-EXPLORE (Outside-The-Box Radical Innovation)"
            ]
        },
        "baselines": {
            "is_mean_return_pct": 53.34,
            "oos_mean_return_pct": 91.59,
            "oos_sharpe_ratio": 2.65,
            "stress_tested_oos_return_pct": 55.83,
            "max_allowed_oos_drawdown_pct": 15.00
        },
        "latest_telemetry": telemetry,
        "experience_bank": eb_summary
    }
    
    print("\n" + "=" * 80)
    print(f"📋 DISPATCH PACKET FOR CHATGPT (GENERATION {next_gen})")
    print("=" * 80)
    print("Master System Prompt: daytrading/evolution/MASTER_META_OPTIMIZER_PROMPT_V3.md")
    print(f"🎯 Recommended Archetype: {recommendation} ({rec_reason})")
    print("Copy and paste the JSON block below into ChatGPT:")
    print("--------------------------------------------------------------------------------")
    print(json.dumps(packet, indent=2))
    print("--------------------------------------------------------------------------------\n")


def verify_generation(generation: int, hypothesis: str):
    print(f"\n[ORCHESTRATOR] Initiating verification for Generation {generation}: '{hypothesis}'")
    cmd = [
        sys.executable,
        str(HARNESS_PATH),
        "--generation", str(generation),
        "--hypothesis", hypothesis
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"\n🎉 [ORCHESTRATOR] Generation {generation} PASSED ALL HURDLES!")
        print("Executing automated git commit and checkpoint tagging...")
        
        # Git commit & tag
        subprocess.run(["git", "add", "daytrading/"], cwd=str(PROJECT_ROOT))
        subprocess.run(["git", "commit", "-m", f"feat(evolution): Gen {generation} - {hypothesis} [PASSED]"], cwd=str(PROJECT_ROOT))
        subprocess.run(["git", "tag", f"checkpoint-gen-{generation}"], cwd=str(PROJECT_ROOT))
        print(f"✅ Created checkpoint tag: checkpoint-gen-{generation}")
        
        # Git push attempt
        try:
            subprocess.run(["git", "push", "origin", "main", "--tags"], cwd=str(PROJECT_ROOT), capture_output=True, timeout=20)
            print("🚀 Pushed updates and tags to remote origin.")
        except Exception:
            pass
            
        show_scoreboard()
    else:
        print(f"\n🚨 [ORCHESTRATOR] Generation {generation} FAILED HURDLES.")
        print("Executing automated rollback protocol: restoring daytrading/ ...")
        
        # Create autopsy report before revert
        AUTOPSIES_DIR.mkdir(parents=True, exist_ok=True)
        autopsy_file = AUTOPSIES_DIR / f"gen_{generation:03d}_autopsy.md"
        with open(autopsy_file, "w") as f:
            f.write(f"# AUTOPSY REPORT: GENERATION {generation}\n\n")
            f.write(f"**Hypothesis:** {hypothesis}\n")
            f.write(f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"**Status:** REJECTED & ROLLED BACK\n\n")
            f.write("The modifications failed empirical walk-forward out-of-sample or friction stress criteria.\n")
        
        # Git restore
        subprocess.run(["git", "restore", "daytrading/"], cwd=str(PROJECT_ROOT))
        print(f"🛡️ Rollback complete. Repository restored to clean baseline.")
        print(f"📄 Autopsy saved to: {autopsy_file}\n")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Evolution Orchestrator")
    parser.add_argument("--mode", choices=["status", "dispatch", "verify"], default="status", help="Orchestration mode")
    parser.add_argument("--generation", type=int, default=None, help="Generation number (for verify)")
    parser.add_argument("--hypothesis", type=str, default="Autonomous Improvement", help="Hypothesis statement (for verify)")
    args = parser.parse_args()

    if args.mode == "status":
        show_scoreboard()
    elif args.mode == "dispatch":
        dispatch_packet_for_chatgpt()
    elif args.mode == "verify":
        gen = args.generation
        if gen is None:
            latest, _ = get_latest_generation()
            gen = latest + 1
        verify_generation(gen, args.hypothesis)


if __name__ == "__main__":
    main()
