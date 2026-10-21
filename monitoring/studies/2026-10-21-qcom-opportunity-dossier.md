# Short-Horizon Opportunity Dossier: QCOM (Qualcomm Incorporated)
**As of Date:** 2026-10-21
**Mandate:** £300 Trading 212 ISA Model Sleeve (Max £100.00 commitment; capped at £75.00 for binary earnings gap <=14d)
**Security:** NASDAQ:QCOM (ISIN US7475251036)
**Quote Currency:** USD | **FX Rate:** 0.7467 GBP per USD | **Current Price:** $177.96

---

## 1. Executive Summary & Catalyst Mechanism
- **The Event/Catalyst:** Q4 FY2026 earnings release and conference call scheduled for **Wednesday, November 4, 2026** (at 1:45 PM PT / 4:45 PM ET) — exactly 14 calendar days away.
- **Business Impact:** Market is hypersensitive to two structural inflections:
  1. Handset recovery and AI Snapdragon smartphone processor content gains.
  2. Non-handset diversification acceleration: Automotive revenue jumped +61% YoY in Q3 to $1.6B, and IoT reached $1.8B.
- **Market Expectations vs. Reality:**
  - Q4 Guidance: Revenue $9.7B - $10.5B, Non-GAAP EPS $2.05 - $2.25, GAAP EPS $1.22 - $1.42.
  - At $177.96, QCOM trades at ~18.5x FY26E Non-GAAP EPS and ~21.8x normalized owner FCFE (4.6% FCFE yield). 

---

## 2. Statutory-to-Owner Cash Flow & Valuation Bridge
- **GAAP vs. Non-GAAP Disconnect:** Noticeable spread between GAAP EPS guide ($1.22–$1.42) and Non-GAAP EPS ($2.05–$2.25). The ~$0.83/share quarterly delta consists of:
  - Stock-Based Compensation (SBC): ~$580M–$620M per quarter (~$2.4B annualized). SBC is treated as a real cash-equivalent dilution cost and subtracted from recurring owner earnings.
  - Acquisition-related amortization & restructuring: ~$250M per quarter.
- **Normalized Owner Cash Flow:**
  - Trailing TTM Operating Cash Flow: ~$11.8B.
  - Less CapEx ($1.4B) = Trailing FCF of $10.4B.
  - Deducting economic SBC ($2.4B) yields **$8.0B true recurring owner FCF** (~$7.20/share).
- **Net Debt Bridge:**
  - Cash, cash equivalents, and marketable securities: ~$13.5B.
  - Total carrying debt: ~$15.4B.
  - Net Debt: ~$1.9B (modest leverage, ~0.15x EBITDA).
- **Fair Value Scenario Matrix:**
  - **Bear Case ($145.00):** Handset cyclical weakness re-emerges, Apple modem replacement timeline accelerates, multiple compresses to 15x GAAP earnings (-18.5%).
  - **Base Case ($205.00):** Clean Q4 beat, automotive/IoT diversification reaches >35% of QCT, FY27 guidance confirms low-double-digit EPS growth (+15.2%).
  - **Bull Case ($240.00):** AI PC Snapdragon X Elite volume surge, premium handset cycle expansion (+34.8%).

---

## 3. Trading 212 Sleeve Economics, Options Positioning & Hurdle Check
*Calculated using `tools/engine.py math` and `tools/engine.py options`:*
- **Current Share Price:** $177.96
- **Options & Dealer Gamma Positioning (Expiry 2026-10-23 & 2026-11-06):**
  - Spot: $177.96 | Max Pain: $177.50 (-0.3% from spot — pinned right at pin strike).
  - Put/Call OI Ratio: 0.62 (Call-heavy). Top Call Walls at $180.00 and $185.00. Top Put Wall at $177.50 / $175.00.
  - Net Dealer GEX: +$6.24M per 1% move (**Positive Gamma / Stabilizing**). Market makers are dampening volatility between $175 and $180 into the monthly cycle.
  - Implied Move into earnings: ~$\pm$6.5% to 8.0%.
- **Sleeve Sizing & Gap Rule:** 14 days to earnings triggers the **£75.00 4-tranche cap** to guard against overnight earnings gaps.
- **Hurdle Analysis at $177.96:**
  - Commitment: £75.01 (0.5636 shares).
  - Break-even: $178.49 (+0.30% to clear Trading 212 FX fee).
  - Base Target ($205.00): Net £86.14 (+£11.14 / +14.85% net).
  - Hard Stop ($164.00, below post-Q3 low support): Net £68.91 (-£6.09 / -8.12% net).
  - Upside-to-Downside Ratio: **1.83:1** (Fails >2:1 hurdle requirement at market price).
- **Strict Entry Ceiling Solve:** **$177.13** (or **$175.00** round at the top Put Wall) to achieve >2:1 asymmetry.

---

## 4. Mandatory Adversarial Challenge (Astra Red-Team)
- **The Binary Earnings Gap Trap:** Backtest calibration on QCOM demonstrates that while the company routinely hits midpoints, post-earnings reactions are volatile ($\pm$7% overnight gap). Entering at market ($177.96) right above the $177.50 Max Pain strike with positive dealer pinning leaves zero margin of safety.
- **Apple Modem Phase-Out:** The structural elephant in the room remains Apple's internal modem transition. Any negative commentary on modem royalty or unit run-rate in Q1 FY27 guidance caps upside.
- **Why Cash Wins Today:** At $177.96, the risk/reward is 1.83:1. Waiting for a dip to the $175.00 Put Wall or evaluating post-earnings price discovery prevents taking uncompensated earnings risk.

---

## 5. Output Contract & Structured Verdict
- **VERDICT: WATCH / LIMIT TRIGGER, QCOM, buy only at or below $175.00.**
- **Rationale:** High-quality fundamental compounder with strong automotive growth, but current price ($177.96) fails the 2:1 asymmetry hurdle ahead of the Nov 4 earnings gap event. Top put support sits at $175.00.

### Telegram Alert Payload
```text
WATCH / LIMIT TRIGGER | QCOM (Qualcomm) US7475251036
Buy ONLY at or below $175.00 (strict math ceiling $177.13; now ~$177.96).
Catalyst: Q4 FY26 earnings Wed 4 Nov 2026 after close. Guide rev $9.7-10.5B, non-GAAP EPS $2.05-2.25.
Why not now: Base gain is +14.8% net but upside/downside is 1.83:1 (needs >2:1). Positive gamma pinning at $177.50 Max Pain.
If triggered <=$175.00: GBP 75 (binary earnings cap), stop $164.00, target $205.00, thesis exit if auto/IoT rev growth drops <15% or handset margin weakens.
Friction: 0.15% FX each way; break-even ~+0.30%.
```
