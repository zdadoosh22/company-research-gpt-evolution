# Company research 2 — focused audit

Completed 7 October 2026. Research cutoff remains 6 October 2026.

The focused Astra review identified material implementation errors and unsupported valuation foundations. The implementation errors have been corrected. Astra's final bounded review found no remaining material implementation blocker within its scope. The research pilots remain **partial**; this audit does not approve a complete valuation package or the general workflow.

## Corrections

- Rejected borrowing that previously created cash without linked debt service and claims.
- Separated growing terminal operating cash from constant financing interest.
- Protected missing and invalid inputs across headline outputs, sensitivities and supporting ratios. Sensitivity cells now validate their own terminal cash rather than borrowing the active case's validity.
- Corrected detailed APP note principal from an inferred $3,600m to the separately dated December $3,550m schedule. Cash interest, GAAP expense and carrying debt remain distinct.
- Incorporated disclosed July outstanding shares and historical awards into the evidence assessment. The mixed-date ownership proxy is explicitly unapproved as an exact current claim count.
- Disclosed terminal-value dependence and restricted simple ownership scaling to its valid zero-buyback case.
- Corrected the scope of JPM's capital comparison and guarded invalid bank case selectors.
- Supported workbooks with missing quotes, strengthened bank numeric validation, and repaired near-total-loss XIRR bracketing and residual checks.

Detailed findings and dispositions: `validation/astra-audit.json`. Approved methodology 1.0.0 was not changed; potential refinements are proposals in `lessons/proposed.md`.

## Verification

51 deterministic tests passed. Targeted workbook mutation checks passed: APP 104, JPM 12, Unilever 6. The missing-quote fixture also retained valuation arithmetic while withholding price-dependent returns through export/import validation.

All three workbooks retain formulas and passed bundled-engine recalculation and export/import checks. The reports match the reviewed arithmetic. APP's standalone PDF has three pages, its full report ten; JPM and Unilever focused reports each have two. PDF pages and changed workbook views were visually inspected. **Native Microsoft Excel has not been tested.**

Astra was configured as `gpt-6-astra`, High reasoning, and worked read-only. It independently reproduced the APP cases and inspected final corrections and mutation records; the parent executed final mutation and visual checks. A separate inherited-model agent reviewed the arithmetic. Its exact model identity and the original implementing chat's model configuration were not independently verified. Account usage is shared; exact review or stage costs are unavailable.

All 108 original pilot files in the audit baseline remain unchanged. The ten inspected reference-repository files and approved methodology hash remain unchanged. Source-register checks reported no archive/hash errors.

## Conclusions still withheld

**APP:** mature reinvestment, sustained margins, lease/cash-interest financing, current ownership claims and the June-to-October baseline bridge are not adequately established. Current intrinsic value, a market-price investment judgement, accepted prospective returns and actionable entries remain withheld. The workbook shows conditional arithmetic illustrations and must not be read as accepted company values.

**JPM:** the steady-state tangible-equity illustration is not a capital-constrained forecast. Reported average-equity ROTCE does not automatically establish long-run earnings on opening equity. Accepted shareholder-return and entry conclusions remain withheld.

**Unilever:** scope-compatible IFRS history, TTM construction and currency handling were checked. A full thesis, security valuation and returns were not produced; dated price and FX inputs remain missing.

The complete operating-company pilot, broader bank capital path, model cost/quality comparison and an actual separate-chat handoff remain open. File-only context reconstruction passed. Other sector patterns remain provisional.

## Next work

The user authorised continued useful validation and additional agents. Separate APP reinvestment and claims investigations and a JPM capital/distribution investigation are underway. Their findings must be checked and versioned before changing any research conclusion. Earlier runs remain preserved; none of the partial pilots has been published as approved research.

## Follow-up validation completed

JPM r003 adds finalized August capital evidence and September dividend disclosure, preserving prior observations. Its three-page PDF and workbook passed export and visual checks; the hypothetical finite equity/ownership example independently reconciled. APP foundation notes and fresh-context Sol High validation are saved under validation/foundation-reviews. Conditional valuation does not universally require an exact daily balance sheet; essential operating assumptions must still be evidence-based and uncertainty bounded. The working-capital note needs the financing-accrual correction recorded in continuation.md. Broader workflow approval remains open.

## Final completion check

The current APP r002, JPM r003 and Unilever r002 exports again passed artifact validation and122 workbook mutation checks. All51 unit tests passed. Current source registers, company indexes, partial-status publication boundaries, original pilot hashes, inspected reference hashes and approved methodology hash were checked. The focused audit is complete; project-wide research acceptance remains open. Astra’s foundation follow-up is recorded in foundation-reviews/app-followup-astra.md: materially bounded dated snapshots can support conditional values, while the existing illustrative model still requires a coherent operating replacement.
