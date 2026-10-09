# APP reinvestment and maturity review

Research cutoff: 6 October 2026. Prepared as an independent foundation review of r002; not a new approved valuation. Existing run files, shared tools, reports and methodology were not edited. All money below is USD million unless stated. Historical reported numbers are separated from calculations and proposed assumptions.

## Finding

The constant 1.4% revenue D&A add-back and 1% capex charge can be replaced with a defensible **structure**, but the evidence does not yet establish all the financing, renewal, tax and ownership inputs needed to approve numerical intrinsic value. The replacement should distinguish finite acquired-amortisation runoff from recurring asset depreciation, expensed cloud/R&D/customer acquisition from capitalised investment, and noncash lease/software additions from cash payments. It should forecast the operating cost structure and positive growth-related working capital instead of interpreting low cash PPE expenditure as free growth.

The most material newly read fact is the H1 2026 addition of **60.319 of right-of-use assets in exchange for lease obligations, net of modifications, and 11.897 of software licences acquired but not yet paid**. The first amount is not split into finance/operating leases in the reviewed interim supplemental disclosure. These are not cash outflows, but they prevent approval of a forecast that simply perpetuates December 2025 rental payments or assumes the June cash-capex line captures infrastructure investment. [S2, cash-flow supplemental disclosure p8]

The existing base-case terminal construction has negative accounting reinvestment. Per unit of final explicit revenue, at 3% perpetual growth: `(1.0%-1.4%)*1.03 + 12%*3% = -0.052%`. Positive perpetual revenue growth therefore increases cash while reducing net modelled capital. That is not rescued by a good-looking sensitivity output. Economic reinvestment also includes expensed technology and cloud costs already included in margins; do not deduct these a second time.

## Sources read and cutoff controls

- **S1:** AppLovin 2025 Form 10-K, filed 19 February 2026, [SEC filing](https://www.sec.gov/Archives/edgar/data/1751008/000175100826000010/app-20251231.htm). Archived r002 file `sources/2025-10k.htm`. Read the business/R&D discussion, MD&A cost categories and cash flow, statements, Notes 2 (policies), 3 (discontinued operations), 5 (PPE/accruals), 6 (commitments), 7 (intangibles), 8 (leases), 11 (SBC), and relevant tax disclosures. Online primary URL was opened to corroborate document access; calculations use the archived filing.
- **S2:** Q2 2026 Form 10-Q, filed 5 August 2026, [SEC filing](https://www.sec.gov/Archives/edgar/data/1751008/000175100826000059/app-20260630.htm). Archived r002 file `sources/2026-q2-10q.htm`. Read balance sheet p3, income statement p4, cash flows/supplemental p8, discontinued-operation disclosure pp10–11, commitments p13, intangible assets pp14–15, SBC p15, revenue policy, FCF reconciliation p20, cost tables/MD&A pp21–25, liquidity pp28–29.
- **S3:** 2024 Form 10-K, filed 27 February 2025, [SEC filing](https://www.sec.gov/Archives/edgar/data/1751008/000175100825000018/app-20241231.htm). Archived r002 file `sources/2024-10k.htm`. Relevant policy, financing/licensed obligation and investing passages read for supporting context. Original combined-group history is not substituted for restated continuing history from S1.
- **Research records:** company index, r002 run/model/report/source registers, README, AGENTS, methodology/current.json, approved v1.0.0 specification, principles, research workflow, confirmed lessons and acceptance standard loaded. Company index has no approved latest run. r002 status is awaiting review in run.json; index still says researching. Do not infer publication approval from existing outputs.

No disclosure published after the research cutoff was used. An HTML-to-text scratch copy under `work/app-reinvestment/` preserves the passages inspected; the archived filings remain untouched. Online source access does not resolve completeness of all pre-cutoff events.

## Acquired amortisation is finite

S1 Note7 p67 reports acquired intangible amortisation of 91.539 in 2023, 92.848 in 2024 and 97.404 in 2025, in continuing cost of revenue and sales/marketing. December 2025 expected book amortisation: 2026 **89.357**, 2027 **81.014**, 2028 **59.469**, 2029 **53.167**, 2030 **48.941**, thereafter **64.766**; total **396.714**, equal to closing net intangible assets.

S2 Note6 pp14–15 updates net intangible assets to **355.661** at June 2026 and H1 amortisation to **51.342**. Remaining useful lives: customer relationships **5.9 years**, developed technology **1.3 years**, other **2.8 years**. This confirms different runoff speeds. The other-assets gross balance rose from 65.790 to 78.207; the newly disclosed unpaid software licences mean the December schedule cannot simply be treated as a perfect June forecast. FX movements also affect the schedule.

S1 continuing D&A/write-offs is 119.152 /128.791 /130.724 in 2023/24/25, whereas consolidated cash-flow D&A is 489.008 /448.680 /194.778. The difference is discontinued Apps D&A of 369.856 /319.889 /64.054 (S1 Note3 p64). Mixing the consolidated add-back with continuing EBIT overstates recurring operating cash. H1 2026 D&A/write-offs of 66.228 is now entirely continuing. The residual after acquired amortisation is 14.886; do not call that pure PPE depreciation because it also includes write-offs and other amortisation.

**Recommendation:** retain the separately reconciled acquired book-amortisation schedule for finite GAAP forecasts. If forecast margin excludes acquired amortisation, do not add the same amortisation again in cash flow. Model any cash tax benefit separately: book amortisation is not proof of matching tax deductibility. Use zero-to-full applicable-tax-rate shield sensitivity until the tax basis is established. No acquired-amortisation percentage belongs in the perpetual terminal add-back. Organically renewed customer relationships and technology are supported by expensed R&D/sales costs; deducting replacement of the same capability again would double-count unless separately capitalised investment is demonstrated.

## What is already expensed

S1 MD&A p40 identifies third-party cloud/datacenter costs and finance-lease ROU amortisation in cost of revenue. R&D contains personnel salaries/benefits, SBC, professional/consulting costs, and allocated facilities/IT. Internal-use software capitalisation was not material in any period presented (S1 Note2 pp61–62). Maintenance/repairs are expensed.

| Continuing metric | 2023 | 2024 | 2025 | H1 2026 |
|---|---:|---:|---:|---:|
| Revenue, reported | 1,841.762 | 3,224.058 | 5,480.717 | 3,766.135 |
| R&D, reported | 333.781 | 374.710 | 226.510 | 194.005 |
| R&D SBC, reported | 216.236 | 229.577 | 114.463 | 136.320 |
| R&D less SBC, calculated | 117.545 | 145.133 | 112.047 | 57.685 |
| Total continuing SBC, reported | 342.551 | 357.431 | 207.958 | 169.252 |
| GAAP EBIT margin, calculated | 41.94% | 59.27% | 75.75% | 77.91% |
| EBIT margin excluding acquired amortisation, after SBC, calculated | 46.91% | 62.15% | 77.53% | 79.27% |

Source: S1 statement/MD&A tables and Note11; S2 MD&A tables/SBC note. H1 figures are six-month figures, not annualised.

H1 2025 cash R&D proxy =100.438-45.000=55.438. H1 2026 proxy 57.685 is only 4.05% higher. The reported 93% R&D increase largely reflects SBC-related payroll costs, as management explains. The proxy is not a cash-paid statement: it still contains accruals and possible noncash allocations. The sharp historical R&D/revenue decline is evidence of leverage and award timing, not proof a 1.5% cash R&D burden can persist indefinitely.

S2 MD&A reports H1 network-infrastructure expense increased 92.0 while revenue increased 1,348.407, a calculated incremental expense/revenue increase of 6.82%. S1 2025 corresponding increases were 150.2/2,256.659=6.66%. These are changes, not an absolute cloud-cost margin. H1 cost of revenue 429.433 less acquired technology amortisation 23.816 is 405.617, or 10.77% revenue, but still contains lease depreciation and other costs. Do not treat 10.77% as isolated cloud expenditure.

Cloud commitment payments rose from cumulative 579.3 at December 2025 to 953.5 at June 2026, a calculated H1 increase of **374.2**. This is cash paid toward a minimum-spend arrangement, not verified same-period expense. S1 remaining minimum commitments were 398.524 in 2026 and 304.322 in 2027; S2 supersedes the cumulative progress. The 1.3bn commitment was agreed in August 2024 over three years. Its end is not the end of cloud costs. Do not deduct commitment payments on top of forecast cloud expense without a prepayment/payable reconciliation.

**Recommendation:** forecast cash R&D, economic SBC, infrastructure cost, customer-acquisition/support expense and G&A explicitly. Growth should be tied to advertiser adoption/retention and monetisation, with costs rising for new verticals. H1 revenue grew 56% while install volume fell 10% and net revenue/installation rose 75% (S2 MD&A); indefinite monetisation extrapolation is not a mature growth foundation. Management's claims that continued innovation will improve advertiser effectiveness remain interested claims, not proof of returns on future R&D.

## Capitalised investment and leases

S1 Note5 p66: 2025 gross PPE 240.012, of which finance-lease ROU assets **212.208**; net PPE **122.445**. PPE depreciation 25.7 /29.3 /26.2 in 2025/24/23. Finance-lease ROU amortisation 19.938 /24.308 /22.673 (S1 Note8 p68). Thus owned/other PPE depreciation is much smaller than combined PPE depreciation, although exact continuing-category reconciliation should precede use of the difference.

Cash PPE purchases were 0.473 /4.776 /4.246 in 2025/24/23. Finance-lease principal was 18.669 /20.875 /20.170. Cash intangible purchases 28.318 /25.553 /63.899 include discontinued amounts 22.429 /15.883 /52.718, leaving calculated continuing amounts **5.889 /9.670 /11.181**. This is not proof of a maintenance/growth split. S2 describes H1 2025 discontinued intangible acquisition payments as earn-outs on prior acquisitions; do not automatically treat all historical intangible purchases as organic replacement capex.

The 2025 combination of PPE cash purchases, continuing intangible payments and full finance-lease cash service (principal18.669+interest6.395) equals31.426, or0.573% continuing revenue. This is a descriptive hybrid because some PPE/lease lines remain consolidated, and renewals are lumpy. It is not sustainable reinvestment estimated to three decimal places. H1 2026 investing outflow7.688 plus leaseprincipal8.528 totals16.216 or0.431% revenue, before lease interest; again it misses noncash new lease/software obligations.

December 2025 finance-lease liability was122.653; cash payments were22.500 in2026 /22.483 in2027 /22.218 in2028 /22.131 in2029 /22.131 in2030 /28.809 thereafter. Average remaining finance-lease term6.3years. Operating-lease payments33.655 total. H1 new ROU60.319 and unpaid licences11.897 are material relative to these schedules. Update the cash-service ladder, liability balances, renewal assumptions and licence payable maturity before using them in a valuation.

**Recommended preferred structure:** use an asset/cohort forecast with finance leases treated as financing in FCFF. New leased asset additions are noncash investment, explicitly paired with new lease debt. Forecast asset depreciation, licence amortisation, lease principal/interest, owned cash capex and licence payments separately. In the EV-to-equity bridge deduct finance-lease debt once; do not also value the same principal as an operating rental expense. Forecast future renewal investment by asset life/capacity, not only existing-contract expiry.

An alternative cash-rental convention is acceptable if finance-lease ROU amortisation and finance-lease interest are removed from reported costs and full future lease payments are charged in cash operating costs, with no second finance-lease-debt deduction. Actual cash taxes require their own bridge: lease principal is not automatically tax-deductible just because the valuation calls it rent. Do not mix the two conventions.

## Working capital and taxes

Net revenue excludes publisher inventory costs; receivables/payables reflect cash settlement of the underlying advertising activity. S1/S2 revenue policy specifies generally payment30days after month-end and cancelable contracts. DSO computed on reported net revenue is a proxy and cannot be equated to contractual payment days. Gross advertiser billings, take rate and full cash settlement timing were not found; this prevents a precise structural receivables-days model.

S1 Note5 splits 2025 accrued/current liabilities572.868 into accrued taxes451.594, compensation18.335, deferred revenue47.682, other55.257. 2024 counterparts263.703 /49.559 /37.053 /51.216. Excluding tax funding:

- 2025 operating WC =1,819.366+124.330-746.977-18.335-47.682-55.257=**1,075.445**, or**19.62%** of revenue.
- 2024 equivalent =1,283.335+140.470-504.302-49.559-37.053-51.216=**781.675**, or**24.25%** of revenue.
- Narrow `(receivables-payables)/revenue` =24.16%(2024),19.57%(2025). June2026 narrow stock is2,171.017-778.942=1,392.075:20.38% of TTM revenue6,829.124 or18.48% of twice-H1 revenue7,532.270. The latter is only an annualised diagnostic, not a seasonal forecast.

Subtracting all accrued liabilities, including taxes, produces an approximately11.38%2025 ratio and explains how a superficially plausible12% shortcut can hide tax funding. S2 combines leases/other current accruals and does not give the same detailed June tax/compensation split. H1 cash-flow working-capital usage504.797 includes tax and other timing, not only operational expansion. Cash tax paid639.820 exceeds tax expense464.783; this must be reconciled rather than made a permanent WC headwind or benefit.

**Exploratory assumption bounds, not verified facts:** narrow AR-minus-AP stock18–24% of forward revenue, plus0–3% ancillary operating WC. Use a seasonally appropriate annual revenue base; initialise from actual dated balances and explicitly transition the ratio. Stress narrow ratio30% for worsened customer settlement/publisher terms. Never count tax accrual as permanent negative reinvestment. Model cash tax settlements separately from normalised operating tax. At3% terminal growth, incremental narrow WC alone is0.524–0.699% of terminal-year revenue; positive growth consumes cash even with fully expensed R&D.

## Forecast horizon and bounded exploration

Keep a five-year shareholder horizon if requested, but use a **ten-year explicit business transition** through approximately2036, with acquired-amortisation runoff and lease/software renewals inside it. A2031 horizon equity value should include the remaining2032–36 forecast and a mature residual; it need not force the business mature in2031. H1 assets have customer-relationship useful life5.9years and finance leases previously6.3years, while the base/bull growth paths still end at8%/12%. Dropping immediately to3% perpetuity in year6 is a large untested discontinuity.

Use fiscal years and an initial6October-to31December2026 stub, with explicit dated cash flows. A JuneTTM figure is not an October operational roll-forward. Unsupported intervening actuals must remain clearly absent; an estimated stub is an assumption. Do not pretend FY2027 cash is exactly one year from the valuation date.

For research exploration after liability/asset schedule reconciliation:

- Forecast cost buckets from the history above; test normalised after-SBC EBIT margin excluding acquired amortisation of**60–80%**, focused base sensitivity**70–78%**. These deliberately broad bounds reflect observed recent77–79% and the earlier62%2024 margin. They are no assurance that60% is a downside floor. A platform/customer-economics failure case can require lower margins or a finite/declining business.
- Test economic SBC burden of**4–7% revenue**, with a**10%** stress, and cash-R&D burden**2–4%** in mature periods. The lower points are near recent observations; higher points challenge perpetual extraordinary revenue/employee leverage. These are analyst stress assumptions, not measured market wages or a future grant schedule. Expenses must sum to the selected margin; do not attach these costs to an already-after-SBC margin again.
- Tie cloud/network cost to activity and capacity, and test a**2–5percentage-point increase in cost/revenue**. Current absolute cloud cost cannot be isolated. Model commitments/prepayments without charging expense twice.
- In a capitalised-assets convention, set mature **cash/noncash replacement investment equal to recurring depreciation/amortisation** plus positive asset expansion for growth. Acquired legacy amortisation is excluded from the replacement identity. Test required net operating PPE/licence stock of**1.5–3% revenue** as an explicit capacity assumption around observed netPPE1.6–2.2%; licenced additions and classification limitations prevent calling this verified. Use cohort useful lives rather than deriving depreciation solely from revenue. Cloud capacity is separately expensed. If asset intensity declines, releases must be finite, bounded by the existing stock, and stop before terminal.
- In a cash-rental convention, a**0.5–1.0% revenue** combined rental/PPE/licence cash burden is an exploratory mature operating-cost range around the2025 descriptive0.573%; a**2%** stress addresses larger renewal/capacity obligations. Do not approve that range until June additions are classified and their future payment terms known. It replaces the associated leased depreciation/interest; it is not an additional charge on a capitalised-assets model.
- Test mature revenue growth**0%,2%,3%**, with3.5% only an upside sensitivity tied to durable nominal activity. Use gradual scenario-specific growth fading; do not fit growth or margins to the share price. Under decline, finite receivables releases are permissible, but cannot recur forever.

The nonnegative mature capital expansion identity is a discipline, not proof that all valuable growth needs balance-sheet capital: `net capital investment = change in required operating asset stock`; `total growth cash burden = net capital investment + change in operating WC`; expensed R&D/cloud/support costs are already in operating profit. A simple economic-ROIC terminal formula would require capitalising R&D/customer investment and consistent amortisation/denominators. The filing's low book-capital denominator alone cannot establish an infinite sustainable ROIC.

## Sensitivities and conclusions still withheld

Use one-at-a-time tests on sustainable margin, SBC/cash-R&D intensity, cloud cost, WC stock/transition, lease renewals/licence payments, tax shield, terminal growth and fade length. Illustrative scale at10bn annual revenue: a5point EBIT-margin reduction costs395m after21% tax; at3%growth moving narrowWC18%to24% consumes17.476m more annual terminal cash, plus a potentially much larger one-time stock-transition cash requirement. Margin/durability dominates the small PPE-line precision. Verify all scenarios with the same timing and claims/financing logic.

This review establishes why the original perpetual D&A construction fails, supplies company-specific expense/investment/WC facts, and proposes a coherent forecast architecture. It does **not** approve the exploration bounds as final scenario inputs. Current intrinsic value, current-price attractiveness, accepted reverse-implied expectations, actionable entry levels and definitive shareholder returns remain withheld until: June lease additions/payment maturities and software liability are reconciled; the cash-tax/book-amortisation bridge is established; starting operating WC/tax balances and October/stub timing are reconciled; revenue/margin scenario economics have independent challenge; current existing claims and financing/cash bridges are completed; and the rebuilt model receives review.

Continuation: first classify the60.319m ROU additions and11.897m licence payable using pre-cutoff filings/issuer disclosure; build financing-consistent renewal and asset-runoff schedules; establish dated opening WC and taxes; then rebuild a separate new run with ten-year business transition and review the results. Do not lift withholding merely because the replacement equations recalculate.
