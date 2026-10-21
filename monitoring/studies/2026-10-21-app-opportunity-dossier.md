# Short-Horizon Opportunity Dossier: APP (AppLovin Corporation)
**As of:** 2026-10-21 (US session in progress; price = delayed Yahoo chart quote 18:45Z / 14:45 ET, **not** a broker quote)
**Mandate:** £300 Trading 212 Stocks ISA Model Sleeve (max £100 per idea; swing horizon days to a few months)
**Security:** NASDAQ:APP (Class A), ISIN US03831W1080 (verify instrument/fractional eligibility in your ISA before ordering)
**Currency / FX:** USD; GBP per USD 0.74638 (GBPUSD 1.3398); T212 FX fee 0.15% each way
**Single-pass run:** engine memory + primary SEC filings + `tools/decision_economics.py` / `tools/finance.py`. Worksheet: `monitoring/studies/evidence/2026-10-21-nflx-app/valuation-worksheet.py` (output JSON and public SEC exhibit text extracts alongside it).
**Prior record:** `companies/applovin-corporation` runs 2026-10-06-r001/r002 are partial (June cutoff, illustrative maturity, claims reconciliation incomplete). This dossier closes the June 30 claims/cash bridge from primary filings; the June-to-October operating bridge remains open until the Q3 print.

> **VERDICT: WATCH / LIMIT TRIGGER, entry ceiling \$260.60.** Cheaper than Netflix on fundamentals and with a dated catalyst (Q3 results **Wed 4 Nov 2026, after the close**), but at \$267.90 it fails both hurdles (base +5.64% net, upside/downside 1.51:1). It is the more compelling of the two setups, not yet a buy.

---

## 1. Catalyst mechanism
- **Event:** Q3'26 results on **2026-11-04** (company-announced date, search-confirmed), 14 days away. Company guide: revenue \$2,055 to \$2,085M, Adjusted EBITDA \$1,710 to \$1,740M (83% margin). Search-derived consensus: revenue ~\$2.07 to \$2.08B, EPS ~\$3.94 to \$3.95, i.e. consensus already sits at the upper half of guidance.
- **Business impact:** the print tests whether the AI ad engine (AXON) keeps compounding (Q2 revenue +53% y/y; the Q3 guide midpoint of \$2,070M implies ~+47% on the primary Q3'25 base of \$1,405M per the 10-Q. A search summary quoted \$1.47B, which is wrong and was not used) and whether e-commerce/web advertising adds a second leg. The e-commerce rollout has been slower than expected per management and analysts (search-derived).
- **Market state:** \$267.90 vs \$272.46 (Oct 20 close); 52-week range \$260.59 to \$738.01 (-64% from the high, -19% from \$330 a month ago); about 17.3x FY26E EPS of ~\$15.46. Recent price-target cuts (Jefferies 550 to 375, Citi; search-derived) and overhangs: Unity dispute, securities class actions, regulatory/short-seller headlines.
- **Base-rate check on "beat and raise" (primary, new finding):** the May-6 Q2 guide was revenue \$1,915 to \$1,945M, Adjusted EBITDA \$1,615 to \$1,645M. **Actual Q2: revenue \$1,924M (below the \$1,930M midpoint) and Adjusted EBITDA \$1,614M (\$1M below the low end).** The company did not beat its own guidance in Q2'26, so I do **not** assume a beat in the base case.

## 2. Statutory-to-owner cash flow and claims bridge (SBC and reinvestment treatment)
Source: Q2'26 8-K Ex. 99.1 (0001751008-26-000057); balance sheet 30 Jun 2026. Q3 not yet reported.

**GAAP to management-adjusted (Q2'26, \$M):** net income 1,267 + interest 51 - other income 60 + tax 239 + D&A 33 - FX gain 2 + **SBC 86** + other 1 = **Adjusted EBITDA 1,614** (84% margin). GAAP operating income is 1,494 (77.7% margin); net margin 66%. The gap between Adjusted EBITDA and cash earnings is mostly **tax (about 15%)** and SBC.

| Item | Value | Treatment |
|---|---|---|
| Cash (30 Jun 2026) | 3,053M | Fully unrestricted per balance sheet; Q3 FCF and buybacks since are unknown |
| Long-term debt | 3,515M carrying (note principal ~3,550M per prior record) | Principal used; no revolver draw disclosed |
| **Net debt** | **~0.5B** | Used in EV |
| Leases | Small (finance-lease principal ~4M/qtr, deducted in company FCF; other non-current liabilities 337M) | Not separately added; immaterial vs \$90B EV |
| Shares | 335.3M outstanding (30 Jun); 337.0M diluted weighted Q2 | 337.0M used |
| **Market cap / EV** | **\$90.3B / \$90.8B** | At \$267.90 |

**SBC and reinvestment (explicit):** SBC is \$86M in Q2 (\$169M for H1; ~4.5% of revenue), already expensed in GAAP income. Company FCF (CFO less capex and finance-lease principal) adds it back, so owner cash must **deduct it as a cash-equivalent cost**: no further dilution charge, to avoid double counting. Net share count fell 338.3M to 335.3M in H1 despite SBC. Reinvestment is light: capex \$1.4M in Q2; the real reinvestment is **working capital**, with receivables up \$353M in H1 (\$2,171M, about 113% of one quarter's revenue; payables \$779M) and cash taxes of \$640M in H1 vs a \$465M provision (catch-up).

**Owner FCFE (after SBC, pre-buyback):**
- H1 actual: (CFO 2,160 - capex/leases 12) - SBC 169 = \$1,979M, annualised **\$3.96B** (yield 4.4%) — depressed by receivable build and the tax catch-up.
- Run-rate from the Q3 guide midpoint (EBITDA \$1,725M, D&A 33, SBC 90, interest 51, interest income 30, 16% tax => net income \$1,328M, i.e. EPS \$3.94 on 337M shares, which matches consensus): ~\$5.0B annualised after a \$0.4B working-capital allowance (yield **5.6%**).
- **Non-recurring items:** none of size identified in 2026 YTD (the 2025 divestiture gain and goodwill impairment are prior-year). Q2 "other income" \$62M is mostly interest on cash and is partly excluded from Adjusted EBITDA.

**Market-implied expectations (reverse DCF, `finance.discounted_cashflows`, 11% discount rate, 3% terminal growth):** the \$90.8B EV implies **only ~7.8% 10-year FCFE growth off the run-rate base, or ~11.0% off the weaker H1-annualised base**. The business is growing ~40% to 50% today. The market is therefore pricing a severe, fast fade (or a durability scare); this is where the fundamental cheapness lies. Cheap does not equal catalyst: the Q2 guidance miss shows the near-term print can still disappoint.

## 3. Trading 212 hurdle check (`decision_economics.scenario_analysis`, all-in GBP)
Entry modelled at **\$268.97** (price +0.4% for spread/manual delay), 0.15% FX each way, break-even exit \$269.78. £100 buys 0.4973 shares; £75 buys 0.3730.

| Scenario (exit shortly after the 4 Nov print, or within weeks) | Exit | Basis | Net on £100 | Net on £75 |
|---|---|---|---|---|
| Bear | \$205 | Miss or soft Q4 guide; ~13x FY26E EPS | **-24.0%** (-£24.01) | -£18.01 |
| Base | \$285 | In-line print, steady guide; ~18.4x FY26E (no beat assumed, given Q2) | **+5.64%** (+£5.64) | +£4.23 |
| Bull | \$360 | Beat and raise, e-commerce traction; ~23x FY26E (near Jefferies' \$375) | **+33.4%** | +£25.08 |
| Stop \$236 | \$236 | -12% price | -12.5% (-£12.52) | -£9.39 |

Analyst-judgement weights (not statistical): bear 30% / base 45% / bull 25% => probability-weighted net **+3.70%**, upside-to-downside **1.51:1**.
- Base-case net return >8%: **FAIL (5.64%)**.
- Upside/downside >2:1: **FAIL (1.51:1)**.
- **Ceiling solve:** highest entry meeting both tests is **\$260.60** (about 2.7% below the current price; this is essentially the 52-week low of \$260.59).
- **What flips the verdict at the current price:** a base case of about **\$291 or higher** (i.e. a beat-and-raise as the central case). Q2 evidence (EBITDA at the bottom of guidance) does not justify that.

## 4. Mandatory adversarial challenge (Astra red-team)
- **"Net cash, 17x earnings, +50% growth" is the bull case, and it is real, but already known.** The reverse DCF shows the cheapness; the market is also telling you it does not trust durability. A cheap stock into a binary print is a coin-flip with a modest edge, which is what the numbers show (1.51:1).
- **The guidance record has already slipped.** Q2 EBITDA landed \$1M below the bottom of guidance; for a company priced on flawless beats, that is the first crack. Sequential revenue growth also had to re-accelerate from +4.4% (Q1 to Q2) to about +7.6% (Q2 to Q3 guide) to hit the guide.
- **Earnings-quality flags:** receivables are 113% of a quarter's revenue and rose 19% in six months; cash taxes ran above provision. FCF conversion (68% of net income in Q2; 87% in H1) is below what an 84% EBITDA margin implies. Adjusted EBITDA overstates owner cash by roughly a quarter once tax, SBC and working capital are taken out (run-rate FCFE \$5.0B vs EBITDA \$6.9B).
- **Catalyst delay / gap risk:** the print is a gap event. A \$236 stop is **not** protective across an overnight gap; a miss can open below it. The true loss limit is the bear case (about -24%), which is why size is capped at £75 in the conditional plan.
- **Event and legal overhangs:** class actions, the Unity dispute and regulatory/short-seller headlines can reprice the stock irrespective of the print. These are not modelled.
- **Opportunity cost vs cash:** probability-weighted net return (+3.7%) over ~2 weeks is attractive in annualised terms but rests on judgement weights; over a 13-week hold, it is below the 8% hurdle. At the current price the expected return does not clearly beat cash after friction and variance, so the answer is a lower entry.
- **Concentration:** if Netflix also triggers, the sleeve would hold two US growth names with ad-revenue sensitivity; keep within max 3 positions and check combined bear loss (about £18 for APP plus £22 to £26 for NFLX).
- **What would overturn this verdict:** an entry at or below \$260.60; or a primary-source signal that moves the base case to ~\$291+ (for example, a Q3 pre-announcement above the top end of guidance, which would be new information).

## 5. Output contract and verdict

**VERDICT: WATCH / LIMIT TRIGGER, APP, buy only at or below \$260.60.**
- Higher-conviction of the two (lower implied growth than delivered growth; dated catalyst), but not yet clearing the sleeve's hurdles.
- **Conditional BUY plan (pre-committed):**
  - (a) **Max entry ceiling \$260.60**; commitment **£75** (4-tranche exception **explicitly justified**: binary gap event, bear loss about £18 = 6% of the sleeve); about 0.38 shares at a \$261.64 delay-adjusted fill.
  - (b) **Hard stop \$228.00** (about -12.5% from the ceiling); gap risk acknowledged, so true bear is ~-21% to -24%.
  - (c) **Thesis-invalidation exit (at the next open after the print):** Q3 revenue below \$2,055M or Adjusted EBITDA below \$1,710M (below the low end of guidance), or Q4 Adjusted EBITDA guide midpoint below \$1.70B.
  - (d) **Time exit / reassess:** the second session after the 4 Nov print (2026-11-06) for event-trade review; hard time exit 2027-01-20 if held for a longer thesis.
- If the price is still above \$260.60 on 4 Nov, **do not chase the print**; reassess against the actual reaction and the new Q4 guide with a fresh dossier.

### Telegram alert payload
```text
WATCH / LIMIT TRIGGER | APP (AppLovin) US03831W1080
Buy ONLY at or below $260.60 (now ~$267.90). Not actionable above ceiling.
Catalyst: Q3 results Wed 4 Nov 2026 after US close. Guide: rev 2,055-2,085M, adj EBITDA 1,710-1,740M. Note Q2 EBITDA landed 1M BELOW guide low end.
Why not now: base +5.6% net, upside/downside 1.51:1 (needs >8% and >2:1). Market implies only ~8-11% 10y FCFE growth vs ~47% guided for Q3, but beat-and-raise is not assured.
If triggered: GBP 75 (of 300), ~0.38 shares, stop $228 (gap risk, true bear ~-24%), exit next open if rev <2,055M or EBITDA <1,710M or Q4 EBITDA guide mid <1.70B.
Time-exit review 2026-11-06; hard exit 2027-01-20. Friction: 0.15% FX each way.
Prices from delayed chart quote, verify in Trading 212 before acting.
```
Command: `.\tools\engine.cmd alert --ticker APP --verdict WATCH_LIMIT_TRIGGER --expires-hours 336 --text "<single-line payload above>"` (336h keeps the watch live through the 4 Nov print; Telegram must be configured first, otherwise it is only staged in the local outbox).

## Sources and limitations
- Primary: [AppLovin Q2'26 8-K Ex. 99.1](https://www.sec.gov/Archives/edgar/data/1751008/000175100826000057/exhibit991-2q26earningspre.htm); [Q1'26 8-K Ex. 99.1](https://www.sec.gov/Archives/edgar/data/1751008/000175100826000042/exhibit991-1q26earningspre.htm) (Q2 guidance); Q2'26 10-Q filed 2026-08-05 (not re-read; balance-sheet figures from the 8-K).
- Secondary (search summaries, not verified against primary): 4 Nov date confirmation, consensus (\$2.07 to \$2.08B revenue, EPS ~\$3.94), analyst target changes, Unity dispute, class actions, regulatory and short-seller items, e-commerce commentary.
- Price/FX: Yahoo Finance chart endpoint (unofficial, delayed); 52-week range from the same feed.
- Judgement inputs (not facts): FY26E EPS (\$15.46: Q1 3.56 + Q2 3.76 + Q3 3.94 consensus + Q4 4.20 assumed), 16% tax rate, working-capital allowance, scenario exit prices, and scenario weights. Sensitivity: the ceiling moves roughly one-for-one with the base target.
- Q3 cash, buybacks and share count since 30 June are unknown until the 10-Q; at the current price the Q2 buyback rate (\$551M per quarter) retires ~2M shares a quarter, roughly twice the Q2 count at ~\$500.
- Model signal for manual review, not advice; no edge from this method has been demonstrated over a sample.
