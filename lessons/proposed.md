# Proposed methodology changes

The approved methodology remains version 1.0.0. The following proposed refinements are not approved changes to that document.

## 7 October 2026 — pilot audit

1. **Explicit terminal reinvestment audit.** APP's acquired amortisation runs off while its illustrative total-D&A ratio continued forever. Require separate finite amortisation, asset renewal, expensed investment and working-capital analysis before accepting mature cash flows. Alternatives include a justified longer transition or a bounded valuation withheld where evidence is inadequate. Company-specific research is in progress; no universal reinvestment ratio is proposed.
2. **Claims and financing schedule specification.** Require dated outstanding, contingent and weighted EPS claims to be distinguished; reconcile debt principal, cash coupons, lease renewal and GAAP finance expense. The current helper is deliberately restricted to zero new borrowing. A richer linked schedule requires independent validation before use.
3. **Bank denominator and capital path.** Require long-run opening-equity earnings assumptions to be distinguished from reported average-equity ROTCE. Validate finite distributions against applicable capital constraints before accepting shareholder returns. The steady-state bank illustration is not a complete bank template.
4. **Review evidence boundaries.** Record which reviewer reproduced arithmetic, inspected corrections, executed mutations or visually checked artifacts. Report native Excel separately. Account usage snapshots are not exact stage costs.

Status: proposed for discussion after validation. Source evidence and confirmed implementation corrections are in validation/astra-audit.json; future company analyses must preserve the existing approved methodology version until a consequential revision is agreed.

## 21 October 2026 — first single-pass short-horizon run (NFLX, APP)

Proposed by the author of `monitoring/studies/2026-10-21-*-opportunity-dossier.md`; not approved methodology changes.

1. **Strip the non-operating windfall before using FCF yield or P/E.** NFLX Q1'26 includes a $2.8B WBD merger termination fee in "Interest and other income" (nine-month figure $2,947M vs $127M prior year), inflating Q1 net income and FCF. Reported-basis FCF yield (~4.4%) overstated normalised yield (3.76%) by ~16%. Always test other income for one-offs before quoting yield screens.
2. **Check the guidance track record from primary filings before assuming "beat and raise".** APP's Q2'26 Adjusted EBITDA ($1,614M) landed $1M below the bottom of the May guide ($1,615M to $1,645M) and revenue below the midpoint. Compare prior guide vs actual in consecutive 8-Ks; do not carry a historical beat pattern into the base case.
3. **Verify every search-summary number against a primary filing.** A search summary gave APP Q3'25 revenue as $1.47B; the 10-Q shows $1,405M (changes implied growth from ~41% to ~47%). Treat search output as discovery only. SEC EDGAR (`data.sec.gov` submissions, `Archives/edgar/data/.../index.json`, XBRL `companyfacts`) is reachable with a descriptive User-Agent and gave primary data in seconds.
4. **Do not subtract content/lease obligations as debt when valuing on FCF after those costs.** NFLX content obligations ($25.2B total, ~$19.6B off balance sheet) and operating leases ($2.33B) are already inside operating cash flow; subtracting them again double counts. Use them only for EBIT-multiple views.
5. **Treat SBC as a cash-equivalent cost once, not twice.** Where reported FCF adds SBC back, deduct it from owner FCF and do not add a separate dilution charge.
6. **Event trades: a stop is not protective across a gap.** For binary prints, size to the bear-case loss (not the stop) and say so in the verdict (APP: £75 tranche, bear ~-24%).
7. **Ceiling-solve method.** Report the highest entry price at which both the >8% net base return and >2:1 asymmetry tests hold, with scenario prices and weights stated as analyst judgement. This turns a failed hurdle into a concrete limit trigger (NFLX $62.00; APP $260.60).
8. **Quote source.** Yahoo chart endpoint gives delayed quotes and GBPUSD for free; label as delayed and non-broker. The route is unofficial and may change.

## 21 October 2026 — backtest calibration & second run (QCOM, NBIS, TE)

Proposed from historical replays and opportunity dossiers covering QCOM, NBIS, and TE:

9. **Quarantined point-in-time backtesting avoids hindsight bias.** In historical replay (`.\tools\engine.cmd backtest <ticker> --as-of YYYY-MM-DD`), the engine must enforce a complete blind quarantine on all forward information before scoring. On QCOM (2026-05-01 at $177.01), it held discipline through an earnings run to $259.92 (+46.8%) while noting a -6.9% initial drawdown.
10. **Micro-cap turnaround drawdowns overwhelm stop-losses.** Backtest of TE (2026-06-15 at $8.92) revealed a devastating -60.8% Maximum Adverse Excursion to $3.49 as capital-raise dilution hit. Penny stocks and restructuring stories with negative recurring EBITDA must be rejected (PASS / REJECT) regardless of bull-case targets.
11. **Isolate non-recurring tariff and tax credits from operating EBITDA.** TE's Q2 2026 Adjusted EBITDA of $10.7M was entirely created by a $24.4M IEEPA tariff refund in cost of sales. Stripping this non-recurring credit exposed true operating EBITDA of -$13.7M. Always audit cost-of-goods-sold notes for government tariff/subsidy windfalls.
12. **Dealer Gamma (GEX) identifies market pinning vs. air-pocket risks.** QCOM's positive gamma regime (+$6.24M/1%) pinned spot at $177.96 directly on top of the $177.50 Max Pain strike, creating tight range-bound action. Conversely, negative gamma regimes (NFLX -$55.5M/1%) accelerate sell-offs down toward major Put Walls ($60.00). Use options structure to validate stop and ceiling placement.
13. **High-growth infrastructure Capex burn demands strict limit discipline.** For hyper-scalers like NBIS (+454% YoY rev growth, >$40B backlog), high CapEx ($600M+/qtr) and negative GAAP earnings mean valuation must be anchored to key institutional Put Walls ($165.00) rather than chasing momentum at market prices.
