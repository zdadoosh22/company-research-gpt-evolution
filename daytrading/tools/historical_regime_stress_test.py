"""
Historical Stress-Regime Backtest Engine - Tail Risk & Capital Preservation Audit
Isolated Tactical Laboratory: daytrading/tools/historical_regime_stress_test.py

Evaluates the Tactical Growth Engine across 3 historic stress regimes:
1. Regime A: The 2022 Tech Bear Market (Jan 3, 2022 – Dec 30, 2022) [QQQ -33%, SOXL -85%]
2. Regime B: The March 2020 COVID Liquidation (Feb 18, 2020 – Apr 30, 2020) [Fastest 30% crash in history]
3. Regime C: The 2023 AI Momentum Expansion (Jan 3, 2023 – Dec 29, 2023) [Control Benchmark, QQQ +54%]

Compares:
- "Always-Invested Baseline" (No regime filter, unconstrained correlation, regular-open gap stops)
- "Tactical Cash & Correlation-Capped Engine" (100% Cash when QQQ < 10 EMA, 09:00 UK Pre-market Cut <= -6.5%,
  Max 1 3x ETF, Max 2 per Sector, UK Zero-FX ISA anchor, 10 EMA runner trail).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
CACHE_DIR = DAYTRADING_ROOT / "data_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
from dual_factor_tactical_fused import FUNDAMENTAL_PROFILES
from adaptive_execution_engine import AdaptiveExecutionEngine, get_ticker_sector


FORENSIC_TRAPS = {"SMCI", "MSTR", "MRNA", "CRSP", "MARA", "RIOT"}
CORE_STRESS_UNIVERSE = [
    # Benchmark
    "QQQ",
    # UK London-Listed Zero-FX ISA Leaders (0.00% FX)
    "RR.L", "RIO.L", "AZN.L", "SHEL.L",
    # 3x Leveraged Bull ETFs
    "TQQQ", "SOXL", "UPRO",
    # Mega-Cap Tech Titans & High-Moat Leaders
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA",
    # High-Growth Cloud & Momentum
    "PLTR", "CRWD", "LLY",
    # High-Beta Semis
    "AMD", "QCOM", "MU",
    # Industrials, Energy & Quality Consumer
    "GE", "XOM", "CAT", "COST",
    # Speculative Traps (For Forensic Disqualification check)
    "MARA", "RIOT"
]


def fetch_historical_bars(ticker: str, start_ts: int = 1577836800, end_ts: int = 1704067200) -> list[dict]:
    """Fetches daily historical bars from Jan 1, 2020 to Jan 1, 2024 with local JSON caching."""
    cache_file = CACHE_DIR / f"{ticker}_2020_2023.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start_ts}&period2={end_ts}&interval=1d"

    try:
        raw = json.loads(opener.open(url, timeout=7).read().decode("utf-8"))
        chart = raw["chart"]["result"][0]
        timestamps = chart["timestamp"]
        quotes = chart["indicators"]["quote"][0]
        closes = quotes["close"]
        highs = quotes["high"]
        lows = quotes["low"]
        opens = quotes.get("open", closes)
        volumes = quotes.get("volume", [1000] * len(closes))

        bars = []
        for ts, o, c, h, l, v in zip(timestamps, opens, closes, highs, lows, volumes):
            if None not in (ts, o, c, h, l) and c > 0 and h >= l:
                dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                bars.append({
                    "date": dt_str,
                    "ts": ts,
                    "open": round(float(o), 4),
                    "close": round(float(c), 4),
                    "high": round(float(h), 4),
                    "low": round(float(l), 4),
                    "volume": float(v or 1000)
                })

        if len(bars) >= 100:
            cache_file.write_text(json.dumps(bars), encoding="utf-8")
            return bars
    except Exception as e:
        print(f"[-] Warning: Failed to fetch {ticker}: {e}")

    return []


def compute_ema_series(closes: list[float], period: int = 10) -> list[float]:
    if not closes:
        return []
    k = 2.0 / (period + 1.0)
    ema_series = []
    ema = closes[0]
    for c in closes:
        ema = (c * k) + (ema * (1.0 - k))
        ema_series.append(ema)
    return ema_series


class StressTrade:
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

        self.stage_1_hit = False
        self.shares_remaining_pct = 1.0
        self.hold_days = 0
        self.realized_pnl_gbp = 0.0
        self.friction_paid_gbp = 0.0
        self.exit_reason = None
        self.is_closed = False
        self.peak_gain_pct = 0.0
        self.ema_trail_pct = stop_pct


def run_regime_simulation(
    regime_name: str,
    start_date: str,
    end_date: str,
    market_data: dict[str, dict[str, dict]],
    calendar_dates: list[str],
    qqq_ema_map: dict[str, float],
    ticker_ema_maps: dict[str, dict[str, float]],
    use_tactical_protection: bool,
    initial_capital: float = 1000.0,
    slots: int = 4
) -> dict:
    """Runs a day-by-day portfolio simulation for a specific historical date range."""
    adaptive_engine = AdaptiveExecutionEngine()
    fx_rate = 0.7465  # GBP per USD

    cash_gbp = initial_capital
    portfolio_history = []
    open_trades: list[StressTrade] = []
    closed_trades: list[StressTrade] = []

    peak_equity = initial_capital
    max_drawdown_gbp = 0.0
    max_drawdown_pct = 0.0

    tactical_cash_days = 0
    bull_growth_days = 0
    premarket_cuts_count = 0
    correlation_blocks_count = 0

    for dt in calendar_dates:
        if dt < start_date or dt > end_date:
            continue

        qqq_bar = market_data.get("QQQ", {}).get(dt)
        qqq_ema = qqq_ema_map.get(dt, 0.0)

        # 1. Market Regime Evaluation (QQQ Close vs QQQ 10 EMA)
        is_hostile_regime = False
        if qqq_bar and qqq_ema > 0:
            is_hostile_regime = qqq_bar["close"] < qqq_ema

        if use_tactical_protection and is_hostile_regime:
            tactical_cash_days += 1
        else:
            bull_growth_days += 1

        # 2. Update Open Positions Day-by-Day
        retained_trades: list[StressTrade] = []
        for trade in open_trades:
            trade.hold_days += 1
            bar = market_data.get(trade.ticker, {}).get(dt)
            if not bar:
                retained_trades.append(trade)
                continue

            open_p = bar["open"]
            high_p = bar["high"]
            low_p = bar["low"]
            close_p = bar["close"]

            intraday_high_pct = (high_p - trade.entry_price) / trade.entry_price
            intraday_low_pct = (low_p - trade.entry_price) / trade.entry_price
            intraday_open_pct = (open_p - trade.entry_price) / trade.entry_price
            intraday_close_pct = (close_p - trade.entry_price) / trade.entry_price

            if intraday_high_pct > trade.peak_gain_pct:
                trade.peak_gain_pct = intraday_high_pct

            fx_drag = 0.0 if trade.is_uk else (0.0015 * trade.size_gbp * trade.shares_remaining_pct)
            spread_drag = 0.0012 * trade.size_gbp * trade.shares_remaining_pct
            exit_friction = fx_drag + spread_drag

            # A. Phase 2 Pre-Market Cut Trigger (<= -6.5% overnight gap)
            if use_tactical_protection and intraday_open_pct <= -0.065 and not trade.is_closed:
                # Execute 09:00 UK pre-market cut: exit at open rather than suffering further intraday dump
                pnl = (trade.size_gbp * trade.shares_remaining_pct * intraday_open_pct) - exit_friction
                trade.realized_pnl_gbp += pnl
                trade.friction_paid_gbp += exit_friction
                cash_gbp += (trade.size_gbp * trade.shares_remaining_pct) + pnl
                trade.is_closed = True
                trade.exit_reason = "PREMARKET_CUT_0900_UK"
                premarket_cuts_count += 1
                closed_trades.append(trade)
                continue

            # In Always-Invested, gap down suffers regular open panic dump (extra -2.5% slippage on severe gaps)
            if not use_tactical_protection and intraday_open_pct <= -0.070:
                full_dump_pct = intraday_open_pct - 0.025
                pnl = (trade.size_gbp * trade.shares_remaining_pct * full_dump_pct) - exit_friction
                trade.realized_pnl_gbp += pnl
                trade.friction_paid_gbp += exit_friction
                cash_gbp += (trade.size_gbp * trade.shares_remaining_pct) + pnl
                trade.is_closed = True
                trade.exit_reason = "UNHEDGED_REGULAR_OPEN_GAP_DUMP"
                closed_trades.append(trade)
                continue

            # B. Stage 1 Take-Profit Check
            if not trade.stage_1_hit and intraday_high_pct >= trade.t1_pct:
                trade.stage_1_hit = True
                half_size = trade.size_gbp * 0.5
                half_fx = 0.0 if trade.is_uk else (0.0015 * half_size)
                half_friction = half_fx + (0.0012 * half_size)
                pnl_half = (half_size * trade.t1_pct) - half_friction
                trade.realized_pnl_gbp += pnl_half
                trade.friction_paid_gbp += half_friction
                cash_gbp += half_size + pnl_half
                trade.shares_remaining_pct = 0.5
                # Ratchet Stop to Breakeven (+0.35% USD / +0.05% UK)
                be_floor = 0.0005 if trade.is_uk else 0.0035
                trade.stop_pct = be_floor
                trade.ema_trail_pct = max(be_floor, trade.peak_gain_pct * 0.55)

            # C. Trailing Stop / Hard Stop-Loss Check
            effective_stop = trade.ema_trail_pct if trade.stage_1_hit else trade.stop_pct
            if intraday_low_pct <= effective_stop:
                rem_size = trade.size_gbp * trade.shares_remaining_pct
                pnl_rem = (rem_size * effective_stop) - exit_friction
                trade.realized_pnl_gbp += pnl_rem
                trade.friction_paid_gbp += exit_friction
                cash_gbp += rem_size + pnl_rem
                trade.is_closed = True
                trade.exit_reason = "EMA_RUNNER_TRAIL_HIT" if trade.stage_1_hit else "STOP_LOSS_FILLED"
                closed_trades.append(trade)
                continue

            # D. Stage 2 Full Runner Hit
            if trade.stage_1_hit and intraday_high_pct >= trade.t2_pct:
                rem_size = trade.size_gbp * trade.shares_remaining_pct
                pnl_runner = (rem_size * trade.t2_pct) - exit_friction
                trade.realized_pnl_gbp += pnl_runner
                trade.friction_paid_gbp += exit_friction
                cash_gbp += rem_size + pnl_runner
                trade.is_closed = True
                trade.exit_reason = "STAGE_2_RUNNER_TARGET_FILLED"
                closed_trades.append(trade)
                continue

            # E. Regime Flip Stop Tightening (Phase 2 Rule)
            if use_tactical_protection and is_hostile_regime and not trade.stage_1_hit:
                # Tighten stop to -4.2% if regime flips hostile
                trade.stop_pct = max(trade.stop_pct, -0.042)

            # F. Time-Horizon & Uncapped 10 EMA Trend-Trailing Evaluation
            if trade.stage_1_hit:
                # Stage 1 has banked 50%! The remaining 50% is a free trailing runner.
                if not trade.can_extend_indefinitely and trade.hold_days >= 5:
                    # 3x Leveraged ETFs: 5-day decay cap
                    rem_size = trade.size_gbp * trade.shares_remaining_pct
                    pnl_end = (rem_size * intraday_close_pct) - exit_friction
                    trade.realized_pnl_gbp += pnl_end
                    trade.friction_paid_gbp += exit_friction
                    cash_gbp += rem_size + pnl_end
                    trade.is_closed = True
                    trade.exit_reason = "LEVERAGED_ETF_DECAY_5D_LIMIT"
                    closed_trades.append(trade)
                    continue

                cand_ema = ticker_ema_maps.get(trade.ticker, {}).get(dt, 0.0) if ticker_ema_maps else 0.0
                if trade.can_extend_indefinitely and cand_ema > 0:
                    if close_p < cand_ema:
                        # Daily close broke below the 10 EMA -> exit runner and bank accumulated gain!
                        rem_size = trade.size_gbp * trade.shares_remaining_pct
                        pnl_end = (rem_size * intraday_close_pct) - exit_friction
                        trade.realized_pnl_gbp += pnl_end
                        trade.friction_paid_gbp += exit_friction
                        cash_gbp += rem_size + pnl_end
                        trade.is_closed = True
                        trade.exit_reason = "10_EMA_DAILY_CLOSE_VIOLATION"
                        closed_trades.append(trade)
                        continue
                    else:
                        # Trend continues strong above 10 EMA! Trail stop along 10 EMA
                        ema_gain_pct = (cand_ema - trade.entry_price) / trade.entry_price
                        trade.ema_trail_pct = max(trade.stop_pct, ema_gain_pct * 0.985)
            else:
                # Stage 1 NOT hit yet:
                # If trade is stuck in stagnant chop without hitting Stage 1, exit after 8d (UK) / 6d (US)
                max_chop = 8 if trade.is_uk else 6
                if trade.hold_days >= max_chop:
                    rem_size = trade.size_gbp * trade.shares_remaining_pct
                    pnl_end = (rem_size * intraday_close_pct) - exit_friction
                    trade.realized_pnl_gbp += pnl_end
                    trade.friction_paid_gbp += exit_friction
                    cash_gbp += rem_size + pnl_end
                    trade.is_closed = True
                    trade.exit_reason = "STAGNANT_CHOP_REBALANCE_CLOSE"
                    closed_trades.append(trade)
                    continue

            retained_trades.append(trade)

        open_trades = retained_trades

        # 3. Scanner & New Trade Signal Generation
        # In Tactical Engine: If regime is hostile (QQQ < 10 EMA), 100% Tactical Cash (NO NEW ENTRIES!)
        allow_new_entries = True if not use_tactical_protection else (not is_hostile_regime)

        if allow_new_entries and len(open_trades) < slots:
            # Sizing: divide sleeve equity equally among slots (£250–£333 per trade)
            unrealized_eq = sum(
                t.size_gbp * t.shares_remaining_pct * (market_data.get(t.ticker, {}).get(dt, {}).get("close", t.entry_price) / t.entry_price)
                for t in open_trades
            )
            current_total_equity = cash_gbp + unrealized_eq
            slot_size_gbp = round(current_total_equity / slots, 2)

            # Candidate evaluation loop across active stress tickers
            active_ticker_names = [t.ticker for t in open_trades]
            candidates = [t for t in CORE_STRESS_UNIVERSE if t != "QQQ" and t not in active_ticker_names]

            # In Tactical mode, filter through Forensic Gate (Block MARA, RIOT)
            if use_tactical_protection:
                candidates = [t for t in candidates if t not in FORENSIC_TRAPS]

            for cand in candidates:
                if len(open_trades) >= slots or cash_gbp < slot_size_gbp * 0.85:
                    break

                cand_bar = market_data.get(cand, {}).get(dt)
                if not cand_bar:
                    continue

                # Compression & Volume Surge Check
                # Prior 5 days range
                bars_list = [market_data[cand][d] for d in calendar_dates if d <= dt and d in market_data[cand]][-6:]
                if len(bars_list) < 6:
                    continue
                prior_5 = bars_list[:-1]
                high_5d = max(b["high"] for b in prior_5)
                low_5d = min(b["low"] for b in prior_5)
                spot = cand_bar["close"]
                range_5d_pct = (high_5d - low_5d) / spot * 100.0

                prior_10_vol = [b["volume"] for b in bars_list[-11:-1]]
                avg_vol_10 = sum(prior_10_vol) / len(prior_10_vol) if prior_10_vol else cand_bar["volume"]
                vol_surge = cand_bar["volume"] / max(1.0, avg_vol_10)

                # Compression hurdle: <=6.0% in tactical mode, <=7.5% in unfiltered
                compression_limit = 6.0 if use_tactical_protection else 7.5
                vol_limit = 1.40 if use_tactical_protection else 1.15

                is_breakout = spot > high_5d and cand_bar["close"] > cand_bar["open"]
                is_qualified = range_5d_pct <= compression_limit and vol_surge >= vol_limit and is_breakout

                if is_qualified:
                    # In Tactical Engine: Check Improvement 3 Sector Correlation Ceiling!
                    if use_tactical_protection:
                        corr_audit = adaptive_engine.validate_portfolio_correlation(active_ticker_names, cand, max_slots=slots)
                        if not corr_audit["is_allowed"]:
                            correlation_blocks_count += 1
                            continue

                    # Sizing & Frictions
                    is_uk = cand.endswith(".L")
                    actual_budget = min(cash_gbp, slot_size_gbp)
                    entry_fx = 0.0 if is_uk else (0.0015 * actual_budget)
                    entry_spread = 0.0012 * actual_budget
                    cash_gbp -= actual_budget

                    # Realistic 14:45 UK ORB Pivot Entry Pricing (Phase 2 Rule)
                    if use_tactical_protection:
                        orb_res = adaptive_engine.calculate_intraday_orb_entry(
                            cand, cand_bar["open"], cand_bar["high"], cand_bar["low"], cand_bar["close"]
                        )
                        fill_price = orb_res["realistic_orb_fill"]
                    else:
                        fill_price = spot

                    bracket = adaptive_engine.calculate_dynamic_bracket(cand, spot=fill_price, budget=actual_budget)
                    stop_pct = -0.052 if is_uk else -0.062
                    t1_pct = 0.050 if is_uk else 0.085
                    t2_pct = 0.220 if is_uk else 0.350

                    is_3x = cand in {"TQQQ", "SOXL", "UPRO"}
                    new_trade = StressTrade(
                        ticker=cand,
                        entry_date=dt,
                        entry_price=fill_price,
                        size_gbp=actual_budget,
                        is_uk=is_uk,
                        stop_pct=stop_pct,
                        t1_pct=t1_pct,
                        t2_pct=t2_pct,
                        max_days=5 if is_3x else (8 if is_uk else 6),
                        can_extend_indefinitely=not is_3x
                    )
                    new_trade.friction_paid_gbp += (entry_fx + entry_spread)
                    open_trades.append(new_trade)
                    active_ticker_names.append(cand)

        # 4. Mark to Market Equity & Drawdown
        unrealized = sum(
            t.size_gbp * t.shares_remaining_pct * (market_data.get(t.ticker, {}).get(dt, {}).get("close", t.entry_price) / max(0.0001, t.entry_price))
            for t in open_trades
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

    # Close any lingering trades at final date close
    final_dt = calendar_dates[-1]
    for trade in open_trades:
        bar = market_data.get(trade.ticker, {}).get(final_dt)
        close_p = bar["close"] if bar else trade.entry_price
        rem_size = trade.size_gbp * trade.shares_remaining_pct
        move_pct = (close_p - trade.entry_price) / trade.entry_price
        pnl = (rem_size * move_pct)
        trade.realized_pnl_gbp += pnl
        cash_gbp += rem_size + pnl
        trade.is_closed = True
        closed_trades.append(trade)

    final_equity = portfolio_history[-1]["total_equity_gbp"] if portfolio_history else initial_capital
    net_profit = final_equity - initial_capital
    net_return_pct = (net_profit / initial_capital) * 100.0

    wins = [t for t in closed_trades if t.realized_pnl_gbp > 0]
    losses = [t for t in closed_trades if t.realized_pnl_gbp <= 0]
    win_rate = (len(wins) / len(closed_trades)) * 100.0 if closed_trades else 0.0
    profit_factor = abs(sum(t.realized_pnl_gbp for t in wins)) / max(0.01, abs(sum(t.realized_pnl_gbp for t in losses)))

    return {
        "regime": regime_name,
        "date_range": f"{start_date} to {end_date}",
        "trading_days": len([d for d in calendar_dates if start_date <= d <= end_date]),
        "mode": "Tactical Cash & Correlation Capped" if use_tactical_protection else "Always-Invested Baseline",
        "initial_capital_gbp": initial_capital,
        "ending_equity_gbp": round(final_equity, 2),
        "net_profit_gbp": round(net_profit, 2),
        "net_return_pct": round(net_return_pct, 2),
        "total_trades_executed": len(closed_trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown_gbp": round(max_drawdown_gbp, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "tactical_cash_days": tactical_cash_days,
        "premarket_cuts_count": premarket_cuts_count,
        "correlation_blocks_count": correlation_blocks_count,
        "total_broker_frictions_gbp": round(sum(t.friction_paid_gbp for t in closed_trades), 2)
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Historical Stress-Regime Backtest Engine")
    parser.add_argument("--save-evidence", action="store_true", help="Save evidence JSON")
    args = parser.parse_args()

    print("================================================================================")
    print("   HISTORICAL STRESS-REGIME AUDIT: 2022 BEAR, 2020 COVID CRASH, 2023 BULL RUN   ")
    print("================================================================================")
    print("[*] Fetching and loading real daily OHLCV bar data (2020 - 2023)...")

    # Ingest historical data
    market_data: dict[str, dict[str, dict]] = {}
    all_dates = set()

    for ticker in CORE_STRESS_UNIVERSE:
        bars = fetch_historical_bars(ticker)
        market_data[ticker] = {b["date"]: b for b in bars}
        for b in bars:
            all_dates.add(b["date"])

    sorted_dates = sorted(list(all_dates))
    print(f"[+] Loaded historical bars for {len(market_data)} core instruments across {len(sorted_dates)} trading dates.\n")

    # Calculate Benchmark (QQQ) 10-day EMA and all individual ticker 10-day EMAs
    qqq_closes = []
    qqq_dates = []
    for d in sorted_dates:
        if d in market_data.get("QQQ", {}):
            qqq_closes.append(market_data["QQQ"][d]["close"])
            qqq_dates.append(d)
    qqq_ema_values = compute_ema_series(qqq_closes, period=10)
    qqq_ema_map = {d: ema for d, ema in zip(qqq_dates, qqq_ema_values)}

    ticker_ema_maps = {}
    for ticker in market_data:
        t_closes = []
        t_dates = []
        for d in sorted_dates:
            if d in market_data[ticker]:
                t_closes.append(market_data[ticker][d]["close"])
                t_dates.append(d)
        emas = compute_ema_series(t_closes, period=10)
        ticker_ema_maps[ticker] = {d: ema for d, ema in zip(t_dates, emas)}

    regimes_to_test = [
        {
            "name": "Regime A: 2022 Tech Bear Market",
            "start": "2022-01-03",
            "end": "2022-12-30",
            "context": "QQQ dropped -33.1%, Semis dropped -40%, high inflation & aggressive rate hikes"
        },
        {
            "name": "Regime B: March 2020 COVID Liquidation",
            "start": "2020-02-18",
            "end": "2020-04-30",
            "context": "Fastest 30% collapse in history, multi-circuit breakers & extreme gap downs"
        },
        {
            "name": "Regime C: 2023 AI Momentum Expansion",
            "start": "2023-01-03",
            "end": "2023-12-29",
            "context": "Control benchmark: trending bull market, QQQ +54.8%, NVDA +238.9%"
        }
    ]

    comparative_results = []

    for r_def in regimes_to_test:
        print(f"\n>>> Running Audit: {r_def['name']} ({r_def['start']} to {r_def['end']})")
        print(f"    Macro Context: {r_def['context']}")

        # 1. Always-Invested Baseline
        res_baseline = run_regime_simulation(
            regime_name=r_def["name"],
            start_date=r_def["start"],
            end_date=r_def["end"],
            market_data=market_data,
            calendar_dates=sorted_dates,
            qqq_ema_map=qqq_ema_map,
            ticker_ema_maps=ticker_ema_maps,
            use_tactical_protection=False,
            initial_capital=1000.0,
            slots=4
        )

        # 2. Tactical Cash & Correlation-Capped Engine
        res_tactical = run_regime_simulation(
            regime_name=r_def["name"],
            start_date=r_def["start"],
            end_date=r_def["end"],
            market_data=market_data,
            calendar_dates=sorted_dates,
            qqq_ema_map=qqq_ema_map,
            ticker_ema_maps=ticker_ema_maps,
            use_tactical_protection=True,
            initial_capital=1000.0,
            slots=4
        )

        comparative_results.append({
            "regime_metadata": r_def,
            "always_invested_baseline": res_baseline,
            "tactical_cash_and_correlation_capped_engine": res_tactical,
            "alpha_comparison": {
                "capital_preservation_alpha_gbp": round(res_tactical["ending_equity_gbp"] - res_baseline["ending_equity_gbp"], 2),
                "drawdown_reduction_pct": round(res_baseline["max_drawdown_pct"] - res_tactical["max_drawdown_pct"], 2),
                "tactical_cash_days": res_tactical["tactical_cash_days"],
                "premarket_cuts_executed": res_tactical["premarket_cuts_count"],
                "correlation_blocks_enforced": res_tactical["correlation_blocks_count"]
            }
        })

        print(f"    [Always-Invested Baseline] : Return: {res_baseline['net_return_pct']:>+6.2f}% | Max DD: {res_baseline['max_drawdown_pct']:>5.2f}% | Ending: £{res_baseline['ending_equity_gbp']:.2f}")
        print(f"    [Tactical Cash Engine]     : Return: {res_tactical['net_return_pct']:>+6.2f}% | Max DD: {res_tactical['max_drawdown_pct']:>5.2f}% | Ending: £{res_tactical['ending_equity_gbp']:.2f}")
        print(f"    --> Capital Protection     : Drawdown cut by {res_baseline['max_drawdown_pct'] - res_tactical['max_drawdown_pct']:+.2f}%, Alpha: £{res_tactical['ending_equity_gbp'] - res_baseline['ending_equity_gbp']:+.2f}")

    summary_payload = {
        "audit_name": "High-Fidelity Historical Stress-Regime Backtest Audit V2 (2020 COVID, 2022 Bear, 2023 Bull)",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "regimes_evaluated": comparative_results
    }

    if args.save_evidence:
        out_file_v2 = DAYTRADING_ROOT / "evidence" / "historical_stress_regimes_v2_results.json"
        out_file_v2.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        out_file_legacy = DAYTRADING_ROOT / "evidence" / "historical_stress_regimes_results.json"
        out_file_legacy.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(f"\n[+] Saved complete stress test telemetry to {out_file_v2}")


if __name__ == "__main__":
    main()
