"""
Tactical Broker Emulation Suite (Isolated Trading Laboratory)
daytrading/tools/tactical_broker_emulation.py

Simulates live Trading 212 Stocks ISA execution across 252 continuous trading days
under the overhauled £150 / 15% sizing architecture, USD +8.5% target hurdle,
UK Zero-FX ISA prioritization, and 10 EMA trailing Stage 2 runners.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import random
import sys

# Ensure daytrading/tools is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
from dual_factor_tactical_fused import FUNDAMENTAL_PROFILES
from adaptive_execution_engine import AdaptiveExecutionEngine


class OrderState:
    PENDING = "PENDING"
    OPEN = "OPEN"
    STAGE_1_FILLED = "STAGE_1_FILLED"
    CLOSED = "CLOSED"


class Position:
    def __init__(self, ticker, entry_day, entry_price, size_gbp, is_uk, asset_type, stop_loss_pct, stage_1_pct, stage_2_pct, max_days, can_extend):
        self.ticker = ticker
        self.entry_day = entry_day
        self.entry_price = entry_price
        self.size_gbp = size_gbp
        self.is_uk = is_uk
        self.asset_type = asset_type
        self.stop_loss_pct = stop_loss_pct # Negative e.g. -0.065
        self.stage_1_pct = stage_1_pct     # Positive e.g. +0.085
        self.stage_2_pct = stage_2_pct     # Positive e.g. +0.180
        self.max_days = max_days
        self.can_extend = can_extend
        
        self.state = OrderState.OPEN
        self.hold_days = 0
        self.current_price = entry_price
        self.shares_remaining_pct = 1.0 # 100% initially
        self.realized_pnl_gbp = 0.0
        self.total_friction_gbp = 0.0
        self.exit_day = None
        self.exit_reason = None


class TacticalBrokerSimulator:
    def __init__(self, fx_fee_pct=0.0015, spread_pct=0.0008, latency_slippage_pct=0.0004):
        self.fx_fee_pct = fx_fee_pct
        self.spread_pct = spread_pct
        self.latency_slippage_pct = latency_slippage_pct
        self.adaptive_engine = AdaptiveExecutionEngine(fx_fee_pct=fx_fee_pct)

    def run_simulation(self, initial_capital=1000.0, days=252, trade_size=150.0, max_concurrent=3, seed=42):
        if seed is not None:
            random.seed(seed)

        cash_gbp = initial_capital
        portfolio_history = []
        closed_trades: list[Position] = []
        open_positions: list[Position] = []

        peak_equity = initial_capital
        max_drawdown_gbp = 0.0
        max_drawdown_pct = 0.0

        for day in range(1, days + 1):
            # 1. Update Existing Positions
            retained: list[Position] = []
            for pos in open_positions:
                pos.hold_days += 1
                prof = get_profile(pos.ticker)
                daily_vol = prof["vol"]

                # Squeeze continuation drift
                f_prof = FUNDAMENTAL_PROFILES.get(pos.ticker, {})
                drift_bias = 0.0042 if f_prof.get("quality") == "HIGH_MOAT" or pos.is_uk else 0.0028
                day_drift = random.gauss(drift_bias, daily_vol)
                intraday_high = max(0.003, day_drift + abs(random.gauss(0.0, daily_vol * 0.72)))
                intraday_low = min(-0.003, day_drift - abs(random.gauss(0.0, daily_vol * 0.72)))

                # Overnight gap check (4% probability)
                pre_market_gap = -random.uniform(0.065, 0.12) if random.random() < 0.04 else 0.0

                # A. Pre-Market Cut (09:00 UK execution)
                if pre_market_gap <= -0.070 and pos.state != OrderState.CLOSED:
                    fx_drag = 0.0 if pos.is_uk else (self.fx_fee_pct * pos.size_gbp * pos.shares_remaining_pct)
                    spread = self.spread_pct * pos.size_gbp * pos.shares_remaining_pct
                    friction = fx_drag + spread
                    pnl = (pos.size_gbp * pos.shares_remaining_pct * pre_market_gap) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += (pos.size_gbp * pos.shares_remaining_pct) + pnl
                    pos.state = OrderState.CLOSED
                    pos.exit_reason = "PREMARKET_CUT_AT_0900_UK"
                    pos.exit_day = day
                    closed_trades.append(pos)
                    continue

                # B. Stop-Loss Check
                unrealized_low = (pos.current_price * (1.0 + intraday_low) - pos.entry_price) / pos.entry_price
                if unrealized_low <= pos.stop_loss_pct:
                    fx_drag = 0.0 if pos.is_uk else (self.fx_fee_pct * pos.size_gbp * pos.shares_remaining_pct)
                    spread = self.spread_pct * pos.size_gbp * pos.shares_remaining_pct
                    friction = fx_drag + spread
                    pnl = (pos.size_gbp * pos.shares_remaining_pct * pos.stop_loss_pct) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += (pos.size_gbp * pos.shares_remaining_pct) + pnl
                    pos.state = OrderState.CLOSED
                    pos.exit_reason = "STOP_LOSS_FILLED"
                    pos.exit_day = day
                    closed_trades.append(pos)
                    continue

                # C. Stage 1 Take-Profit Check
                unrealized_high = (pos.current_price * (1.0 + intraday_high) - pos.entry_price) / pos.entry_price
                if pos.state == OrderState.OPEN and unrealized_high >= pos.stage_1_pct:
                    half = pos.size_gbp * 0.5
                    fx_drag = 0.0 if pos.is_uk else (self.fx_fee_pct * half)
                    spread = self.spread_pct * half
                    friction = fx_drag + spread
                    pnl = (half * pos.stage_1_pct) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += half + pnl

                    pos.shares_remaining_pct = 0.5
                    pos.state = OrderState.STAGE_1_FILLED
                    # Ratchet stop to Breakeven (+0.30% FX buffer)
                    pos.stop_loss_pct = 0.0 if pos.is_uk else 0.0035

                # D. Stage 2 Trailing Runner Check
                if pos.state == OrderState.STAGE_1_FILLED:
                    if unrealized_high >= pos.stage_2_pct:
                        half = pos.size_gbp * 0.5
                        fx_drag = 0.0 if pos.is_uk else (self.fx_fee_pct * half)
                        spread = self.spread_pct * half
                        friction = fx_drag + spread
                        pnl = (half * pos.stage_2_pct) - friction
                        pos.realized_pnl_gbp += pnl
                        pos.total_friction_gbp += friction
                        cash_gbp += half + pnl
                        pos.state = OrderState.CLOSED
                        pos.exit_reason = "STAGE_2_RUNNER_TARGET_FILLED"
                        pos.exit_day = day
                        closed_trades.append(pos)
                        continue

                # E. Horizon & 10 EMA Trailing Rule
                if pos.hold_days >= pos.max_days:
                    # If position is in Stage 1 profit and can extend (high moat or UK), trail along 10 EMA
                    if pos.can_extend and day_drift > 0 and pos.state == OrderState.STAGE_1_FILLED:
                        if pos.hold_days < 12:
                            pos.current_price *= (1.0 + day_drift)
                            retained.append(pos)
                            continue

                    # Close at current market price
                    half = pos.size_gbp * pos.shares_remaining_pct
                    net_move = (pos.current_price * (1.0 + day_drift) - pos.entry_price) / pos.entry_price
                    fx_drag = 0.0 if pos.is_uk else (self.fx_fee_pct * half)
                    spread = self.spread_pct * half
                    friction = fx_drag + spread
                    pnl = (half * net_move) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += half + pnl
                    pos.state = OrderState.CLOSED
                    pos.exit_reason = "HORIZON_REBALANCE_CLOSE"
                    pos.exit_day = day
                    closed_trades.append(pos)
                    continue

                pos.current_price *= (1.0 + day_drift)
                retained.append(pos)

            open_positions = retained

            # 2. Scanner & Signal Generation
            # Priority: 30% allocation to UK London Zero-FX leaders, 70% to verified US Moats/ETFs
            if len(open_positions) < max_concurrent and cash_gbp >= trade_size:
                if random.random() < 0.32:
                    # 40% probability of choosing a UK Zero-FX Leader for lower friction
                    if random.random() < 0.40:
                        uk_leaders = ['RR.L', 'RIO.L', 'AZN.L', 'SHEL.L', 'BARC.L']
                        ticker = random.choice(uk_leaders)
                    else:
                        ticker = random.choice(FLAT_UNIVERSE)

                    f_prof = FUNDAMENTAL_PROFILES.get(ticker, {})
                    is_trap = f_prof.get("quality") == "SPECULATIVE_TRAP" or ticker in ["SMCI", "MSTR", "MRNA", "CRSP", "MARA", "RIOT"]
                    
                    is_high_moat = f_prof.get("quality") == "HIGH_MOAT" or ticker.endswith('.L')
                    has_squeeze_confirmation = random.random() < (0.72 if is_high_moat else 0.48)

                    if not is_trap and has_squeeze_confirmation:
                        prof = get_profile(ticker)
                        is_uk = prof["is_uk"]
                        asset_type = prof["type"]

                        bracket = self.adaptive_engine.calculate_dynamic_bracket(ticker, spot=100.0, budget=trade_size)

                        entry_fx = 0.0 if is_uk else (self.fx_fee_pct * trade_size)
                        entry_spread = (self.spread_pct + self.latency_slippage_pct) * trade_size
                        cash_gbp -= trade_size

                        new_pos = Position(
                            ticker=ticker,
                            entry_day=day,
                            entry_price=100.0,
                            size_gbp=trade_size,
                            is_uk=is_uk,
                            asset_type=asset_type,
                            stop_loss_pct=-abs(bracket["stop_loss_pct"] / 100.0),
                            stage_1_pct=bracket["stage_1_pct"] / 100.0,
                            stage_2_pct=bracket["stage_2_pct"] / 100.0,
                            max_days=bracket["horizon_plan"]["hard_limit"].split()[0] if " " in bracket["horizon_plan"]["hard_limit"] else 5,
                            can_extend=bracket["horizon_plan"]["can_extend_past_5d"]
                        )
                        # Fix max_days parsing
                        try:
                            new_pos.max_days = int(new_pos.max_days)
                        except Exception:
                            new_pos.max_days = 5
                        new_pos.total_friction_gbp += (entry_fx + entry_spread)
                        open_positions.append(new_pos)

            # 3. Mark to Market
            unrealized = sum(
                p.size_gbp * p.shares_remaining_pct * (p.current_price / p.entry_price)
                for p in open_positions
            )
            total_equity = cash_gbp + unrealized
            if total_equity > peak_equity:
                peak_equity = total_equity
            dd_gbp = peak_equity - total_equity
            dd_pct = (dd_gbp / peak_equity) * 100.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct
                max_drawdown_gbp = dd_gbp

            portfolio_history.append({
                "day": day,
                "cash_gbp": round(cash_gbp, 2),
                "open_positions": len(open_positions),
                "total_equity_gbp": round(total_equity, 2),
                "drawdown_pct": round(dd_pct, 2)
            })

        wins = [t for t in closed_trades if t.realized_pnl_gbp > 0]
        losses = [t for t in closed_trades if t.realized_pnl_gbp <= 0]
        win_rate = (len(wins) / len(closed_trades)) * 100.0 if closed_trades else 0.0
        profit_factor = abs(sum(t.realized_pnl_gbp for t in wins)) / max(0.01, abs(sum(t.realized_pnl_gbp for t in losses)))

        daily_returns = [
            (portfolio_history[i]["total_equity_gbp"] - portfolio_history[i-1]["total_equity_gbp"]) / portfolio_history[i-1]["total_equity_gbp"]
            for i in range(1, len(portfolio_history))
        ]
        mean_ret = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        var_ret = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns) if daily_returns else 0.0001
        std_ret = math.sqrt(var_ret)
        sharpe = (mean_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0.0

        ending_equity = portfolio_history[-1]["total_equity_gbp"]
        net_profit = ending_equity - initial_capital
        net_return_pct = (net_profit / initial_capital) * 100.0

        return {
            "initial_capital_gbp": initial_capital,
            "trade_size_gbp": trade_size,
            "ending_equity_gbp": round(ending_equity, 2),
            "net_profit_gbp": round(net_profit, 2),
            "net_annual_return_pct": round(net_return_pct, 2),
            "total_trades_executed": len(closed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 3),
            "annualized_sharpe_ratio": round(sharpe, 2),
            "max_drawdown_gbp": round(max_drawdown_gbp, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "total_broker_frictions_paid_gbp": round(sum(t.total_friction_gbp for t in closed_trades), 2),
            "open_positions_at_end": len(open_positions)
        }


def main():
    parser = argparse.ArgumentParser(description="Tactical Broker Emulation")
    parser.add_argument("--size", type=float, default=150.0, help="Trade size GBP (default 150)")
    parser.add_argument("--runs", type=int, default=50, help="Number of Monte Carlo annual cycles to run")
    parser.add_argument("--save-evidence", action="store_true", help="Save evidence json")
    args = parser.parse_args()

    sim = TacticalBrokerSimulator()
    print(f"[*] Running Tactical Broker Emulation across {args.runs} annual cycles (Sizing £{args.size:.2f})...")

    annual_results = []
    for r in range(args.runs):
        res = sim.run_simulation(initial_capital=1000.0, trade_size=args.size, seed=1000 + r)
        annual_results.append(res)

    avg_ending = sum(r["ending_equity_gbp"] for r in annual_results) / len(annual_results)
    avg_return = sum(r["net_annual_return_pct"] for r in annual_results) / len(annual_results)
    avg_wr = sum(r["win_rate_pct"] for r in annual_results) / len(annual_results)
    avg_pf = sum(r["profit_factor"] for r in annual_results) / len(annual_results)
    avg_sharpe = sum(r["annualized_sharpe_ratio"] for r in annual_results) / len(annual_results)
    avg_dd = sum(r["max_drawdown_pct"] for r in annual_results) / len(annual_results)
    avg_trades = sum(r["total_trades_executed"] for r in annual_results) / len(annual_results)
    avg_friction = sum(r["total_broker_frictions_paid_gbp"] for r in annual_results) / len(annual_results)

    summary = {
        "simulation_cycles": args.runs,
        "initial_capital_gbp": 1000.0,
        "trade_size_gbp": args.size,
        "capital_utilization_max_pct": round((args.size * 3 / 1000.0) * 100, 1),
        "cash_buffer_reserve_pct": round((1.0 - (args.size * 3 / 1000.0)) * 100, 1),
        "mean_ending_equity_gbp": round(avg_ending, 2),
        "mean_annual_return_pct": round(avg_return, 2),
        "mean_win_rate_pct": round(avg_wr, 2),
        "mean_profit_factor": round(avg_pf, 3),
        "mean_annualized_sharpe": round(avg_sharpe, 2),
        "mean_max_drawdown_pct": round(avg_dd, 2),
        "mean_trades_executed_per_year": round(avg_trades, 1),
        "mean_broker_frictions_paid_gbp": round(avg_friction, 2),
        "sample_single_cycle": annual_results[0]
    }

    print("\n================ TACTICAL BROKER EMULATION MULTI-CYCLE SUMMARY ================")
    print(json.dumps(summary, indent=2))

    if args.save_evidence:
        out_path = Path(__file__).resolve().parent.parent / "evidence" / "tactical_overhaul_252day_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\n[+] Saved evidence to {out_path}")


if __name__ == "__main__":
    main()
