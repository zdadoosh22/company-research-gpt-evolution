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
