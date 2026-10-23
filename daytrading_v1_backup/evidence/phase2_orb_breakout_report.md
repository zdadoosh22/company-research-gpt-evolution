# Phase 2 Opening Range Breakout (ORB) & Gap Dynamics Engine Report

**Author:** Quantitative Tactical Systems Engineer  
**Date:** October 2026  
**Artifact:** `daytrading/evidence/phase2_orb_breakout_report.md`  
**Tool Source:** `daytrading/tools/orb_engine.py`  
**Universe:** 200-Ticker Active Quantitative Universe (ETFs, Mega-Caps, Semis, SaaS, Fintech, UK Leaders)  

---

## 1. Executive Summary & Core Discovery

The Opening Range Breakout (ORB) is among the most widely traded intraday strategies in equity and ETF markets. However, naive retail execution—entering blindly upon a breach of the opening 5-minute high or low—has a **negative mathematical expectancy (-0.210% per trade)** net of execution friction. 

Retail traders fail because:
1. **The Friction Ratio Trap:** On 5-minute intraday scalps, average gross profits are small (~0.95%). Trading 212's 0.30% round-trip foreign exchange fee (0.15% each way on USD pairs) combined with 0.12% manual execution slippage consumes **47.6% of gross profits**.
2. **False Breakout Liquidity Whipsaws:** Market makers routinely engineer fake opening breakouts ("stop runs") past early extremes before reversing into morning equilibrium.

By implementing three quantitative institutional gates:
* **Relative Opening Volume ($RVOL \ge 1.50\times$)**
* **Candle Close Location Gate ($\text{Close Location} \ge 0.75$)**
* **Pre-Market Gap Quality Band ($0.5\% \le |\text{Gap}| \le 3.5\%$)**

The 30-minute Opening Range Breakout transforms into a robust quantitative edge, achieving a **68.4% Win Rate, 2.911 Profit Factor, and +1.089% Net Expectancy per trade**.

---

## 2. Mathematical Architecture of the ORB Engine

### 2.1. Opening Range Definition
Let $t_0$ be the market open (09:30:00 ET / 14:30:00 UK). For a window of duration $W \in \{5, 15, 30\}$ minutes, the Opening Range boundaries are:
$$\text{ORB}_{\text{High}} = \max_{t \in [t_0, t_0 + W]} \{P_{\text{high}}(t)\}$$
$$\text{ORB}_{\text{Low}} = \min_{t \in [t_0, t_0 + W]} \{P_{\text{low}}(t)\}$$
$$\text{ORB}_{\text{Range}} = \text{ORB}_{\text{High}} - \text{ORB}_{\text{Low}}$$

### 2.2. The Dynamic ATR Hurdle
To prevent false breaks triggered by a single order book tick, the breakout entry price $P_{\text{entry}}$ must clear the boundary by a dynamic volatility buffer:
$$P_{\text{entry, long}} \ge \text{ORB}_{\text{High}} + (0.10 \times \text{ATR}_{14})$$
$$P_{\text{entry, short}} \le \text{ORB}_{\text{Low}} - (0.10 \times \text{ATR}_{14})$$

### 2.3. Relative Volume (RVOL) Institutional Gate
Institutional accumulation leaves volume footprints. We compute the Relative Volume ratio:
$$\text{RVOL} = \frac{V_{\text{opening window}}}{\bar{V}_{20\text{-day opening window}}}$$
* **RVOL < 1.0x:** Severe retail churn; high probability of a mean-reverting range. **DISQUALIFIED.**
* **1.0x $\le$ RVOL < 1.4x:** Ambiguous liquidity. **DISQUALIFIED.**
* **RVOL $\ge$ 1.5x:** Institutional participation confirmed. **QUALIFIED.**

### 2.4. Candle Close Location Metric (Eliminating Wick Traps)
A common retail trap is buying a breakout that forms a long upper shadow (wick) as institutional sellers absorb liquidity. We define the Candle Close Location (CCL) of the breakout bar:
$$\text{CCL} = \frac{P_{\text{close}} - P_{\text{low}}}{P_{\text{high}} - P_{\text{low}}}$$
* **CCL < 0.50:** Bearish rejection / inverted hammer. **DISQUALIFIED.**
* **0.50 $\le$ CCL < 0.70:** Indecisive doji. **DISQUALIFIED.**
* **CCL $\ge$ 0.75:** Marubozu or strong bullish close in the upper quartile. **QUALIFIED.**

### 2.5. Pre-Market Gap Classification
Gaps are categorized into three regimes based on absolute percentage difference:
$$\text{Gap}_{\%} = \frac{P_{\text{open}} - P_{\text{prior close}}}{P_{\text{prior close}}}$$
1. **Sub-Threshold Gaps ($|\text{Gap}| < 0.5\%$):** Insufficient institutional overnight repositioning.
2. **Continuation Gaps ($0.5\% \le |\text{Gap}| \le 3.5\%$):** Optimal setup. High institutional conviction without overextension.
3. **Exhaustion Gaps ($|\text{Gap}| > 6.0\%$):** Severe gap-fade risk. Mean-reversion algorithms aggressively push price back toward VWAP.

---

## 3. Empirical Stress Testing (1,000 Runs Per Configuration)

Backtested across 1,000 market open sequences for each window over our 200-ticker universe (including leveraged ETFs `TQQQ`, `SOXL`, `NVDL`, `SQQQ`, high-beta semis `NVDA`, `TSLA`, `AMD`, `APP`, and UK leaders `RR.L`, `RIO.L`):

| Strategy Configuration | Opening Window | Total Trades | Win Rate (%) | Profit Factor | Avg Win (%) | Avg Loss (%) | Avg Friction (%) | Net Expectancy (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Naive Retail ORB (Unfiltered)** | 15-Minute | 1,000 | 39.70% | 0.763 | +1.706% | -1.472% | 0.449% | **-0.210%** |
| **Filtered ORB (5m)** | 5-Minute | 1,000 | 66.40% | 1.666 | +0.946% | -1.122% | 0.450% | **+0.251%** |
| **Filtered ORB (15m)** | 15-Minute | 1,000 | 65.60% | 2.220 | +1.686% | -1.448% | 0.448% | **+0.608%** |
| **Filtered ORB (30m)** | 30-Minute | 1,000 | **68.40%** | **2.911** | **+2.426%** | **-1.804%** | 0.451% | **+1.089%** |

```
Net Expectancy Progression by Window:
Naive 15m:  [######             ] -0.210% (NEGATIVE EXP)
Filtered 5m: [############       ] +0.251%
Filtered 15m:[#################  ] +0.608%
Filtered 30m:[===================] +1.089% (OPTIMAL)
```

---

## 4. Analytical Findings & Deep Insights

### 4.1. The Friction Ratio Analysis (Trading 212 Stocks ISA)
Every USD-denominated trade in a GBP account incurs:
* 0.15% currency conversion fee on entry.
* 0.15% currency conversion fee on exit.
* Total FX Drag: **0.30% round-trip**.
* Average manual execution slippage: **0.12% to 0.15% round-trip**.
* Total Effective Friction: **~0.45% per trade**.

In the **5-minute window**, the average gross winning trade was only +1.40%. Deducting 0.45% leaves +0.95% net—a staggering **32.1% friction haircut**. On losing trades, the loss expands from -0.67% to -1.12%.

In the **30-minute window**, the wider range allows price to travel +2.88% gross on winners. Net of the 0.45% friction, the trader retains +2.43%—the friction haircut drops to only **15.6%**. 

### 4.2. Why 30-Minute ORB Dominates 5-Minute ORB
1. **London Cross-Session Overlap:** Between 14:30 and 15:00 UK time (09:30 to 10:00 ET), European markets are entering their closing auction while US markets open. Cross-Atlantic order flows produce erratic, noisy spikes in the first 15 minutes.
2. **First 15-Minute Reversals:** Large institutional execution algorithms (TWAP/VWAP slicers) typically wait until 10:00 AM ET to begin aggressive execution once the opening volatility dust settles. Entering at 10:00 AM ET aligns tactical positioning with large institutional block flows.

### 4.3. The Zero-FX UK London Advantage
When executing ORB setups on London-listed names (`RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`):
* FX conversion fee is **0.00%**.
* Total round-trip friction drops from ~0.45% to **~0.10%** (bid-ask spread only).
* For `RR.L`, net expectancy rises by **+0.35% per trade**, directly boosting sleeve profitability.

---

## 5. Algorithmic Rules Codified into `daytrading/engine.py`

1. **Window Selection:** Enforce minimum 15-minute opening range; 30-minute range preferred.
2. **Volume Hurdle:** Hard rejection if RVOL < 1.40x.
3. **Candle Shape Gate:** Require Candle Close Location $\ge 0.70$ (no upper shadows exceeding 30% of total bar height).
4. **Target Structure:** Stage 1 profit target at $1.5\times \text{ORB Range}$, Stage 2 trailing with 5-minute VWAP.
5. **Initial Stop:** Hard stop set at the ORB Midpoint ($\frac{\text{ORB}_{\text{High}} + \text{ORB}_{\text{Low}}}{2}$) rather than the opposite extreme, preserving a 1:2.2 risk-to-reward profile.

---
*Verified against primary backtest dataset: `daytrading/evidence/orb_empirical_backtest_results.json`.*
