# Phase 11: Dynamic 10 EMA Trailing Runner & Two-Stage Profit Harvesting
**Date:** October 2026  
**Environment:** Isolated Tactical Laboratory (`daytrading/`)  
**Mandate:** Protect the 84.6% Mean-Reversion Crest at Stage 1 | Compound the Remaining 50% Runner Along the 10 EMA (4–12 Days)  

---

## 1. Mathematical & Structural Solution to the "Runner Dilemma"

Our forensic excursion study established two fundamental truths about momentum breakouts:
1. **84.6% of trades that reach Stage 1 (+7.5% to +8.5%) crest before +18.0% and suffer a mean-reverting pullback.** Banking 50% at Stage 1 is essential to lock in cash profits and eliminate round-trip risk.
2. **However, managing the remaining 50% with a fixed +18.0% limit or a rigid 5-day time cutoff leaves massive alpha on the table in two ways:**
   * For the **84.6% crest-and-pullback cohort**, waiting passively for a fixed +18.0% target allows the remaining 50% to fall all the way back to the Breakeven Ratchet (+0.30% USD / 0.00% UK), yielding almost zero second-stage profit.
   * For **multi-day institutional trends** that grind higher steadily over 6 to 12 trading days, a rigid Day 5 time ejection prematurely kills the runner right before the second leg of institutional expansion.

### The Three-Step Harvesting State Machine (`AdaptiveExecutionEngine`)
Implemented in [`daytrading/tools/adaptive_execution_engine.py`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/tools/adaptive_execution_engine.py):

1. **Stage 1 Take-Profit (50% Position Harvest):**
   * **USD Equities / Leveraged ETFs:** Sell 50% between **+7.5% and +8.5%** (or snapped -0.5% below the Options GEX Call Wall).
   * **UK Zero-FX ISA Leaders (`RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`):** Sell 50% at **+5.0% to +5.5%** (0.00% FX drag).
2. **Immediate Breakeven Ratchet:**
   * Upon Stage 1 fill, immediately raise the hard stop on the remaining 50% to **Entry + 0.35%** (USD) or **Entry + 0.05%** (UK), guaranteeing a risk-free runner net of Trading 212 fees.
3. **Stage 2 Dynamic 10-Day EMA / 2-Day Low Trailing Runner (4 to 12 Trading Days):**
   $$\text{Stop}_{\text{Runner}, t} = \max\left(\text{Breakeven Ratchet}, \ \text{EMA}_{10, t}, \ \min(\text{Low}_{t-1}, \text{Low}_{t-2})\right)$$
   * As long as daily close remains above the ascending 10-day EMA, the runner is permitted to compound for **4 to 12 trading days**.
   * When the stock eventually crests and closes below the 10-day EMA (or hits the volatility-scaled Stage 2 limit of +16% to +26%), the remaining 50% is harvested at the elevated trail level (+4% to +22%) rather than falling all the way back to 0.0% breakeven.

---

## 2. Empirical Backtest Results: Fixed +18% / 5D Cutoff vs. 10 EMA Trailing Runner (1,500 Trades)

Executed via `python -B daytrading/tools/adaptive_execution_engine.py --phase3 --save-evidence`. Full JSON telemetry is saved in [`daytrading/evidence/phase11_trailing_runner_results.json`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase11_trailing_runner_results.json).

| Performance Metric (1,500 Breakout Trades) | Fixed +18.0% / Rigid 5-Day Cutoff | Dynamic 10 EMA Trailing Runner (4–12 Days) | Profit Expansion Delta |
| :--- | :---: | :---: | :---: |
| **Total Trades Evaluated** | 1,500 | 1,500 | — |
| **Win Rate (%)** | 64.53% | 64.53% | Identical Entry & Stage 1 Gate |
| **Profit Factor** | **1.693** | **2.477** | **+0.784x Profit Factor Surge** |
| **Net Expectancy / Trade (After FX)** | **+1.378%** | **+2.936%** | **+1.558% / Trade (+113% Increase)** |
| **Average Winner Net (%)** | **+5.215%** | **+7.628%** | **+241.3 bps (+2.41%) per Winner** |
| **Average Loser Net (%)** | -5.603% | -5.603% | Identical Downside Risk Floor |
| **Cumulative 1,500-Trade Net Return** | **+2,067.1%** | **+4,403.3%** | **+2,336.2% Total Alpha Expansion** |

---

## 3. Runner Cohort Breakdown

Across the **968 winning trades** that reached Stage 1 out of 1,500 total setups:
* **Runners Compounded Across 4 to 12 Days (`309 trades`):** High-FCF moats and UK zero-FX leaders rode the ascending 10-day EMA beyond Day 5, capturing +11.5% to +24.0% on the second half instead of being ejected at +4% on Day 5.
* **Pullbacks Harvested Above Breakeven (`659 trades`):** When trades crested at +9.5% to +13.5% and began reversing, the ascending 10 EMA / 2-day low trail locked in **+3.8% to +7.8%** on the runner instead of letting it round-trip all the way down to +0.35% breakeven.
