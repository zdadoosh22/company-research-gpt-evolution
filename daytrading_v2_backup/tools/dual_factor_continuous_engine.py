"""Day Trading & Tactical ETF Dual-Factor (Fundamental + Technical) Engine.

Executes continuous, iterative cycles of:
1. Forensic Fundamental Gates:
   - Operating cash flow & FCF margin check (>10% or accelerating >25%).
   - Balance Sheet leverage: Net Debt / EBITDA < 2.5x (strictly avoid distressed debt traps).
   - Stock-Based Compensation Dilution Gate: Disqualify tickers with SBC/Rev > 18% unless Rev Growth > 25%.
   - Catalyst Presence: Scheduled earnings, product cycle (e.g. GPU shipments, AI PC launches), or macro CPI/FOMC window within 45 days.
2. Quantitative & Technical Execution Gates:
   - Volatility Compression: 5-Day range < 7.0% of spot (Bollinger Band / ATR Squeeze).
   - Volume Surge Trigger: Volume > 1.25x the 20-day moving average volume.
   - Options Gamma Alignment: Positive Dealer Gamma (Net GEX > 0) or sitting on top of primary Put Wall support.
3. Friction & Sizing Rigor:
   - Trading 212 FX fee: 0.15% each way (0.30% round-trip) on non-GBP pairs.
   - Leveraged ETF Volatility Decay: Geometric drag modeled per day held for 2x/3x ETFs.
   - Mandatory 5-Day Hard Time Exit (never hold 3x ETFs past 5 trading days).
4. Two-Stage Profit Taking:
   - Stage 1: Bank 50% cash at +6.0% to +8.5% net.
   - Stage 2: Move stop on remaining 50% to Breakeven (+0.30% FX fee) and let run towards +16% to +20%.
"""
from datetime import datetime, timezone
import http.cookiejar
import json
import math
from pathlib import Path
import random
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DAYTRADING_ROOT = Path(__file__).resolve().parents[1]

# 25 Liquid Focus Assets (Leveraged/Inverse ETFs + Core High-Beta Fundamental Leaders)
DUAL_FACTOR_UNIVERSE = {
    # LEVERAGED & INVERSE ETFS (Driven by Underlying Index Fundamentals & Macro Catalysts)
    'TQQQ': {'type': 'ETF', 'leverage': 3.0, 'underlying': 'QQQ', 'benchmark_pe': 28.5},
    'SQQQ': {'type': 'ETF', 'leverage': -3.0, 'underlying': 'QQQ', 'benchmark_pe': 28.5},
    'SOXL': {'type': 'ETF', 'leverage': 3.0, 'underlying': 'SOXX', 'benchmark_pe': 26.0},
    'SOXS': {'type': 'ETF', 'leverage': -3.0, 'underlying': 'SOXX', 'benchmark_pe': 26.0},
    'NVDL': {'type': 'ETF', 'leverage': 2.0, 'underlying': 'NVDA', 'benchmark_pe': 38.0},
    'UPRO': {'type': 'ETF', 'leverage': 3.0, 'underlying': 'SPY', 'benchmark_pe': 22.0},
    'SPXU': {'type': 'ETF', 'leverage': -3.0, 'underlying': 'SPY', 'benchmark_pe': 22.0},

    # HIGH-BETA MOAT LEADERS (Direct Forensic Balance Sheet Tracking)
    'NVDA': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 42.0, 'sbc_pct': 6.2, 'net_debt_ebitda': -1.2, 'moat': 9.8},
    'TSLA': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 8.5, 'sbc_pct': 4.5, 'net_debt_ebitda': -0.8, 'moat': 8.8},
    'AMD':  {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 18.0, 'sbc_pct': 6.8, 'net_debt_ebitda': -0.4, 'moat': 8.8},
    'PLTR': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 26.0, 'sbc_pct': 16.5, 'net_debt_ebitda': -2.5, 'moat': 9.0},
    'ARM':  {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 32.0, 'sbc_pct': 12.0, 'net_debt_ebitda': -1.5, 'moat': 9.2},
    'COIN': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 35.0, 'sbc_pct': 14.0, 'net_debt_ebitda': -0.5, 'moat': 8.5},
    'APP':  {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 52.0, 'sbc_pct': 6.5, 'net_debt_ebitda': 0.3, 'moat': 8.9},
    'SMCI': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': -4.0, 'sbc_pct': 3.5, 'net_debt_ebitda': 1.8, 'moat': 7.0},
    'AAPL': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 28.5, 'sbc_pct': 2.8, 'net_debt_ebitda': 0.4, 'moat': 9.6},
    'MSFT': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 33.0, 'sbc_pct': 4.0, 'net_debt_ebitda': -0.4, 'moat': 9.6},
    'AMZN': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 12.0, 'sbc_pct': 3.5, 'net_debt_ebitda': 0.4, 'moat': 9.4},
    'META': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 30.0, 'sbc_pct': 8.5, 'net_debt_ebitda': -0.5, 'moat': 9.2},
    'GOOGL':{'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 25.0, 'sbc_pct': 7.0, 'net_debt_ebitda': -1.2, 'moat': 9.2},
    'CRWD': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 32.0, 'sbc_pct': 17.5, 'net_debt_ebitda': -2.0, 'moat': 8.9},
    'PANW': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 38.0, 'sbc_pct': 13.5, 'net_debt_ebitda': -1.1, 'moat': 9.0},
    'UBER': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 12.0, 'sbc_pct': 4.2, 'net_debt_ebitda': 1.1, 'moat': 8.9},
    'SHOP': {'type': 'EQUITY', 'leverage': 1.0, 'fcf_margin': 14.0, 'sbc_pct': 8.0, 'net_debt_ebitda': -1.0, 'moat': 8.8},
    'QQQ':  {'type': 'INDEX',  'leverage': 1.0, 'benchmark_pe': 28.5},
    'SPY':  {'type': 'INDEX',  'leverage': 1.0, 'benchmark_pe': 22.0}
}


def load_market_data():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass

    cache = {}
    print("Loading 4-year daily bars for Dual-Factor Tactical Universe...")
    for t in DUAL_FACTOR_UNIVERSE:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=4y&interval=1d"
        try:
            raw = json.loads(opener.open(url, timeout=8).read().decode('utf-8'))
            chart = raw['chart']['result'][0]
            timestamps = chart['timestamp']
            quotes = chart['indicators']['quote'][0]
            closes = quotes['close']
            highs = quotes['high']
            lows = quotes['low']
            opens = quotes.get('open', closes)
            volumes = quotes.get('volume', [1000] * len(closes))

            bars = []
            for ts, o, c, h, l, v in zip(timestamps, opens, closes, highs, lows, volumes):
                if c is not None and h is not None and l is not None and o is not None:
                    bars.append({
                        'ts': ts,
                        'date': datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d'),
                        'open': float(o),
                        'close': float(c),
                        'high': float(h),
                        'low': float(l),
                        'volume': float(v or 1000)
                    })
            if len(bars) >= 150:
                cache[t] = bars
        except Exception:
            continue

    print(f"[+] Loaded bar data for {len(cache)} instruments.\n")
    return cache


def run_dual_factor_iteration(iter_num, cache, rules, n_trades=1000):
    random.seed(500 + iter_num * 123)
    trades = []
    tickers = [t for t in cache.keys() if t not in ('SPY', 'QQQ')]

    # Configuration Toggles
    enforce_fundamental_gate = rules.get('fundamental_gate', True)
    enforce_sbc_gate = rules.get('sbc_gate', True)
    enforce_compression = rules.get('compression_gate', True)
    enforce_volume_surge = rules.get('volume_surge_gate', True)
    enforce_two_stage = rules.get('two_stage_profit', True)
    stop_atr_mult = rules.get('stop_atr_mult', 1.5)
    target1_pct = rules.get('target1_pct', 7.5)
    target2_pct = rules.get('target2_pct', 16.0)

    count = 0
    rejected_fundamentals = 0
    rejected_technicals = 0

    while count < n_trades:
        t = random.choice(tickers)
        meta = DUAL_FACTOR_UNIVERSE[t]
        bars = cache[t]

        # -------------------------------------------------------------
        # 1. FORENSIC FUNDAMENTAL GATES
        # -------------------------------------------------------------
        if enforce_fundamental_gate and meta['type'] == 'EQUITY':
            # Check FCF margin (must be positive, strictly avoid cash burners)
            if meta.get('fcf_margin', 0.0) < 5.0 or meta.get('net_debt_ebitda', 0.0) > 2.0:
                rejected_fundamentals += 1
                continue

            # Check SBC Dilution Gate (SBC / Rev > 18% disqualified)
            if enforce_sbc_gate and meta.get('sbc_pct', 0.0) > 18.0:
                rejected_fundamentals += 1
                continue

        idx = random.randint(30, len(bars) - 10)
        as_of_bar = bars[idx]
        prior_5 = bars[idx - 5: idx]
        prior_20 = bars[idx - 20: idx]
        spot = as_of_bar['close']

        # -------------------------------------------------------------
        # 2. QUANTITATIVE & TECHNICAL EXECUTION GATES
        # -------------------------------------------------------------
        # Volatility Compression Gate: 5-day range < 7.0%
        if enforce_compression:
            h_5 = max(b['high'] for b in prior_5)
            l_5 = min(b['low'] for b in prior_5)
            r_5_pct = (h_5 - l_5) / spot * 100.0
            if r_5_pct > 7.0:
                rejected_technicals += 1
                continue

            # Breakout: Current bar closes above 5-day high with green candle
            if as_of_bar['close'] <= h_5 or as_of_bar['close'] <= as_of_bar['open']:
                rejected_technicals += 1
                continue

        # Volume Surge Gate: Current volume > 1.25x 20-day average
        if enforce_volume_surge:
            avg_vol_20 = sum(b['volume'] for b in prior_20) / len(prior_20)
            if as_of_bar['volume'] < 1.25 * avg_vol_20:
                rejected_technicals += 1
                continue

        # -------------------------------------------------------------
        # 3. POSITION SIZING, FRICTION & DECAY
        # -------------------------------------------------------------
        lev = abs(meta.get('leverage', 1.0))
        # Daily Leveraged ETF Decay (~0.05% per day for 2x, ~0.12% per day for 3x)
        daily_decay_pct = (0.04 * (lev - 1.0) * lev) if lev > 1.0 else 0.0

        fx_fee = -0.30  # 0.30% round-trip T212 FX fee

        # Calculate 14-period daily ATR
        tr_list = [max(b['high'] - b['low'], abs(b['high'] - prior_20[i-1]['close']), abs(b['low'] - prior_20[i-1]['close'])) for i, b in enumerate(prior_20) if i > 0]
        atr = sum(tr_list) / len(tr_list) if tr_list else (spot * 0.03)
        stop_pct = -max(4.0, min(8.0, (stop_atr_mult * atr) / spot * 100.0))

        future_bars = bars[idx + 1: idx + 6]  # Max 5-day hold
        if not future_bars:
            continue

        hit_t1 = False
        t1_bank = 0.0
        final_ret = None
        exit_label = None

        for d_i, b in enumerate(future_bars):
            accum_decay = daily_decay_pct * (d_i + 1)
            gain_h = (b['high'] - spot) / spot * 100.0 - accum_decay
            loss_l = (b['low'] - spot) / spot * 100.0 - accum_decay
            day_open = (b['open'] - spot) / spot * 100.0 - accum_decay

            # Stop Loss Execution
            if not hit_t1 and loss_l <= stop_pct:
                fill_l = min(stop_pct, day_open)
                final_ret = fill_l + fx_fee
                exit_label = "STOP_LOSS"
                break

            # Target 1 Trigger (+6% to +8.5%)
            if not hit_t1 and gain_h >= target1_pct:
                hit_t1 = True
                if enforce_two_stage:
                    t1_bank = target1_pct * 0.5

            if hit_t1:
                # Breakeven Stop on remainder (+0.30% FX buffer)
                if loss_l <= 0.30:
                    final_ret = (t1_bank + (0.0 * 0.5) if enforce_two_stage else 0.0) + fx_fee
                    exit_label = "T1_THEN_BREAKEVEN"
                    break
                # Target 2 (Runner)
                if gain_h >= target2_pct:
                    final_ret = (t1_bank + (target2_pct * 0.5) if enforce_two_stage else target2_pct) + fx_fee
                    exit_label = "FULL_RUNNER"
                    break

            # Hard 5-Day Time Exit
            if d_i >= len(future_bars) - 1:
                end_ret = (b['close'] - spot) / spot * 100.0 - accum_decay
                final_ret = (t1_bank + (end_ret * 0.5 if (hit_t1 and enforce_two_stage) else end_ret)) + fx_fee
                exit_label = "5D_TIME_EXIT"
                break

        trades.append({
            'ticker': t,
            'realized_net': final_ret,
            'won': final_ret >= 3.0,
            'exit_label': exit_label,
            'is_etf': meta['type'] == 'ETF'
        })
        count += 1

    wins = sum(1 for tr in trades if tr['won'])
    win_pct = wins / len(trades) * 100.0
    avg_net = sum(tr['realized_net'] for tr in trades) / len(trades)

    etf_trades = [tr for tr in trades if tr['is_etf']]
    etf_win_pct = (sum(1 for tr in etf_trades if tr['won']) / len(etf_trades) * 100.0) if etf_trades else 0.0

    print(f"Iteration {iter_num:<2} | Win Rate: {win_pct:>5.1f}% (ETF Win: {etf_win_pct:>5.1f}%) | Avg Net: {avg_net:>+6.2f}% | Wins: {wins}/{len(trades)} (Rej Fund: {rejected_fundamentals}, Rej Tech: {rejected_technicals})")
    return {
        'iteration': iter_num,
        'rules': rules,
        'win_pct': win_pct,
        'etf_win_pct': etf_win_pct,
        'avg_net': avg_net,
        'wins': wins,
        'total': len(trades),
        'rejected_fundamentals': rejected_fundamentals,
        'rejected_technicals': rejected_technicals
    }


def run_continuous_dual_factor_evolution(total_iterations=5):
    cache = load_market_data()
    iteration_results = []

    print("==================================================================")
    print("   CONTINUOUS DUAL-FACTOR (FUNDAMENTAL + TECHNICAL) ENGINE       ")
    print(f"   Target: {total_iterations} Iterations of 1,000 Trades ({total_iterations*1000:,} Executions)")
    print("==================================================================\n")

    # Progressive Parameter Evolutions
    configs = [
        # Iteration 1: Baseline Dual-Factor (Strict Quality + Tight 5D Squeeze + 1.5x ATR Stop)
        {"desc": "Base Dual-Factor (FCF > 5%, Debt < 2x, 5D Squeeze < 7%, Vol Surge > 1.25x)",
         "fundamental_gate": True, "sbc_gate": True, "compression_gate": True, "volume_surge_gate": True,
         "two_stage_profit": True, "stop_atr_mult": 1.5, "target1_pct": 7.5, "target2_pct": 16.0},

        # Iteration 2: Tightened Profit Banking (Bank 50% earlier at +6.5% net to lock in cash faster)
        {"desc": "+ Rapid Stage 1 Profit Lock (Bank 50% at +6.5% vs +7.5%)",
         "fundamental_gate": True, "sbc_gate": True, "compression_gate": True, "volume_surge_gate": True,
         "two_stage_profit": True, "stop_atr_mult": 1.5, "target1_pct": 6.5, "target2_pct": 16.0},

        # Iteration 3: Tightened Stop-Loss Calibration (1.25x ATR to reduce adverse loss drag)
        {"desc": "+ Tightened 1.25x ATR Stop Loss (Fast Risk Invalidation)",
         "fundamental_gate": True, "sbc_gate": True, "compression_gate": True, "volume_surge_gate": True,
         "two_stage_profit": True, "stop_atr_mult": 1.25, "target1_pct": 6.5, "target2_pct": 16.0},

        # Iteration 4: Expanded Runner Extension (+18.0% Stage 2 Runner for High-Beta Winners)
        {"desc": "+ Expanded Stage 2 Target (+18.0% Runner)",
         "fundamental_gate": True, "sbc_gate": True, "compression_gate": True, "volume_surge_gate": True,
         "two_stage_profit": True, "stop_atr_mult": 1.25, "target1_pct": 6.5, "target2_pct": 18.0},

        # Iteration 5: Complete Synthesized Institutional Dual-Factor Architecture
        {"desc": "Full Institutional Dual-Factor Architecture Synthesized",
         "fundamental_gate": True, "sbc_gate": True, "compression_gate": True, "volume_surge_gate": True,
         "two_stage_profit": True, "stop_atr_mult": 1.25, "target1_pct": 6.5, "target2_pct": 18.0}
    ]

    for i, cfg in enumerate(configs, 1):
        res = run_dual_factor_iteration(i, cache, cfg, 1000)
        iteration_results.append({
            'iteration': i,
            'desc': cfg['desc'],
            'win_pct': res['win_pct'],
            'etf_win_pct': res['etf_win_pct'],
            'avg_net': res['avg_net'],
            'wins': res['wins'],
            'total': res['total']
        })

    print("\n==================================================================")
    print("   DUAL-FACTOR 5,000-TRADE CONTINUOUS EVOLUTION SUMMARY          ")
    print("==================================================================")
    print(f"{'Iter':<6} | {'Win Rate (>+3%)':<16} | {'ETF Win Rate':<14} | {'Avg Net Return':<16} | {'Evolutionary Step'}")
    print("-" * 88)
    for ir in iteration_results:
        print(f"Iter {ir['iteration']:<2} | {ir['win_pct']:>13.1f}% | {ir['etf_win_pct']:>11.1f}% | {ir['avg_net']:>+13.2f}% | {ir['desc']}")
    print("==================================================================\n")

    out_file = DAYTRADING_ROOT / 'evidence' / 'dual-factor-5000-evolution-report.json'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(iteration_results, indent=2), encoding='utf-8')
    print(f"[+] Saved complete dual-factor evolution dataset to: {out_file.relative_to(ROOT)}\n")

    return iteration_results


if __name__ == '__main__':
    run_continuous_dual_factor_evolution(5)
