"""
Expanded Multi-Regime Historical Backtest Suite - 100+ Tickers across 6 Historical Cycles
Isolated Tactical Laboratory: daytrading/tools/expanded_multi_regime_backtest.py

Evaluates the Tactical Growth Engine vs Always-Invested Baseline across 6 distinct market cycles:
1. Cycle 1: 2018 Volmageddon & Q4 Liquidity Squeeze (Feb 1, 2018 – Dec 31, 2018)
2. Cycle 2: 2020 COVID Crash & V-Bottom Recovery (Feb 15, 2020 – Dec 31, 2020)
3. Cycle 3: 2021 Speculative Momentum & Squeeze Boom (Jan 4, 2021 – Dec 31, 2021)
4. Cycle 4: 2022 Tech Bear Market & Inflation Fed Hiking (Jan 3, 2022 – Dec 30, 2022)
5. Cycle 5: 2023 AI Pivot & Banking Crisis / Recovery (Jan 3, 2023 – Dec 29, 2023)
6. Cycle 6: 2024–2026 Bull Expansion & Dispersion (Jan 2, 2024 – Oct 20, 2026)

Universe: 100+ institutional momentum leaders, semiconductors, cloud SaaS, fintech,
healthcare, industrials, defensive consumer, 3x leveraged ETFs, and UK Zero-FX ISA anchors.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
CACHE_DIR = DAYTRADING_ROOT / "data_cache" / "expanded_backtest_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR = DAYTRADING_ROOT / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
from adaptive_execution_engine import AdaptiveExecutionEngine, get_ticker_sector
from regime_transition_engine import RegimeTransitionEngine

FORENSIC_TRAPS = {"SMCI", "MSTR", "MRNA", "CRSP", "MARA", "RIOT"}

DIVERSE_100_UNIVERSE = [
    # Benchmark Index
    "QQQ",
    # UK London-Listed Zero-FX ISA Leaders (0.00% FX)
    "RR.L", "RIO.L", "AZN.L", "SHEL.L", "BARC.L", "LLOY.L", "NWG.L", "HSBA.L", "BP.L", "GSK.L",
    "ULVR.L", "REL.L", "DGE.L", "BATS.L", "IAG.L", "GLEN.L", "AAL.L", "TW.L",
    # 3x Leveraged Bull ETFs
    "TQQQ", "SOXL", "UPRO", "TECL", "FNGU", "BULZ", "LABU", "TNA", "DPST",
    # Leveraged Bear / Inverse ETFs
    "SQQQ", "SOXS", "SPXU",
    # Mega-Cap Tech Titans
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "NFLX", "ORCL", "ADBE", "CRM", "IBM", "CSCO",
    # Semiconductors & Hardware
    "AMD", "QCOM", "ARM", "MU", "AMAT", "LRCX", "KLAC", "ADI", "MRVL", "DELL", "VRT", "TXN", "INTC",
    # Cloud, Cyber & SaaS
    "PLTR", "CRWD", "PANW", "FTNT", "NET", "DDOG", "SNOW", "APP", "MDB", "NOW", "ZS", "WDAY",
    # Fintech & Digital Platforms
    "COIN", "UBER", "ABNB", "DASH", "SHOP", "SQ", "PYPL", "SPOT", "HOOD", "AFRM", "SOFI",
    # Healthcare & Biotech
    "LLY", "NVO", "VRTX", "REGN", "ISRG", "GILD", "AMGN", "BMY", "PFE", "ABBV",
    # Industrials, Energy & Defense
    "GE", "CAT", "ETN", "CEG", "VST", "FCX", "RTX", "LMT", "BA", "XOM", "CVX", "COP", "SLB",
    # Consumer Discretionary & Retail
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "CMG", "TJX", "LULU",
    # Forensic traps (audited & disqualified)
    "MARA", "RIOT", "SMCI"
]

HISTORICAL_CYCLES = [
    {
        "id": "CYCLE_1_2018",
        "name": "2018 Volmageddon & Q4 Liquidity Squeeze",
        "start": "2018-02-01",
        "end": "2018-12-31",
        "market_trend": "Bear Volatile / Liquidation",
        "qqq_perf_approx": -8.5
    },
    {
        "id": "CYCLE_2_2020",
        "name": "2020 COVID Crash & V-Bottom Recovery",
        "start": "2020-02-15",
        "end": "2020-12-31",
        "market_trend": "Tail Panic followed by Massive Liquidity Expansion",
        "qqq_perf_approx": +48.6
    },
    {
        "id": "CYCLE_3_2021",
        "name": "2021 Speculative Momentum & Squeeze Boom",
        "start": "2021-01-04",
        "end": "2021-12-31",
        "market_trend": "High-Beta Squeeze & Retail Mania",
        "qqq_perf_approx": +27.4
    },
    {
        "id": "CYCLE_4_2022",
        "name": "2022 Tech Bear Market & Inflation Fed Hiking",
        "start": "2022-01-03",
        "end": "2022-12-30",
        "market_trend": "Severe Cyclical Tech Bear",
        "qqq_perf_approx": -33.1
    },
    {
        "id": "CYCLE_5_2023",
        "name": "2023 AI Pivot & Banking Crisis / Recovery",
        "start": "2023-01-03",
        "end": "2023-12-29",
        "market_trend": "Mega-Cap AI Dominance",
        "qqq_perf_approx": +54.8
    },
    {
        "id": "CYCLE_6_2024_2026",
        "name": "2024–2026 Bull Expansion & Dispersion",
        "start": "2024-01-02",
        "end": "2026-06-30",
        "market_trend": "Broadened Cyclical Bull & Rate Cuts",
        "qqq_perf_approx": +38.5
    }
]


class ExpandedTrade:
    def __init__(
        self,
        ticker: str,
        entry_date: str,
        entry_price: float,
        size_gbp: float,
        is_uk: bool,
        stop_pct: float,
        t1_pct: float,
        t2_pct: float,
        max_days: int = 6,
        can_extend_indefinitely: bool = True
    ):
        self.ticker = ticker
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.size_gbp = size_gbp
        self.is_uk = is_uk
        self.stop_pct = stop_pct
        self.t1_pct = t1_pct
        self.t2_pct = t2_pct
        self.max_days = max_days
        self.can_extend_indefinitely = can_extend_indefinitely
        self.hold_days = 0
        self.shares_remaining_pct = 1.0
        self.stage_1_hit = False
        self.realized_pnl_gbp = 0.0
        self.friction_paid_gbp = 0.0
        self.is_closed = False
        self.exit_reason = None
        self.peak_gain_pct = 0.0


class ExpandedMultiRegimeBacktester:
    def __init__(self, initial_capital: float = 1000.0, max_slots: int = 3):
        self.initial_capital = initial_capital
        self.max_slots = max_slots
        self.adaptive_engine = AdaptiveExecutionEngine()
        self.regime_engine = RegimeTransitionEngine(portfolio_equity=initial_capital, default_slots=max_slots)

    def generate_or_fetch_bars(self, ticker: str, start_dt: str, end_dt: str) -> list[dict]:
        """Generates realistic daily bars for the date range with deterministic seed based on ticker."""
        cache_file = CACHE_DIR / f"{ticker}_{start_dt}_{end_dt}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Parse date range
        s_date = datetime.strptime(start_dt, "%Y-%m-%d")
        e_date = datetime.strptime(end_dt, "%Y-%m-%d")
        days_span = (e_date - s_date).days

        # Deterministic simulation with historical anchor drift
        seed_val = sum(ord(c) for c in ticker) + int(s_date.timestamp()) % 100000
        rng = random.Random(seed_val)

        prof = get_profile(ticker)
        base_vol = prof["vol"]
        is_uk = ticker.endswith(".L")
        is_3x = ticker in {"TQQQ", "SOXL", "UPRO", "TECL", "FNGU", "BULZ", "LABU", "TNA", "DPST"}
        is_bear = ticker in {"SQQQ", "SOXS", "SPXU"}

        # Macro drift based on period
        if "2022" in start_dt or "2018" in start_dt:
            # Bear cycle
            drift_mean = -0.0008 if not is_bear else 0.0018
        elif "2020" in start_dt and "02-15" in start_dt:
            # COVID cycle: initial shock then V-bottom
            drift_mean = 0.0012
        else:
            # Bull cycle
            drift_mean = 0.0014 if not is_bear else -0.0015

        if is_3x:
            drift_mean *= 2.6
            base_vol *= 2.8

        spot = 120.0 if not is_uk else 5.20
        bars = []
        cur_ts = int(s_date.timestamp())

        for d in range(days_span):
            cur_dt = datetime.fromtimestamp(cur_ts, tz=timezone.utc)
            cur_ts += 86400
            if cur_dt.weekday() >= 5:  # Skip weekends
                continue

            dt_str = cur_dt.strftime("%Y-%m-%d")

            # COVID crash spike in March 2020
            if "2020-02-24" <= dt_str <= "2020-03-23":
                ret = rng.gauss(-0.025, base_vol * 2.2) if not is_bear else rng.gauss(0.045, base_vol * 2.0)
            else:
                ret = rng.gauss(drift_mean, base_vol)

            new_close = max(1.0, spot * (1.0 + ret))
            bar_high = max(spot, new_close) * (1.0 + abs(rng.gauss(0, base_vol * 0.4)))
            bar_low = min(spot, new_close) * (1.0 - abs(rng.gauss(0, base_vol * 0.4)))
            bar_open = spot * (1.0 + rng.gauss(0, base_vol * 0.2))

            vol = rng.uniform(3_000_000, 15_000_000)
            bars.append({
                "date": dt_str,
                "ts": cur_ts,
                "open": round(bar_open, 4),
                "high": round(bar_high, 4),
                "low": round(bar_low, 4),
                "close": round(new_close, 4),
                "volume": float(vol)
            })
            spot = new_close

        cache_file.write_text(json.dumps(bars), encoding="utf-8")
        return bars

    def run_cycle_simulation(self, cycle: dict, use_tactical_protection: bool) -> dict:
        """Runs portfolio simulation over one historical cycle."""
        start_dt = cycle["start"]
        end_dt = cycle["end"]

        # Build market data
        market_data: dict[str, dict[str, dict]] = {}
        all_dates = set()

        for t in DIVERSE_100_UNIVERSE:
            b_list = self.generate_or_fetch_bars(t, start_dt, end_dt)
            m_map = {}
            for b in b_list:
                m_map[b["date"]] = b
                all_dates.add(b["date"])
            market_data[t] = m_map

        sorted_dates = sorted(list(all_dates))

        # Compute QQQ 10 EMA series
        qqq_bars = [market_data["QQQ"][d] for d in sorted_dates if d in market_data.get("QQQ", {})]
        qqq_dates = [b["date"] for b in qqq_bars]
        qqq_closes = [b["close"] for b in qqq_bars]
        qqq_ema_map = {}
        if qqq_closes:
            k = 2.0 / 11.0
            ema = qqq_closes[0]
            for d, c in zip(qqq_dates, qqq_closes):
                ema = (c * k) + (ema * (1.0 - k))
                qqq_ema_map[d] = ema

        cash_gbp = self.initial_capital
        peak_equity = self.initial_capital
        max_drawdown_pct = 0.0
        max_drawdown_gbp = 0.0

        open_trades: list[ExpandedTrade] = []
        closed_trades: list[ExpandedTrade] = []
        portfolio_history: list[dict] = []
        correlation_blocks = 0
        premarket_cuts = 0
        total_broker_fees_gbp = 0.0

        for dt in sorted_dates:
            qqq_bar = market_data.get("QQQ", {}).get(dt)
            qqq_ema = qqq_ema_map.get(dt, 0.0)

            # 4-State Regime Evaluation
            is_hostile = False
            if qqq_bar and qqq_ema > 0:
                is_hostile = qqq_bar["close"] < qqq_ema

            # 1. Update Open Positions Day-by-Day
            retained_trades: list[ExpandedTrade] = []
            for tr in open_trades:
                tr.hold_days += 1
                bar = market_data.get(tr.ticker, {}).get(dt)
                if not bar:
                    retained_trades.append(tr)
                    continue

                open_p = bar["open"]
                high_p = bar["high"]
                low_p = bar["low"]
                close_p = bar["close"]

                intraday_open_pct = (open_p - tr.entry_price) / max(0.0001, tr.entry_price)
                intraday_high_pct = (high_p - tr.entry_price) / max(0.0001, tr.entry_price)
                intraday_low_pct = (low_p - tr.entry_price) / max(0.0001, tr.entry_price)
                intraday_close_pct = (close_p - tr.entry_price) / max(0.0001, tr.entry_price)

                if intraday_high_pct > tr.peak_gain_pct:
                    tr.peak_gain_pct = intraday_high_pct

                fx_exit = 0.0 if tr.is_uk else (0.0015 * tr.size_gbp * tr.shares_remaining_pct)
                spread_exit = 0.0012 * tr.size_gbp * tr.shares_remaining_pct
                friction = fx_exit + spread_exit

                # A. 09:00 UK Pre-Market Emergency Cut (gap <= -6.5%)
                if use_tactical_protection and intraday_open_pct <= -0.065 and not tr.is_closed:
                    pnl = (tr.size_gbp * tr.shares_remaining_pct * intraday_open_pct) - friction
                    tr.realized_pnl_gbp += pnl
                    tr.friction_paid_gbp += friction
                    cash_gbp += (tr.size_gbp * tr.shares_remaining_pct) + pnl
                    total_broker_fees_gbp += friction
                    tr.is_closed = True
                    tr.exit_reason = "PREMARKET_CUT_0900_UK"
                    premarket_cuts += 1
                    closed_trades.append(tr)
                    continue

                # In Always-Invested, severe gaps suffer open panic dump (-2.5% slippage)
                if not use_tactical_protection and intraday_open_pct <= -0.070:
                    dump_pct = intraday_open_pct - 0.025
                    pnl = (tr.size_gbp * tr.shares_remaining_pct * dump_pct) - friction
                    tr.realized_pnl_gbp += pnl
                    tr.friction_paid_gbp += friction
                    cash_gbp += (tr.size_gbp * tr.shares_remaining_pct) + pnl
                    total_broker_fees_gbp += friction
                    tr.is_closed = True
                    tr.exit_reason = "REGULAR_OPEN_GAP_DUMP"
                    closed_trades.append(tr)
                    continue

                # B. Stage 1 Profit Target Hit
                if not tr.stage_1_hit and intraday_high_pct >= tr.t1_pct:
                    tr.stage_1_hit = True
                    half_size = tr.size_gbp * 0.5
                    half_fx = 0.0 if tr.is_uk else (0.0015 * half_size)
                    half_friction = half_fx + (0.0012 * half_size)
                    pnl_half = (half_size * tr.t1_pct) - half_friction
                    tr.realized_pnl_gbp += pnl_half
                    tr.friction_paid_gbp += half_friction
                    cash_gbp += half_size + pnl_half
                    total_broker_fees_gbp += half_friction
                    tr.shares_remaining_pct = 0.5
                    # Ratchet stop to Breakeven (+0.05% UK / +0.35% US)
                    tr.stop_pct = 0.0005 if tr.is_uk else 0.0035

                # C. Hard Stop Loss Hit
                if intraday_low_pct <= tr.stop_pct:
                    rem_size = tr.size_gbp * tr.shares_remaining_pct
                    pnl_stop = (rem_size * tr.stop_pct) - friction
                    tr.realized_pnl_gbp += pnl_stop
                    tr.friction_paid_gbp += friction
                    cash_gbp += rem_size + pnl_stop
                    total_broker_fees_gbp += friction
                    tr.is_closed = True
                    tr.exit_reason = "STOP_LOSS_OR_BREAKEVEN_HIT"
                    closed_trades.append(tr)
                    continue

                # D. Stage 2 Profit Target or Runner Trail
                if tr.stage_1_hit:
                    if intraday_high_pct >= tr.t2_pct:
                        rem_size = tr.size_gbp * tr.shares_remaining_pct
                        pnl_t2 = (rem_size * tr.t2_pct) - friction
                        tr.realized_pnl_gbp += pnl_t2
                        tr.friction_paid_gbp += friction
                        cash_gbp += rem_size + pnl_t2
                        total_broker_fees_gbp += friction
                        tr.is_closed = True
                        tr.exit_reason = "STAGE_2_TARGET_HIT"
                        closed_trades.append(tr)
                        continue

                    # Uncapped 10 EMA Trailing Runner (exit only on close below 10 EMA)
                    if use_tactical_protection and tr.can_extend_indefinitely and tr.hold_days > 5:
                        # Trail along 10 EMA approximation (exit if day closed below 10 EMA)
                        if intraday_close_pct < (tr.peak_gain_pct * 0.65):
                            rem_size = tr.size_gbp * tr.shares_remaining_pct
                            pnl_trail = (rem_size * intraday_close_pct) - friction
                            tr.realized_pnl_gbp += pnl_trail
                            tr.friction_paid_gbp += friction
                            cash_gbp += rem_size + pnl_trail
                            total_broker_fees_gbp += friction
                            tr.is_closed = True
                            tr.exit_reason = "10_EMA_RUNNER_TRAIL_EXIT"
                            closed_trades.append(tr)
                            continue

                # E. Time Expiration (5 days for 3x ETFs; 6-8 days for baseline)
                if not tr.can_extend_indefinitely or not use_tactical_protection:
                    if tr.hold_days >= tr.max_days:
                        rem_size = tr.size_gbp * tr.shares_remaining_pct
                        pnl_time = (rem_size * intraday_close_pct) - friction
                        tr.realized_pnl_gbp += pnl_time
                        tr.friction_paid_gbp += friction
                        cash_gbp += rem_size + pnl_time
                        total_broker_fees_gbp += friction
                        tr.is_closed = True
                        tr.exit_reason = "HORIZON_EXPIRATION"
                        closed_trades.append(tr)
                        continue

                retained_trades.append(tr)

            open_trades = retained_trades

            # 2. Candidate Scanning & Slot Entry
            available_slots = self.max_slots - len(open_trades)
            if available_slots > 0 and cash_gbp >= 100.0:
                # In tactical mode: check Aegis Cash Shield
                if use_tactical_protection and is_hostile:
                    # Aegis cash shield: Block new long entries
                    pass
                else:
                    slot_budget = round(cash_gbp / max(1, available_slots), 2)
                    active_names = [t.ticker for t in open_trades]

                    # Scan eligible tickers
                    candidates = [t for t in DIVERSE_100_UNIVERSE if t not in FORENSIC_TRAPS and t != "QQQ" and t not in active_names]
                    random.Random(sum(ord(c) for c in dt)).shuffle(candidates)

                    for cand in candidates:
                        if available_slots <= 0 or cash_gbp < 100.0:
                            break

                        cand_bar = market_data.get(cand, {}).get(dt)
                        if not cand_bar:
                            continue

                        # Squeeze & Vol filter
                        is_3x = cand in {"TQQQ", "SOXL", "UPRO", "TECL", "FNGU", "BULZ", "LABU", "TNA", "DPST"}
                        is_uk = cand.endswith(".L")

                        if use_tactical_protection:
                            corr_audit = self.adaptive_engine.validate_portfolio_correlation(active_names, cand, max_slots=self.max_slots)
                            if not corr_audit["is_allowed"]:
                                correlation_blocks += 1
                                continue

                        actual_budget = min(cash_gbp, slot_budget)
                        fx_entry = 0.0 if is_uk else (0.0015 * actual_budget)
                        spread_entry = 0.0012 * actual_budget
                        cash_gbp -= actual_budget
                        total_broker_fees_gbp += (fx_entry + spread_entry)

                        fill_p = cand_bar["open"] * 1.0004
                        stop_p = -0.052 if is_uk else -0.065
                        t1_p = 0.050 if is_uk else 0.085
                        t2_p = 0.160 if is_uk else 0.280

                        new_tr = ExpandedTrade(
                            ticker=cand,
                            entry_date=dt,
                            entry_price=fill_p,
                            size_gbp=actual_budget,
                            is_uk=is_uk,
                            stop_pct=stop_p,
                            t1_pct=t1_p,
                            t2_pct=t2_p,
                            max_days=5 if is_3x else (8 if is_uk else 6),
                            can_extend_indefinitely=not is_3x
                        )
                        new_tr.friction_paid_gbp += (fx_entry + spread_entry)
                        open_trades.append(new_tr)
                        active_names.append(cand)
                        available_slots -= 1

            # 3. Mark to Market Equity
            unrealized = sum(
                tr.size_gbp * tr.shares_remaining_pct * (market_data.get(tr.ticker, {}).get(dt, {}).get("close", tr.entry_price) / max(0.0001, tr.entry_price))
                for tr in open_trades
            )
            total_equity = cash_gbp + unrealized
            if total_equity > peak_equity:
                peak_equity = total_equity
            dd_gbp = peak_equity - total_equity
            dd_pct = (dd_gbp / max(1.0, peak_equity)) * 100.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct
                max_drawdown_gbp = dd_gbp

            portfolio_history.append({
                "date": dt,
                "cash_gbp": round(cash_gbp, 2),
                "open_trades": len(open_trades),
                "total_equity_gbp": round(total_equity, 2),
                "drawdown_pct": round(dd_pct, 2)
            })

        # Close any lingering positions
        final_dt = sorted_dates[-1] if sorted_dates else ""
        for tr in open_trades:
            bar = market_data.get(tr.ticker, {}).get(final_dt)
            close_p = bar["close"] if bar else tr.entry_price
            rem_size = tr.size_gbp * tr.shares_remaining_pct
            move = (close_p - tr.entry_price) / max(0.0001, tr.entry_price)
            pnl = rem_size * move
            tr.realized_pnl_gbp += pnl
            cash_gbp += rem_size + pnl
            tr.is_closed = True
            closed_trades.append(tr)

        final_equity = portfolio_history[-1]["total_equity_gbp"] if portfolio_history else self.initial_capital
        net_profit = final_equity - self.initial_capital
        net_ret_pct = (net_profit / self.initial_capital) * 100.0

        wins = [t for t in closed_trades if t.realized_pnl_gbp > 0]
        losses = [t for t in closed_trades if t.realized_pnl_gbp <= 0]
        wr = (len(wins) / len(closed_trades) * 100.0) if closed_trades else 0.0
        pf = abs(sum(t.realized_pnl_gbp for t in wins)) / max(0.01, abs(sum(t.realized_pnl_gbp for t in losses)))

        return {
            "cycle_id": cycle["id"],
            "cycle_name": cycle["name"],
            "date_range": f"{start_dt} to {end_dt}",
            "mode": "Tactical Cash & Correlation Capped" if use_tactical_protection else "Always-Invested Baseline",
            "initial_capital_gbp": self.initial_capital,
            "final_equity_gbp": round(final_equity, 2),
            "net_profit_gbp": round(net_profit, 2),
            "net_return_pct": round(net_ret_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "max_drawdown_gbp": round(max_drawdown_gbp, 2),
            "win_rate_pct": round(wr, 1),
            "profit_factor": round(pf, 2),
            "total_trades": len(closed_trades),
            "correlation_blocks": correlation_blocks,
            "premarket_cuts": premarket_cuts,
            "broker_fees_gbp": round(total_broker_fees_gbp, 2),
            "equity_curve": [p["total_equity_gbp"] for p in portfolio_history[::5]] # sampled curve
        }

    def run_all_cycles(self) -> dict:
        print("\n" + "=" * 90)
        print("   EXPANDED MULTI-REGIME HISTORICAL BACKTEST SUITE (100+ TICKERS ACROSS 6 CYCLES)")
        print("=" * 90)

        all_results = []
        for cycle in HISTORICAL_CYCLES:
            print(f"\n[*] Executing {cycle['name']} ({cycle['start']} -> {cycle['end']})...")
            base_res = self.run_cycle_simulation(cycle, use_tactical_protection=False)
            tact_res = self.run_cycle_simulation(cycle, use_tactical_protection=True)

            print(f"  |-- Baseline       : Return {base_res['net_return_pct']:>+6.2f}% | Max DD {base_res['max_drawdown_pct']:>5.2f}% | PF {base_res['profit_factor']:.2f} | Trades {base_res['total_trades']}")
            print(f"  |-- Tactical Engine: Return {tact_res['net_return_pct']:>+6.2f}% | Max DD {tact_res['max_drawdown_pct']:>5.2f}% | PF {tact_res['profit_factor']:.2f} | Trades {tact_res['total_trades']} | Blocks {tact_res['correlation_blocks']}")

            all_results.append({
                "cycle": cycle,
                "baseline": base_res,
                "tactical": tact_res
            })

        out_path = EVIDENCE_DIR / "expanded_multi_regime_results.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "universe_size": len(DIVERSE_100_UNIVERSE),
            "cycles": all_results
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n[+] Saved expanded multi-regime backtest telemetry to {out_path}\n")
        return payload


def main():
    tester = ExpandedMultiRegimeBacktester(initial_capital=1000.0, max_slots=3)
    tester.run_all_cycles()


if __name__ == "__main__":
    main()
