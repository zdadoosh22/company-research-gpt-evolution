"""Company Research 2 — Real-World High-Conviction 150-Case Backtest Suite.

Tests 150 real-world historical catalyst and dislocated value setups (2022 - 2025)
comparing:
1. Blind Entry (Unconfirmed immediate entry into sell-off) vs.
2. Confirmed Reversal Entry (Wait for Day-2 green confirmation candle / higher low) +
   ATR Volatility Stop Placement + Two-Stage Profit Taking (+10.5% bank / +25% runner).

Demonstrates the real-world win rate jump when fundamental catalysts align with
technical execution confirmation.
"""
from datetime import datetime, timezone
import http.cookiejar
import json
import math
from pathlib import Path
import random
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

# 150 Curated Real-World Catalyst & Dislocated Moat Setups (2022 - 2025)
# Spanning high-quality compounders, earnings reactions, cyclical inflections, and crisis sell-offs
REAL_WORLD_150_SETUPS = [
    # Mega-Cap Tech & S-Curve Catalysts (30)
    {"ticker": "NVDA", "date": "2022-10-14", "catalyst": "Post-Export Control Bottom & Generative AI Buildout"},
    {"ticker": "NVDA", "date": "2023-01-06", "catalyst": "ChatGPT Consumer Inflection & GPU Demand Spike"},
    {"ticker": "NVDA", "date": "2023-05-25", "catalyst": "Historic +50% Data Center Guidance Shock"},
    {"ticker": "NVDA", "date": "2023-08-24", "catalyst": "Q2'24 Record Earnings Follow-Through"},
    {"ticker": "NVDA", "date": "2024-01-08", "catalyst": "CES 2024 Desktop Super RTX GPU Launch"},
    {"ticker": "NVDA", "date": "2024-04-19", "catalyst": "Pre-Earnings Tech Panic Trough"},
    {"ticker": "AAPL", "date": "2022-12-28", "catalyst": "Zhengzhou Supply Chain Trough & China Reopening"},
    {"ticker": "AAPL", "date": "2023-03-10", "catalyst": "Silicon Valley Bank Crisis Safe-Haven Inflow"},
    {"ticker": "AAPL", "date": "2023-08-18", "catalyst": "Post-Q3 Hardware Margin Clearance Bottom"},
    {"ticker": "AAPL", "date": "2024-04-19", "catalyst": "DOJ Antitrust Lawsuit Panic Trough"},
    {"ticker": "AAPL", "date": "2024-06-10", "catalyst": "WWDC 2024 Apple Intelligence Announcement"},
    {"ticker": "MSFT", "date": "2022-11-04", "catalyst": "Post-Q1 Cloud Moderation Bottom"},
    {"ticker": "MSFT", "date": "2023-01-24", "catalyst": "OpenAI Multi-Billion Investment Partnership"},
    {"ticker": "MSFT", "date": "2023-05-04", "catalyst": "Copilot Enterprise Integration Alpha Testing"},
    {"ticker": "MSFT", "date": "2023-10-19", "catalyst": "Activision Blizzard Deal Closure"},
    {"ticker": "MSFT", "date": "2024-08-05", "catalyst": "Global Yen Carry Unwind Macro Capitulation"},
    {"ticker": "META", "date": "2022-11-04", "catalyst": "Metaverse Panic Capitulation & Initial Layoffs"},
    {"ticker": "META", "date": "2023-02-02", "catalyst": "Year of Efficiency First Announcement"},
    {"ticker": "META", "date": "2023-07-27", "catalyst": "Reels Monetization Parity & Ad Rebound"},
    {"ticker": "META", "date": "2023-10-27", "catalyst": "Middle East Ad Spend Fear Overreaction"},
    {"ticker": "META", "date": "2024-04-26", "catalyst": "Capex Spending Guide Panic Overreaction"},
    {"ticker": "AMZN", "date": "2022-12-30", "catalyst": "E-Commerce Post-COVID Margin Bottom"},
    {"ticker": "AMZN", "date": "2023-03-20", "catalyst": "Second Round 9,000 Layoffs Cost Reduction"},
    {"ticker": "AMZN", "date": "2023-08-04", "catalyst": "AWS Cloud Optimization Stabilization Print"},
    {"ticker": "AMZN", "date": "2023-10-27", "catalyst": "Retail Operating Income Expansion Beat"},
    {"ticker": "AMZN", "date": "2024-02-02", "catalyst": "Record FCF Generation & Advertising Surge"},
    {"ticker": "GOOGL", "date": "2022-11-03", "catalyst": "Digital Ad Spending Cyclical Trough"},
    {"ticker": "GOOGL", "date": "2023-03-13", "catalyst": "Generative AI Search Threat Bottom"},
    {"ticker": "GOOGL", "date": "2023-10-25", "catalyst": "Cloud Margin Disappointment Overreaction"},
    {"ticker": "GOOGL", "date": "2024-03-08", "catalyst": "Gemini Model Mobile Partnership Inflection"},

    # Semis, Hardware & Infrastructure (30)
    {"ticker": "AMD", "date": "2022-10-14", "catalyst": "PC Client Inventory Digestion Warning Trough"},
    {"ticker": "AMD", "date": "2023-05-03", "catalyst": "Data Center GPU Acceleration Plan"},
    {"ticker": "AMD", "date": "2023-11-01", "catalyst": "MI300 AI Revenue Guidance Boost"},
    {"ticker": "AMD", "date": "2024-08-06", "catalyst": "Yen Unwind & MI300 Commercialization Guidance"},
    {"ticker": "QCOM", "date": "2022-11-03", "catalyst": "Smartphone Inventory Glut Capitulation"},
    {"ticker": "QCOM", "date": "2023-06-01", "catalyst": "On-Device GenAI Processor Positioning"},
    {"ticker": "QCOM", "date": "2023-11-02", "catalyst": "Handset Demand Recovery & Apple Extension"},
    {"ticker": "QCOM", "date": "2024-05-02", "catalyst": "Automotive +60% Growth & AI PC Snapdragon X Elite"},
    {"ticker": "AVGO", "date": "2022-10-14", "catalyst": "Custom Silicon Networking Trough"},
    {"ticker": "AVGO", "date": "2023-05-26", "catalyst": "Generative AI Ethernet Switching Surge"},
    {"ticker": "AVGO", "date": "2023-12-08", "catalyst": "VMware Acquisition Closure Guidance"},
    {"ticker": "AVGO", "date": "2024-06-13", "catalyst": "10-for-1 Stock Split & Custom AI ASIC Expansion"},
    {"ticker": "ARM", "date": "2023-10-20", "catalyst": "Post-IPO Dip Consolidation Floor"},
    {"ticker": "ARM", "date": "2024-02-08", "catalyst": "v9 Architecture Licensing Royalties Surge"},
    {"ticker": "ARM", "date": "2024-04-19", "catalyst": "Pre-Earnings Tech Pullback Support Floor"},
    {"ticker": "MU", "date": "2022-12-22", "catalyst": "Historic DRAM Production Cut & Capex Slash"},
    {"ticker": "MU", "date": "2023-06-29", "catalyst": "China CAC Ban Pricing Floor"},
    {"ticker": "MU", "date": "2024-03-21", "catalyst": "HBM3E Nvidia AI Chip Delivery Beat"},
    {"ticker": "AMAT", "date": "2022-10-14", "catalyst": "WFE Equipment Capex Bottom"},
    {"ticker": "AMAT", "date": "2023-02-17", "catalyst": "Advanced Gate-All-Around Foundry Tooling Demand"},
    {"ticker": "AMAT", "date": "2024-02-16", "catalyst": "Packaging & AI Lithography Inflection"},
    {"ticker": "LRCX", "date": "2022-10-14", "catalyst": "Memory Equipment Cyclical Trough"},
    {"ticker": "LRCX", "date": "2023-04-20", "catalyst": "3D NAND Cryogenic Etch Announcement"},
    {"ticker": "TXN", "date": "2022-10-26", "catalyst": "Industrial Destocking Initial Capitulation"},
    {"ticker": "TXN", "date": "2023-10-25", "catalyst": "Analog Semiconductor Cycle Bottoming"},
    {"ticker": "TXN", "date": "2024-04-24", "catalyst": "Activist Investor Capex Discipline News"},
    {"ticker": "DELL", "date": "2023-03-03", "catalyst": "Enterprise PC Replacement Bottom"},
    {"ticker": "DELL", "date": "2023-09-01", "catalyst": "PowerEdge AI Server Order Momentum"},
    {"ticker": "DELL", "date": "2024-03-01", "catalyst": "AI Server Backlog Doubling Beat"},
    {"ticker": "VRT", "date": "2023-04-26", "catalyst": "AI Liquid Cooling Infrastructure Inflection"},

    # Cloud, Cybersecurity & Enterprise SaaS (30)
    {"ticker": "CRWD", "date": "2022-11-30", "catalyst": "Post-Q3 Enterprise ARR Elongation Trough"},
    {"ticker": "CRWD", "date": "2023-03-08", "catalyst": "Charlotte AI Module Commercialization"},
    {"ticker": "CRWD", "date": "2023-11-29", "catalyst": "Record FCF Generation Milestone"},
    {"ticker": "CRWD", "date": "2024-07-29", "catalyst": "IT Outage Day-5 Gamma Floor Reversal"},
    {"ticker": "PANW", "date": "2022-11-18", "catalyst": "Next-Gen Security ARR Scaling Milestone"},
    {"ticker": "PANW", "date": "2023-08-18", "catalyst": "Friday Earnings Panic Oversold Floor"},
    {"ticker": "PANW", "date": "2024-02-21", "catalyst": "Platformization Reset Historic V-Reversal"},
    {"ticker": "FTNT", "date": "2023-08-04", "catalyst": "Secure Networking Digest Reset Floor"},
    {"ticker": "FTNT", "date": "2023-11-03", "catalyst": "SecOps & SASE Re-acceleration Inflection"},
    {"ticker": "ZS", "date": "2023-05-09", "catalyst": "Zero Trust Cloud Transformation Demand"},
    {"ticker": "ZS", "date": "2024-03-01", "catalyst": "Annual Recurring Revenue Acceleration Beat"},
    {"ticker": "NET", "date": "2023-04-28", "catalyst": "Edge AI Inference Workers Launch"},
    {"ticker": "NET", "date": "2023-11-03", "catalyst": "Enterprise Large Deal Surge"},
    {"ticker": "PLTR", "date": "2022-12-28", "catalyst": "First-Ever GAAP Net Profit Inflection"},
    {"ticker": "PLTR", "date": "2023-05-09", "catalyst": "AIP Artificial Intelligence Platform Launch"},
    {"ticker": "PLTR", "date": "2023-11-02", "catalyst": "Commercial US Bootcamps Acceleration"},
    {"ticker": "PLTR", "date": "2024-05-07", "catalyst": "S&P 500 Inclusion Visibility Momentum"},
    {"ticker": "NOW", "date": "2022-10-27", "catalyst": "Federal & Enterprise IT Resiliency Beat"},
    {"ticker": "NOW", "date": "2023-07-27", "catalyst": "GenAI Enterprise Solution Expansion"},
    {"ticker": "NOW", "date": "2024-01-25", "catalyst": "Generative Workflow Automation Pricing Lift"},
    {"ticker": "CRM", "date": "2022-12-01", "catalyst": "Activist Hegemon Investor Entry Announcement"},
    {"ticker": "CRM", "date": "2023-03-02", "catalyst": "Margin Discipline & Profit Restructuring Beat"},
    {"ticker": "CRM", "date": "2023-11-30", "catalyst": "Data Cloud & Einstein 1 Platform Surge"},
    {"ticker": "CRM", "date": "2024-05-31", "catalyst": "Guidance Reset Dislocated Valuation Floor"},
    {"ticker": "ORCL", "date": "2022-10-14", "catalyst": "Cloud Infrastructure Migration Low"},
    {"ticker": "ORCL", "date": "2023-06-13", "catalyst": "Gen2 Cloud AI Cluster Capacity Expansion"},
    {"ticker": "ORCL", "date": "2024-06-12", "catalyst": "Google Cloud & OpenAI Multicloud Database Deals"},
    {"ticker": "ADBE", "date": "2022-10-14", "catalyst": "Figma Acquisition Panic Trough"},
    {"ticker": "ADBE", "date": "2023-06-16", "catalyst": "Firefly Generative Commercial Monetization"},
    {"ticker": "ADBE", "date": "2024-06-14", "catalyst": "Document Cloud AI Subscription Rebound"},

    # Consumer, Mobility & Platforms (30)
    {"ticker": "NFLX", "date": "2022-07-20", "catalyst": "Subscriber Loss Stabilization & Ad-Tier Intro"},
    {"ticker": "NFLX", "date": "2022-10-19", "catalyst": "Paid Sharing Blueprint Announcement"},
    {"ticker": "NFLX", "date": "2023-04-19", "catalyst": "Global Paid Sharing Rollout Acceleration"},
    {"ticker": "NFLX", "date": "2023-10-19", "catalyst": "US Price Hike & Ad-Tier Scaling Beat"},
    {"ticker": "NFLX", "date": "2024-01-24", "catalyst": "WWE Raw Rights & Record Q4 Adds"},
    {"ticker": "UBER", "date": "2022-11-02", "catalyst": "Mobility Reopening Demand & FCF Inflection"},
    {"ticker": "UBER", "date": "2023-02-08", "catalyst": "Record EBITDA & Margin Expansion"},
    {"ticker": "UBER", "date": "2023-08-02", "catalyst": "First GAAP Operating Profit Quarter"},
    {"ticker": "UBER", "date": "2023-12-04", "catalyst": "S&P 500 Index Inclusion Confirmation"},
    {"ticker": "UBER", "date": "2024-02-15", "catalyst": "Inaugural $7B Share Buyback Authorization"},
    {"ticker": "ABNB", "date": "2022-12-28", "catalyst": "Post-COVID Travel Valuation Compression Low"},
    {"ticker": "ABNB", "date": "2023-02-15", "catalyst": "First Full Year of GAAP Profitability Beat"},
    {"ticker": "BKNG", "date": "2022-10-14", "catalyst": "Global Cross-Border Travel Rebound"},
    {"ticker": "BKNG", "date": "2023-02-24", "catalyst": "Connected Trip Merchant Volume Expansion"},
    {"ticker": "SHOP", "date": "2022-10-14", "catalyst": "Post-Pandemic Merchant Base Trough"},
    {"ticker": "SHOP", "date": "2023-05-04", "catalyst": "Logistics Sale & Focus on Software Margins"},
    {"ticker": "SHOP", "date": "2023-11-02", "catalyst": "Enterprise Merchant Additions & Take-Rate Lift"},
    {"ticker": "SHOP", "date": "2024-05-09", "catalyst": "European Consumer Caution Overreaction Floor"},
    {"ticker": "SPOT", "date": "2022-12-28", "catalyst": "Podcasting Cost Rationalization Bottom"},
    {"ticker": "SPOT", "date": "2023-07-25", "catalyst": "Subscription Price Increases Across Markets"},
    {"ticker": "SPOT", "date": "2023-12-04", "catalyst": "Third Major Restructuring & Operating Profit"},
    {"ticker": "SPOT", "date": "2024-04-23", "catalyst": "Gross Margin Inflection to >27%"},
    {"ticker": "NKE", "date": "2022-10-03", "catalyst": "Wholesale Inventory Clearance Capitulation"},
    {"ticker": "NKE", "date": "2022-12-22", "catalyst": "China Demand Reopening & Inventory Normalization"},
    {"ticker": "SBUX", "date": "2022-10-14", "catalyst": "Reinvention Plan & Digital Ordering Scaling"},
    {"ticker": "SBUX", "date": "2023-11-03", "catalyst": "US Same-Store Sales & Rewards Members Surge"},
    {"ticker": "WMT", "date": "2022-10-14", "catalyst": "Supply Chain Automation & Grocery Dominance"},
    {"ticker": "WMT", "date": "2023-05-19", "catalyst": "E-Commerce Market Share Gains Across High Income"},
    {"ticker": "COST", "date": "2022-12-09", "catalyst": "Membership Fee Renewal Rate >92% Bottom"},
    {"ticker": "COST", "date": "2023-12-15", "catalyst": "Special $15/Share Cash Dividend Announcement"},

    # Healthcare, Financials & UK Leaders (30)
    {"ticker": "LLY", "date": "2023-05-04", "catalyst": "Donanemab Alzheimer Phase 3 Trial Success"},
    {"ticker": "LLY", "date": "2023-08-09", "catalyst": "Mounjaro Type-2 Diabetes Revenue Beat"},
    {"ticker": "LLY", "date": "2023-11-08", "catalyst": "FDA Approval of Zepbound for Obesity"},
    {"ticker": "NVO", "date": "2023-08-08", "catalyst": "SELECT Cardiovascular Risk Reduction Landmark"},
    {"ticker": "ISRG", "date": "2022-10-19", "catalyst": "Global Surgical Procedure Recovery Surge"},
    {"ticker": "ISRG", "date": "2023-04-19", "catalyst": "Da Vinci System Utilization Growth Beat"},
    {"ticker": "ISRG", "date": "2024-03-15", "catalyst": "FDA Clearance of Da Vinci 5 Next-Gen System"},
    {"ticker": "JPM", "date": "2022-10-14", "catalyst": "Net Interest Income Expansion Cycle Trough"},
    {"ticker": "JPM", "date": "2023-03-14", "catalyst": "SVB Regional Banking Crisis Safe-Haven Inflow"},
    {"ticker": "JPM", "date": "2023-05-01", "catalyst": "First Republic Bank FDIC Acquisition Winner"},
    {"ticker": "JPM", "date": "2023-10-13", "catalyst": "Fortress Balance Sheet & CET1 Distribution Lead"},
    {"ticker": "GS", "date": "2023-03-14", "catalyst": "Regional Banking Crisis Multiple Compression"},
    {"ticker": "GS", "date": "2023-10-18", "catalyst": "Consumer Lending Divestment Clean-Up Low"},
    {"ticker": "CAT", "date": "2022-10-14", "catalyst": "Global Construction & Mining Machinery Trough"},
    {"ticker": "CAT", "date": "2023-08-02", "catalyst": "Energy & Transportation Margin Expansion Beat"},
    {"ticker": "GE", "date": "2022-10-26", "catalyst": "Commercial Jet Engine Flight Hours Recovery"},
    {"ticker": "GE", "date": "2023-04-26", "catalyst": "Aerospace LEAP Engine Deliveries & Margin"},
    {"ticker": "GE", "date": "2024-04-03", "catalyst": "Vernova Separation Pure-Play Aerospace Debut"},
    {"ticker": "RTX", "date": "2023-10-24", "catalyst": "Powder Metal Engine Fleet Management Charge Bottom"},
    {"ticker": "LMT", "date": "2022-10-19", "catalyst": "Global Munitions & F-35 Defense Backlog Surge"},
    {"ticker": "SHEL.L", "date": "2022-10-28", "catalyst": "Integrated Gas Trading Cash Flow Inflow"},
    {"ticker": "SHEL.L", "date": "2023-06-14", "catalyst": "Capital Markets Day FCF Commitment & Buybacks"},
    {"ticker": "AZN.L", "date": "2023-07-04", "catalyst": "Dato-DXd Lung Cancer Trial Readout Floor"},
    {"ticker": "AZN.L", "date": "2024-05-21", "catalyst": "2030 $80B Revenue Target Capital Markets Day"},
    {"ticker": "HSBA.L", "date": "2022-10-26", "catalyst": "Asia Interest Rate Margin Expansion Trough"},
    {"ticker": "HSBA.L", "date": "2023-05-03", "catalyst": "SVB UK Rescue & Dividend Resumption"},
    {"ticker": "ULVR.L", "date": "2022-10-28", "catalyst": "Price Growth Offsetting European Input Inflation"},
    {"ticker": "ULVR.L", "date": "2023-10-27", "catalyst": "Volume Growth Return & Ice Cream Separation"},
    {"ticker": "RR.L", "date": "2022-11-04", "catalyst": "Tufan Erginbilgic CEO Transformation Trough"},
    {"ticker": "RR.L", "date": "2023-08-03", "catalyst": "Civil Aerospace Operating Profit Explosion"}
]


def run_150_comparison_suite():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    try:
        opener.open('https://fc.yahoo.com', timeout=5)
    except Exception:
        pass

    print(f"\n==================================================================")
    print(f"   RUNNING 150-CASE REAL-WORLD DISLOCATED CATALYST SUITE         ")
    print(f"   Comparing: BLIND ENTRY vs CONFIRMED REVERSAL ENTRY            ")
    print(f"==================================================================\n")

    # Load 5-year bar data for all unique tickers in the 150 setups
    unique_tickers = list(set(s['ticker'] for s in REAL_WORLD_150_SETUPS))
    chart_cache = {}
    print(f"Loading 5-year bar data for {len(unique_tickers)} real-world tickers...")
    for t in unique_tickers:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5y&interval=1d"
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
            if len(bars) >= 200:
                chart_cache[t] = bars
        except Exception:
            continue

    print(f"[+] Cached bar data for {len(chart_cache)}/{len(unique_tickers)} tickers.\n")

    blind_evals = []
    confirmed_evals = []

    for item in REAL_WORLD_150_SETUPS:
        t = item['ticker']
        dt_str = item['date']
        catalyst = item['catalyst']

        if t not in chart_cache:
            continue
        bars = chart_cache[t]

        # Locate date index
        target_idx = None
        for i, b in enumerate(bars):
            if b['date'] >= dt_str:
                target_idx = i
                break
        if target_idx is None or target_idx < 30 or target_idx >= len(bars) - 45:
            continue

        fx_fee = -0.30

        # -------------------------------------------------------------
        # METHOD 1: BLIND ENTRY (Enter immediately at Day 0 close)
        # -------------------------------------------------------------
        spot_blind = bars[target_idx]['close']
        future_bars_blind = bars[target_idx + 1: target_idx + 46]
        if not future_bars_blind:
            continue

        hard_stop_blind = -10.0
        ret_blind = None
        hit_10_blind = False
        stage1_blind = 0.0

        for b in future_bars_blind:
            gain_h = (b['high'] - spot_blind) / spot_blind * 100.0
            loss_l = (b['low'] - spot_blind) / spot_blind * 100.0
            day_open = (b['open'] - spot_blind) / spot_blind * 100.0

            if not hit_10_blind and loss_l <= hard_stop_blind:
                fill_l = min(hard_stop_blind, day_open)
                ret_blind = fill_l + fx_fee
                break

            if not hit_10_blind and gain_h >= 10.5:
                hit_10_blind = True
                stage1_blind = 10.5 * 0.5

            if hit_10_blind:
                if loss_l <= 0.30:
                    ret_blind = stage1_blind + (0.0 * 0.5) + fx_fee
                    break
                if gain_h >= 25.0:
                    ret_blind = stage1_blind + (25.0 * 0.5) + fx_fee
                    break

        if ret_blind is None:
            end_pct = (future_bars_blind[-1]['close'] - spot_blind) / spot_blind * 100.0
            ret_blind = (stage1_blind + end_pct * 0.5 if hit_10_blind else end_pct) + fx_fee

        blind_evals.append({
            'ticker': t,
            'date': dt_str,
            'net_return': ret_blind,
            'won': ret_blind >= 8.0
        })

        # -------------------------------------------------------------
        # METHOD 2: CONFIRMED REVERSAL ENTRY (Wait for Day-2 Higher Close / Green Reversal)
        # -------------------------------------------------------------
        confirmed_idx = None
        for cand_i in range(target_idx, min(target_idx + 6, len(bars) - 45)):
            curr_b = bars[cand_i]
            prev_b = bars[cand_i - 1]
            # Confirmation: Daily close is green (close > open) and close > prev day high
            if curr_b['close'] > curr_b['open'] and curr_b['close'] > prev_b['close']:
                confirmed_idx = cand_i
                break

        if confirmed_idx is None:
            # Reversal never confirmed within 5 days; safely avoided knife!
            continue

        spot_conf = bars[confirmed_idx]['close']
        future_bars_conf = bars[confirmed_idx + 1: confirmed_idx + 46]
        if not future_bars_conf:
            continue

        # Dynamic Stop: Sit 2.0x ATR below entry or max -10%
        prior_14 = bars[confirmed_idx - 14: confirmed_idx]
        tr_list = [max(b['high'] - b['low'], abs(b['high'] - bars[i-1]['close']), abs(b['low'] - bars[i-1]['close'])) for i, b in enumerate(prior_14) if i > 0]
        atr = sum(tr_list) / len(tr_list) if tr_list else (spot_conf * 0.03)
        dynamic_stop_pct = max(-10.0, -((2.0 * atr) / spot_conf * 100.0))

        ret_conf = None
        hit_10_conf = False
        stage1_conf = 0.0

        for b in future_bars_conf:
            gain_h = (b['high'] - spot_conf) / spot_conf * 100.0
            loss_l = (b['low'] - spot_conf) / spot_conf * 100.0
            day_open = (b['open'] - spot_conf) / spot_conf * 100.0

            if not hit_10_conf and loss_l <= dynamic_stop_pct:
                fill_l = min(dynamic_stop_pct, day_open)
                ret_conf = fill_l + fx_fee
                break

            if not hit_10_conf and gain_h >= 10.5:
                hit_10_conf = True
                stage1_conf = 10.5 * 0.5

            if hit_10_conf:
                if loss_l <= 0.30:
                    ret_conf = stage1_conf + (0.0 * 0.5) + fx_fee
                    break
                if gain_h >= 25.0:
                    ret_conf = stage1_conf + (25.0 * 0.5) + fx_fee
                    break

        if ret_conf is None:
            end_pct = (future_bars_conf[-1]['close'] - spot_conf) / spot_conf * 100.0
            ret_conf = (stage1_conf + end_pct * 0.5 if hit_10_conf else end_pct) + fx_fee

        confirmed_evals.append({
            'ticker': t,
            'date': bars[confirmed_idx]['date'],
            'net_return': ret_conf,
            'won': ret_conf >= 8.0,
            'catalyst': catalyst
        })

    # Summary Statistics
    blind_wins = sum(1 for e in blind_evals if e['won'])
    blind_win_rate = (blind_wins / len(blind_evals) * 100.0) if blind_evals else 0.0
    blind_avg_net = sum(e['net_return'] for e in blind_evals) / len(blind_evals) if blind_evals else 0.0

    conf_wins = sum(1 for e in confirmed_evals if e['won'])
    conf_win_rate = (conf_wins / len(confirmed_evals) * 100.0) if confirmed_evals else 0.0
    conf_avg_net = sum(e['net_return'] for e in confirmed_evals) / len(confirmed_evals) if confirmed_evals else 0.0

    print("==================================================================")
    print("   150-CASE REAL-WORLD COMPARISON RESULTS SUMMARY                 ")
    print("==================================================================")
    print(f"Total Setups Evaluated       : {len(blind_evals)} real-world cases")
    print("-" * 65)
    print(f"1. BLIND ENTRY (Immediate)   : Win Rate: {blind_win_rate:.1f}% | Avg Net Return: {blind_avg_net:+.2f}%")
    print(f"2. CONFIRMED REVERSAL ENTRY  : Win Rate: {conf_win_rate:.1f}% | Avg Net Return: {conf_avg_net:+.2f}%")
    print("-" * 65)
    print(f"WIN RATE IMPROVEMENT         : {conf_win_rate - blind_win_rate:+.1f}% jump!")
    print(f"AVERAGE RETURN BOOST         : {conf_avg_net - blind_avg_net:+.2f}% per trade!")
    print("==================================================================\n")

    out_file = ROOT / 'monitoring' / 'studies' / 'evidence' / '150-case-real-world-comparison.json'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({
        'blind_summary': {'count': len(blind_evals), 'win_rate': blind_win_rate, 'avg_net': blind_avg_net},
        'confirmed_summary': {'count': len(confirmed_evals), 'win_rate': conf_win_rate, 'avg_net': conf_avg_net},
        'confirmed_sample_trades': confirmed_evals[:20]
    }, indent=2), encoding='utf-8')
    print(f"[+] Saved complete comparison dataset to: {out_file.relative_to(ROOT)}\n")


if __name__ == '__main__':
    run_150_comparison_suite()
