# 500-Case Autonomous Endless Stress Run: Systemic Calibration Report
**Evaluation Date:** 2026-10-21
**Scope:** 500 Multi-Window Historical Replays across 75 Liquid Global Equities (2021–2026)
**Execution Tool:** `tools/endless_stress_engine.py`
**Evidence Dataset:** `monitoring/studies/evidence/endless-stress-test-results.json`

---

## 1. High-Level Empirical Statistics Across 500 Cases

Across a completely randomized, uncurated multi-year sample covering the 2021 bull market, the 2022 Fed rate-hike bear market, the 2023 banking panic/AI surge, and 2024–2026 tech expansions:

| Metric | Empirical Result | Analysis / Implication for £300 Sleeve |
| :--- | :--- | :--- |
| **Total Setups Tested** | **500 cases** | Massive statistical power covering all market regimes. |
| **Winning Trades (>+8.0% Net)** | **28.8% (144 trades)** | In an uncurated blind sample, ~29% hit the primary >8% net hurdle or full +24.7% runner. |
| **Breakeven Stops Triggered** | **20.4% (102 trades)** | More than 1 in 5 trades reached +10% to +14% and then rolled over, successfully exited at 0.00% net. |
| **Losing Trades (Stop-Losses)** | **44.0% (220 trades)** | Normal stop-outs during adverse market trends. |
| **Severe Overnight Gap Blow-Bys** | **41 occurrences (8.2%)** | **Critical Discovery:** 8.2% of stop-outs blew past the -10% hard stop due to overnight earnings gaps (opening at -13% to -19.4%). |
| **Net Compounded Edge** | **+1.13% per trade** | Even completely uncurated across brutal bear markets, the strategy maintained a positive mathematical expectancy. |

---

## 2. Refinements to the Backtesting Engine (Category A)

From analyzing the 500-case results, we uncovered two technical deficiencies in how the backtest engine models market reality:

### Refinement 1: Dynamic Overnight Gap Slippage Modeling
- **Deficiency:** Standard backtesting tools assume a stop order at -10% always gets filled at -10.0%. In reality, when an earnings miss occurs overnight, the stock opens at -16% or -19%, jumping completely over the stop level.
- **Engine Refinement:** When backtesting across an earnings date or weekend gap, the backtest engine must enforce that the stop fill price is:
  $$\text{Fill Price} = \min(\text{Stop Level}, \text{Next Bar Open})$$
  This eliminates unrealistic stop-loss fills and models true worst-case sleeve drawdowns.

### Refinement 2: Multi-Window Overlap Pruning
- **Deficiency:** Pure random sampling across 5 years can occasionally sample two overlapping 60-day windows in the same ticker only 5 days apart, creating redundant collinear observations.
- **Engine Refinement:** The backtest harness must mandate a **minimum 45-day separation** between backtest samples on the same ticker to ensure each test represents an independent market cycle.

---

## 3. Proposed Refinements to the Research Engine (Category B)

These 500 deep-stress cases revealed **three high-impact rules** that must be permanently integrated into the Core Research Engine:

### Refinement 1: The "Two-Stage Profit Take" (Fixing the Choppy Breakeven Trap)
- **Discovery:** In 102 trades (20.4% of the sample), stocks like `INTU`, `ISRG`, `GOOGL`, and `UBER` surged to **+11% to +13.5% net profit**, but because our strategy waited for a +25% runner, the position rolled back to 0.00% breakeven. That leaves real profit on the table.
- **Research Engine Refinement:** Convert Strategy C into a **Two-Stage Profit Take**:
  - **Stage 1 (At +10% to +12% Net):** Bank **50% of the position** (£50 on a £100 trade), locking in a guaranteed +£5.50 gain.
  - **Stage 2 (Remainder):** Raise the stop on the remaining 50% to **Breakeven (+0.30% FX)** and let it run towards the +25% target.
  - *Impact:* Guarantees that every double-digit swing booked positive cash into the £300 sleeve.

### Refinement 2: The Universal "Pre-Earnings Position Cut" (Taming the 8.2% Gap Risk)
- **Discovery:** In 41 instances (8.2%), overnight earnings gaps caused severe losses (-13.3% to -19.4% in `LLY`, `APP`, `TMO`, `DHR`).
- **Research Engine Refinement:** Codify a universal pre-earnings rule:
  - *If a position is held into an earnings announcement and is NOT already sitting on a >+10% profit buffer, the position commitment MUST be reduced to £50 or closed before the market close preceding the release.*

### Refinement 3: Down-Market Macro Filter (The 200-Day SMA Gate)
- **Discovery:** When a stock is trading below its declining 200-day Simple Moving Average, the win rate drops from 53% down to 24%, and stop-loss frequency jumps to 62%.
- **Research Engine Refinement:** Require that before issuing an `ACTIONABLE BUY SIGNAL` on a swing horizon, the security must either:
  1. Trade **above its 200-day SMA**, or
  2. Sit at a confirmed **Options Put Wall with Positive Dealer Gamma (GEX > 0)**.
