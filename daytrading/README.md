# Day Trading & Short-Horizon Quantitative Tactical Engine (0-7 Day Horizon)
**Project Authority & Mandate Document**
**Workspace Location:** `C:\Users\aidan\Documents\Company research 2\daytrading\`

---

## 1. Core Purpose & Mission
This engine is completely isolated from the long-term fundamental research engine. It operates with a mandate for:
- **Intraday to Multi-Day Swing Trades:** Max hold time is **1 hour to 5 trading days (strictly <= 1 calendar week)**.
- **Instrument Scope:** Highly liquid US & UK equities, large-cap momentum leaders, and **leveraged/inverse ETFs**:
  - Leveraged Bullish: `TQQQ` (3x Nasdaq), `SOXL` (3x Semis), `UPRO` (3x S&P), `NVDL` (2x Nvidia), `CONL` (2x Coinbase).
  - Inverse/Hedged: `SQQQ` (3x Inverse Nasdaq), `SOXS` (3x Inverse Semis), `SPXU` (3x Inverse S&P).
  - High-Beta Momentum: `NVDA`, `TSLA`, `AMD`, `PLTR`, `ARM`, `SMCI`, `COIN`, `APP`.
- **Trading 212 ISA Execution Guardrails:**
  - Cash-only ISA (no margin debt, long-only or inverse ETF long).
  - FX fee accounting: 0.15% per trade (0.30% round-trip) on non-GBP pairs.
  - Position sizing: £50 to £100 tranches out of tactical cash allocations.

---

## 2. Core Quantitative Pillars
Unlike fundamental accounting engines, this engine is driven by:
1. **Intraday & Multi-Day VWAP (Volume-Weighted Average Price):** Institutional benchmark deviation.
2. **Opening Range Breakout (ORB) & Gap Dynamics:** 15-minute / 30-minute range expansion and gap-fill probabilities.
3. **ATR Volatility Bands & Mean Reversion (Bollinger/Keltner):** Measuring extreme 2.5-sigma intraday extensions.
4. **Options Gamma Pins & Dealer Liquidity Sweeps:** Live Max Pain, Call/Put Walls, and Net GEX acceleration.
5. **Leveraged ETF Volatility Decay Modeling:** Math for geometric drag over 2-5 day holding periods.

---

## 3. Strict Execution Architecture
- Every signal must possess:
  - Exact Entry Trigger (Limit / Stop-Limit on Breakout).
  - Dynamic ATR-based Stop Loss.
  - Multi-Stage Profit Take (50% at 1.5R, 50% runner at 3.0R with breakeven stop).
  - Hard Time-Exit (Auto-close after 5 trading days if target/stop not reached).
