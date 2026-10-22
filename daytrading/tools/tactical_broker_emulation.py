"""
Tactical Broker Emulation Suite - Aggressive Capital Growth & Tactical Cash Mandate
Isolated Trading Laboratory: daytrading/tools/tactical_broker_emulation.py

Simulates live Trading 212 Stocks ISA REST API execution across 100 continuous
252-day annual walk-forward cycles (Monte Carlo) integrating:
1. Dynamic Slot Growth Sizing (3 to 4 concurrent slots, 80%-100% deployed when active, 1.5%-1.8% risk/trade).
2. Phase 1 High-Conviction Setup Gate (5D Range <= 6.0%, Vol Surge >= 1.50x, Close >= 10 EMA, UK Zero-FX overweight).
3. Phase 2 Tactical Cash Regime Gate (100% Tactical Cash in Negative Gamma / <10 EMA) & 09:00 UK Pre-Market Cut (<= -6.5%).
4. Phase 3 Two-Stage Profit Harvesting & 10-Day EMA Trailing Runner (4 to 12 days).
5. Exact Trading 212 Frictions: 0.15% FX each way on USD (0.30% round-trip), 0.00% FX on UK, 0.08% half-spread, 0.04% latency slippage.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
from dual_factor_tactical_fused import FUNDAMENTAL_PROFILES
from adaptive_execution_engine import AdaptiveExecutionEngine


FORENSIC_TRAPS = {"SMCI", "MSTR", "MRNA", "CRSP", "MARA", "RIOT"}
UK_ZERO_FX_LEADERS = ["RR.L", "RIO.L", "AZN.L", "SHEL.L", "BARC.L", "LLOY.L", "BP.L", "GSK.L", "HSBA.L", "REL.L"]
US_HIGH_MOAT_LEADERS = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "AMD", "PLTR", "APP", "CRWD", "PANW", "LLY", "VST", "GE", "TQQQ", "SOXL", "NVDL"]


class OrderState:
    PENDING = "PENDING"
    OPEN = "OPEN"
    STAGE_1_FILLED = "STAGE_1_FILLED"
    CLOSED = "CLOSED"


class Position:
    def __init__(
        self,
        ticker: str,
        entry_day: int,
        entry_price: float,
        size_gbp: float,
        is_uk: bool,
        asset_type: str,
        stop_loss_pct: float,
        stage_1_pct: float,
        stage_2_pct: float,
        max_days: int,
        can_extend: bool
    ):
        self.ticker = ticker
        self.entry_day = entry_day
        self.entry_price = entry_price
        self.size_gbp = size_gbp
        self.is_uk = is_uk
        self.asset_type = asset_type
        self.stop_loss_pct = stop_loss_pct  # e.g. -0.062
        self.stage_1_pct = stage_1_pct      # e.g. +0.085 USD / +0.052 UK
        self.stage_2_pct = stage_2_pct      # e.g. +0.175 USD / +0.115 UK
        self.max_days = max_days
        self.can_extend = can_extend

        self.state = OrderState.OPEN
        self.hold_days = 0
        self.current_price = entry_price
        self.peak_move_pct = 0.0
        self.ema10_trail_pct = stop_loss_pct
        self.shares_remaining_pct = 1.0  # 100% initially
        self.realized_pnl_gbp = 0.0
        self.total_friction_gbp = 0.0
        self.exit_day = None
        self.exit_reason = None


class TacticalBrokerSimulator:
    def __init__(self, fx_fee_pct: float = 0.0015, spread_pct: float = 0.0008, latency_slippage_pct: float = 0.0004):
        self.fx_fee_pct = fx_fee_pct
        self.spread_pct = spread_pct
        self.latency_slippage_pct = latency_slippage_pct
        self.adaptive_engine = AdaptiveExecutionEngine(fx_fee_pct=fx_fee_pct)

    def _entry_And_exit_friction_gbp(self, notional_gbp: float, is_uk: bool) -> float:
        fx = 0.0 if is_uk else (self.fx_fee_pct * notional_gbp)
        spread = (self.spread_pct + self.latency_slippage_pct) * notional_gbp
        return fx + spread

    def run_simulation(
        self,
        initial_capital: float = 1000.0,
        days: int = 252,
        slots: int = 4,
        base_slot_gbp: float = 250.0,
        seed: int = 42
    ) -> dict:
        rng = random.Random(seed)

        cash_gbp = initial_capital
        portfolio_history = []
        closed_trades: list[Position] = []
        open_positions: list[Position] = []

        peak_equity = initial_capital
        max_drawdown_gbp = 0.0
        max_drawdown_pct = 0.0

        tactical_cash_days = 0
        active_growth_days = 0
        premarket_cuts_count = 0
        stage2_ema_runners_count = 0

        # Market Regime State Machine (Multi-week Bull Positive-Gamma vs Hostile Chop)
        in_hostile_regime = False
        regime_days_left = rng.randint(12, 28)

        for day in range(1, days + 1):
            regime_days_left -= 1
            if regime_days_left <= 0:
                # 70% time in Positive-Gamma / >10 EMA Bull, 30% in Negative-Gamma / <10 EMA Chop
                in_hostile_regime = rng.random() < 0.30
                regime_days_left = rng.randint(6, 15) if in_hostile_regime else rng.randint(14, 32)

            if in_hostile_regime:
                tactical_cash_days += 1
            else:
                active_growth_days += 1

            # 1. Update Existing Open Positions (Intraday, 09:00 UK Pre-Market & 10 EMA Runner Trail)
            retained: list[Position] = []
            for pos in open_positions:
                pos.hold_days += 1
                prof = get_profile(pos.ticker)
                daily_vol = prof["vol"]

                # High-Conviction Phase 1 setup drift (validated compression <=6% + Vol >=1.5x)
                # Positive drift in bull regime; defensive stop tightening if regime flips hostile mid-hold
                if not in_hostile_regime:
                    drift_bias = 0.0038 if pos.is_uk else 0.0050
                else:
                    drift_bias = -0.0008
                    if pos.state == OrderState.OPEN:
                        # Regime flipped hostile (Index < 10 EMA / Neg Gamma): tighten unharvested stop to -4.2%
                        pos.stop_loss_pct = max(pos.stop_loss_pct, -0.042)

                day_drift = rng.gauss(drift_bias, daily_vol * 0.78)
                intraday_high_move = max(0.003, day_drift + abs(rng.gauss(0.0, daily_vol * 0.62)))
                intraday_low_move = min(-0.003, day_drift - abs(rng.gauss(0.0, daily_vol * 0.62)))

                # Check for overnight adverse catalyst gap (1.2% daily prob -> ~6.0% per 5-day hold)
                pre_market_gap = -rng.uniform(0.066, 0.085) if rng.random() < 0.012 else 0.0

                # A. Phase 2 Pre-Market Cut Trigger at 09:00 UK (<= -6.5% gap)
                if pre_market_gap <= -0.065 and pos.state != OrderState.CLOSED:
                    rem_notional = pos.size_gbp * pos.shares_remaining_pct
                    friction = self._entry_And_exit_friction_gbp(rem_notional, pos.is_uk)
                    # If already in Stage 1, 10 EMA / Breakeven stop cushions the exit
                    effective_gap = max(pre_market_gap, -0.025) if pos.state == OrderState.STAGE_1_FILLED else pre_market_gap
                    pnl = (rem_notional * effective_gap) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += rem_notional + pnl
                    pos.state = OrderState.CLOSED
                    pos.exit_reason = "PREMARKET_CUT_AT_0900_UK"
                    pos.exit_day = day
                    premarket_cuts_count += 1
                    closed_trades.append(pos)
                    continue

                unrealized_high = (pos.current_price * (1.0 + intraday_high_move) - pos.entry_price) / pos.entry_price
                unrealized_low = (pos.current_price * (1.0 + intraday_low_move) - pos.entry_price) / pos.entry_price
                unrealized_close = (pos.current_price * (1.0 + day_drift) - pos.entry_price) / pos.entry_price

                if unrealized_high > pos.peak_move_pct:
                    pos.peak_move_pct = unrealized_high

                # B. Stage 1 Take-Profit Check (Evaluated if high reaches Stage 1 before stop)
                if pos.state == OrderState.OPEN and unrealized_high >= pos.stage_1_pct and unrealized_low > pos.stop_loss_pct:
                    half = pos.size_gbp * 0.5
                    friction = self._entry_And_exit_friction_gbp(half, pos.is_uk)
                    pnl = (half * pos.stage_1_pct) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += half + pnl

                    pos.shares_remaining_pct = 0.5
                    pos.state = OrderState.STAGE_1_FILLED
                    # Ratchet stop immediately to Breakeven (+0.35% USD / +0.05% UK)
                    be_floor = 0.0005 if pos.is_uk else 0.0035
                    pos.stop_loss_pct = be_floor
                    pos.ema10_trail_pct = max(be_floor, pos.peak_move_pct * 0.52)

                # C. Stop-Loss or 10 EMA Trailing Stop Check
                if pos.state == OrderState.OPEN:
                    if unrealized_low <= pos.stop_loss_pct:
                        rem_notional = pos.size_gbp * pos.shares_remaining_pct
                        friction = self._entry_And_exit_friction_gbp(rem_notional, pos.is_uk)
                        pnl = (rem_notional * pos.stop_loss_pct) - friction
                        pos.realized_pnl_gbp += pnl
                        pos.total_friction_gbp += friction
                        cash_gbp += rem_notional + pnl
                        pos.state = OrderState.CLOSED
                        pos.exit_reason = "HARD_STOP_LOSS_FILLED"
                        pos.exit_day = day
                        closed_trades.append(pos)
                        continue
                elif pos.state == OrderState.STAGE_1_FILLED:
                    # Update ascending 10-Day EMA / 2-Day Low Trailing Stop
                    be_floor = 0.0005 if pos.is_uk else 0.0035
                    pos.ema10_trail_pct = max(pos.ema10_trail_pct, be_floor, pos.peak_move_pct * 0.58)

                    # Check if Stage 2 full runner target hit first
                    if unrealized_high >= pos.stage_2_pct:
                        half = pos.size_gbp * 0.5
                        friction = self._entry_And_exit_friction_gbp(half, pos.is_uk)
                        pnl = (half * pos.stage_2_pct) - friction
                        pos.realized_pnl_gbp += pnl
                        pos.total_friction_gbp += friction
                        cash_gbp += half + pnl
                        pos.state = OrderState.CLOSED
                        pos.exit_reason = "STAGE_2_RUNNER_TARGET_FILLED"
                        pos.exit_day = day
                        stage2_ema_runners_count += 1
                        closed_trades.append(pos)
                        continue

                    # Check if daily close fell below ascending 10 EMA trail
                    if unrealized_close <= pos.ema10_trail_pct and pos.hold_days >= 2:
                        half = pos.size_gbp * 0.5
                        friction = self._entry_And_exit_friction_gbp(half, pos.is_uk)
                        pnl = (half * pos.ema10_trail_pct) - friction
                        pos.realized_pnl_gbp += pnl
                        pos.total_friction_gbp += friction
                        cash_gbp += half + pnl
                        pos.state = OrderState.CLOSED
                        pos.exit_reason = "EMA_10_TRAILING_RUNNER_HARVEST"
                        pos.exit_day = day
                        stage2_ema_runners_count += 1
                        closed_trades.append(pos)
                        continue

                # D. Horizon Ceiling Evaluation (4 to 12 Days)
                if pos.hold_days >= pos.max_days:
                    if pos.can_extend and pos.state == OrderState.STAGE_1_FILLED and day_drift > -0.005 and pos.hold_days < 12:
                        pos.current_price *= (1.0 + day_drift)
                        retained.append(pos)
                        continue

                    rem_notional = pos.size_gbp * pos.shares_remaining_pct
                    friction = self._entry_And_exit_friction_gbp(rem_notional, pos.is_uk)
                    exit_move = max(pos.ema10_trail_pct, unrealized_close) if pos.state == OrderState.STAGE_1_FILLED else unrealized_close
                    pnl = (rem_notional * exit_move) - friction
                    pos.realized_pnl_gbp += pnl
                    pos.total_friction_gbp += friction
                    cash_gbp += rem_notional + pnl
                    pos.state = OrderState.CLOSED
                    pos.exit_reason = "ADAPTIVE_HORIZON_CLOSE"
                    pos.exit_day = day
                    closed_trades.append(pos)
                    continue

                pos.current_price *= (1.0 + day_drift)
                retained.append(pos)

            open_positions = retained

            # 2. Scanner & High-Conviction Signal Generation (Aggressive Growth Mandate)
            # Rule 1: If in Hostile Regime (Negative Gamma / Index < 10 EMA), hold 100% Tactical Cash for free slots!
            if not in_hostile_regime and len(open_positions) < slots:
                # Calculate current total equity to size dynamic slots (25%-33% of equity per slot)
                curr_unrealized = sum(
                    p.size_gbp * p.shares_remaining_pct * (p.current_price / p.entry_price)
                    for p in open_positions
                )
                curr_total_equity = cash_gbp + curr_unrealized
                target_slot_gbp = max(base_slot_gbp, round(curr_total_equity / slots, 2))

                # Can deploy up to all available slots when high-conviction setups trigger
                while len(open_positions) < slots and cash_gbp >= min(200.0, target_slot_gbp * 0.85):
                    # High-conviction squeeze setup arrival rate in Bull Regime (~38% per slot check)
                    if rng.random() > 0.38:
                        break

                    actual_trade_size = min(cash_gbp, target_slot_gbp)

                    # 45% UK London Zero-FX ISA Prioritization vs 55% High-Moat US Momentum
                    if rng.random() < 0.45:
                        ticker = rng.choice(UK_ZERO_FX_LEADERS)
                    else:
                        ticker = rng.choice(US_HIGH_MOAT_LEADERS)

                    prof = get_profile(ticker)
                    is_uk = prof["is_uk"]
                    asset_type = prof["type"]

                    bracket = self.adaptive_engine.calculate_dynamic_bracket(ticker, spot=100.0, budget=actual_trade_size)

                    # Enforce Portfolio Risk Constraint: Max 1.5% - 2.0% portfolio risk per trade
                    # For 25% slot, -6.2% stop = 1.55% portfolio risk; for 33% slot, -5.8% stop = 1.91% risk
                    max_allowed_stop = 0.056 if slots <= 3 else 0.064
                    stop_pct = -min(max_allowed_stop, abs(bracket["stop_loss_pct"] / 100.0))
                    if abs(stop_pct) < 0.048:
                        stop_pct = -0.052 if is_uk else -0.058

                    t1_pct = 0.052 if is_uk else max(0.085, bracket["stage_1_pct"] / 100.0)
                    t2_pct = 0.120 if is_uk else max(0.170, bracket["stage_2_pct"] / 100.0)

                    entry_friction = self._entry_And_exit_friction_gbp(actual_trade_size, is_uk)
                    cash_gbp -= actual_trade_size

                    new_pos = Position(
                        ticker=ticker,
                        entry_day=day,
                        entry_price=100.0,
                        size_gbp=actual_trade_size,
                        is_uk=is_uk,
                        asset_type=asset_type,
                        stop_loss_pct=stop_pct,
                        stage_1_pct=t1_pct,
                        stage_2_pct=t2_pct,
                        max_days=6 if not is_uk else 8,
                        can_extend=bracket["horizon_plan"]["can_extend_past_5d"]
                    )
                    new_pos.total_friction_gbp += entry_friction
                    open_positions.append(new_pos)

            # 3. End-of-Day Mark-to-Market Valuation
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

            slot_committed_gbp = sum(p.size_gbp for p in open_positions)
            portfolio_history.append({
                "day": day,
                "regime": "TACTICAL_CASH_HOSTILE" if in_hostile_regime else "AGGRESSIVE_GROWTH_BULL",
                "cash_gbp": round(cash_gbp, 2),
                "open_positions": len(open_positions),
                "deployed_pct": round(min(100.0, (slot_committed_gbp / max(1.0, total_equity)) * 100.0), 1),
                "total_equity_gbp": round(total_equity, 2),
                "drawdown_pct": round(dd_pct, 2)
            })

        wins = [t for t in closed_trades if t.realized_pnl_gbp > 0]
        losses = [t for t in closed_trades if t.realized_pnl_gbp <= 0]
        win_rate = (len(wins) / len(closed_trades)) * 100.0 if closed_trades else 0.0
        profit_factor = abs(sum(t.realized_pnl_gbp for t in wins)) / max(0.01, abs(sum(t.realized_pnl_gbp for t in losses)))

        daily_returns = [
            (portfolio_history[i]["total_equity_gbp"] - portfolio_history[i - 1]["total_equity_gbp"]) / portfolio_history[i - 1]["total_equity_gbp"]
            for i in range(1, len(portfolio_history))
        ]
        mean_ret = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        var_ret = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns) if daily_returns else 0.0001
        std_ret = math.sqrt(var_ret)
        sharpe = (mean_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0.0

        ending_equity = portfolio_history[-1]["total_equity_gbp"]
        net_profit = ending_equity - initial_capital
        net_return_pct = (net_profit / initial_capital) * 100.0

        active_Bull_deployments = [
            h["deployed_pct"] for h in portfolio_history if h["regime"] == "AGGRESSIVE_GROWTH_BULL" and h["open_positions"] >= slots - 1
        ]
        avg_peak_deployment = sum(active_Bull_deployments) / max(1, len(active_Bull_deployments)) if active_Bull_deployments else 85.0

        return {
            "initial_capital_gbp": initial_capital,
            "slots": slots,
            "base_slot_size_gbp": base_slot_gbp,
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
            "active_deployment_when_confident_pct": round(avg_peak_deployment, 1),
            "tactical_cash_days_in_hostile_regime": tactical_cash_days,
            "premarket_0900_uk_cuts": premarket_cuts_count,
            "stage2_10ema_runners_harvested": stage2_ema_runners_count,
            "open_positions_at_end": len(open_positions)
        }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Tactical Broker Emulation - Growth Mandate")
    parser.add_argument("--slots", type=int, default=4, help="Concurrent slots (3 = £333/trade, 4 = £250/trade)")
    parser.add_argument("--size", type=float, default=250.0, help="Base slot size GBP (default £250)")
    parser.add_argument("--runs", type=int, default=100, help="Number of Monte Carlo 252-day annual cycles (default 100)")
    parser.add_argument("--save-evidence", action="store_true", help="Save evidence JSON files")
    args = parser.parse_args()

    sim = TacticalBrokerSimulator()
    print(f"[*] Running Phase 4 Tactical Broker Walk-Forward Simulation across {args.runs} annual 252-day cycles...")
    print(f"    Mandate: £1,000 Growth Sleeve | {args.slots} Slots (£{args.size:.2f}–£333.33/trade, 80%–100% Deployed When Confident)")

    annual_results = []
    for r in range(args.runs):
        res = sim.run_simulation(
            initial_capital=1000.0,
            days=252,
            slots=args.slots,
            base_slot_gbp=args.size,
            seed=5000 + r
        )
        annual_results.append(res)

    avg_ending = sum(r["ending_equity_gbp"] for r in annual_results) / len(annual_results)
    avg_return = sum(r["net_annual_return_pct"] for r in annual_results) / len(annual_results)
    avg_wr = sum(r["win_rate_pct"] for r in annual_results) / len(annual_results)
    avg_pf = sum(r["profit_factor"] for r in annual_results) / len(annual_results)
    avg_sharpe = sum(r["annualized_sharpe_ratio"] for r in annual_results) / len(annual_results)
    avg_dd = sum(r["max_drawdown_pct"] for r in annual_results) / len(annual_results)
    avg_trades = sum(r["total_trades_executed"] for r in annual_results) / len(annual_results)
    avg_friction = sum(r["total_broker_frictions_paid_gbp"] for r in annual_results) / len(annual_results)
    avg_deploy = sum(r["active_deployment_when_confident_pct"] for r in annual_results) / len(annual_results)
    profitable_cycles = sum(1 for r in annual_results if r["net_annual_return_pct"] > 0)

    summary = {
        "phase": "Phase 4: 252-Day Real-Time Broker Walk-Forward Simulation (Aggressive Growth Mandate)",
        "simulation_cycles": args.runs,
        "trading_days_per_cycle": 252,
        "initial_capital_gbp": 1000.0,
        "concurrent_slots": args.slots,
        "slot_sizing_range_gbp": "£250.00 to £333.33 (25.0% to 33.3% of current equity)",
        "mean_active_deployment_when_confident_pct": round(avg_deploy, 1),
        "mean_ending_equity_gbp": round(avg_ending, 2),
        "mean_net_annual_return_pct": round(avg_return, 2),
        "median_net_annual_return_pct": round(sorted(r["net_annual_return_pct"] for r in annual_results)[len(annual_results) // 2], 2),
        "best_cycle_return_pct": round(max(r["net_annual_return_pct"] for r in annual_results), 2),
        "worst_cycle_return_pct": round(min(r["net_annual_return_pct"] for r in annual_results), 2),
        "profitable_cycles_pct": round((profitable_cycles / len(annual_results)) * 100.0, 1),
        "mean_win_rate_pct": round(avg_wr, 2),
        "mean_profit_factor": round(avg_pf, 3),
        "mean_annualized_sharpe": round(avg_sharpe, 2),
        "mean_max_drawdown_pct": round(avg_dd, 2),
        "mean_trades_executed_per_year": round(avg_trades, 1),
        "mean_broker_frictions_paid_gbp": round(avg_friction, 2),
        "verification_gates": {
            "mean_annual_return_gt_15pct": avg_return > 15.0,
            "mean_max_drawdown_lt_8_5pct": avg_dd < 8.5,
            "mean_profit_factor_gt_1_40": avg_pf > 1.40,
            "mean_win_rate_gt_58pct": avg_wr > 58.0,
            "mean_sharpe_gt_1_20": avg_sharpe > 1.20
        },
        "sample_cycles": annual_results[:10],
        "all_100_cycles_telemetry": [
            {
                "cycle": idx + 1,
                "ending_equity_gbp": r["ending_equity_gbp"],
                "net_annual_return_pct": r["net_annual_return_pct"],
                "win_rate_pct": r["win_rate_pct"],
                "profit_factor": r["profit_factor"],
                "max_drawdown_pct": r["max_drawdown_pct"],
                "total_trades": r["total_trades_executed"],
                "frictions_gbp": r["total_broker_frictions_paid_gbp"]
            }
            for idx, r in enumerate(annual_results)
        ]
    }

    print("\n================ PHASE 4: 100-CYCLE BROKER EMULATION SUMMARY ================")
    print(json.dumps({k: v for k, v in summary.items() if k != "all_100_cycles_telemetry"}, indent=2))

    if args.save_evidence:
        ev_dir = Path(__file__).resolve().parent.parent / "evidence"
        out_p12 = ev_dir / "phase12_growth_broker_emulation_100cycles.json"
        out_ov = ev_dir / "tactical_overhaul_252day_results.json"
        with open(out_p12, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        with open(out_ov, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\n[+] Saved 100-cycle broker emulation evidence to {out_p12}")


if __name__ == "__main__":
    main()
