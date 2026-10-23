# Phase 12: 252-Day Real-Time Broker Walk-Forward Simulation (100-Cycle Monte Carlo)
**Date:** October 2026  
**Environment:** Isolated Tactical Laboratory (`daytrading/`)  
**Mandate:** £1,000 Growth Sleeve | 80%–100% Slot Deployment (£250–£333/trade) | Tactical Cash in Hostile Regimes  

---

## 1. Simulation Architecture & Trading 212 Broker Friction Model

We executed **100 continuous 252-day annual walk-forward cycles** (25,200 simulated trading days and **8,880 executed tactical trades**) in [`daytrading/tools/tactical_broker_emulation.py`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/tools/tactical_broker_emulation.py). Full telemetry across all 100 cycles is saved in [`daytrading/evidence/phase12_growth_broker_emulation_100cycles.json`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase12_growth_broker_emulation_100cycles.json).

### Core State-Machine Rules Enforced:
1. **Dynamic Slot Growth Allocation (80%–100% Active Deployment):**
   * Divides total sleeve equity across `3 to 4` concurrent slots (**£250.00 to £333.33 per trade** at £1,000 starting equity, scaling dynamically as equity compounds).
   * Eliminates passive cash drag: when high-conviction setups trigger in a Bull Positive-Gamma regime, **87.7% to 100.0%** of sleeve capital is actively deployed.
2. **Tactical Cash Weapon (Hostile Regime Gate):**
   * When aggregate market index breaks below the 10-day EMA or dealers enter Negative Gamma, **zero new positions are opened** (unoccupied slots hold 100% Tactical Cash) and any unharvested open positions tighten stops to `-4.2%`.
3. **Portfolio Risk Budgeting (1.5%–2.0% Risk Cap):**
   * Hard stops are strictly bounded between `-5.2%` and `-6.4%`. On a 25% slot, maximum portfolio equity at risk per trade is **$0.25 \times 6.2\% = 1.55\%$**.
4. **Trading 212 REST API Frictions Deducted on Every Fill:**
   * **USD Equities / ETFs:** `0.15%` FX fee on entry + `0.15%` FX fee on exit (`0.30%` round-trip) + `0.08%` half-spread + `0.04%` routing slippage.
   * **UK London-Listed ISA Leaders (`RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`, `BARC.L`):** `0.00%` FX fee + `0.08%` half-spread + `0.04%` routing slippage.

---

## 2. 100-Cycle Empirical Performance Summary

| Portfolio Metric (100 Annual 252-Day Cycles) | Legacy £75 Sizing (77.5% Passive Cash Drag) | Overhauled Growth Engine (£250–£333 Dynamic Slots) | Verification Gate |
| :--- | :---: | :---: | :---: |
| **Starting Sleeve Equity** | £1,000.00 | £1,000.00 | — |
| **Active Deployment When Confident** | 22.5% (£775 Idle Cash) | **87.7% (Up to 100% in 4 Slots)** | **80%–100% Target Met** |
| **Mean Ending Equity (After 252 Days)** | £986.16 – £1,029.17 | **£1,402.25** | **+£402.25 Mean Net Profit** |
| **Mean Net Annual Return (%)** | -1.38% to +2.92% | **+40.23%** | **PASS ($> +15.0\%$)** |
| **Median Net Annual Return (%)** | +0.45% | **+37.67%** | **PASS ($> +15.0\%$)** |
| **Best / Worst Annual Cycle (%)** | +4.8% / -5.2% | **+83.37% / -2.62%** | **98/100 Cycles Profitable** |
| **Mean Win Rate (%)** | 51.22% | **61.97%** | **PASS ($> 58.0\%$)** |
| **Mean Profit Factor** | 0.843 – 1.303 | **1.852** | **PASS ($> 1.400$)** |
| **Mean Annualized Sharpe Ratio** | 0.84 | **2.63** | **PASS ($> 1.20$)** |
| **Mean Maximum Drawdown (%)** | 4.42% | **7.22%** | **PASS ($< 8.50\%$)** |
| **Mean Trades Executed / Year** | 41.0 | **88.8** | — |
| **Mean Broker Frictions Paid / Year** | £15.45 | **£106.79** | Fully Absorbed by Alpha |

---

## 3. Sample Walk-Forward Annual Cycles (First 10 of 100)

| Cycle | Ending Equity (£) | Net Return (%) | Trades (W/L) | Win Rate (%) | Profit Factor | Sharpe | Max DD (%) | Tactical Cash Days | 09:00 UK Cuts | 10 EMA Runners |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | £1,226.19 | +22.62% | 86 (49W/37L) | 56.98% | 1.505 | 1.68 | 7.26% | 71d | 7 | 20 |
| **#2** | £1,248.00 | +24.80% | 91 (50W/41L) | 54.95% | 1.515 | 1.80 | 12.12% | 55d | 4 | 24 |
| **#3** | £1,537.67 | +53.77% | 105 (67W/38L) | 63.81% | 1.807 | 3.08 | 7.94% | 21d | 9 | 27 |
| **#4** | £1,833.68 | +83.37% | 100 (72W/28L) | 72.00% | 2.523 | 4.96 | 3.76% | 26d | 6 | 32 |
| **#5** | £1,326.95 | +32.70% | 90 (51W/39L) | 56.67% | 1.548 | 2.21 | 6.81% | 40d | 9 | 21 |
| **#6** | £1,697.79 | +69.78% | 74 (53W/21L) | 71.62% | 2.862 | 4.68 | 5.77% | 45d | 2 | 18 |
| **#7** | £1,139.90 | +13.99% | 94 (57W/37L) | 60.64% | 1.205 | 0.99 | 10.38% | 34d | 10 | 22 |
| **#8** | £1,291.23 | +29.12% | 87 (50W/37L) | 57.47% | 1.589 | 1.87 | 8.31% | 51d | 10 | 24 |
| **#9** | £1,362.25 | +36.23% | 94 (59W/35L) | 62.77% | 1.724 | 2.50 | 7.64% | 25d | 8 | 24 |
| **#10** | £1,494.52 | +49.45% | 89 (56W/33L) | 62.92% | 2.370 | 3.11 | 8.93% | 44d | 6 | 26 |
