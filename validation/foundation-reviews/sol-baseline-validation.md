# Sol baseline validation and fresh-context handoff

Date: 7 October 2026. Scope: bounded review of the three active 2026-10-06-r002 pilots, preserving their 6 October historical cutoff. No shared methodology, tools, models, run records or outputs changed.

## Configuration and independence limits

The assigned validation configuration is GPT-6.1 Sol High; workflows/model-review.md specifies Standard speed. This is the configured/assigned identity, not backend attestation. I cannot independently attest the serving backend or give exact per-stage token, credit or monetary cost. This pass must not be represented as an Astra review or a complete Sol-led thesis run.

I began with fresh task context, then loaded AGENTS.md, README, current methodology manifest, approved 1.0.0 methodology, principles, research workflow, acceptance standard, confirmed lessons, all three indexes, active run records, reports, models, observations, source registers and reviewed numerical snapshots. There is no approved `latest`; every index selects r002 through `latest_active` and labels it partial.

I did not open validation/astra-audit.json, validation/audit-report.md or other agents' review artifacts before saving this initial assessment. However, required confirmed lessons and the required corrected r002 run/report records themselves contain prior audit findings. Consequently this is independent calculation and evidence checking of corrected files, not a fully blinded error-discovery experiment. The initial section below is frozen before audit comparison.

## Initial independent findings

### 1. Material analytical blockers are real and correctly constrain the current conclusions

APP is not an accepted valuation. Its 1.4% revenue D&A add-back and 1% capex assumption do not establish sustainable mature cash. The archived 2025 10-K note 7 gives a finite acquired-amortisation runoff, including USD89.357m in 2026 and USD48.941m in 2030. The Base illustration instead reaches USD199.591m of annual D&A by 2031. Some replacement/infrastructure spending is already expensed, some involves leases and noncash acquisitions; the model needs a category-level bridge before calling its equity cash sustainable. Keeping the illustration with explicit withholding is defensible; labelling the same numbers accepted intrinsic value would not be.

APP's ownership and financing foundations remain incomplete. The Q2 10-Q cover reports July outstanding A 304.443m + B 30.208m = 334.651m. EPS note 9 reports 1.231m quarterly weighted dilutive awards and 0.107m excluded awards. Their sum gives the saved 335.989m proxy, but it is not a valuation-date outstanding claim roll-forward. The December annual filing records options 1.256114m at USD6.10 strike, nonvested RSUs 0.358162m and contingent PSUs 0.920526m. Current quantities, vesting, exercise proceeds and overlap need reconciliation rather than simply adding every disclosed quantity.

December note principal of USD3,550m reconciles the detailed annual note; June debt carrying value and GAAP interest are different observations. Q2 cash-flow information verifies H1 cash interest USD99.653m versus expense USD102.315m. Twice expense = USD204.630m is an assumption, not a cash coupon or lease service schedule. Constant debt refinancing and zero net borrowing are coherent provisional constraints; neither verifies future financing. June cash USD3,053.306m less the assumed USD1,000m reserve produces opening excess cash USD2,053.306m, but no June-to-October roll-forward has been established.

These are material analytical blockers, not newly discovered hidden defects: the r002 narratives and statuses already identify them. No accepted current-price, entry or return conclusion should be released until they are resolved.

### 2. Present value, future value and returns reproduce and remain distinct

Reproduced APP Base from model inputs in an independent scratch calculation without importing shared valuation functions. First-year revenue USD8,536.405m and FCFE USD4,860.309m; fifth-year revenue USD14,256.496m and FCFE USD8,215.618m. Retained horizon cash USD35,478.558m. Terminal pre-interest cash USD8,707.797m. Growing cash value less separately capitalised constant after-tax interest gives terminal operating equity USD107,377.844m. Add cash once and divide by proxy ownership: conditional 2031 value USD425.181783. Discount at 11% over 5.002739726 actual/365 years from 6 October 2026: USD252.252560.

Return from the 5 October price USD281.97 uses 5.005479452 years to 6 October 2031 and gives 8.5513669%. The one-day difference from the valuation-date duration explains the initially different CAGR and is not a defect. The 10% hurdle illustration is USD263.935506. Terminal dependence is 75.1649%. All match the saved JSON and workbook outputs within rounding. Zero dividends make CAGR and XIRR coincide here; this does not independently test the solver with distributed receipts or extreme losses.

The report explicitly calls these unapproved arithmetic, not investment forecasts or accepted implied market expectations. Its reverse-growth 19.1% is conditional on fixed unvalidated inputs. No mechanical combination with an incompatible valuation is used. I did not reproduce the reverse solver in this bounded pass.

### 3. Bank substitution is appropriate, with a missing capital transition

The archived JPM release/supplement verify USD113.35 June TBVPS, 29% reported quarterly annualised ROTCE, 23% excluding significant items, USD16.9bn adjusted versus USD21.2bn reported earnings, Standardized estimated CET1 14.1%, and USD1.50 quarterly declared dividend. The source's Advanced-versus-Standardized total-capital comparison has the limited scope the r002 report now states.

Independent Base algebra: 113.35 x (0.18-0.04)/(0.10-0.04) = USD264.483333; retention 0.04/0.18 = 22.2222%; implied next-period distributable earnings USD15.869/share. At 19% return, the same formula gives USD283.375. Saved workbook Bank model B18/B24/B25 match.

The USD15.869 implied distribution exceeds four times the currently declared USD1.50 dividend. This is not an arithmetic error: total distributable earnings could include repurchases, and the former is an unvalidated steady-state assumption. It makes clear why the next revision needs earnings, common/tangible equity, RWA, all binding capital/leverage constraints, buybacks and dividends on a finite dated path. Reported average-equity ROTCE cannot substitute for a forecast return on opening equity. No industrial EV/debt subtraction is applied and price-dependent conclusions remain withheld.

### 4. Global period/scope calculations work, but extracts alone cannot support all qualitative claims

Unilever turnover bridge reproduces EUR50,503m + EUR25,623m - EUR25,506m = EUR50,620m. H1 IFRS operating margin = 4,885/25,623 = 19.0649%. Saved workbook Reconciliation B7/B8 match. The report distinguishes continuing CFO, reported/underlying measures, EUR accounts, GBp/GBP security units and the post-demerger consolidation. Price and FX are absent rather than treated as zero.

Locally preserved u1/u2 files are selected numerical extracts, not originals. A new chat can reproduce the numbers locally, but cannot independently verify the share-consolidation, transitional-services or audit/review assertions from those extracts alone. The source registers honestly describe this preservation limitation. I reopened both issuer PDFs through browsing and verified continuing/re-presented turnover, operating profit and CFO at the identified financial-statement sections. This establishes a usable continuation route today; it does not turn the local extract into a full archived primary source. Sources: https://www.unilever.com/files/unilever-annual-report-and-accounts-2025.pdf and https://www.unilever.com/files/unilever-q2-2026-results-full-announcement.pdf.

### 5. Fresh-context continuation succeeds for status and next actions, not evidentiary completion

| Scope | Can correctly resume without memory? | Concrete next action / blocker |
| --- | --- | --- |
| APP full pilot | Yes: r002, prospective buyer, dated price and withheld valuation are identifiable. | Create new revision preserving r002; reconcile latest-disclosed claims with exercise/vesting, cash/lease/coupon/maturity schedule and June-to-cutoff bridge; replace illustrative mature reinvestment; test advertiser economics and independent valuation cross-check. Freshness review must examine actual post-August disclosures, not infer their immateriality from the inventory. |
| JPM focused bank pilot | Yes: narrow example completed, complete thesis and capital-constrained return path unfinished. | Create/validate a finite earnings/TCE/common equity/RWA/distribution model with applicable regulatory and management requirements. Verify a dated security quote only when making price/return conclusions. More annual/interim evidence is required for a full thesis. |
| Unilever focused global pilot | Yes: currency/provenance example completed, no security valuation. | For full thesis select/verify listing, consolidated ownership and quote, dated EUR-per-GBP FX, investigate economics and valuation. Reopen original financial statements for qualitative claims because local extracts lack those passages. |

The records give a sufficient practical continuation point and prevent the unfinished pilot from becoming an approved thesis. They do not eliminate the need for new evidence. Reading local files is a useful handoff test, not evidence of complete global/sector support.

## Initial disposition and limits

No new material numerical mismatch was confirmed in the selected APP Base, bank Base or Unilever bridge. This conclusion is bounded: I inspected formulas/cached outputs without recalculating XLSX in native Excel; I did not repeat all mutation checks, run a complete legal/event update, visually inspect all PDFs or certify every historical observation. Source archival hashes for APP/JPM were checked with no mismatch printed. Selected relevant primary passages were read, not every page of every source. Existing analytical blockers still prevent acceptance of any complete valuation package.

The corrected-package validation supports using Sol for retrieval, source/period reconciliation, reproducible calculations and ordinary focused questions, followed by a targeted stronger review of cash-flow sustainability, ownership/financing, capital transitions and evidence-to-conclusion judgement. It does not support a cheapest-model certification: one bounded check of already-corrected files is not comparable to authoring a fresh thesis, and configuration plus usage snapshots cannot establish exact cost per successful research output. Use known failures to target stronger review and preserve its material findings; avoid routine wholesale prose rewrites.

## Post-save audit comparison

After saving the initial assessment, I read validation/audit-report.md, validation/astra-audit.json and the historical validation/usage.json. I did not read the current reinvestment, ownership or bank investigations by other agents.

### Overlap with Astra

- The remaining APP mature reinvestment, financing/cash-interest, current claims and June-to-October gaps agree with the audit's analytical limits. My primary-source passages independently support those limits.
- The revised APP Base arithmetic agrees with Astra's recorded outputs. Constant terminal financing interest, separately disclosed debt principal/expense/cash interest, dated award evidence, terminal dependence and qualified market expectations are visible in the corrected files.
- The bank formula/denominator distinction and limited Advanced-versus-Standardized capital statement agree with Astra. Its missing capital-constrained distribution path remains the decisive blocker.
- Unilever's compatible continuing-scope TTM, missing price/FX and focused status agree with Astra. None of these focused examples establishes general sector coverage.
- I did not independently revalidate all implementation corrections F01-F07/R01-R03/C01-C03 through mutations. Formula inspection and selected numerical reproduction must not be described as repeating Astra/parent's 51 tests or 122 workbook mutations.

### Additional observations from this pass

1. A fresh context can select the correct r002, reconstruct all three scope boundaries and name practical next actions without conversational memory. This is stronger than merely saying files exist. It is still a delegated fresh-context test within the same parent task, not an independently opened user chat or confirmation of every desktop registration behavior.
2. Unilever's local numerical extracts preserve enough for arithmetic, but not all cited qualitative claims. Source access is currently possible through browsing; the original documents must be reread at the required passages before extending conclusions. This is a handoff preservation boundary, not evidence that the recorded qualitative claims are wrong.
3. JPM Base implies USD15.869/share distributable earnings under its assumed opening-equity economics versus a USD6/share declared-dividend run rate. The difference illustrates the material role of repurchases, retention and regulatory capacity; it is not a verified payout forecast or a defect in the algebra.
4. APP return timing starts at the October 5 price observation, while PV and hurdle timing start October 6. This is internally deliberate and reproduces once both clocks are preserved. Reports/updates should retain both rather than treating rounded five years as identical.

No new hidden material defect was confirmed within this bounded scope. Additional observations must not be promoted into proof of a full workflow or proof that stronger review is unnecessary.

### Concrete quality and cost workflow conclusion

Retain Sol-led evidence collection, reconciliations, input-linked modeling and ordinary focused answers as a provisional workflow. Use deterministic arithmetic/domain tests for errors they can actually detect. Escalate the economically decisive ownership/financing, reinvestment/maturity, bank capital transition and evidence-to-conclusion judgements to a targeted stronger review after primary evidence is assembled. Require the review to return material findings and dispositions rather than polished rewriting. If omissions recur in a specific stage, use the stronger model for that stage's analysis, not merely for proofreading afterward.

This pass supplies evidence that assigned Sol can reload and check a corrected package. It does not test whether Sol alone would have discovered all original errors, authored a new defensible thesis, or delivered the lowest cost per accepted output. The historical usage record has no project baseline and unknown original configuration; its pending review field describes the earlier snapshot, not today's completed Astra status. No credible monetary savings percentage, token-stage estimate or universal cheapest-model conclusion follows. A future comparison should use matched fresh tasks, recorded configuration/speed, wall time and available account snapshots, plus unresolved material-error counts and rework; shared usage still limits attribution.
