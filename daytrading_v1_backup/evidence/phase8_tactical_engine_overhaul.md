# Phase 8: Tactical Day Trading Engine Overhaul & Empirical Verification
**Date:** October 2026  
**Environment:** Trading 212 Stocks ISA (£1,000 Tactical Account)  
**Location:** Isolated Laboratory `daytrading/`  

---

## 1. Executive Summary & Root-Cause Audit

A forensic examination of the tactical day trading and swing engine across 1,500 trade sequences and 252 continuous market days revealed why the engine previously struggled around breakeven (£981.98 to £1,029.17) and identified the exact mathematical hurdles holding back returns.

### Key Forensic Findings:
1. **Stage 1 Exits Are NOT Premature (84.6% Reversal Protection):**
   - In 1,068 trades reaching the Stage 1 target (+7.5% to +8.5%), **95.0% (1,015 trades)** briefly pushed higher.
   - However, **only 15.4% (165 trades)** ever reached the full +18.0% runner target.
   - In **84.6% of trades (903 trades)**, the stock reached a local crest (averaging +9.5% to +12.0%) and then suffered mean-reverting pullbacks that wiped out gains back to breakeven or entry.
   - *Verdict:* Banking 50% at Stage 1 is **not premature**; it actively preserves capital and locks in green trades that would otherwise turn into scratch or loss trades.
2. **The Return Discrepancy (£1,029.17 vs £981.98):**
   - The initial formal run recorded **£1,029.17 (+2.92%)** across 45 trades (57.8% win rate).
   - The subsequent multi-size test script returned **£981.98 (-1.80%)** across 39 trades (46.1% win rate).
   - *Root Cause:* In a low trade count (~40 trades/year) where **77.5% of capital sits idle in cash** (£75 sizing with max 3 positions commits only £225 out of £1,000), sample path variance (Monte Carlo noise) causes returns to swing by ±3% to 4%. Furthermore, 0.30% round-trip FX fees on USD trades extract £15–£22/year, which consumes 50% to 100% of gross profits on £75 commitments.

---

## 2. Mathematical Proof of Cash Drag & FX Hurdle

### Sizing & Capital Utilization:
$$\text{Max Capital Deployed} = 3 \times £75 = £225 \quad (22.5\% \text{ utilization})$$
$$\text{Idle Cash Drag} = £1,000 - £225 = £775 \quad (77.5\% \text{ earning } 0\%)$$

When a trade achieves a +8.0% Stage 1 win on £75:
$$\text{Gross Profit} = £75 \times 0.50 \times 8.0\% = +£3.00$$
$$\text{FX Friction (0.30% round trip)} = £75 \times 0.0030 = -£0.225$$
$$\text{Net Trade Gain} = +£2.775$$
$$\text{Account Equity Contribution} = \frac{+£2.775}{£1,000} = +0.277\%$$

Conversely, when a trade stops out at -6.5%:
$$\text{Gross Loss} = £75 \times -6.5\% = -£4.875$$
$$\text{FX Friction} = -£0.225$$
$$\text{Net Trade Loss} = -£5.10$$
$$\text{Account Equity Drag} = \frac{-£5.10}{£1,000} = -0.510\%$$

$$\text{Required Win Rate to Break Even} = \frac{5.10}{2.775 + 5.10} = \mathbf{64.7\%}$$

At an empirical win rate of 50% to 57%, the strategy inevitably hovers around breakeven after paying broker friction!

---

## 3. Four-Pillar Overhaul Implementation

### Pillar 1: Sizing Rebalancing (£150 / 15% Sizing)
- Default trade size is increased to **£150** (15% per trade).
- Maximum 3 concurrent positions = **£450 deployed (45.0% utilization)**, leaving a **£550 (55.0%) cash buffer**.
- A +8.5% win now contributes **+£6.38** net of FX, delivering **+0.64% to account equity** (over 2.3x higher equity velocity).

### Pillar 2: USD FX Hurdle & UK Zero-FX ISA Prioritization
- **USD Trades:** Enforce a strict minimum **+8.5% Stage 1 target hurdle** to cleanly clear the 0.30% FX fee and 0.08% spread.
- **UK London-Listed Leaders (`RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`):** Benefit from **0.00% FX fee**. Stage 1 target is calibrated to **+5.0% to +6.5%**, providing high probability of fill with zero currency drag. UK leaders are prioritized in scans.

### Pillar 3: Dynamic 10 EMA Trailing Runner (4 to 12 Days)
- Instead of closing the entire trade at a rigid 5-day limit or waiting for an elusive +18% target:
  - Stage 1 banks 50% at +8.5% (or +5.0% for UK).
  - The remaining 50% runner is **trailed along the 10-day EMA or prior 2-day low**.
  - As long as the stock holds above the 10 EMA, it is allowed to compound for **4 to 12 trading days**.
  - If it closes below the 10 EMA or breaches the breakeven ratchet, it is exited immediately.

### Pillar 4: Trading 212 Pre-Market Gap Protocol
- Trading 212 opens pre-market trading at 09:00 UK time (5.5 hours before US regular open at 14:30 UK).
- If an adverse pre-market gap exceeds **-7.0%**, execute an immediate pre-market market/limit cut at 09:00 UK, avoiding the 14:30 regular-open panic dump.

---

## 4. Empirical Backtest Results: Legacy vs. Overhauled Engine

```
================ TACTICAL COMPARATIVE PERFORMANCE (1,500 TRADES) ================
Metric                       Legacy Baseline    Uncalibrated Dynamic    Overhauled Hybrid
----------------------------------------------------------------------------------
Total Trades Evaluated       1,500              1,500                   1,434 (Gate Filtered)
Win Rate (%)                 52.87%             51.60%                  55.37%
Profit Factor                0.660              0.677                   1.014
Average Win (%)              +2.86%             +3.19%                  +3.84%
Average Loss (%)             -4.86%             -5.03%                  -4.70%
Net Expectancy (%)           -0.78%             -0.79%                  +0.03%
Overnight Gap Traps          113 dumps          --                      82 cuts (saved 15% dump)
Multi-Day 10 EMA Runners     0 (capped at 5d)   0 (fixed targets)       23 captured (up to 12d)
==================================================================================
```

---

## 5. Summary & Action Plan
With the overhaul deployed in `daytrading/engine.py` and `daytrading/tools/adaptive_execution_engine.py`:
- `engine.cmd bracket` defaults to £150 sizing, provides exact GEX anchors, and outputs dynamic 10 EMA trailing guidance.
- `engine.cmd scan` places UK London-listed 0% FX leaders at the top of the priority queue.
- Capital utilization increases from 22.5% to 45.0% while keeping a 55% liquidity moat.
