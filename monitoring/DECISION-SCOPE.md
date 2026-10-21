# £300 Model Portfolio Sleeve — Decision Scope & Risk Rules

This document defines the active operational scope for the isolated £300 Trading 212 Stocks ISA Model Sleeve. Along with `AGENTS.md` and `CLAUDE.md`, it supersedes any legacy "observation-only nonactionable" or "10-gate checkpoint" restrictions.

## 1. Mandate & Execution Boundary
- **Capital**: £300.00 GBP isolated model sleeve inside Aidan's Trading 212 Stocks ISA (no leverage, no margin, isolated from long-term holdings).
- **Execution**: The assistant acts as the **Model Portfolio Signal Generator** and delivers structured trade alerts via Telegram (`tools/observation.py` / `tools/observation_transport.py`). Aidan retains 100% personal discretion and manually reviews and places all orders in Trading 212.

## 2. Portfolio & Risk Rules
- **Position Sizing**: Max **£100.00 GBP per idea** (33.3% of sleeve; max 3 concurrent positions), unless a 2-tranche (£150) or 4-tranche (£75) exception is explicitly justified.
- **Holding Horizon**: Days to a few months (catalyst / swing horizon; no intraday trading).
- **Transaction Friction Hurdle**: Explicitly account for Trading 212's **0.15% FX fee** on non-GBP stocks (**0.30% round-trip**), bid-ask spread, and realistic manual execution delay (15 minutes to several hours).
- **Minimum Return Hurdle**: Base-case expected return over the holding window must exceed **>8% net of fees/FX**, with an asymmetric upside-to-downside ratio (**>2:1**).
- **Mandatory Exit Controls**: Every BUY signal must specify:
  1. **Max Entry Price Ceiling** (above which the trade is passed/waited on),
  2. **Hard Price Stop-Loss** (or explicit priced-loss limit),
  3. **Thesis-Invalidation / Catalyst-Failure Exit Trigger**, and
  4. **Time-Exit Reassessment Date**.

## 3. Analytical & Red-Team Requirements
A Short-Horizon Opportunity Dossier does not require regenerating a 5-year PDF/Excel package, but must rigorously cover:
1. **Security & Accounting Bridge**: Exact listing/ISIN/currency, statutory GAAP/IFRS vs. management-adjusted figures, recurring owner cash flow (stripping one-off windfalls), SBC, lease obligations, and net debt/claims bridge.
2. **Catalyst & Market Expectations**: How the catalyst changes fundamental cash flows vs. what is already priced into the current share price.
3. **Mandatory Adversarial Challenge (Astra Red-Team)**: Dedicated section attacking the bull case, testing catalyst delays, and verifying why the setup beats holding cash after FX/spread friction.

## 4. Output Contract
Every Short-Horizon Opportunity Dossier must conclude with one of three verdicts:
1. **ACTIONABLE BUY SIGNAL**: Ready-to-send Telegram alert payload (`Ticker/ISIN`, `Max Buy Price`, `GBP Commitment out of £300`, `Estimated Shares`, `Catalyst & Timeline`, `Stop-Loss`, `Thesis-Exit`, `Time-Exit Date`).
2. **WATCH / LIMIT TRIGGER**: Business/catalyst setup is valid, but current price is too high. Specify the exact entry price ceiling where risk/reward becomes attractive (>8% net return, >2:1 upside/downside).
3. **PASS / REJECT**: Concise explanation of why the catalyst, accounting quality, or risk/reward fails.
