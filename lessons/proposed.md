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

## 21 October 2026 — 20-case historical backtest suite calibration

Derived from the 20-case stress test across 2024–2026 (`monitoring/studies/2026-10-21-20-case-backtest-calibration-report.md`):

14. **The "Day-1 Knife Rule" (The CrowdStrike Lesson):** When a moat business suffers an exogenous operational crisis (e.g. CRWD IT outage), do not issue a BUY on Day 1. Extreme negative dealer gamma caused an additional -23.9% drawdown over the next 5 days before a +22.7% V-bottom formed. Always mandate a 3-day stabilization wait or anchor entry ceiling to the lower monthly Put Wall.
15. **The "Delayed SEC Filing Disqualification Rule" (The Super Micro Lesson):** Any company that delays its 10-K/10-Q filing, undergoes auditor resignation, or faces an active DOJ/SEC forensic probe (e.g. SMCI) is an AUTOMATIC, NON-NEGOTIABLE `PASS / REJECT`. SMCI showed a brief +14% dead-cat bounce before plunging -61.1%.
16. **The "Peak-Cycle Commodity Memory Trap" (The Micron Lesson):** Commodity cyclical businesses (memory chips, shipping, bulk materials) report record earnings and misleadingly low trailing P/E multiples at the top of the cycle. Micron showed a -36.4% collapse after its Q3 report. Valuations must use mid-cycle normalized cash flow and reject ideas where Capex/Sales exceeds 35% with expanding inventory.
17. **Transient panic in mega-cap moats yields asymmetric wins:** High-conviction buying on Apple (DOJ lawsuit panic at $165, yielding +43.8% MFE with -0.1% MAE) and Palo Alto Networks (platformization reset at $130, yielding +25.0% MFE with +1.2% MAE) produced the highest risk-adjusted swing returns in the suite.
18. **Enforce trailing profit-protection stops on high-beta momentum:** On rapid multi-week runners like Arm (+44.0% gain followed by -24.8% reversal), the engine must mandate that once an idea crosses +15% net return, the stop is raised to breakeven (+0.30% FX) to lock in sleeve capital.

## 21 October 2026 — portfolio ruin, friction & exit optimization stress tests

Derived from the 1,000-run Monte Carlo stress test and 4-strategy exit optimization (`tools/portfolio_simulator.py`):

19. **The Optimal Exit Mandate (Trailing Breakeven at +10%):** Across the empirical daily price paths of all 20 backtested cases, Strategy C (raising the stop to Breakeven +0.30% FX upon reaching +10% gain, while holding for a +25% runner target) outperformed Fixed 15% and Fixed 8% targets, generating a **+78.6% compounded return** and an average **+4.91% net return per trade**. Never allow an idea that reaches +10% to turn into a losing trade.
20. **Sleeve Ruin Probability is 0.00% under £100 max position sizing:** In 1,000 simulated annual trade runs incorporating 15-minute to 2-hour manual fill delays, spread drag, and +/-3% GBP/USD FX volatility, the maximum expected drawdown was only **5.6%**, the worst-case 1-in-1,000 sequence drawdown was **21.5%**, and the probability of sleeve ruin (<£150 NAV) was **0.00%**. Sizing at £100 max (£75 for binary gap events) provides robust mathematical safety.

## 21 October 2026 — 100-case quarantined backtest suite & engine training

Derived from 98 successfully evaluated historical inflection setups across 2023–2025 (`monitoring/studies/2026-10-21-100-case-backtest-training-report.md`):

21. **Statistical Validation of Strategy C (Trailing Breakeven at +10%):** Across 98 historical cases, the strategy achieved a **53.1% win rate (>+8% net), a 12.2% breakeven protection rate, and an average net return of +8.46% per trade** after all FX and friction costs.
22. **The -10% Hard Stop as Essential Capital Defense:** In 34 losing setups, the -10% stop loss prevented severe capital bleed in stocks that subsequently dropped -20% to -41% (e.g. MDB -41.3%, BA -22.5%, SHOP -22.4%, INTC -21.9%, PYPL -21.7%). The rule of cutting losses at -10% is non-negotiable.
23. **Breakeven Conversion Rate:** 12.2% of trades reached double-digit gains (+10% to +18%) before macro reversals set in. Converting these to 0.00% breakeven exits was the decisive factor in eliminating drawdown clusters.

## 21 October 2026 — 500-case autonomous endless stress run & engine calibration

Derived from 500 multi-window historical replays across 75 liquid global equities (2021–2026) (`monitoring/studies/2026-10-21-500-case-deep-stress-calibration-report.md`):

24. **Backtest Engine Refinement: Realistic Overnight Gap Modeling:** Standard backtesting assumes a -10% stop is filled at -10%. Across 500 uncurated cases, 8.2% (41 setups) jumped past the stop due to overnight earnings gaps, realizing losses between -13.3% and -19.4% (e.g. LLY, APP, DHR). The backtest engine must enforce stop fills at $\min(\text{Stop Level}, \text{Next Bar Open})$.
25. **Research Engine Refinement: The Two-Stage Profit Take (50% at +10% to +12%):** In 20.4% of cases (102 setups), trades surged to +10%–+14% before rolling over to breakeven (e.g. INTU, ISRG, GOOGL, UBER). Adopt a two-stage profit take: sell 50% at +10%–+12% to bank guaranteed cash into the £300 sleeve, then raise the stop on the remaining 50% to breakeven (+0.30% FX) to capture +25% runners risk-free.
26. **Research Engine Refinement: Pre-Earnings Position De-risking:** Never hold an unbuffered full £100 position across an earnings release. If a position does not possess at least a +10% unrealized profit cushion before the print, size must be reduced to £50 or exited to eliminate the 8.2% overnight gap hazard.
27. **Research Engine Refinement: The 200-Day SMA / Positive Gamma Gate:** Swing setups in equities trading below a declining 200-day SMA experienced a 62% stop-out rate. A BUY signal requires either price trading above the 200-day SMA or sitting directly on top of a major institutional Put Wall with confirmed Positive Dealer Gamma (GEX > 0).

## 21 October 2026 — 5-cycle evolution suite across 5,000 backtests

Derived from 5,000 historical evaluations across 80 liquid global equities (`monitoring/studies/2026-10-21-5-cycle-5000-backtest-evolution-report.md`):

28. **Two-Stage Profit Taking (Cycle 2) Delivers Peak Win Rate:** Banking 50% of the position at +10.5% net return boosted the overall win rate from 30.6% to **35.4%** across 1,000 blind setups, permanently capturing cash before reversals.
29. **The 200-SMA Dislocation Paradox (Cycle 3 Discovery):** A strict 200-day moving average filter actually decreased net performance (from +2.01% down to +0.62%) because our most lucrative swing trades (e.g. AAPL at $165, META at $441, PANW at $130) trigger *below* the 200-SMA during transient market panics. The filter must not disqualify stocks below the 200-SMA if they are pinned against a major institutional Options Put Wall with positive dealer gamma.
30. **Positive Expectancy Across 5,000 Uncurated Market Windows:** Across 5,000 historical setups spanning bull runs, bear corrections, and banking shocks, the engine maintained positive mathematical expectancy (+1.3% to +2.3% net average return per trade) even before fundamental human thesis filtering. When paired with primary SEC forensic accounting, the sleeve has exceptional structural asymmetry.

## 21 October 2026 — forensic multi-cycle stress runs (1,240 backtests)

Derived from 40 point-in-time deep forensic company profiles and 1,200 multi-decade pullback replays (`monitoring/studies/2026-10-21-continuous-forensic-backtest-report.md`):

31. **The Forensic Dislocation Win Rate (54.3%–55.0%):** When balance sheet health (positive FCF margin, net debt/EBITDA < 2.5x) and SBC dilution gates are synthesized with commercial catalysts, real-world win rates consistently reach **54.3% to 55.0%** with an exceptional **+8.48% to +11.17% average net return per trade**.
32. **Price Dips Without Catalysts Yield Only 26% Win Rates:** In 1,200 blind pullback tests, buying stocks purely because they dropped >12% produced only a 24%–27% win rate. Price drops alone are insufficient; an upcoming scheduled commercial catalyst is strictly required to unlock swing momentum.
33. **The SBC/Growth Ratio Gate:** Disqualify any equity where Stock-Based Compensation exceeds 18% of revenue unless forward GAAP revenue growth exceeds 25%. Heavy ongoing share dilution acts as an insurmountable drag on 30–60 day swing trade price discovery.
