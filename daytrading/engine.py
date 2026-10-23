"""Master Quantitative Day Trading & Tactical Swing Engine CLI.
Isolated Tactical Trading Laboratory: daytrading/engine.py

Commands:
  scan                  Scans active Volatility Squeeze, ORB, and VWAP setups across universe
  bracket               Calculates exact two-stage take-profit and stop orders (£150 / 15% sizing)
  gex <ticker>          Outputs options dealer gamma structure, Call/Put walls, Max Pain & Pin strikes
  decay <ticker>        Calculates leveraged ETF volatility decay drag over N holding days
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
import math
from pathlib import Path
import subprocess
import sys
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add tools directory to path
TOOLS_DIR = Path(__file__).resolve().parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    from orb_engine import UNIVERSE_200, FLAT_UNIVERSE, get_profile
    from options_gex_tactical_engine import OptionsGEXTacticalEngine
    from leveraged_etf_decay_engine import LeveragedETFDecayEngine
    from dual_factor_tactical_fused import FUNDAMENTAL_PROFILES
    from adaptive_execution_engine import AdaptiveExecutionEngine, get_ticker_sector
    from dynamic_universe_screener import DynamicUniverseScreener
    from t212_execution_daemon import LiveExecutionDaemon
except ImportError:
    pass


def _yahoo_opener():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=4)
    except Exception:
        pass
    crumb = ""
    try:
        crumb = opener.open('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=4).read().decode('utf-8').strip()
    except Exception:
        pass
    return opener, crumb


def cmd_scan(args):
    """Scans liquid momentum leaders, leveraged ETFs, and UK leaders for tactical setups via DynamicUniverseScreener."""
    top_n = getattr(args, 'top', 25)
    max_comp = getattr(args, 'max_compression', 6.0)
    min_rvol = getattr(args, 'min_rvol', 1.40)
    output_json = getattr(args, 'json', False)

    screener = DynamicUniverseScreener()
    results = screener.run_dynamic_scan(max_compression=max_comp, min_rvol=min_rvol, top_n=top_n)

    if output_json:
        print(json.dumps(results, indent=2))
        return

    print("\n" + "=" * 115)
    print("        DYNAMIC INSTITUTIONAL LIQUIDITY & VOLATILITY SQUEEZE SCREENER (TRADING 212 ISA)")
    print("=" * 115)
    print(f"{'Ticker':<7} | {'Sector / Cluster':<18} | {'Spot':<9} | {'5D Band':<8} | {'RVOL':<7} | {'$ Vol/Day':<13} | {'Status / Signal'}")
    print("-" * 115)

    for r in results:
        status = "[!] " + r["disqualification_reason"]
        if r["is_passed"]:
            status = "[+] SQUEEZE BREAKOUT (QUALIFIED)"
            if r["is_uk"]:
                status += " [0% FX UK ANCHOR]"

        curr_symbol = "£" if r["is_uk"] else "$"
        spot_str = f"{curr_symbol}{r['spot']:.2f}"
        dvol_str = f"{curr_symbol}{r['dollar_volume']:,.0f}" if r["dollar_volume"] > 0 else "N/A"
        band_str = f"{r['compression_pct']:.1f}%" if r["compression_pct"] > 0 else "N/A"
        rvol_str = f"{r['rvol']:.2f}x" if r["rvol"] > 0 else "N/A"

        print(f"{r['ticker']:<7} | {r.get('sector', 'UNKNOWN'):<18} | {spot_str:<9} | {band_str:<8} | {rvol_str:<7} | {dvol_str:<13} | {status}")

    print("=" * 115)
    passed_count = sum(1 for r in results if r["is_passed"])
    print(f"[*] Evaluated dynamic liquid universe. Actionable Setups Found: {passed_count}/{len(results)}.\n")


def cmd_bracket(args):
    """Calculates adaptive dynamic bracket orders, volatility-normalized targets, and extended-hours gap risk."""
    spot = float(args.price)
    portfolio = float(args.portfolio)
    slots = max(1, int(args.slots))
    if args.budget is not None:
        budget = float(args.budget)
    else:
        # Full Growth Deployment: divide sleeve equity equally across active slots
        budget = round(portfolio / slots, 2)
    fx_rate = float(args.fx)
    ticker = args.ticker.upper() if args.ticker else "EQUITY"

    adaptive_engine = AdaptiveExecutionEngine()
    bracket = adaptive_engine.calculate_dynamic_bracket(ticker, spot=spot, budget=budget, fx_rate=fx_rate)
    gap_risk = adaptive_engine.evaluate_extended_hours_gap_risk(
        ticker, spot=spot, pre_market_price=args.pre_market, overnight_catalyst=args.catalyst
    )

    active_tickers = [t.strip().upper() for t in args.active_slots.split(",") if t.strip()] if getattr(args, 'active_slots', None) else []
    corr_audit = adaptive_engine.validate_portfolio_correlation(active_tickers, ticker, max_slots=slots)

    sym = "£" if bracket["is_uk"] else "$"
    risk_gbp = budget * abs(bracket["stop_loss_pct"]) / 100.0
    portfolio_risk_pct = (risk_gbp / max(1.0, portfolio)) * 100.0
    blended_target_pct = (bracket["stage_1_pct"] * 0.5) + (bracket["stage_2_pct"] * 0.5)
    rr_ratio = blended_target_pct / max(0.1, abs(bracket["stop_loss_pct"]))

    print("\n" + "=" * 74)
    print(f"       TACTICAL ADAPTIVE BRACKET & GROWTH SLOT EXECUTION PLAN")
    print("=" * 74)
    if args.ticker:
        fx_desc = "Zero-FX UK ISA Edge (0.00% FX)" if bracket["is_uk"] else "USD Pair (0.30% Round-Trip FX)"
        print(f"Ticker Asset       : {ticker} [{fx_desc}]")
    print(f"Sector / Cluster   : {corr_audit['candidate_sector']} (Active in sector: {corr_audit['active_sector_count']}/2 | 3x ETFs: {corr_audit['active_3x_etfs_count']}/1)")
    print(f"Correlation Gate   : {corr_audit['status']}")
    if not corr_audit["is_allowed"]:
        print(f"  |-- [!] CONCENTRATION BLOCKED : {corr_audit['violation_reason']}")
    if not corr_audit["uk_anchor_satisfied"]:
        print(f"  |-- [!] UK ANCHOR DEFICIT     : {corr_audit['uk_anchor_note']}")
    print(f"Spot Entry Price   : {sym}{spot:.2f} | 14D ATR: {bracket['atr_14_pct']:.2f}% | Vol: {bracket['daily_vol_pct']:.2f}%")
    print(f"Growth Sleeve Pool : £{portfolio:.2f} | Active Slot Sizing: £{budget:.2f} ({budget/portfolio*100:.1f}% / {slots} Slots)")
    print(f"Position Units     : ~{bracket['shares']} units @ {sym}{spot:.2f} | Blended R:R = 1:{rr_ratio:.2f}")
    print("-" * 74)
    print(f"Dynamic Hard Stop  : {sym}{bracket['stop_loss_price']:.2f} ({bracket['stop_loss_pct']:+.1f}% | Risk: £{risk_gbp:.2f} = {portfolio_risk_pct:.2f}% of Sleeve)")
    if bracket['put_wall_note'] != "None":
        print(f"  |-- Anchor Note   : {bracket['put_wall_note']}")
    print(f"Stage 1 Target(50%): {sym}{bracket['stage_1_take_profit']:.2f} (+{bracket['stage_1_pct']:.1f}% | Bank 50% = +£{(budget * 0.5 * bracket['stage_1_pct']/100):.2f})")
    if bracket['call_wall_note'] != "None":
        print(f"  |-- Snapping Note : {bracket['call_wall_note']}")
    print(f"Breakeven Ratchet  : Upon Stage 1 hit, raise stop on remaining 50% to {sym}{bracket['breakeven_ratchet']:.2f}")
    print(f"Stage 2 Target(50%): {sym}{bracket['stage_2_take_profit']:.2f} (+{bracket['stage_2_pct']:.1f}% | Bank 50% = +£{(budget * 0.5 * bracket['stage_2_pct']/100):.2f})")
    print("-" * 72)
    print(f"Adaptive Horizon   : {bracket['horizon_plan']['recommended_horizon']} (Desire Window)")
    print(f"Horizon Soft Limit : {bracket['horizon_plan']['hard_limit']}")
    print(f"Runner Trail Rule  : {bracket['horizon_plan'].get('runner_trail_rule', 'Trail along 10 EMA')}")
    print(f"Can Extend Past 5D?: {'YES (Allow runner to compound if above 10 EMA)' if bracket['horizon_plan']['can_extend_past_5d'] else 'NO (Compounding decay limit on 3x products)'}")
    print(f"Horizon Rationale  : {bracket['horizon_plan']['rationale']}")
    print("-" * 72)
    regime_info = adaptive_engine.evaluate_4state_market_regime(index_spot=495.0, index_ema_10=490.0)
    print(f"Macro 4-State Reg. : {regime_info['regime_state']} (Target Cash: {regime_info['target_cash_pct']:.0f}% | Deployment: {regime_info['target_deployment_pct']:.0f}%)")
    if 'risk_parity_sizing' in bracket:
        rp = bracket['risk_parity_sizing']
        print(f"Vol-Target Risk Sz : £{rp['allocated_budget_gbp']:.2f} (Portfolio Risk: £{rp['actual_risk_gbp']:.2f} = {rp['actual_portfolio_risk_pct']:.2f}% of Sleeve)")
    print(f"Overnight Gap Risk : {gap_risk['gap_risk_score']}/100 [{gap_risk['protocol']}]")
    print(f"Extended-Hours T212: {gap_risk['action_guidance']}")
    print("=" * 72 + "\n")


def cmd_gex(args):
    """Outputs options dealer gamma structure, walls, and pinning strikes."""
    ticker = args.ticker.upper()
    spot = args.spot
    
    # If spot not provided, attempt quick fetch
    if spot is None:
        opener, _ = _yahoo_opener()
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1m"
            raw = json.loads(opener.open(url, timeout=4).read().decode('utf-8'))
            closes = raw['chart']['result'][0]['indicators']['quote'][0]['close']
            valid_c = [c for c in closes if c is not None]
            spot = valid_c[-1] if valid_c else 135.0
        except Exception:
            spot = 135.0 if ticker in ["NVDA", "SMCI"] else (220.0 if ticker == "TSLA" else 480.0)

    engine = OptionsGEXTacticalEngine()
    gex_data = engine.simulate_strike_chain(spot, vol=0.38, dte=args.dte)

    print("\n" + "=" * 65)
    print(f"       OPTIONS DEALER GAMMA (GEX) STRUCTURE: {ticker}")
    print("=" * 65)
    print(f"Current Spot Price : ${spot:.2f}")
    print(f"Days to Expiration : {args.dte} DTE")
    print(f"Call Wall (Ceiling): ${gex_data['call_wall']:.2f}")
    print(f"Put Wall (Support) : ${gex_data['put_wall']:.2f}")
    print(f"Max Pain Strike    : ${gex_data['max_pain']:.2f} (Magnetic OPEX Pin)")
    print(f"Gamma Flip Line    : ${gex_data['gamma_flip']:.2f} (Zero-Line Barrier)")
    print(f"Total Net GEX ($)  : ${gex_data['total_net_gex_usd']:,.2f} per 1% move")
    print(f"Regime             : {gex_data['regime']}")
    print("-" * 65)
    if gex_data['regime'] == "POSITIVE_GAMMA_PINNING":
        print("[!] POSITIVE GAMMA: High mean reversion. Expect tight range pinning to Max Pain.")
    else:
        print("[!] NEGATIVE GAMMA: High directional velocity. Breakouts accelerate rapidly.")
    print("=" * 65 + "\n")


def cmd_decay(args):
    """Calculates leveraged ETF compounding decay over N days."""
    ticker = args.ticker.upper()
    days = args.days
    
    # Identify beta
    if ticker in ["TQQQ", "SOXL", "UPRO", "TECL", "FNGU", "BULZ", "LABU", "TNA", "DFEN", "DPST", "YINN"]:
        beta = 3.0
    elif ticker in ["NVDL", "CONL", "ERX", "CWEB"]:
        beta = 2.0
    elif ticker in ["SQQQ", "SOXS", "SPXU", "TECS", "FNGD", "BERZ", "LABD", "TZA", "SDOW", "FAZ", "YANG"]:
        beta = -3.0
    elif ticker in ["ERY", "KOLD", "BOIL"]:
        beta = -2.0
    else:
        beta = 3.0 # Default assumption

    prof = get_profile(ticker)
    annual_vol = prof["vol"] * math.sqrt(252)

    engine = LeveragedETFDecayEngine()
    res = engine.calculate_discrete_decay(beta=beta, annual_vol=annual_vol, days=days, drift=0.0)

    print("\n" + "=" * 65)
    print(f"     LEVERAGED ETF VOLATILITY DECAY CALCULATOR: {ticker}")
    print("=" * 65)
    print(f"Leverage Multiplier: {beta:+.1f}x")
    print(f"Realized Volatility: {res['annual_vol_pct']:.1f}% Annualized")
    print(f"Holding Horizon    : {days} Trading Days")
    print(f"Compounding Drag   : {res['decay_drag_pct']:+.3f}% (Beta-Slippage Cost)")
    print(f"Max Hold Ceiling   : 5 Trading Days (Hard Time Exit Rule)")
    print("-" * 65)
    if beta < 0:
        print("[!] CAUTION: Inverse ETF decays at 2x the rate of a Bull ETF (6 * sigma^2).")
        print("    Holding inverse ETFs past 3-5 days in chop destroys capital geometrically.")
    print("=" * 65 + "\n")


def cmd_live(args):
    """Launches or queries the Trading 212 REST API Practice Execution Daemon."""
    from t212_execution_daemon import main as daemon_main
    # Pass along sys.argv without the 'live' command
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    daemon_main()


def cmd_ui(args):
    """Launches the Aegis Cyber-Institutional Trading War Room Web Dashboard."""
    ui_script = Path(__file__).resolve().parent / "ui" / "serve_dashboard.py"
    port = getattr(args, 'port', 8765)
    no_browser = getattr(args, 'no_browser', False)
    
    cmd = [sys.executable, str(ui_script), "--port", str(port)]
    if no_browser:
        cmd.append("--no-browser")
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description="Master Quantitative Tactical Day Trading Engine")
    sub = parser.add_subparsers(dest='command', required=True)

    # scan
    s = sub.add_parser('scan', help="Scan active Squeeze, ORB, and VWAP setups across dynamic universe")
    s.add_argument('--top', type=int, default=25, help="Top N candidates to display (default 25)")
    s.add_argument('--max-compression', type=float, default=6.0, help="Maximum 5-day bandwidth pct (default 6.0)")
    s.add_argument('--min-rvol', type=float, default=1.40, help="Minimum RVOL threshold (default 1.40)")
    s.add_argument('--json', action='store_true', help="Output raw JSON telemetry")

    # bracket
    b = sub.add_parser('bracket', help="Calculate adaptive dynamic bracket orders and horizon plan")
    b.add_argument('--price', type=float, required=True, help="Current spot entry price")
    b.add_argument('--ticker', type=str, default="", help="Ticker symbol (e.g. NVDA, SOXL, RR.L)")
    b.add_argument('--budget', type=float, default=None, help="GBP commitment (default derived from slots or £250)")
    b.add_argument('--portfolio', type=float, default=1000.0, help="Total tactical sleeve equity (default £1000)")
    b.add_argument('--slots', type=int, default=3, help="Max concurrent trade slots for growth deployment (default 3 slots = 33.3%% per trade)")
    b.add_argument('--fx', type=float, default=0.7465, help="GBP per 1 USD (default 0.7465)")
    b.add_argument('--pre-market', type=float, default=None, help="Pre-market quote price (if active)")
    b.add_argument('--catalyst', action='store_true', help="Flag if overnight binary catalyst is active (FOMC/Earnings)")
    b.add_argument('--active-slots', type=str, default="", help="Comma-separated active tickers (e.g. 'TQQQ,NVDA') to verify correlation limits")

    # gex
    g = sub.add_parser('gex', help="Calculate live options dealer gamma structure and walls")
    g.add_argument('ticker', type=str, help="Ticker symbol (e.g. NVDA, TSLA, SPY)")
    g.add_argument('--spot', type=float, default=None, help="Spot price (optional, auto-fetched if omitted)")
    g.add_argument('--dte', type=int, default=3, help="Days to expiration (default 3)")

    # decay
    d = sub.add_parser('decay', help="Calculate leveraged ETF volatility decay drag")
    d.add_argument('ticker', type=str, help="Leveraged/Inverse ETF symbol (e.g. TQQQ, SOXL, SQQQ)")
    d.add_argument('--days', type=int, default=5, help="Holding duration in trading days (default 5)")

    # live
    sub.add_parser('live', help="Trading 212 REST API Practice Execution Daemon and Supervisor")

    # ui
    u = sub.add_parser('ui', help="Launch Aegis Cyber Trading War Room Dashboard")
    u.add_argument('--port', type=int, default=8765, help="Local port (default 8765)")
    u.add_argument('--no-browser', action='store_true', help="Do not automatically open browser")

    args, unknown = parser.parse_known_args()
    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'bracket':
        cmd_bracket(args)
    elif args.command == 'gex':
        cmd_gex(args)
    elif args.command == 'decay':
        cmd_decay(args)
    elif args.command == 'live':
        cmd_live(args)
    elif args.command == 'ui':
        cmd_ui(args)


if __name__ == '__main__':
    main()
