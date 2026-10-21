# Short-Horizon Opportunity Dossier: NFLX (Netflix, Inc.)
**As of:** 2026-10-21 (US session in progress; price = delayed Yahoo chart quote 18:45Z / 14:45 ET, **not** a broker quote)
**Mandate:** £300 Trading 212 Stocks ISA Model Sleeve (max £100 per idea; swing horizon days to a few months)
**Security:** NASDAQ:NFLX, ISIN US64110L1061 (verify instrument/fractional eligibility in your ISA before ordering)
**Currency / FX:** USD; GBP per USD 0.74638 (GBPUSD 1.3398, 2026-10-21 18:44Z); T212 FX fee 0.15% each way
**Single-pass run:** engine memory + primary SEC filings + `tools/decision_economics.py` / `tools/finance.py`. Worksheet: `monitoring/studies/evidence/2026-10-21-nflx-app/valuation-worksheet.py` (output JSON and public SEC exhibit text extracts alongside it).

> **VERDICT: WATCH / LIMIT TRIGGER, entry ceiling \$62.00.** Business and balance sheet are sound and the sell-off is real, but at \$65.80 the setup fails the >2:1 asymmetry test (1.18:1) and just misses the >8% net base-case hurdle (7.76%). There is also no scheduled catalyst until the Q4 print in mid/late January 2027.

---

## 1. Catalyst mechanism and what changed since our preserved framework
- **Event just happened (not tradable as a pre-event setup).** Q3'26 reported 2026-10-20 (8-K 0001065280-26-000290, Ex. 99.1). The pre-event protocol (`2026-10-10-netflix-pre-event-protocol-r002.md`) is now superseded by actuals; no pre-event entry exists to take.
- **Print (primary):** revenue \$12,874M (+11.8% y/y, in line with its own forecast); operating income \$4,459M, margin 34.6% (vs 28.2% Q3'25), "ahead of forecast primarily due to the timing of expenses"; diluted EPS \$0.87.
- **What the market punished (primary):** Q4 guide revenue \$13,442M (+11.5%), operating margin 26.0% (OI \$3,500M, includes ~120bp from headcount reductions), EPS \$0.67; FY26 revenue guide \$51.1B (0.2% below prior midpoint), margin 31.5%; 2026 ad revenue cut to ~\$2.7B from ~\$3B; FY26 FCF guide cut to ~\$12.0B from ~\$12.5B on a Q4 real-estate transaction. Management acknowledged "investor concern about our view hours growth".
- **Reaction:** NFLX \$68.69 (Oct 20 close) to \$65.80 now; 52-week range \$64.10 to \$116.73 (about -44% from the high). Street targets cut (search-derived, secondary): BofA 105 to 90, JPM 85 to 81, Guggenheim 80 to 78, MS 80 to 77; Needham to Hold.
- **Next scheduled catalyst:** Q4'26 results, expected mid/late January 2027 (date not confirmed in sources read). The Q4 print also resets the Jan 2027 pro forma reference in our r002 framework.

## 2. Statutory-to-owner cash flow and equity bridge (resolves the open item in `<preserved_company_facts>`)
All figures \$ unless stated; balance sheet at 30 Sep 2026 from Ex. 99.1.

| Item | Value | Treatment |
|---|---|---|
| Cash and equivalents + short-term investments | 8,194 + 29 = **8,223M** | Treated as available liquidity; no restricted-cash split disclosed in the letter |
| Total debt (carrying) | 15,132M (+59M issue costs/OID = ~15.19B; letter says gross debt \$15.3B) | A \$1B bond issued in Q3 pre-funds a \$1B Q4 maturity, so net debt is not distorted by it |
| **Net debt (company definition)** | **7,114M** | Used in EV |
| Operating lease liability | 2,330M (30 Jun 2026, 10-Q XBRL; Q3 10-Q not yet filed) | **Not subtracted** from FCF-based EV: lease cash cost is already inside operating cash flow. Added only for the EBIT-multiple view (EV incl. leases \$283.5B) |
| Total streaming content obligations | 25,223M, of which 5,608M on balance sheet; ~19.6B off balance sheet | **Not subtracted**: future content cash spend is already embedded in FCF (guided cash content spend / amortisation ~1.1x). Subtracting it as debt would double count |
| Share count (FD) | Q3 weighted diluted 4,195M; 63.9M repurchased in Q3 ($4.8B); **period-end estimate 4,165M** | Estimate (letter gives weighted, not period-end); +/-1% moves market cap by about \$2.7B |
| **Market cap / EV** | \$274.1B / **\$281.2B** | At \$65.80 |

**Non-recurring items stripped (hard accounting rule):**
- **Q1'26 \$2.8B Warner Bros. Discovery merger termination fee** (paid by Paramount Skydance on WBD's behalf), booked in "Interest and other income" (nine-month figure \$2,947M vs \$127M prior year). It inflates Q1 net income (\$5,283M, EPS \$1.23) and Q1 FCF (\$5,094M). I strip **\$2.2B after tax** from FY26 cash flow (range \$1.8 to \$2.8B; exact cash-tax on the fee is not isolated in the sources read).
- **Q4 real-estate transaction** (FCF guide cut \$0.5B): treated as a one-off asset purchase, added back at \$0.5B (the amount is inferred from the guide change, not disclosed).
- Normalised recurring FY26 FCF = 12.0 - 2.2 + 0.5 = **\$10.3B** (range ~\$9.8 to \$10.8B).
- **SBC:** GAAP operating income already expenses it (Q3 \$134M; nine months \$405M); reported FCF adds it back via CFO. SBC-adjusted owner FCF is ~\$9.75B (yield 3.56% vs 3.76% reported basis). No separate dilution charge is made, to avoid double counting; buybacks (4.8B in Q3) far exceed SBC.

**Market-implied expectations (reverse DCF via `finance.discounted_cashflows`):** with normalised FCF \$10.3B, EV \$281.2B, 3% terminal growth, the price implies **9.1% FCF growth for 10 years at a 9% discount rate (6.6% at 8%)**. That is roughly in line with 11% revenue growth plus modest margin expansion and buyback accretion, so the market is not pricing a collapse and the stock is **not obviously cheap on fundamentals**; it is cheaper, not mispriced.

**FY27E EPS scenarios (analyst assumptions, formula in worksheet; FY26 revenue \$51.1B, net interest -\$0.66B, 17% tax):**

| Case | FY27 rev growth | Op margin | FD shares | EPS |
|---|---|---|---|---|
| Bear | 9.0% | 30.0% | 4,100M | \$3.25 |
| Base | 11.5% | 32.5% | 4,046M | \$3.66 |
| Bull | 13.0% | 34.0% | 3,990M | \$3.95 |

At \$65.80 the stock trades at **18.0x base FY27E EPS** (20.2x bear EPS).

## 3. Trading 212 hurdle check (`decision_economics.scenario_analysis`, all-in GBP)
Entry modelled at **\$66.06** (price +0.4% for spread and manual-delay allowance), £100 budget buys **2.0251 shares**; 0.15% FX fee each way; round-trip break-even exit \$66.26.

| Scenario (exit ~mid/late Jan 2027) | Exit price | Basis | Net result on £100 |
|---|---|---|---|
| Bear | \$48.70 | 15x bear EPS; Q4 print disappoints again, view-hours fear persists | **-26.5%** (-£26.50) |
| Base | \$71.40 | 19.5x base EPS; stabilisation plus buyback accretion | **+7.76%** (+£7.76) |
| Bull | \$90.90 | 23x bull EPS; engagement fears fade, ad tier launches (15 new markets in 2027) | **+37.2%** |
| Stop at \$60.00 | \$60.00 | -9.2% price | -9.45% (-£9.45) |

Analyst-judgement weights (not statistical): bear 35% / base 45% / bull 20% => probability-weighted net **+1.65%**, upside-to-downside **1.18:1**.
- Base-case net return >8%: **FAIL (7.76%)**, marginally.
- Upside/downside >2:1: **FAIL (1.18:1)**.
- **Ceiling solve:** the highest entry price at which base net >8% and ratio >2:1 both hold is **\$62.00** (about 5.8% below the current price).

## 4. Mandatory adversarial challenge (Astra red-team)
- **"It is down 44%, so it must be cheap."** The reverse DCF says the price implies ~9% growth for a decade, which is about what the business plausibly delivers. Price fell because earnings power was cut and the multiple compressed; the value case is modest, not compelling.
- **Q3 margin quality.** The 34.6% margin was flattered by expense timing and moves against Q4 (26.0% guide). Annualising Q3 would overstate earnings; I used guided FY26 31.5% as the anchor.
- **Engagement.** Management itself says it must "accelerate growth in view hours". Subscription pricing power is the thesis; if price-led revenue growth meets flat view hours, churn risk rises with the next price increase.
- **Windfall distortion.** Trailing P/E and FCF yield screens that do not strip the \$2.8B WBD fee overstate cheapness by roughly 16% (reported-basis yield ~4.4% vs 3.76% normalised). The "FCF yield 3.5 to 4.5%" quoted by commentary is on the reported basis.
- **Catalyst delay.** No scheduled catalyst for ~13 weeks. A 60 to 90 day delay costs nothing against a time exit, but dead capital in a £300 sleeve has an opportunity cost, and the 0.30% round trip plus spread is ~0.7% to clear.
- **Falling knife / stop noise.** The stock moved -4.2% today and -5.8% since the Oct 19 close. A stop within ~5% is noise-prone; the stop used here (\$60, -9%) already breaks the 2:1 test even at a strong base case. That is why the answer is a lower entry, not a tighter stop.
- **Why cash may be better today:** at the current price, the probability-weighted net return (+1.65%) is below a plausible cash/T-bill alternative over 13 weeks plus friction risk. Cash wins until the entry improves.
- **What would overturn this verdict:** an entry at or below \$62.00; or a base case that moves to ~\$74 or more on new evidence (for example, evidence view hours reaccelerating).

## 5. Output contract and verdict

**VERDICT: WATCH / LIMIT TRIGGER, NFLX, buy only at or below \$62.00.**
- If NFLX trades at or below **\$62.00** (US market hours), re-run `engine math` with the live price, then the BUY plan below applies.
- **Conditional BUY plan (pre-committed so it is not improvised later):**
  - (a) **Max entry ceiling \$62.00**; commitment **£100** (about 2.14 shares at a \$62.25 delay-adjusted fill, all-in with FX fee).
  - (b) **Hard stop \$55.00** (about -11%, below the Oct low zone); at \$62 entry the bear scenario is \$48.70.
  - (c) **Thesis-invalidation exit:** Q4 results show revenue growth under 10% y/y, or FY27 margin guidance below 30%, or management guides a view-hours decline.
  - (d) **Time exit / reassess:** the session after the Q4'26 print (expected mid/late Jan 2027); hard time exit 2027-02-27.

### Telegram alert payload
```text
WATCH / LIMIT TRIGGER | NFLX (Netflix) US64110L1061
Buy ONLY at or below $62.00 (now ~$65.80). Not actionable above ceiling.
Why not now: base +7.8% net, upside/downside 1.18:1 (needs >8% and >2:1). Market implies ~9% 10y FCF growth, so fair rather than cheap.
If triggered: GBP 100 (of 300), ~2.1 shares, stop $55.00, thesis exit: Q4 rev growth <10% or FY27 margin guide <30%.
Catalyst: Q4'26 results ~mid/late Jan 2027 (date unconfirmed). Time-exit review: day after print; hard exit 2027-02-27.
Friction: 0.15% FX each way; break-even ~+0.7% incl. spread/delay.
Prices from delayed chart quote, verify in Trading 212 before acting.
```
Command: `.\tools\engine.cmd alert --ticker NFLX --verdict WATCH_LIMIT_TRIGGER --expires-hours 720 --text "<single-line payload above>"` (Telegram must be configured first, otherwise it is only staged in the local outbox).

## Sources and limitations
- Primary: [Netflix 8-K and Ex. 99.1, 2026-10-20](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000290/ex991_q326.htm); NFLX XBRL company facts (operating lease liabilities, 30 Jun 2026).
- Secondary (search summaries, not verified against primary): Q1'26 WBD termination fee description and booking; analyst target changes; "Radford Studio lot" description of the real-estate transaction; Q4 earnings date.
- Price/FX: Yahoo Finance chart endpoint (unofficial, delayed); 52-week range from the same feed.
- Judgement inputs (not facts): share count estimate, windfall after-tax size, Radford add-back, FY27 scenarios, scenario exit multiples, and scenario weights. Sensitivity: the ceiling moves roughly one-for-one with the base target.
- Q3 10-Q is not yet filed, so lease and maturity detail is as of 30 Jun 2026.
- This is a model signal for manual review, not advice; no edge from this method has been demonstrated over a sample.
