# Initial pilot findings and review boundary

The original r001 artefacts are preserved. The focused Astra audit has occurred; audit revisions are r002, with corrections and remaining analytical limits recorded in validation/astra-audit.json. No general workflow approval or unsupported investment conclusion follows from this audit.

Confirmed implementation fixes:

- Removed hidden XBRL metadata from HTML text extraction so filing headers do not overwhelm readable evidence. Retained original HTML separately; visual/layout-sensitive source review remains necessary.
- Rebuilt terminal-period working capital at terminal growth, rather than mechanically growing the last forecast FCFE.
- Separated the observed share-price cash-flow date from the research valuation date.
- Added mandatory-input checks: deleting a forecast input withholds the affected value instead of silently treating a blank as zero.
- Added a genuine sensitivity/base consistency check and independent current-to-horizon calculation checks.
- Made source IDs directly clickable in the standalone thesis; a source appendix in another file alone did not satisfy standalone usability.
- Increased source-actual row space to preserve long scope descriptions.
- Added publication guards to artifact generators and a required-review gate to the lifecycle.

Research findings affecting reuse/conviction:

- APP 2021-2022 original total-group history is not directly comparable to 2023-2025 re-presented continuing history.
- APP historical CFO/management FCF includes discontinued Apps cash flows. It cannot silently become a clean recurring FCFE input.
- APP Class B voting rights are 20 votes per share in the filing. Existing/contingent compensation claims require exact analysis; a summary is not evidence.
- JPM headline quarterly returns include investment gains. The issuer compares Advanced total capital with Standardized total capital; that comparison does not rank every CET1/leverage constraint.
- Unilever re-presented continuing results and rebased share denominators after the Ice Cream demerger. Missing price/FX inputs remain blank.
- Local download access to Unilever PDFs failed; verified numerical extracts and precise online locations were retained. The originals were readable through browsing but not locally preserved.

Open review items: APP current ownership/contingent claims, maturity and reinvestment assumptions, retained-cash and refinancing construction; full bank capital/distribution constraints; and evidence-to-judgement consistency. Other sector methods remain unvalidated. Native Excel behaviour is unverified; bundled-engine and exported/imported formula checks are recorded separately.

No methodology change is silently approved by these findings. The initial method remains 1.0.0. Proposed refinements go in lessons/proposed.md for discussion after the audit.
