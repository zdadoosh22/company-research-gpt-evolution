# Short-Horizon Opportunity Dossier: TE (T1 Energy Inc.)
**As of Date:** 2026-10-21
**Mandate:** £300 Trading 212 ISA Model Sleeve (Max £100.00 commitment)
**Security:** NYSE:TE (ISIN US8724451080, formerly FREYR Battery)
**Quote Currency:** USD | **FX Rate:** 0.7467 GBP per USD | **Current Price:** $2.38

---

## 1. Executive Summary & Catalyst Mechanism
- **The Event/Catalyst:** Commercialization milestone of G2_Austin Phase 1 (2.1 GW solar cell fab in Texas) and Q3 2026 earnings (mid-November 2026).
- **Business Impact:** Pivot from Scandinavian battery development to domestic US solar cell manufacturing. Recent 641 MW supply agreement with Clearway Energy Group validates demand for domestic content.
- **Market Expectations vs. Reality:**
  - Share price collapsed from >$10.00 in mid-2026 down to $2.38 (-76% drawdown) as capital intensity, debt restructuring fears, and execution delays weighed on sentiment.
  - Q2 Net Sales reported at $250.1M, but profitability is heavily dependent on regulatory/tax relief.

---

## 2. Statutory-to-Owner Cash Flow & Valuation Bridge
- **The Tariff Refund Distortion (Mandatory Accounting Strip):**
  - In Q2 2026, TE reported Adjusted EBITDA of $10.7M. However, this metric was flattered by a **$24.4 million one-off tariff refund** under IEEPA recognized in cost of sales.
  - **Stripping this non-recurring cash receipt:** Recurring operational Adjusted EBITDA was actually **negative $(13.7)M**.
- **Cash Burn & Liquidity Runway:**
  - Building out G2_Austin requires ongoing CapEx. Cash balance has depleted, creating near-term overhang of dilutive capital raises (warrants/equity offerings).
- **Fair Value Scenario Matrix:**
  - **Bear Case ($1.20):** Secondary equity offering at steep discount, further tariff policy uncertainty (-49.6%).
  - **Base Case ($3.50):** G2_Austin begins initial tool installation on schedule, Clearway milestone payments unlock (+47.1%).
  - **Bull Case ($5.50):** Additional multi-gigawatt off-take agreements signed, US domestic content solar tax credits monetize (+131.1%).

---

## 3. Trading 212 Sleeve Economics, Options Positioning & Hurdle Check
*Calculated using `tools/engine.py math` and `tools/engine.py options`:*
- **Current Share Price:** $2.38
- **Options & Dealer Gamma Positioning (Expiry 2026-10-23):**
  - Spot: $2.38 | Max Pain: $2.50 (+5.0% vs Spot).
  - Put/Call Ratio: 0.16 (dominated by speculative retail call lottery tickets).
  - Top Call Wall: $3.00 (1,818 OI). Top Put Wall: $2.50 (438 OI).
  - Net Dealer GEX: Virtually zero ($+0.00M), indicating low institutional liquidity and wide bid-ask spreads.
- **Hurdle Analysis at $2.38:**
  - Commitment: £75.00 (42.139 shares).
  - Break-even: $2.39 (+0.42% to clear FX and wider penny-stock spread).
  - Target ($3.50): Net £109.96 (+£34.96 / +46.62% net).
  - Hard Stop ($1.80): Net £56.55 (-£18.45 / -24.60% net).
  - Upside-to-Downside Ratio: **1.90:1** (Fails >2:1 hurdle requirement at $2.38).
- **Strict Entry Ceiling Solve:** **$2.36** to achieve 2:1 asymmetry against a $1.80 stop.

---

## 4. Mandatory Adversarial Challenge (Astra Red-Team)
- **High Insolvency / Dilution Risk:** Micro-cap turnaround/pivot companies with ongoing fab buildout costs and negative recurring EBITDA have a high probability of diluting existing shareholders before cash flow turns positive.
- **Backtest Lesson Calibration:** Our point-in-time backtest replay of TE on 2026-06-15 (when it was at $8.92) demonstrated how dangerous these momentum surges can be—TE proceeded to suffer a **-60.8% Maximum Adverse Excursion** to $3.49 within 30 trading days.
- **Accounting Quality Trap:** Relying on headline Adjusted EBITDA without stripping the $24.4M tariff refund gives a false impression of operating profitability.

---

## 5. Output Contract & Structured Verdict
- **VERDICT: PASS / REJECT.**
- **Rationale:** Despite high theoretical upside to $3.50 (+46%), the business has negative recurring EBITDA once the $24.4M one-off tariff refund is stripped, faces imminent dilution risk to fund G2_Austin, and failed the >2:1 hurdle ratio (1.90:1) with severe drawdown history. Not suitable for the £300 capital-preservation mandate.

### Telegram Alert Payload
```text
PASS / REJECT | TE (T1 Energy Inc.) US8724451080
Verdict: PASS / REJECT at $2.38.
Why rejected: Headline Q2 EBITDA ($10.7M) was flattered by a $24.4M non-recurring tariff refund (true recurring EBITDA is -$13.7M). High dilution/offering risk to fund G2_Austin fab buildout. Backtest shows -60% adverse drawdowns in this ticker. Capital better deployed in cash or high-quality watch setups.
```
