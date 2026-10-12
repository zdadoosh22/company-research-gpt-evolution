# LEVI cash timing — bounded independent review

12 October 2026. **Terminal: accepted for limited historical-fact and explicitly labelled sensitivity use. No material defect found.** No normalized cash, valuation, opportunity or entry acceptance follows.

Reviewed only the four files bound by `validation/levi-cash-timing-review-input-2026-10-12-r001.json` (manifest SHA-256 `cb4695c235228bcf4631ea236a44e248b6db8f787b153ae7cfe35ec85693c1cd`). All four hashes matched. Read the locally captured original HTML with a standard-library parser; its SHA-256 matched `33cc70914b298e0f98182f153a8c2a30ffb66211a15364c76f5641549b2b4700`. No web recapture or author-verifier execution. All 604 baseline files at `fd4e5c9d500055b116632d8c891eb45abf9b8ad7` matched their Git blobs. Earlier reviews remain unchanged.

Requested route remains Astra High, with parent-reported dispatch. Actual backend model and reasoning setting remain unknown; no backend-verified certification is claimed.

## Source and checks

Primary source: [LEVI 10-Q, quarter ended 30 August 2026](https://www.sec.gov/Archives/edgar/data/94845/000009484526000047/lvis-20260830.htm), filed 7 October, successfully archived locally. Named sections below were inspected in original-derived text; rendering line references in the author note are not original-file line numbers.

- **Note 10:** 78.6m refund recognition reduced cost of goods sold; 57.1m had been received, with the remainder receivable. Interest is separate. Note 14 footnote (4) additionally describes 4.7m refund interest as received. This does not invalidate sensitivities expressly retaining interest.
- **Cash flows / Adjusted Free Cash Flow:** nine-month CFO includes the identified receipt. FCF retains continuing and discontinued operations, including Dockers; no continuing-only cash conclusion is established.
- **Note 1, Share Repurchases:** the 200m ASR payment occurred at inception on 30 January; Q3 delivered and retired the final 1.6m shares. Settlement is not another 200m outflow.
- **Note 8 / MD&A liquidity:** carrying debt 1,043.6m, approximately 1.1bn required principal, and unused credit availability 696.7m are distinct dated measures. Capacity follows 715.8m availability less 19.1m credit usage and is not cash.
- **MD&A results:** the 490bp wording is reproduced. The prior release-based 330bp diagnostic remains a differently specified presentation after redeployment, not a demonstrated source correction. No recurring-spend bridge is established.

Independent Decimal checks, USD millions:

| Diagnostic | Calculation | Result |
|---|---|---:|
| Identified principal-refund receivable residual | 78.6 − 57.1 | 21.5 |
| CFO with identified principal receipt removed | 585.2 − 57.1 | 528.1 |
| Issuer FCF with identified principal receipt removed | 427.3 − 57.1 | 370.2 |

The residual inherits the source's reported precision. The latter two are sensitivities, not cash forecasts. They retain interest, taxes, redeployment and Dockers effects. Removing recognized profit from CFO instead, adding the same receivable twice, or subtracting January ASR cash again at Q3 settlement would introduce errors; the frozen note correctly prevents these operations.

## Disposition and next dependency

No correction required for this narrow use. The source resolves receipt versus recognition for the identified principal refund; it does not establish sustainable cash generation. Before broader quantitative reuse, separate continuing/discontinued cash, recurring tariff and redeployment economics, current claims, and contemporaneous expectations and delayed prices as relevant to the proposed analysis. Preserve the distinct margin presentations until a supported spending bridge is available.

The successful direct capture applies to this 10-Q only; no other historic capture failures are cleared. No source-portability supplement, additional release, old review, model, trade, automation or monitoring task was reviewed or launched. Only this report and its companion JSON were written. Bounded review complete.
