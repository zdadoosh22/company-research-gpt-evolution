# Independent Uber financing and cash-definition challenge

Review date: 12 October 2026. **Terminal outcome: bounded review completed; one medium-severity contractual-summary correction required before quantitative reuse.** No incorrect proceeds or coupon arithmetic was found. The frozen notes' decision to withhold current funding and normalized owner-cash conclusions remains justified. This is not valuation, investment, monitoring or execution acceptance.

## Identity and binding

Requested route: Astra High. The parent reports dispatch with `model=gpt-6-astra`, `reasoning_effort=high`, `fork_turns=none`. Actual backend model identity and actual reasoning setting are not exposed to this reviewer and remain **unknown**. Dispatch metadata is not backend attestation. This is a separate-agent economic challenge; it must not be described as backend-verified Astra certification. No CLI/API model, paid fallback or further agent was launched.

Scope is exactly the seven files in `validation/uber-funding-review-input-2026-10-12-r001.json`, frozen at 01:04:56.282461 UTC. Manifest SHA-256: `c2de47319fa441556313cf9397890bc7ebd9eeea24c4e773a8a3f51f8ba5dcc8`. All seven hashes matched. All 604 baseline files matched the Git blobs at `fd4e5c9d500055b116632d8c891eb45abf9b8ad7`. Approved methodology 1.0.0 matched its declared hash. The author verifier was inspected but not executed because it overwrites a bound result file. Independent checks ran in memory. `research_enabled` remained false.

Loaded AGENTS, README, approved methodology, principles, research workflow, acceptance, model-review workflow and confirmed lessons. No Uber company index exists in `companies/`; the frozen studies supply this focused review boundary. Earlier review conclusions were not re-audited. The post-freeze capital-use supplement is outside scope and was not reviewed.

## F1 — Medium: preserve bridge repayment exceptions

**Verified omission, not a demonstrated incorrect current balance.** The funding note and fact register summarize post-closing proceeds and loan-first allocation without carrying the section 2.05(b)(i) Final Settlement Date deferral or section 2.05(b)(ii) restricted-subsidiary-proceeds exception. These can matter within the intended short holding window. Section 2.06(b)(iii)(A) separately addresses commitment reduction on receipt, subject to section 2.06(c); do not collapse those provisions into an unconditional repayment date, or assume the deferral overrides every reduction provision. [Amended bridge, sections 2.05–2.06](https://www.sec.gov/Archives/edgar/data/1543151/000155278126000414/e26328_ex10-2.htm), rendered lines 829–852; Final Settlement Date definition at line 511.

**Disposition:** open; preserve r001 and add a sourced correction. Before a dated bridge schedule, establish applicable closing/final-settlement status and reconcile the interacting provisions. The current withholding conclusion is sound.

The preclosing blocked-account condition and qualifying-facility mechanism were reproduced. Debt Issuance excludes a qualifying facility already reducing commitments; do not reduce again when it draws. Definitions establish rules, not actual cash location or balances. The unresolved classification of proceeds must remain unresolved. [Definitions](https://www.sec.gov/Archives/edgar/data/1543151/000155278126000414/e26328_ex10-2.htm), section 1.01, lines 439 and 593–594.

## Reproduced financing checks

Independent Decimal calculations used the primary Schedule I inputs, rather than trusting the frozen verification result. All amounts below are EUR millions. [Underwriting agreement, Schedule I](https://www.sec.gov/Archives/edgar/data/1543151/000155278126000486/e26383_ex1-1.htm), dated 9 September 2026, rendered lines 801–810.

| Maturity | Face | Purchase % | Issuer purchase amount | Annual coupon |
|---|---:|---:|---:|---:|
| 2029 | 750 | 99.589 | 746.9175 | 28.125 |
| 2032 | 1,000 | 99.245 | 992.4500 | 41.250 |
| 2034 | 1,000 | 99.197 | 991.9700 | 43.750 |
| 2038 | 1,000 | 99.256 | 992.5600 | 47.500 |
| 2046 | 750 | 98.738 | 740.5350 | 39.375 |
| Total | 4,500 | — | 4,464.4325 | 200.000 |

Face less purchase is 35.5675. It is not an independently separated commission, and subtracting it again from purchase proceeds would count the same shortfall twice. Remaining issuance expenses, any applicable accrued interest, actual receipt and restrictions still require evidence. No final net cash or USD conversion is established.

The indenture independently supports annual interest, first nominally 15 September 2027, accruing from issuance, ACTUAL/ACTUAL ICMA and business-day adjustment. The first normal accrual interval is 365 days. No scheduled 2026 coupon does not imply zero accrued financing cost. EUR200m is a nominal full-year coupon on the stated original tranches, not a verified future payment or effective financing cost. [Third supplemental indenture, section 2.02](https://www.sec.gov/Archives/edgar/data/1543151/000155278126000486/e26383_ex4-1.htm), 15 September 2026, lines 277–282.

The term agreement supports up to two conditional borrowing dates, no reborrowing, and commitment-fee accrual starting 13 November 2026 on actual commitments; payment is due on commitment termination. Actual/360 applies to fees. Accrual onset must not be mistaken for a same-day payment or evidence that commitments then remain outstanding. [Term-loan agreement, sections 2.01–2.02 and 2.09–2.10](https://www.sec.gov/Archives/edgar/data/1543151/000155278126000414/e26328_ex10-1.htm), 6 August 2026, lines 696–706 and 743–748. No defect found in the frozen term-loan summary.

## G1 — Unresolved evidence, not a new arithmetic defect: compensation and reserves

The June 10-Q reproduces Note 7 Q2 expense `71+27+336+122=556`, H1 expense `131+52+622+224=1,029`, and equity additions `484+563=1,047`, all USD millions. Equity minus Note 7 is 18; equity minus cash-flow addback is 24. Expense and equity recognition are differently situated measures, but that alone does not explain their numerical differences. [June 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000032/uber-20260630.htm), equity statement lines 354–373, Note 7 lines 926–938, cash flows lines 416–435.

The accessible issuer release independently reproduces Q2/H1 cash-flow addbacks of 550/1,023 and adjusted-EBITDA exclusions of 549/1,022. Therefore the H1 Note 7 gaps are 6 and 7; equity minus EBITDA is 25. H1 less Q2 gives Q1 expense/addback/exclusion of 473 in each case, locating those expense/addback differences in Q2 without explaining them. [Issuer release, 5 August 2026](https://investor.uber.com/news-events/news/press-release-details/2026/Uber-Announces-Results-for-Second-Quarter-2026/default.aspx), cash-flow table lines 214–232 and EBITDA reconciliation lines 360–380. Reviewed definitions and tables do not supply an explicit reconciliation.

Insurance balance change is `3,758+9,528−3,387−9,076=823`, versus cash-flow adjustment 830: difference 7. The cash-flow table explicitly excludes acquisition/disposal impacts from working-capital changes, but this is not a quantified explanation of the residual. [10-Q](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000032/uber-20260630.htm), balance sheet lines 197/202 and cash flows lines 427–432. No assumed FX, acquisition, capitalization or award-classification plug was accepted.

**Disposition:** retain the frozen cash note's unresolved status. Do not use any of these measures interchangeably or treat the smallest subtraction as normalized owner cash. The independent checks support its arithmetic and caution; they do not discharge account reconciliation. No claim of issuer accounting error is made.

## Source access and limits

This review reopened official SEC web rendering for underwriting, indenture, amended bridge, term loan and June 10-Q, and the issuer release for the cash/EBITDA comparison. Rendered source locations are retrieval aids, not stable original-byte archives. The five direct failures in the frozen capture register remain failures. The June original-capture failure reported in the cash note remains unclosed. The prospectus was not reopened in this bounded review; its recorded failure was not converted into access or a fees estimate. No new raw-document archive was created. Only the two review files were written.

No current administrator statement, blocked-account proof, actual net receipt, draw/repayment evidence, full funding uses, current FX or complete accounting bridge was obtained. Metadata cutoff was checked against the frozen submissions snapshot only; this is not a fresh global subsequent-event search. Nominal contract terms do not establish current funding. No price, trade, recommendation, valuation, Careem/Delivery Hero consolidation review or monitoring activation was undertaken.

## Precise next dependencies

1. Add a dated source-linked F1 correction without editing the frozen inputs; obtain a narrow correction review covering only that delta.
2. Before any current funding number, obtain public evidence of actual receipts, excluded issuance classifications, cash restrictions, facility effectiveness, draw/repayment status, and relevant closing/final-settlement dates. Apply each receipt/commitment replacement and each fee once.
3. Before a normalized compensation/owner-cash conclusion, corroborate complete source tables and obtain a disclosed or independently supportable account reconciliation. Preserve residuals if none is available; decide whether the proposed analysis can proceed without that normalization.
4. Preserve archive-access limitations and requested-versus-verified reviewer identity. The economic challenge is complete; a backend-verified Astra acceptance claim remains unsupported by this review's metadata.
