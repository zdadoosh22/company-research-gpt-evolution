"""Company Research 2 — Unified Analyst Engine CLI.

Consolidates memory retrieval, Trading 212 break-even economics, dossier scaffolding,
and Telegram alert dispatch into a single deterministic command-line interface.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import json
import os
from pathlib import Path
import re
import sys

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

    # Budget in foreign currency (approximate shares)
    # Total entry cost in GBP = (shares * price * fx) * (1 + fx_fee)
    # shares = budget / (price * fx * (1 + fx_fee))
    share_denom = price * fx_rate * (Decimal('1') + fx_fee_rate)
    shares = (budget / share_denom).quantize(Decimal('0.0001'))
    
    # Precise Entry Cost (GBP)
    gross_entry_gbp = shares * price * fx_rate
    entry_fx_fee_gbp = gross_entry_gbp * fx_fee_rate
    total_entry_gbp = gross_entry_gbp + entry_fx_fee_gbp

    # Target Exit Proceeds (GBP)
    gross_target_gbp = shares * target * fx_rate
    target_fx_fee_gbp = gross_target_gbp * fx_fee_rate
    net_target_gbp = gross_target_gbp - target_fx_fee_gbp
    net_gain_gbp = net_target_gbp - total_entry_gbp
    net_return_pct = (net_gain_gbp / total_entry_gbp * Decimal('100')).quantize(Decimal('0.01'))

    # Stop-Loss Exit Proceeds (GBP)
    gross_stop_gbp = shares * stop * fx_rate
    stop_fx_fee_gbp = gross_stop_gbp * fx_fee_rate
    net_stop_gbp = gross_stop_gbp - stop_fx_fee_gbp
    net_loss_gbp = total_entry_gbp - net_stop_gbp
    net_loss_pct = (net_loss_gbp / total_entry_gbp * Decimal('100')).quantize(Decimal('0.01'))

    # Break-even price
    # shares * P_be * fx * (1 - fx_fee) = total_entry_gbp
    be_price = (total_entry_gbp / (shares * fx_rate * (Decimal('1') - fx_fee_rate))).quantize(Decimal('0.01'))
    be_gain_pct = ((be_price - price) / price * Decimal('100')).quantize(Decimal('0.02'))

    ratio = (net_gain_gbp / net_loss_gbp).quantize(Decimal('0.01')) if net_loss_gbp > 0 else Decimal('99.9')
    passes_hurdles = net_return_pct >= Decimal('8.0') and ratio >= Decimal('2.0')

    print("\n=== TRADING 212 SLEEVE ECONOMICS & FRICTION CHECK ===")
    print(f"Currency / FX Rate : {currency} @ {fx_rate:.4f} GBP per 1 {currency}")
    print(f"Position Sizing    : £{total_entry_gbp:.2f} GBP commitment -> {shares} shares @ {currency} ${price:.2f}")
    print(f"Break-even Price   : {currency} ${be_price:.2f} (+{be_gain_pct}% hurdle to clear 0.30% round-trip FX fee)")
    print(f"Target Outcome     : {currency} ${target:.2f} -> Net £{net_target_gbp:.2f} (+£{net_gain_gbp:.2f} / +{net_return_pct}%)")
    print(f"Stop-Loss Outcome  : {currency} ${stop:.2f} -> Net £{net_stop_gbp:.2f} (-£{net_loss_gbp:.2f} / -{net_loss_pct}%)")
    print(f"Upside/Downside    : {ratio}:1 ratio (Target Gain £{net_gain_gbp:.2f} vs Stop Loss £{net_loss_gbp:.2f})")
    print(f"Hurdle Evaluation  : {'PASSED (>8% Net Gain AND >2:1 Asymmetry)' if passes_hurdles else 'FAILED (Does not satisfy >8% net or >2:1 ratio)'}")
    print("=====================================================\n")


def cmd_memory(args):
    """Search prior studies, confirmed lessons, and company files for verified findings."""
    query = args.query.lower()
    matches = []

    # Check lessons/confirmed.md
    confirmed_path = ROOT / 'lessons' / 'confirmed.md'
    if confirmed_path.exists():
        text = confirmed_path.read_text(encoding='utf-8', errors='ignore')
        for line in text.splitlines():
            if query in line.lower() and line.strip().startswith(('-', '*', '#', '1', '2', '3', '4', '5')):
                matches.append(('Lesson', line.strip()))

    # Check monitoring/studies/
    studies_dir = ROOT / 'monitoring' / 'studies'
    if studies_dir.exists():
        for file in sorted(studies_dir.glob('*.md'), reverse=True):
            content = file.read_text(encoding='utf-8', errors='ignore')
            if query in content.lower():
                # Extract first matching paragraph or header
                lines = content.splitlines()
                summary_snippet = ""
                for i, l in enumerate(lines):
                    if query in l.lower() and len(l.strip()) > 10:
                        summary_snippet = l.strip()
                        break
                matches.append(('Study', f"{file.name}: {summary_snippet or 'Matches query'}"))

    # Check companies/
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
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f"{today}-{ticker.lower()}-opportunity-dossier.md"
    out_path = ROOT / 'monitoring' / 'studies' / filename

    template = f"""# Short-Horizon Opportunity Dossier: {ticker}
**As of Date:** {today}
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

## 3. Trading 212 Sleeve Economics & Hurdle Check
*Calculated using `tools/engine.py math`:*
- **Current Share Price:** $[Price]
- **Proposed Entry Ceiling:** $[Ceiling] (Max £100.00 commitment)
- **Target Price:** $[Target]
- **Hard Stop-Loss:** $[Stop]
- **Trading 212 FX Friction:** 0.15% fee each way (0.30% round-trip)
- **Break-Even Price:** $[Price] (+[X]% to clear FX fee)
- **Net Expected Return:** [X]% (>8.0% hurdle requirement: [PASS/FAIL])
- **Upside-to-Downside Ratio:** [X]:1 (>2:1 requirement: [PASS/FAIL])

---

## 4. Mandatory Adversarial Challenge (Astra Red-Team)
- **Vulnerabilities in Bull Thesis:** [What could break the core assumption?]
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
    os.system(' '.join(f'"{c}"' if ' ' in c else c for c in cmd))


def main():
    parser = argparse.ArgumentParser(description="Company Research 2 Unified Engine")
    sub = parser.add_subparsers(dest='command', required=True)

    # status
    sub.add_parser('status', help="Show £300 sleeve status and Telegram connectivity")

    # math
    m = sub.add_parser('math', help="Calculate T212 break-even, FX drag, and hurdle ratios")
    m.add_argument('--price', required=True, help="Entry price in native currency")
    m.add_argument('--target', required=True, help="Target exit price in native currency")
    m.add_argument('--stop', required=True, help="Hard stop-loss price in native currency")
    m.add_argument('--budget', default='100.00', help="GBP capital commitment (default £100)")
    m.add_argument('--currency', default='USD', help="Quote currency (default USD)")
    m.add_argument('--fx', default='0.77', help="GBP per 1 foreign major currency unit (e.g. 0.77 for USD)")

    # memory
    mem = sub.add_parser('memory', help="Search SQLite memory, studies, and lessons")
    mem.add_argument('query', help="Ticker, company name, or accounting concept")

    # scaffold
    scaf = sub.add_parser('scaffold', help="Generate a standardized Opportunity Dossier markdown file")
    scaf.add_argument('ticker', help="Stock ticker symbol (e.g. NFLX, APP)")
    scaf.add_argument('--exchange', default='NASDAQ', help="Exchange (default NASDAQ)")
    scaf.add_argument('--currency', default='USD', help="Currency (default USD)")

    # alert
    al = sub.add_parser('alert', help="Send model trade signal to Telegram and SQLite ledger")
    al.add_argument('--ticker', required=True, help="Stock ticker")
    al.add_argument('--text', required=True, help="Formatted signal message text")
    al.add_argument('--verdict', default='ACTIONABLE_BUY_SIGNAL', help="Verdict type")

    args = parser.parse_args()
    handlers = {
        'status': cmd_status,
        'math': cmd_math,
        'memory': cmd_memory,
        'scaffold': cmd_scaffold,
        'alert': cmd_alert
    }
    handlers[args.command](args)


if __name__ == '__main__':
    main()
