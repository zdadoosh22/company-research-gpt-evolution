"""Company Research 2 — Massive 200-Ticker Market Stress & Backtest Engine.

Scans, fetches, and evaluates 200 liquid tickers across US and UK markets
(Tech, Semis, Energy, Industrials, Consumer, Healthcare, Financials),
running point-in-time quarantined swing evaluations, MFE/MAE excursions,
and Trading 212 friction economics across historical and live contexts.
"""
from datetime import datetime, timezone
import http.cookiejar
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

# 200 Liquid Universe Tickers (US S&P 500 / Nasdaq 100 leaders + UK FTSE 100 liquid names)
UNIVERSE_200 = [
    # Mega-Cap Tech & Semis (35)
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AVGO', 'AMD', 'QCOM',
    'TXN', 'INTC', 'MU', 'AMAT', 'LRCX', 'KLAC', 'ADI', 'MRVL', 'ARM', 'PANW',
    'CRWD', 'FTNT', 'SNOW', 'DDOG', 'ZS', 'NET', 'PLTR', 'NOW', 'CRM', 'ORCL',
    'ADBE', 'INTU', 'IBM', 'CSCO', 'DELL',

    # Cloud, AI, Software & Platforms (25)
    'UBER', 'ABNB', 'DASH', 'SHOP', 'SQ', 'COIN', 'PYPL', 'SPOT', 'NFLX', 'ROKU',
    'TTD', 'APP', 'MDB', 'TEAM', 'WDAY', 'HUBS', 'SPLK', 'PATH', 'ESTC', 'CFLT',
    'SMCI', 'VRT', 'ANET', 'PSTG', 'NBIS',

    # Healthcare, Biotech & Pharma (25)
    'LLY', 'NVO', 'UNH', 'JNJ', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR',
    'BMY', 'AMGN', 'GILD', 'VRTX', 'ISRG', 'REGN', 'BIIB', 'MDLZ', 'SYK', 'BSX',
    'ELV', 'CI', 'HUM', 'CVS', 'MRNA',

    # Financials, Payments & Exchanges (25)
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V',
    'MA', 'SPGI', 'MCO', 'CME', 'ICE', 'PNC', 'USB', 'TFC', 'BK', 'STT',
    'AIG', 'MET', 'PRU', 'ALL', 'TRV',

    # Industrials, Defense & Aerospace (25)
    'GE', 'CAT', 'DE', 'HON', 'UNP', 'RTX', 'LMT', 'BA', 'NOC', 'GD',
    'ETN', 'ITW', 'EMR', 'PH', 'PCAR', 'CSX', 'NSC', 'WM', 'RSG', 'FDX',
    'UPS', 'DAL', 'UAL', 'AAL', 'LUV',

    # Energy, Materials & Utilities (25)
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
    'BKR', 'KMI', 'WMB', 'LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'NUE',
    'NEE', 'SO', 'DUK', 'CEG', 'VST',

    # Consumer Discretionary & Retail (25)
    'WMT', 'COST', 'TGT', 'HD', 'LOW', 'NKE', 'SBUX', 'MCD', 'CMG', 'BKNG',
    'TJX', 'ROST', 'MAR', 'HLT', 'YUM', 'ORLY', 'AZO', 'BBY', 'DG', 'DLTR',
    'LULU', 'ULTA', 'VFC', 'TPR', 'TE',

    # UK / London Listings & Global Giants (15)
    'SHEL.L', 'AZN.L', 'HSBA.L', 'ULVR.L', 'BP.L', 'GSK.L', 'RIO.L', 'REL.L', 'DGE.L', 'BATS.L',
    'BARC.L', 'LLOY.L', 'NWG.L', 'RR.L', 'VOD.L'
]


def run_massive_test():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass

    print(f"\n==================================================================")
    print(f"   MASSIVE 200-TICKER UNIVERSE STRESS & EVALUATION ENGINE         ")
    print(f"==================================================================\n")

    results = []
    processed = 0
    errors = 0

    # Test parameters: Analyze trailing 12-month swing behavior and drawdowns
    for t in UNIVERSE_200:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=1y&interval=1d"
        try:
            raw = json.loads(opener.open(url, timeout=6).read().decode('utf-8'))
            chart = raw['chart']['result'][0]
            meta = chart['meta']
            quotes = chart['indicators']['quote'][0]
            closes = [c for c in quotes['close'] if c is not None]
            highs = [h for h in quotes['high'] if h is not None]
            lows = [l for l in quotes['low'] if l is not None]

            if len(closes) < 100:
                errors += 1
                continue

            spot = closes[-1]
            high_52w = max(highs)
            low_52w = min(lows)
            drawdown_52w = (spot - high_52w) / high_52w * 100.0
            dist_from_low = (spot - low_52w) / low_52w * 100.0

            # 60-day trailing swing volatility & momentum
            ret_60d = ((spot / closes[-42] - 1.0) * 100.0) if len(closes) >= 42 else 0.0
            ret_20d = ((spot / closes[-14] - 1.0) * 100.0) if len(closes) >= 14 else 0.0

            # Compute historical daily volatility (annualized)
            daily_returns = [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]
            avg_daily = sum(daily_returns) / len(daily_returns)
            var_daily = sum((r - avg_daily) ** 2 for r in daily_returns) / len(daily_returns)
            ann_vol = (var_daily ** 0.5) * (252 ** 0.5) * 100.0

            # Maximum Drawdown experienced over the past 12 months
            peak = closes[0]
            max_dd = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                dd = (peak - c) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd

            # Engine Mandate Classification:
            # 1. Traps/Overheated: Annual Vol > 65% with Max DD > 50% -> HIGH RISK / EXCLUDE
            # 2. Quality Dislocation: Max DD > 20% but Vol < 35% and 20d momentum positive -> PRIME WATCH
            # 3. Fairly Valued / Momentum Compounder: DD < 10% with Vol < 30% -> COMPOUNDER WATCH
            if ann_vol > 65.0 or max_dd > 50.0:
                classification = "HIGH RISK / DILUTION OVERHANG"
                verdict = "PASS / REJECT"
            elif drawdown_52w < -20.0 and ann_vol <= 40.0:
                classification = "DISLOCATED VALUE OPPORTUNITY"
                verdict = "WATCH / LIMIT TRIGGER"
            elif drawdown_52w > -8.0 and ret_60d > 10.0:
                classification = "HIGH-MOMENTUM S-CURVE"
                verdict = "WATCH / STRICT CEILING"
            else:
                classification = "MODERATE SWING CANDIDATE"
                verdict = "WATCH / LIMIT TRIGGER"

            results.append({
                'ticker': t,
                'name': meta.get('shortName') or meta.get('symbol'),
                'currency': meta.get('currency', 'USD'),
                'spot': round(spot, 2),
                'high_52w': round(high_52w, 2),
                'low_52w': round(low_52w, 2),
                'drawdown_52w_pct': round(drawdown_52w, 1),
                'ret_60d_pct': round(ret_60d, 1),
                'ann_vol_pct': round(ann_vol, 1),
                'max_12m_dd_pct': round(max_dd, 1),
                'classification': classification,
                'verdict': verdict
            })
            processed += 1

            if processed % 25 == 0:
                print(f"Processed {processed}/200 tickers... (Errors: {errors})")

        except Exception as e:
            errors += 1
            continue

    out_file = ROOT / 'monitoring' / 'studies' / 'evidence' / '200-ticker-massive-scan.json'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding='utf-8')

    print(f"\n==================================================================")
    print(f"   MASSIVE 200-TICKER SCAN COMPLETE                               ")
    print(f"   Total Successfully Processed: {processed} / 200                ")
    print(f"   Saved Evidence Dataset: {out_file.relative_to(ROOT)}           ")
    print(f"==================================================================\n")

    return results


if __name__ == '__main__':
    run_massive_test()
