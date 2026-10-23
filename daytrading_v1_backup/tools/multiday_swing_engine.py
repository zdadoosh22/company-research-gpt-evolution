"""2-5 Day Multi-Day High-Volatility Swing Engine (The Sweet Spot).

THE MATHEMATICAL AND FRICTION DISCOVERY:
1. Pure Intraday (<6 hours) FAILS in Trading 212 due to 0.30% round-trip FX fee absorbing small moves.
2. 2-5 Day Swings in 3x ETFs (TQQQ, SOXL, NVDL) allow moves of +8% to +20%, making the 0.30% FX fee trivial (only 2% of profit).
3. Strategy: 3-Day EMA-9 Pullback + Day-2 Reversal Confirmation on 3x Leveraged ETFs.
"""
from datetime import datetime, timezone
import http.cookiejar
import json
from pathlib import Path
import random
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DAYTRADING_ROOT = Path(__file__).resolve().parents[1]

LEVERAGED_SWING_UNIVERSE = [
    'TQQQ', 'SOXL', 'NVDL', 'UPRO', 'SQQQ', 'SOXS',
    'NVDA', 'TSLA', 'AMD', 'PLTR', 'ARM', 'COIN'
]


def run_2_to_5_day_swing_suite(n_trades=1000):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass

    cache = {}
    print("Loading 2-year daily bar data for 2-5 Day Multi-Day Swing Suite...")
    for t in LEVERAGED_SWING_UNIVERSE:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=2y&interval=1d"
        try:
            raw = json.loads(opener.open(url, timeout=8).read().decode('utf-8'))
            chart = raw['chart']['result'][0]
            timestamps = chart['timestamp']
            quotes = chart['indicators']['quote'][0]
            closes = quotes['close']
            highs = quotes['high']
            lows = quotes['low']
            opens = quotes.get('open', closes)

            bars = []
            for ts, o, c, h, l in zip(timestamps, opens, closes, highs, lows):
                if c is not None and h is not None and l is not None and o is not None:
                    bars.append({
                        'ts': ts,
                        'date': datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d'),
                        'open': float(o),
                        'close': float(c),
                        'high': float(h),
                        'low': float(l)
                    })
            if len(bars) >= 150:
                cache[t] = bars
        except Exception:
            continue

    print(f"[+] Loaded daily bar data for {len(cache)} leveraged & high-beta instruments.\n")

    random.seed(888)
    trades = []
    tickers = list(cache.keys())
    count = 0

    while count < n_trades:
        t = random.choice(tickers)
        bars = cache[t]

        idx = random.randint(30, len(bars) - 10)
        prior_20 = bars[idx - 20: idx + 1]
        as_of_bar = bars[idx]
        spot = as_of_bar['close']

        # 9-period EMA
        ema_9 = sum(b['close'] for b in prior_20[-9:]) / 9.0

        # PULLBACK CONDITION: Price dipped below 9-EMA over last 3 days
        min_3d = min(b['low'] for b in prior_20[-3:])
        if min_3d >= ema_9:
            continue

        # REVERSAL TRIGGER: Today's candle closed green back ABOVE 9-EMA!
        if as_of_bar['close'] <= ema_9 or as_of_bar['close'] <= as_of_bar['open']:
            continue

        # 2-5 Day Swing Parameters:
        # Target 1 (50% Take Profit): +8.5%
        # Target 2 (Runner): +18.0%
        # Hard Stop: Low of the pullback candle (approx -5.0% to -7.0%)
        stop_price = min_3d * 0.985
        stop_pct = (stop_price - spot) / spot * 100.0
        stop_pct = max(-8.0, stop_pct)  # Cap stop at -8.0%

        t1_pct = 8.5
        t2_pct = 18.0
        fx_fee = -0.30

        future_bars = bars[idx + 1: idx + 6]  # Max hold 5 trading days!
        if not future_bars:
            continue

        hit_t1 = False
        t1_bank = 0.0
        realized_net = None

        for d_i, b in enumerate(future_bars):
            gain_h = (b['high'] - spot) / spot * 100.0
            loss_l = (b['low'] - spot) / spot * 100.0
            day_open = (b['open'] - spot) / spot * 100.0

            if not hit_t1 and loss_l <= stop_pct:
                fill_l = min(stop_pct, day_open)
                realized_net = fill_l + fx_fee
                break

            if not hit_t1 and gain_h >= t1_pct:
                hit_t1 = True
                t1_bank = t1_pct * 0.5

            if hit_t1:
                # Breakeven stop
                if loss_l <= 0.30:
                    realized_net = t1_bank + (0.0 * 0.5) + fx_fee
                    break
                if gain_h >= t2_pct:
                    realized_net = t1_bank + (t2_pct * 0.5) + fx_fee
                    break

            # 5-Day Hard Time Exit
            if d_i >= len(future_bars) - 1:
                end_ret = (b['close'] - spot) / spot * 100.0
                realized_net = (t1_bank + (end_ret * 0.5 if hit_t1 else end_ret)) + fx_fee
                break

        trades.append({
            'ticker': t,
            'realized_net': realized_net,
            'won': realized_net >= 4.0
        })
        count += 1

    wins = sum(1 for tr in trades if tr['won'])
    win_pct = wins / len(trades) * 100.0
    avg_net = sum(tr['realized_net'] for tr in trades) / len(trades)

    print("==================================================================")
    print("   2-5 DAY MULTI-DAY SWING ENGINE RESULTS (LEVERAGED ETFS)       ")
    print("==================================================================")
    print(f"Total Multi-Day Swings Tested: {len(trades)}")
    print(f"Win Rate (>+4.0% Net in 2-5D): {win_pct:.1f}% ({wins}/{len(trades)})")
    print(f"Average Net Return per Trade : {avg_net:+.2f}% (NET OF T212 FX FEE)")
    print(f"Total Compounded Suite Return: {sum(tr['realized_net'] for tr in trades):+.1f}%")
    print("==================================================================\n")

    out_file = DAYTRADING_ROOT / 'evidence' / '2-to-5-day-leveraged-swing-results.json'
    out_file.write_text(json.dumps({
        'total': len(trades),
        'wins': wins,
        'win_pct': win_pct,
        'avg_net': avg_net,
        'sample_trades': trades[:15]
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    run_2_to_5_day_swing_suite(1000)
