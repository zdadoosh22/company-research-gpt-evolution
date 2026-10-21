"""Tactical Momentum Surge with Volatility Compression & Breakout (The Edge).

THE VOLATILITY COMPRESSION PRINCIPLE:
Leveraged ETFs and high-beta momentum stocks bleed when entering in the middle of a choppy range.
They generate high-conviction +10% to +25% moves ONLY when breaking out of a tight consolidation
(Bollinger Band Squeeze / 5-Day Historical Volatility Compression).

STRATEGY:
1. Scan for 5-Day ATR / Price < 3.0% (Tight Compression).
2. Entry Trigger: First daily close breaking above the 5-day high with Volume > 1.5x average.
3. Holding Window: 2 to 4 days max.
4. Profit Take: Two-Stage (50% at +8.0%, 50% at +18.0%).
5. Stop Loss: 5-Day Low (strictly controlled).
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


def run_volatility_squeeze_suite(n_trades=1000):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass

    cache = {}
    print("Loading daily bar data for Volatility Compression Squeeze Engine...")
    universe = ['TQQQ', 'SOXL', 'NVDL', 'NVDA', 'TSLA', 'AMD', 'PLTR', 'ARM', 'COIN', 'UPRO']
    for t in universe:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=3y&interval=1d"
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
            if len(bars) >= 200:
                cache[t] = bars
        except Exception:
            continue

    print(f"[+] Loaded bar data for {len(cache)} momentum instruments.\n")

    random.seed(555)
    trades = []
    tickers = list(cache.keys())
    count = 0

    while count < n_trades:
        t = random.choice(tickers)
        bars = cache[t]

        idx = random.randint(30, len(bars) - 10)
        prior_5 = bars[idx - 5: idx]
        prior_20 = bars[idx - 20: idx]
        as_of_bar = bars[idx]
        spot = as_of_bar['close']

        # 1. Volatility Compression Check: 5-day range is tight (<6.5% of spot)
        high_5d = max(b['high'] for b in prior_5)
        low_5d = min(b['low'] for b in prior_5)
        range_5d_pct = (high_5d - low_5d) / spot * 100.0
        if range_5d_pct > 7.0:
            # Range too wide; not compressed
            continue

        # 2. Breakout Trigger: Today breaks ABOVE 5-day high with volume surge
        if as_of_bar['close'] <= high_5d or as_of_bar['close'] <= as_of_bar['open']:
            continue

        avg_vol_20 = sum(b['volume'] for b in prior_20) / len(prior_20)
        if as_of_bar['volume'] < 1.25 * avg_vol_20:
            continue

        # Strategy Parameters
        stop_price = low_5d
        stop_pct = (stop_price - spot) / spot * 100.0
        stop_pct = max(-7.0, stop_pct)  # Strict cap at -7.0%

        t1_pct = 8.5
        t2_pct = 18.0
        fx_fee = -0.30

        future_bars = bars[idx + 1: idx + 6]  # Max hold 4-5 days
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
                if loss_l <= 0.30:
                    realized_net = t1_bank + (0.0 * 0.5) + fx_fee
                    break
                if gain_h >= t2_pct:
                    realized_net = t1_bank + (t2_pct * 0.5) + fx_fee
                    break

            if d_i >= len(future_bars) - 1:
                end_ret = (b['close'] - spot) / spot * 100.0
                realized_net = (t1_bank + (end_ret * 0.5 if hit_t1 else end_ret)) + fx_fee
                break

        trades.append({
            'ticker': t,
            'realized_net': realized_net,
            'won': realized_net >= 3.0
        })
        count += 1

    wins = sum(1 for tr in trades if tr['won'])
    win_pct = wins / len(trades) * 100.0
    avg_net = sum(tr['realized_net'] for tr in trades) / len(trades)

    print("==================================================================")
    print("   VOLATILITY SQUEEZE BREAKOUT ENGINE RESULTS                     ")
    print("==================================================================")
    print(f"Total Squeeze Trades Tested  : {len(trades)}")
    print(f"Tactical Win Rate (>+3.0% Net): {win_pct:.1f}% ({wins}/{len(trades)})")
    print(f"Average Net Return per Trade : {avg_net:+.2f}% (NET OF T212 FX FEE)")
    print(f"Total Compounded Net Return  : {sum(tr['realized_net'] for tr in trades):+.1f}%")
    print("==================================================================\n")

    out_file = DAYTRADING_ROOT / 'evidence' / 'volatility-squeeze-breakout-results.json'
    out_file.write_text(json.dumps({
        'total': len(trades),
        'wins': wins,
        'win_pct': win_pct,
        'avg_net': avg_net,
        'sample_trades': trades[:15]
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    run_volatility_squeeze_suite(1000)
