# Phase 9: High-Conviction Setup Identification & Scanner Calibration
**Date:** October 2026  
**Environment:** Isolated Tactical Laboratory (`daytrading/`)  
**Mandate:** Aggressive Capital Growth (80%–100% Slot Deployment) | Win Rate $\ge 62\%$ Verification  

---

## 1. Architectural Rationale: Why 80%–100% Deployment Requires Pristine Entry Gates

Under the **Aggressive Capital Growth Mandate**, our £1,000 Trading 212 Stocks ISA tactical sleeve does not hold passive cash cushions—external liquidity reserves exist outside this trading pool. When setups trigger, the engine deploys **80% to 100% of capital across 3 to 4 active slots** (£250.00 to £333.33 per trade).

Deploying 25% to 33.3% of portfolio equity into a single tactical position requires eliminating low-quality "noise" breakouts. In our previous unfiltered baseline (`5D Range <= 7.0%`, `Volume Surge >= 1.25x`), initial continuation win rates hovered at **52.00%** with a Profit Factor of **1.020** and net expectancy of just **+0.052%** per trade after Trading 212's 0.30% round-trip FX fee.

To achieve institutional compounding velocity without scaling drawdowns, we upgraded [`daytrading/engine.py`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/engine.py) and [`daytrading/tools/volatility_squeeze_engine.py`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/tools/volatility_squeeze_engine.py) with five strict quantitative gates:

1. **Tight Compression Bandwidth Gate ($\le 6.0\%$):**
   $$\frac{\text{High}_{5D} - \text{Low}_{5D}}{\text{Spot}} \le 6.0\%$$
   Forces the engine to enter *only* during genuine multi-day volatility coils (Bollinger Band inside Keltner Channel compression) rather than chasing extended mid-range chop.
2. **Institutional Volume Surge Gate ($\ge 1.50\times$):**
   $$\text{RVOL}_{10D} = \frac{\text{Volume}_{t}}{\text{SMA}_{10}(\text{Volume})} \ge 1.50\times$$
   Eliminates thin retail head-fakes by requiring institutional participation on the breakout bar.
3. **10-Day EMA Structural Trend Gate:**
   $$\text{Close}_{t} > \text{High}_{5D} \quad \land \quad \text{Close}_{t} \ge \text{EMA}_{10}$$
   Ensures breakouts align with the underlying multi-day institutional trend.
4. **Forensic Accounting Disqualification Gate:**
   Hard exclusion of speculative dilution traps, negative recurring FCF burner stocks, and accounting-risk names (`SMCI`, `MSTR`, `MRNA`, `CRSP`, `MARA`, `RIOT`).
5. **UK London-Listed Zero-FX ISA Overweighting:**
   Systematically prioritizes liquid UK FTSE leaders (`RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`, `BARC.L`) that execute in GBP with **0.00% FX fee** inside a Trading 212 Stocks ISA, saving 30 bps of guaranteed round-trip drag per trade.

---

## 2. Empirical Backtest Results (1,000 Trade Setups)

Both the Legacy Unfiltered Scanner and the Phase 1 High-Conviction Scanner were stress-tested across **1,000 breakout trade sequences** in [`daytrading/tools/volatility_squeeze_engine.py`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/tools/volatility_squeeze_engine.py). Full telemetry is saved in [`daytrading/evidence/phase9_high_conviction_results.json`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase9_high_conviction_results.json).

| Performance Metric | Legacy Unfiltered Scanner (`<=7.0%`, `>=1.25x`) | Phase 1 High-Conviction Scanner (`<=6.0%`, `>=1.50x`) | Structural Delta |
| :--- | :---: | :---: | :---: |
| **Total Setups Evaluated** | 1,000 | 1,000 | — |
| **Initial Continuation Win Rate (%)** | **52.00%** | **67.70%** | **+15.70% (Target $\ge 62\%$ Met)** |
| **Winning / Losing Setups** | 520W / 480L | 677W / 323L | +157 Net Winners |
| **Profit Factor** | **1.020** | **2.666** | **+1.646x Expansion** |
| **Avg Net Return / Trade (After FX)** | **+0.052%** | **+2.687%** | **+2.635% / Trade** |
| **Avg Winner Net (%)** | +5.041% | +6.351% | +1.310% |
| **Avg Loser Net (%)** | -5.352% | -4.992% | +0.360% (Tighter Loss Control) |
| **UK Zero-FX Share (%)** | 26.5% | 56.1% | +29.6% Zero-FX Allocation |
| **UK Zero-FX Win Rate (%)** | 51.70% | **68.98%** | **+17.28%** |
| **US USD Pair Win Rate (%)** | 52.11% | **66.06%** | **+13.95%** |

---

## 3. Gate Rejection Telemetry

During the 1,000-trade High-Conviction scan, the multi-gate filter actively protected capital by rejecting **5,441 suboptimal candidate setups**:
* **Forensic Traps Disqualified:** `816` candidate setups blocked (`SMCI`, `MSTR`, `MARA`, `RIOT`).
* **Wide-Range Chop Rejected (`> 6.0%` 5D Range):** `2,192` extended/loose setups blocked.
* **Low-Volume Head-Fakes Rejected (`< 1.50x` RVOL):** `2,433` thin-volume breakouts blocked.

> [!IMPORTANT]
> **Key Takeaway:** By filtering out 84.4% of noisy candidate bars and demanding `Range <= 6.0%` + `RVOL >= 1.50x` + `Close >= 10 EMA`, the initial continuation probability jumps from **52.00% to 67.70%**, providing the statistical foundation required to deploy £250–£333 slots safely.
