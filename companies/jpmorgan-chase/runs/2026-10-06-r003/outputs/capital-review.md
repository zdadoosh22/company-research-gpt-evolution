# JPM focused capital and return validation

Research cutoff: **2026-10-06**. Review performed after that date using only publications available by the cutoff. This is a focused validation note, not an approved JPM thesis, quote-specific valuation or distribution forecast. No company run, report, model, shared utility or approved methodology was edited.

## Result and source boundary

The existing r002 steady-state formula is valid under its stated opening-equity assumptions. It is appropriate as a teaching/cross-check or terminal-state calculation. A defensible current JPM valuation and prospective return calculation require a finite equity/capital/share-count path before that terminal state. In particular, reported ROTCE uses average TCE; TCE differs from regulatory CET1; capital distributions depend on more than CET1; and buyback dollars do not automatically become the continuing investor's cash receipt.

The archived July supplement is preliminary capital evidence. A newer **within-cutoff** filing and dividend announcement materially extend it:

| Primary source | Publication | Exact location / access |
|---|---|---|
| [Q2 earnings release](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfexhibit991narrative.htm) (j1) | 2026-07-14 | Archived r002 sources/2026-q2-release.htm; p1, notes 2b/2d and 13–14 |
| [Q2 financial supplement](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm) (j2) | 2026-07-14 | Archived r002 sources/2026-q2-supplement.htm; pp2,9–11,28 |
| [Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm) | 2026-08-06 | Capital Risk Management pp44,46–47,49; Note21 pp177–178. Full HTML fetched and read locally in work/jpm-q2-10q.htm; SHA256 4ba60f17c069172a3bb4aa681d5f2a7ae3ac49e557f989101b4e3e1cbe4cad38. [SEC filing index](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/0001628280-26-054343-index.html) verifies filing date. |
| [Regulatory capital, Note21 extract](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/R29.htm) | Same filing | Requirements, footnotes and finalized capital tables; read directly |
| [Dividend intention and $50bn repurchase authorization](https://www.jpmorganchase.com/ir/news/2026/jpmc-dividend-increase-common-share-repurchase) | 2026-06-24 | Issuer announcement; read directly |
| [Dividend declaration](https://www.jpmorganchase.com/ir/news/2026/jpmc-declares-increased-common-stock-dividend-9-15) | 2026-09-15 | $1.65, October31 payment, October6 record date; read directly |

The large 10-Q exceeded the browser reader's size limit; this was resolved by fetching its exact SEC HTML and extracting/read-checking the relevant sections locally. No later-quarter filing was used. All issuer figures below are issuer-reported facts; non-GAAP definitions and preliminary estimates remain labelled.

## Actual earnings, denominator and distributions

At June30, reported TCE was **$301.314bn**, period-end shares **2.6582bn**, and TBVPS **$113.35**. Reconciliation: 353.558 common equity − 52.711 goodwill − 2.437 other intangibles + 2.904 related deferred tax liabilities = 301.314. Mortgage servicing rights are not removed in this definition. Independent division gives 301.314/2.6582 = **$113.352645**, matching rounded reported TBVPS. [j2 pp2,10,28](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm).

Q2 net income applicable to common equity was **$20.847bn** (net income21.155 less preferred dividends0.308), average TCE **$290.852bn**, opening March31 TCE **$291.708bn**. Reported annualized ROTCE is29%. Using actual quarter-day annualization, 20.847/290.852 ×365/91 = **28.7490%**; replacing the denominator with opening TCE gives **28.6647%**. Neither is a sustainable forecast. The release reports23% excluding significant items; its $16.9bn adjusted net income is after removing $4.2bn of after-tax gains from headline net income, not automatically the exact common-equity numerator. [j1 notes2b/2d](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfexhibit991narrative.htm); [j2 pp10–11,28](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm).

For a clean illustrative year with equity growing evenly from B to B(1+g), average equity is B(1+g/2), so **r_open = r_average ×(1+g/2)**. With18% average ROTCE and4% equity growth, opening return is18.36%, not18%. This translation is an assumption-dependent identity, not an issuer restatement; distributions' timing, OCI and issuance can invalidate the simple average approximation.

| Q2 actual history, $bn except shares/price | Actual | Definition |
|---|---:|---|
| Common dividends declared | 4.033 | $1.50 declared per share; not a cash-payment-date schedule |
| Gross repurchases | 6.703 | 21.7m shares; reported average purchase price$308.21 |
| Employee shares issued | 0.4m | Treasury issuance; employee-equity impact+$0.518bn |
| End shares | 2,658.2m | Opening2,679.5 −21.7 +0.4 =2,658.2 at disclosed precision |
| Net treasury-stock purchase in CET1 rollforward | 6.717 | Distinct accounting line, not the headline net-buyback metric |
| Release's common net repurchases | approximately6.2 | Includes employee-equity impact, excludes excise tax/commissions:6.703−0.518=6.185, rounded6.2 |

Sources: [j2 pp9,11](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm), [j1 capital distributions and note13](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfexhibit991narrative.htm). Dollar net issuance does not equal shares issued times the buyback price. At June30, $50bn authorized July1 repurchases were prospective authority, not completed spending. September15's board declaration raised the dividend to$1.65 payable October31, record October6; $6.60 annualization is a run rate, not five years of contracted cash flows. Sources: [authorization](https://www.jpmorganchase.com/ir/news/2026/jpmc-dividend-increase-common-share-repurchase), [declaration](https://www.jpmorganchase.com/ir/news/2026/jpmc-declares-increased-common-stock-dividend-9-15). Investor eligibility for that particular payment must be established from trade/ex-dividend timing; the record date alone does not authorize assuming a new October6 buyer receives it.

Actual capital retention is not just earnings less dividends. The finalized H1 CET1 bridge, $bn, is:

**288.469 +37.065 −8.100 −13.842 −0.555 −2.081 −0.188 +0.032 +0.041 +1.778 =302.619.**

These terms include treasury stock, paid-in capital, AOCI and regulatory adjustments. The July estimated Q2 bridge separately reconciles to302.620; preserve it as preliminary rather than rewriting its source actual. [10-Q p47](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm); [j2 p9](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm).

## Regulatory constraints: finalized June capital versus preliminary July supplement

The finalized10-Q reports standardized CET1 **14.2%**, against the supplement's estimated14.1%; standardized RWA changed from$2,141.738bn to$2,132.428bn. The filing identifies Advanced total capital as the most binding **Basel III risk-based** constraint. This does not rank every liquidity, subsidiary, resolution, leverage or management constraint. [10-Q pp44,46](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm).

| BHC constraint | Final reported ratio | Required including buffers | Calculated fixed-denominator dollar headroom, $bn |
|---|---:|---:|---:|
| Standardized CET1 | 14.2% | 11.5% | 57.390 |
| Standardized Tier1 | 15.1% | 13.0% | 45.504 |
| Standardized total capital | 17.0% | 15.0% | 42.859 |
| Advanced CET1 | 14.2% | 11.5% | 58.375 |
| Advanced Tier1 | 15.2% | 13.0% | 46.618 |
| Advanced total capital | 16.3% | 15.0% | **27.669** |
| Tier1 leverage | 6.6% | 4.0% | 125.847 |
| SLR | 5.5% | 4.25% exact;4.3% displayed | 74.332 |

Inputs and requirements: [Note21](https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/R29.htm). Risk-based buffers include4.5% GSIB plus2.5% SCB/CCB and0% countercyclical buffer. SLR's footnote gives3% minimum +1.25% supplementary buffer. Headroom is independently calculated as numerator − requirement×denominator, using unrounded disclosed dollars, not rounded ratios. For example Advanced total346.248−15%×2,123.862=27.6687. The table's headroom is a static mechanical diagnostic, **not cash freely distributable**. It assumes no RWA/exposure growth, no capital-mix change and no prudential cushion. Do not sum headroom across overlapping ratios. The tightest demonstrated risk-based headroom is Advanced total, consistent with the issuer statement.

TCE is not CET1: the filed component bridge uses different goodwill deductions and regulatory adjustments. Preferred and eligible Tier2 instruments also affect constraints independently of common equity. A future common distribution reduces common/Tier1/total numerators; replacing capital with preferred or eligible debt changes the mixture and financing cost. Subsidiary upstreamability, liquidity and stress targets can further restrict holding-company distributions.

## Controlled finite path: independently reconciled, entirely illustrative

**None of the following numbers are JPM forecasts or source actuals.** This controlled example uses a hypothetical bank with opening TCE$1,000m and10m common shares on2026-10-06. Earnings are explicitly defined on opening TCE:14%,16%,18%,18%,18%. Assumed required closing TCE grows6%,5%,4%,4%,4%, determining retained equity. Dividends equal4%,5%,6%,6%,6% of opening TCE; remaining distributable earnings buy shares. No OCI, intangibles change, preferred claims, SBC, issuance, excise tax or other claims exist. The capital floor is an **assumed economic retention constraint**, not a claim that a TCE floor reproduces JPM's regulatory capital regime. Payments/repurchases occur at the five dated anniversaries; annual financial rates are assumed for those intervals, while discounting/XIRR uses actualdays/365.

| Payment date | Opening TCE | Earnings | Retained | Dividends | Buybacks | Closing TCE |
|---|---:|---:|---:|---:|---:|---:|
| 2027-10-06 | 1000.000000 | 140.000000 | 60.000000 | 40.000000 | 40.000000 | 1060.000000 |
| 2028-10-06 | 1060.000000 | 169.600000 | 53.000000 | 53.000000 | 63.600000 | 1113.000000 |
| 2029-10-06 | 1113.000000 | 200.340000 | 44.520000 | 66.780000 | 89.040000 | 1157.520000 |
| 2030-10-06 | 1157.520000 | 208.353600 | 46.300800 | 69.451200 | 92.601600 | 1203.820800 |
| 2031-10-06 | 1203.820800 | 216.687744 | 48.152832 | 72.229248 | 96.305664 | 1251.973632 |

Dollar amounts above are$m; each row satisfies **closing B = opening B + earnings − dividends − buybacks**. Retention fractions are42.8571%,31.25%,22.2222%,22.2222%,22.2222%, following the capital-growth needs, not one constant payout inferred from a single-quarter return.

Assume terminal opening-TCE return18%, common equity growth4% and equity discount rate10%, with capital/distribution economics unchanged after the terminal date. The ex-distribution terminal common equity value is:

**TV5 = B5 ×(r_terminal−g_terminal)/(k−g_terminal) =1251.973632×(.18−.04)/(.10−.04) =$2921.271808m.**

This uses terminal next-year earnings. It is conditional continuation value, not current value or a future market-price prediction. The finite transition differs from applying the terminal multiple immediately: immediate steady-state would give$233.333333/share; the finite path gives$231.478637/share.

To make ownership arithmetic independently reconcilable, repurchases are assumed to occur at the model's then-current fair ex-dividend price. This is a controlled neutral-price assumption, not an empirical price forecast or fitting to JPM's quote. Work backwards to calculate company continuation value E_t **after** time-t distributions; E5=TV5 and:

**E_(t−1) = (D_t + R_t + E_t)/(1+k)^Δt.**

Then work forwards through the ownership schedule:

**Q_t=(E_t+R_t)/S_(t−1); shares bought=R_t/Q_t; S_t=S_(t−1)−R_t/Q_t; dividend/share=D_t/S_(t−1).**

Dividend is paid before the modeled repurchase. Remaining-share fair price is E_t/S_t=Q_t. This establishes a consistent ordering and prevents counting repurchase cash twice.

| Date | Beginning shares,m | Repurchase price,$ | Shares repurchased,m | Closing shares,m | Dividend/share,$ | Closing TBV/share,$ |
|---|---:|---:|---:|---:|---:|---:|
| 2027-10-06 | 10.000000000 | 250.626501 | 0.159600042 | 9.840399958 | 4.000000 | 107.719199 |
| 2028-10-06 | 9.840399958 | 270.375189 | 0.235228684 | 9.605171274 | 5.385960 | 115.875081 |
| 2029-10-06 | 9.605171274 | 290.460203 | 0.306548019 | 9.298623254 | 6.952505 | 124.482944 |
| 2030-10-06 | 9.298623254 | 312.037247 | 0.296764572 | 9.001858683 | 7.468977 | 133.730249 |
| 2031-10-06 | 9.001858683 | 335.217157 | 0.287293362 | 8.714565320 | 8.023815 | 143.664496 |

Company-level PV of D+R+terminal is **$2314.786369m**; divided by original10m shares equals **$231.478636943/share**. A holder who does not tender receives only dividends plus terminal share value **TV5/S5=$335.217156637/share**. Their exact dated cash flows are:

| Date | Per-share cash flow,$ |
|---|---:|
| 2026-10-06 | −231.478636943 at calculated PV; alternatively−200 assumed entry |
| 2027-10-06 | +4.000000000 |
| 2028-10-06 | +5.385959943 |
| 2029-10-06 | +6.952504864 |
| 2030-10-06 | +7.468976654 |
| 2031-10-06 | +343.240971556 (8.023814919 dividend+335.217156637 terminal sale) |

ACT/365 exponents are1.000000000,2.002739726,3.002739726,4.002739726,5.002739726. Independently discounting the continuing holder's receipts at10% gives **$231.478636943**, matching original-share aggregate value to below$1e−10. XIRR solves −entry +ΣCF_t/(1+x)^years_t=0: **10.000000% at calculated PV;13.396102% at assumed$200 entry**, with NPV residual below$2e−13. No extra buyback yield is added. If repurchases occur above/below intrinsic value, value transfers between selling and continuing holders; the aggregate-PV/original-share identity need not equal a continuing holder's PV. Future repurchase price must then be explicitly modeled.

Arithmetic is saved in work/jpm-controlled-path.json; machine-readable inputs and expected period outputs are in work/jpm-capital-fixture.json. A separate recomputation from those inputs checked every period output, ownership PV equality, dated XIRR residual and archived-source hashes. This independently derived fixture validates finite-path arithmetic and timing, not JPM economics, a complete regulatory-capital model, native Excel behavior or scenario calibration. Primary-source copies and their publication dates, locations and hashes are preserved in work/jpm-capital-sources/source-metadata.json.

## What a real forward distribution model still needs

1. Bridge verified valuation-date/common-share ownership and financial opening balances from June to the cutoff; preserve source dates. Establish actual dividends receivable by the prospective buyer and verified dated entry price.
2. Forecast common earnings through NII, fee income, expenses, losses/provisions and preferred dividends; distinguish source-average ROTCE diagnostics from the model's opening/average denominator and avoid mechanically annualizing gains.
3. Roll forward common equity/TCE and separately CET1, Tier1 and total capital: OCI, regulatory deductions, goodwill, credit allowances, preferred/debt issuance/redemption and stress effects cannot be dropped into one generic retention rate.
4. Forecast both RWA approaches and leverage exposure, applicable buffers/phase-ins and management targets, plus subsidiary liquidity/upstreaming. Compute permitted distributions under all relevant constraints; shortfalls require distribution cuts or separately costed financing.
5. Make dividend dates, repurchase spending/prices, employee issuance, existing awards and terminal shares explicit. Link common compensation expense/APIC/award settlement to dilution; distinguish recorded expense from cash cost and do not both deduct a separate full SBC charge and dilute the identical awards without a claims reconciliation.
6. Use steady-state P/TBV only once sustainable returns and required capital growth/payout are supportable. Discount the same dated per-share dividends and conditional terminal value to obtain current PV and XIRR/entry levels. A terminal multiple alone does not prove the distributions can occur.

Deposits fund bank assets and influence NII, liquidity and required capital. Deposit inflows are not distributable owner cash. Deposits/ordinary debt are already liabilities in common book, interest cost is in common earnings, and debt repayment/refinancing affects funding/capital: do not subtract them again from a direct common-equity valuation. Preferred claims are excluded from common book and preferred dividends from common earnings; keep their future cost and regulatory contribution consistent. Add only demonstrably surplus, separately modeled assets not already counted. Retained earnings increase the closing equity base; do not both pay them out and use them to support asset growth. Buybacks reduce both equity and shares and benefit a continuing holder through ownership; do not add their yield on top of already adjusted per-share value.

Recommendation: retain the existing illustrative template as an explicitly limited steady-state cross-check/terminal module. Any approval of JPM current valuation, horizon value, capital-permitted distributions or prospective shareholder returns should require the finite capital/ownership path and sourced assumptions above. The focused pilot can be arithmetic-complete while real JPM valuation/returns remain withheld.
