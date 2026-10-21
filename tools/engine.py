"""Company Research 2 —Unified Analyst Engine CLI.

Consolidates memory retrieval, Trading 212 break-even economics, dossier scaffolding,
Telegram alert dispatch, live options/gamma positioning (`options`), point-in-time
historical replay (`backtest`), and passive limit-trigger monitoring (`check-triggers`).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import http.cookiejar
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

try:
    import decision_economics
    import observation_core
    import observation
except ImportError as err:
    print(f"Warning: Tool imports failed ({err})", file=sys.stderr)


def _dec(val) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        return Decimal(str(val))


def _yahoo_opener():
    """Build a urllib opener with Yahoo Finance cookie and crumb for live market/options data."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass
    crumb = ""
    try:
        crumb = opener.open('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=5).read().decode('utf-8').strip()
    except Exception:
        pass
    return opener, crumb


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0.0 or sigma <= 0.001 or S <= 0.0 or K <= 0.0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def cmd_status(args):
    """Display compact, clean status of the £300 model sleeve."""
    with observation_core.Store(ROOT / 'state' / 'observation' / 'operations.sqlite3') as store:
        st = store.status()
        telegram_configured = (ROOT / 'state' / 'observation' / 'telegram.dpapi').exists()

        print("\n=== £300 MODEL PORTFOLIO SLEEVE STATUS ===")
        print(f"Total Capital : £{st.get('capital_gbp', '300.00')}")
        print(f"Cash Balance  : £{st.get('cash_gbp', '300.00')}")
        print(f"Reserved Cash : £{st.get('reserved_gbp', '0.00')}")
        print(f"Available Cash: £{st.get('available_gbp', '300.00')}")
        print(f"Holdings      : {st.get('holdings', {}) or 'None (100% Cash)'}")
        print(f"NAV           : £{st.get('net_asset_value_gbp', '300.00')}")
        print(f"Telegram Bot  : {'Connected (DPAPI Encrypted)' if telegram_configured else 'Pending Setup (run tools\\observation.cmd configure-telegram)'}")
        print("==========================================\n")


def cmd_math(args):
    """Calculate exact Trading 212 friction, round-trip break-even, and upside/downside ratio."""
    price = _dec(args.price)
    target = _dec(args.target)
    stop = _dec(args.stop)
    budget = _dec(args.budget)
    currency = args.currency.upper()
    fx_rate = _dec(args.fx) if currency != 'GBP' else Decimal('1.0')
    fx_fee_rate = Decimal('0.0015') if currency != 'GBP' else Decimal('0.0')  # 0.15% per way

    if args.days_to_earnings is not None and int(args.days_to_earnings) <= 14 and budget > Decimal('75.00'):
        print(f"\n[!] BINARY EVENT GAP WARNING: Catalyst is {args.days_to_earnings} days away (<=14d).")
        print("    Per <risk_rules>, overnight gap risk invalidates normal stop-losses; capping budget to £75.00 (4-tranche rule).")
        budget = Decimal('75.00')

    share_denom = price * fx_rate * (Decimal('1') + fx_fee_rate)
    shares = (budget / share_denom).quantize(Decimal('0.0001'))

    gross_entry_gbp = shares * price * fx_rate
    entry_fx_fee_gbp = gross_entry_gbp * fx_fee_rate
    total_entry_gbp = gross_entry_gbp + entry_fx_fee_gbp

    gross_target_gbp = shares * target * fx_rate
    target_fx_fee_gbp = gross_target_gbp * fx_fee_rate
    net_target_gbp = gross_target_gbp - target_fx_fee_gbp
    net_gain_gbp = net_target_gbp - total_entry_gbp
    net_return_pct = (net_gain_gbp / total_entry_gbp * Decimal('100')).quantize(Decimal('0.01'))

    gross_stop_gbp = shares * stop * fx_rate
    stop_fx_fee_gbp = gross_stop_gbp * fx_fee_rate
    net_stop_gbp = gross_stop_gbp - stop_fx_fee_gbp
    net_loss_gbp = total_entry_gbp - net_stop_gbp
    net_loss_pct = (net_loss_gbp / total_entry_gbp * Decimal('100')).quantize(Decimal('0.01'))

    be_price = (total_entry_gbp / (shares * fx_rate * (Decimal('1') - fx_fee_rate))).quantize(Decimal('0.01'))
    be_gain_pct = ((be_price - price) / price * Decimal('100')).quantize(Decimal('0.02'))

    ratio = (net_gain_gbp / net_loss_gbp).quantize(Decimal('0.01')) if net_loss_gbp > 0 else Decimal('99.9')
    passes_hurdles = net_return_pct >= Decimal('8.0') and ratio >= Decimal('2.0')

    # Solve exact strict Base-vs-Stop entry ceiling where ratio >= 2.0 and net_return >= 8.0%
    fee_factor = (Decimal('1') - fx_fee_rate) / (Decimal('1') + fx_fee_rate)
    ceiling_8pct = (target * fee_factor / Decimal('1.08')).quantize(Decimal('0.01'))
    ceiling_2to1 = (((target + Decimal('2') * stop) * fee_factor) / Decimal('3')).quantize(Decimal('0.01'))
    strict_ceiling = min(ceiling_8pct, ceiling_2to1)

    print("\n=== TRADING 212 SLEEVE ECONOMICS & FRICTION CHECK ===")
    print(f"Currency / FX Rate : {currency} @ {fx_rate:.4f} GBP per 1 {currency}")
    print(f"Position Sizing    : £{total_entry_gbp:.2f} GBP commitment -> {shares} shares @ {currency} ${price:.2f}")
    print(f"Break-even Price   : {currency} ${be_price:.2f} (+{be_gain_pct}% hurdle to clear 0.30% round-trip FX fee)")
    print(f"Target Outcome     : {currency} ${target:.2f} -> Net £{net_target_gbp:.2f} (+£{net_gain_gbp:.2f} / +{net_return_pct}%)")
    print(f"Stop-Loss Outcome  : {currency} ${stop:.2f} -> Net £{net_stop_gbp:.2f} (-£{net_loss_gbp:.2f} / -{net_loss_pct}%)")
    print(f"Upside/Downside    : {ratio}:1 ratio (Target Gain £{net_gain_gbp:.2f} vs Stop Loss £{net_loss_gbp:.2f})")
    print(f"Strict Entry Ceil  : {currency} ${strict_ceiling:.2f} (Max price for BOTH >=8% net return & >=2:1 Target/Stop)")
    print(f"Hurdle Evaluation  : {'PASSED (>8% Net Gain AND >2:1 Asymmetry)' if passes_hurdles else 'FAILED (Does not satisfy >8% net or >2:1 ratio)'}")
    print("=====================================================\n")


def cmd_options(args):
    """Fetch live options open interest, Call/Put walls, Max Pain, and Black-Scholes Dealer Gamma Exposure (GEX)."""
    ticker = args.ticker.upper()
    opener, crumb = _yahoo_opener()
    base_url = f"https://query2.finance.yahoo.com/v7/finance/options/{ticker}?crumb={crumb}"
    try:
        raw = json.loads(opener.open(base_url, timeout=10).read().decode('utf-8'))
        res = raw['optionChain']['result'][0]
    except Exception as err:
        print(f"Error fetching options chain for {ticker}: {err}", file=sys.stderr)
        sys.exit(1)

    quote = res.get('quote', {})
    spot = float(quote.get('regularMarketPrice') or quote.get('postMarketPrice') or 0.0)
    expirations = res.get('expirationDates', [])
    if not expirations or spot <= 0:
        print(f"No valid options data or spot price found for {ticker}.")
        return

    # Select requested expiry index (default 0 = nearest expiry, or user --expiry-index)
    idx = min(max(0, args.expiry_index), len(expirations) - 1)
    exp_ts = expirations[idx]
    if idx != 0:
        exp_url = f"{base_url}&date={exp_ts}"
        raw = json.loads(opener.open(exp_url, timeout=10).read().decode('utf-8'))
        res = raw['optionChain']['result'][0]

    opt_block = res['options'][0]
    calls = opt_block.get('calls', [])
    puts = opt_block.get('puts', [])
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc).strftime('%Y-%m-%d')
    now_ts = datetime.now(timezone.utc).timestamp()
    T = max((exp_ts - now_ts) / (365.25 * 86400.0), 1.0 / 365.25)
    r = 0.045

    strikes = sorted(set(float(c['strike']) for c in calls) | set(float(p['strike']) for p in puts))
    if not strikes:
        print(f"No strikes available for {ticker} expiry {exp_dt}.")
        return

    # 1. Max Pain (strike where total intrinsic option payout is minimized)
    pain_by_strike = {}
    for s in strikes:
        c_intrinsic = sum(max(0.0, s - float(c['strike'])) * int(c.get('openInterest') or 0) for c in calls)
        p_intrinsic = sum(max(0.0, float(p['strike']) - s) * int(p.get('openInterest') or 0) for p in puts)
        pain_by_strike[s] = c_intrinsic + p_intrinsic
    max_pain = min(pain_by_strike, key=pain_by_strike.get)

    # 2. Call Wall & Put Wall (focus within +/- 35% of spot so deep-leaps noise doesn't distort swing walls)
    near_calls = [c for c in calls if 0.65 * spot <= float(c['strike']) <= 1.35 * spot] or calls
    near_puts = [p for p in puts if 0.65 * spot <= float(p['strike']) <= 1.35 * spot] or puts
    top_calls = sorted(near_calls, key=lambda x: int(x.get('openInterest') or 0), reverse=True)[:3]
    top_puts = sorted(near_puts, key=lambda x: int(x.get('openInterest') or 0), reverse=True)[:3]

    total_call_oi = sum(int(c.get('openInterest') or 0) for c in calls)
    total_put_oi = sum(int(p.get('openInterest') or 0) for p in puts)
    pc_ratio = (total_put_oi / total_call_oi) if total_call_oi > 0 else 0.0

    # 3. Black-Scholes Dealer Gamma Exposure (GEX) per 1% spot move ($ Millions)
    # Convention: Dealers long calls (positive gamma stabilizing), short puts (negative gamma accelerating)
    gex_by_strike = {}
    for c in calls:
        k = float(c['strike'])
        oi = int(c.get('openInterest') or 0)
        iv = float(c.get('impliedVolatility') or 0.0)
        g = _bs_gamma(spot, k, T, r, iv)
        gex_by_strike[k] = gex_by_strike.get(k, 0.0) + (g * oi * 100.0 * spot * spot * 0.01)

    for p in puts:
        k = float(p['strike'])
        oi = int(p.get('openInterest') or 0)
        iv = float(p.get('impliedVolatility') or 0.0)
        g = _bs_gamma(spot, k, T, r, iv)
        gex_by_strike[k] = gex_by_strike.get(k, 0.0) - (g * oi * 100.0 * spot * spot * 0.01)

    net_gex_m = sum(gex_by_strike.values()) / 1e6
    pos_gex_strike = max(gex_by_strike, key=gex_by_strike.get)
    neg_gex_strike = min(gex_by_strike, key=gex_by_strike.get)

    # Approximate ATM Implied Move for this expiry
    atm_call = min(calls, key=lambda c: abs(float(c['strike']) - spot)) if calls else {}
    atm_put = min(puts, key=lambda p: abs(float(p['strike']) - spot)) if puts else {}
    straddle_mid = float(atm_call.get('lastPrice') or 0.0) + float(atm_put.get('lastPrice') or 0.0)
    implied_move_pct = (straddle_mid / spot * 100.0) if spot > 0 else 0.0

    regime = (
        "POSITIVE GAMMA (Stabilizing / Mean-Reverting — dealers sell rips & buy dips; pin risk near Max Pain)"
        if net_gex_m >= 0
        else "NEGATIVE GAMMA (Volatility-Amplifying / Momentum — dealers hedge WITH direction; beware downside air-pockets)"
    )

    avail_exps = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d') for ts in expirations[:6]]

    print(f"\n=== OPTIONS & GAMMA STRUCTURE: {ticker} (Spot: ${spot:.2f}) ===")
    print(f"Selected Expiry    : {exp_dt} (Index {idx} of {len(expirations)}; Next 6: {', '.join(avail_exps)})")
    print(f"Put/Call OI Ratio  : {pc_ratio:.2f} (Calls: {total_call_oi:,} OI | Puts: {total_put_oi:,} OI)")
    print(f"ATM Straddle Move  : +/-${straddle_mid:.2f} (+/-{implied_move_pct:.1f}% implied move by {exp_dt})")
    print(f"Max Pain Strike    : ${max_pain:.2f} ({((max_pain - spot) / spot * 100):+.1f}% vs Spot)")
    print(f"Top Call Walls     : " + ", ".join(f"${c['strike']} ({int(c.get('openInterest') or 0):,} OI)" for c in top_calls))
    print(f"Top Put Walls      : " + ", ".join(f"${p['strike']} ({int(p.get('openInterest') or 0):,} OI)" for p in top_puts))
    print(f"Net Dealer GEX     : ${net_gex_m:+.2f}M per 1% move | Magnet Strike: ${pos_gex_strike:.2f} | Accel Strike: ${neg_gex_strike:.2f}")
    print(f"Gamma Regime       : {regime}")
    print("==============================================================\n")


def cmd_backtest(args):
    """Fetch point-in-time historical price context and forward outcome for quarantined historical backtest runs."""
    ticker = args.ticker.upper()
    as_of_str = args.as_of
    horizon_days = int(args.horizon_days)
    as_of_dt = datetime.strptime(as_of_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    start_ts = int(as_of_dt.timestamp()) - (370 * 86400)
    end_ts = int(as_of_dt.timestamp()) + ((horizon_days + 15) * 86400)

    opener, _ = _yahoo_opener()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start_ts}&period2={end_ts}&interval=1d"
    try:
        raw = json.loads(opener.open(url, timeout=10).read().decode('utf-8'))
        res = raw['chart']['result'][0]
    except Exception as err:
        print(f"Error fetching historical chart for {ticker}: {err}", file=sys.stderr)
        sys.exit(1)

    timestamps = res.get('timestamp', [])
    quote = res['indicators']['quote'][0]
    closes = quote.get('close', [])
    highs = quote.get('high', [])
    lows = quote.get('low', [])

    bars = []
    for ts, c, h, l in zip(timestamps, closes, highs, lows):
        if c is not None:
            dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
            bars.append({'date': dt_str, 'close': float(c), 'high': float(h or c), 'low': float(l or c)})

    prior_bars = [b for b in bars if b['date'] <= as_of_str]
    future_bars = [b for b in bars if b['date'] > as_of_str][:horizon_days]

    if not prior_bars:
        print(f"No historical bars found on or before {as_of_str} for {ticker}.")
        return

    as_of_bar = prior_bars[-1]
    spot = as_of_bar['close']
    high_52w = max(b['high'] for b in prior_bars[-252:])
    low_52w = min(b['low'] for b in prior_bars[-252:])
    ret_1m = ((spot / prior_bars[-21]['close'] - 1.0) * 100.0) if len(prior_bars) >= 21 else 0.0
    ret_3m = ((spot / prior_bars[-63]['close'] - 1.0) * 100.0) if len(prior_bars) >= 63 else 0.0

    print(f"\n=== POINT-IN-TIME BACKTEST SNAPSHOT: {ticker} (AS OF {as_of_bar['date']}) ===")
    print(f"[QUARANTINE RULE] Use ONLY filings, guidance, and news published on or before {as_of_bar['date']}.")
    print(f"As-Of Close Price  : ${spot:.2f}")
    print(f"Trailing 52w Range : ${low_52w:.2f} - ${high_52w:.2f} (Spot is {((spot - high_52w)/high_52w*100):.1f}% from 52w High)")
    print(f"Trailing Momentum  : 1-Month: {ret_1m:+.1f}% | 3-Month: {ret_3m:+.1f}%")

    if args.reveal_outcome and future_bars:
        end_bar = future_bars[-1]
        max_fwd = max(future_bars, key=lambda b: b['high'])
        min_fwd = min(future_bars, key=lambda b: b['low'])
        end_ret = (end_bar['close'] / spot - 1.0) * 100.0
        mfe_ret = (max_fwd['high'] / spot - 1.0) * 100.0
        mae_ret = (min_fwd['low'] / spot - 1.0) * 100.0
        print("\n--- FORWARD REALIZED OUTCOME (FOR POST-VERDICT SCORING ONLY) ---")
        print(f"Horizon End ({end_bar['date']}) : ${end_bar['close']:.2f} ({end_ret:+.2f}%)")
        print(f"Max Favorable Excursion : ${max_fwd['high']:.2f} ({mfe_ret:+.2f}% on {max_fwd['date']})")
        print(f"Max Adverse Excursion   : ${min_fwd['low']:.2f} ({mae_ret:+.2f}% on {min_fwd['date']})")
    else:
        print("\n[Outcome Hidden] Run your quarantined valuation & verdict first, then re-run with --reveal-outcome to grade the trade.")
    print("====================================================================\n")


def cmd_check_triggers(args):
    """Scan all WATCH / LIMIT TRIGGER dossiers in monitoring/studies/ against live prices."""
    studies_dir = ROOT / 'monitoring' / 'studies'
    if not studies_dir.exists():
        print("No monitoring/studies directory found.")
        return

    watch_items = []
    for f in sorted(studies_dir.glob('*-opportunity-dossier.md'), reverse=True):
        text = f.read_text(encoding='utf-8', errors='ignore')
        if 'WATCH / LIMIT TRIGGER' not in text and 'WATCH_LIMIT_TRIGGER' not in text:
            continue
        m_ticker = re.search(r'-([a-z0-9\.]+)-opportunity-dossier\.md$', f.name)
        if not m_ticker:
            continue
        ticker = m_ticker.group(1).upper()
        # Avoid duplicate older dossiers for the same ticker
        if any(w['ticker'] == ticker for w in watch_items):
            continue
        # Extract ceiling price from 'buy only at or below \$62.00' or 'Max entry ceiling \$62.00'
        m_ceil = re.search(r'(?:buy only at or below|Max entry ceiling|Buy ONLY at or below)\s+\\?\$([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
        if m_ceil:
            watch_items.append({
                'ticker': ticker,
                'ceiling': float(m_ceil.group(1)),
                'file': f.name,
            })

    print("\n=== PASSIVE LIMIT-TRIGGER MONITOR (£300 SLEEVE) ===")
    if not watch_items:
        print("No active WATCH / LIMIT TRIGGER dossiers found.")
        print("===================================================\n")
        return

    opener, _ = _yahoo_opener()
    for item in watch_items:
        t = item['ticker']
        ceil = item['ceiling']
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range=5d"
        try:
            raw = json.loads(opener.open(url, timeout=8).read().decode('utf-8'))
            meta = raw['chart']['result'][0]['meta']
            spot = float(meta.get('regularMarketPrice') or 0.0)
            dist_pct = ((spot - ceil) / ceil * 100.0) if ceil > 0 else 0.0
            status = "TRIGGERED (<= CEILING!)" if spot <= ceil else f"WAITING ({dist_pct:+.2f}% above ceiling)"
            print(f"{t:<6} | Spot: ${spot:>7.2f} | Ceiling: ${ceil:>7.2f} | {status} [{item['file']}]")
        except Exception as err:
            print(f"{t:<6} | Ceiling: ${ceil:>7.2f} | Quote fetch failed ({err}) [{item['file']}]")
    print("===================================================\n")


def cmd_memory(args):
    """Search prior studies, confirmed lessons, and company files for verified findings."""
    query = args.query.lower()
    matches = []

    for lesson_file, label in (('confirmed.md', 'Lesson'), ('proposed.md', 'Proposed lesson')):
        lesson_path = ROOT / 'lessons' / lesson_file
        if lesson_path.exists():
            text = lesson_path.read_text(encoding='utf-8', errors='ignore')
            for line in text.splitlines():
                if query in line.lower() and line.strip():
                    matches.append((label, line.strip()[:400]))

    studies_dir = ROOT / 'monitoring' / 'studies'
    if studies_dir.exists():
        for file in sorted(studies_dir.glob('*.md'), reverse=True):
            content = file.read_text(encoding='utf-8', errors='ignore')
            if query in content.lower():
                lines = content.splitlines()
                summary_snippet = ""
                for l in lines:
                    if query in l.lower() and len(l.strip()) > 10:
                        summary_snippet = l.strip()
                        break
                matches.append(('Study', f"{file.name}: {summary_snippet or 'Matches query'}"))

    companies_dir = ROOT / 'companies'
    if companies_dir.exists():
        for file in companies_dir.glob(f"*{query}*"):
            matches.append(('Company Directory', str(file.relative_to(ROOT))))

    print(f"\n=== ENGINE MEMORY SEARCH: '{args.query}' ===")
    if not matches:
        print("No prior findings or lessons found in memory for this term.")
    else:
        for cat, note in matches[:15]:
            print(f"[{cat}] {note}")
    print("==========================================\n")


def cmd_scaffold(args):
    """Generate a clean, standardized Opportunity Dossier markdown template."""
    ticker = args.ticker.upper()
    as_of = args.as_of or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    suffix = "backtest-dossier" if args.as_of else "opportunity-dossier"
    filename = f"{as_of}-{ticker.lower()}-{suffix}.md"
    out_path = ROOT / 'monitoring' / 'studies' / filename

    template = f"""# Short-Horizon Opportunity Dossier: {ticker}
**As of Date:** {as_of}
**Mandate:** £300 Trading 212 ISA Model Sleeve (Max £100 commitment, swing horizon: days to a few months)
**Security:** {args.exchange or 'NASDAQ'}:{ticker}
**Currency:** {args.currency or 'USD'}

---

## 1. Executive Summary & Catalyst Mechanism
- **The Event/Catalyst:** [Specific date and event: e.g. Q3 earnings, product cycle, regulatory inflection]
- **Business Impact:** [How the catalyst changes recurring cash generation vs. market perception]
- **Market Expectations vs. Reality:** [What consensus currently prices in vs. our fundamental estimate]

---

## 2. Statutory-to-Owner Cash Flow & Valuation Bridge
- **Statutory GAAP vs. Management Non-GAAP:** [Reconciliation and adjustments]
- **Non-Recurring Items Stripped:** [One-off cash receipts, legal windfalls, tax items excluded]
- **Stock-Based Compensation (SBC) & Dilution:** [True economic expense treatment]
- **Net Debt / Claims Bridge:**
  - Cash & Equivalents: 
  - Total Debt:
  - Operating Leases / Off-Balance-Sheet Claims:
  - Net Debt / (Net Cash):
  - Shares Outstanding:
- **Fair Value Scenario Matrix:**
  - **Bear Case:** $[Price] ([Thesis])
  - **Base Case:** $[Price] ([Thesis])
  - **Bull Case:** $[Price] ([Thesis])

---

## 3. Trading 212 Sleeve Economics, Options Positioning & Hurdle Check
*Calculated using `tools/engine.py math` and `tools/engine.py options`:*
- **Current Share Price:** $[Price]
- **Options / Gamma Positioning:** [Max Pain, Top Call/Put Walls, Net Dealer GEX regime, ATM implied move]
- **Proposed Entry Ceiling:** $[Ceiling] (Max £100.00 commitment; £75.00 if binary catalyst <=14 days)
- **Target Price:** $[Target]
- **Hard Stop-Loss:** $[Stop]
- **Trading 212 FX Friction:** 0.15% fee each way (0.30% round-trip)
- **Break-Even Price:** $[Price] (+[X]% to clear FX fee)
- **Net Expected Return:** [X]% (>8.0% hurdle requirement: [PASS/FAIL])
- **Upside-to-Downside Ratio:** [X]:1 (>2:1 requirement: [PASS/FAIL])

---

## 4. Mandatory Adversarial Challenge (Astra Red-Team)
- **Vulnerabilities in Bull Thesis:** [What could break the core assumption?]
- **Options / Dealer Gamma & Gap Risk:** [Are we buying into a Call Wall, Negative Gamma air-pocket, or binary earnings gap?]
- **Catalyst Delay Stress Test:** [What happens if the catalyst is delayed by 60–90 days?]
- **Why Cash is Inferior:** [Why this setup beats holding cash in the sleeve]

---

## 5. Output Contract & Structured Verdict
- **VERDICT:** [ACTIONABLE BUY SIGNAL | WATCH / LIMIT TRIGGER | PASS / REJECT]
- **Rationale:** [1-2 sentences summarizing the decisive reason]

### Telegram Alert Payload
```text
TICKER: {ticker}
ACTION: [BUY / WATCH / PASS]
MAX ENTRY CEILING: $[Price]
COMMITMENT: £[Amount] GBP (out of £300)
ESTIMATED SHARES: [Shares]
CATALYST TIMELINE: [Date & Description]
HARD STOP-LOSS: $[Price]
THESIS-INVALIDATION EXIT: [Trigger condition]
TIME-EXIT REASSESSMENT: [Date]
```
"""
    out_path.write_text(template, encoding='utf-8')
    print(f"\n[+] Created scaffolded Opportunity Dossier: {out_path.relative_to(ROOT)}\n")


def cmd_alert(args):
    """Push a verified signal directly to iPhone via Telegram and record in SQLite ledger."""
    cmd = [
        sys.executable, '-B', str(ROOT / 'tools' / 'observation.py'), 'send-signal',
        '--ticker', args.ticker.upper(),
        '--text', args.text,
        '--verdict', args.verdict
    ]
    if args.expires_hours is not None:
        cmd += ['--expires-hours', str(args.expires_hours)]
    import subprocess
    subprocess.run(cmd, check=False)


def main():
    parser = argparse.ArgumentParser(description="Company Research 2 Unified Engine")
    sub = parser.add_subparsers(dest='command', required=True)

    # status
    sub.add_parser('status', help="Show £300 sleeve status and Telegram connectivity")

    # math
    m = sub.add_parser('math', help="Calculate T212 break-even, FX drag, binary gap sizing, and hurdle ratios")
    m.add_argument('--price', required=True, help="Entry price in native currency")
    m.add_argument('--target', required=True, help="Target exit price in native currency")
    m.add_argument('--stop', required=True, help="Hard stop-loss price in native currency")
    m.add_argument('--budget', default='100.00', help="GBP capital commitment (default £100)")
    m.add_argument('--currency', default='USD', help="Quote currency (default USD)")
    m.add_argument('--fx', default='0.77', help="GBP per 1 foreign major currency unit (e.g. 0.77 for USD)")
    m.add_argument('--days-to-earnings', type=int, default=None, help="Days until binary earnings event (auto-caps budget to £75 if <=14d)")

    # options (Gamma / Max Pain / Call & Put Walls)
    opt = sub.add_parser('options', help="Analyze live Options Open Interest, Max Pain, Call/Put Walls, and Dealer Net GEX")
    opt.add_argument('ticker', help="Stock ticker symbol (e.g. NFLX, APP)")
    opt.add_argument('--expiry-index', type=int, default=0, help="Expiration index (0 = nearest weekly/monthly expiry, 1 = next, etc.)")

    # backtest (Point-in-time historical snapshot & optional post-verdict reveal)
    bt = sub.add_parser('backtest', help="Generate point-in-time historical market snapshot for quarantined backtests")
    bt.add_argument('ticker', help="Stock ticker symbol")
    bt.add_argument('--as-of', required=True, help="Historical point-in-time date (YYYY-MM-DD)")
    bt.add_argument('--horizon-days', type=int, default=45, help="Forward trading days to evaluate when --reveal-outcome is set (default 45)")
    bt.add_argument('--reveal-outcome', action='store_true', help="Reveal forward realized price performance AFTER verdict is locked")

    # check-triggers (Passive watcher for WATCH / LIMIT TRIGGER dossiers)
    sub.add_parser('check-triggers', help="Check live prices against all active WATCH / LIMIT TRIGGER ceilings")

    # memory
    mem = sub.add_parser('memory', help="Search SQLite memory, studies, and lessons")
    mem.add_argument('query', help="Ticker, company name, or accounting concept")

    # scaffold
    scaf = sub.add_parser('scaffold', help="Generate a standardized Opportunity Dossier markdown file")
    scaf.add_argument('ticker', help="Stock ticker symbol (e.g. NFLX, APP)")
    scaf.add_argument('--exchange', default='NASDAQ', help="Exchange (default NASDAQ)")
    scaf.add_argument('--currency', default='USD', help="Currency (default USD)")
    scaf.add_argument('--as-of', default=None, help="Optional historical date (YYYY-MM-DD) for backtest dossiers")

    # alert
    al = sub.add_parser('alert', help="Send model trade signal to Telegram and SQLite ledger")
    al.add_argument('--ticker', required=True, help="Stock ticker")
    al.add_argument('--text', required=True, help="Formatted signal message text")
    al.add_argument('--verdict', default='ACTIONABLE_BUY_SIGNAL', help="ACTIONABLE_BUY_SIGNAL | WATCH_LIMIT_TRIGGER | PASS_REJECT")
    al.add_argument('--expires-hours', type=float, default=None, help="Alert lifetime (default 24h for BUY, 168h for WATCH/PASS)")

    args = parser.parse_args()
    handlers = {
        'status': cmd_status,
        'math': cmd_math,
        'options': cmd_options,
        'backtest': cmd_backtest,
        'check-triggers': cmd_check_triggers,
        'memory': cmd_memory,
        'scaffold': cmd_scaffold,
        'alert': cmd_alert,
    }
    handlers[args.command](args)


if __name__ == '__main__':
    main()
