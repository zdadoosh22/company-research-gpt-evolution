# Refinement verification — 7 October 2026

The local extension was refined by three independent implementation reviews and parent integration review. The confirmed mandate is aggressive growth over days to a few months, no intraday requirement, with the isolated £300 declaration recorded. No real investment, broker connection or phone message was made. Cash is user-declared rather than independently verified at Trading 212.

## Executed checks

165 tests pass: 51 original evidence/calculation/lifecycle checks and 114 extension checks. The machine-readable run, module counts and results are in `refinement-report.json`. Eight seeded histories exercise 2,400 mixed ledger operations, with an independent cash/share/reservation model. Tests include duplicate reports, partial fills, fees, sell deficits within spare cash, cancellation/reopening, failed writes, abrupt process exit and concurrent reads.

All 110 company/methodology files in the original integrity baseline remain unchanged. The live SQLite database passes integrity checking. Both daily and latest-ledger backups were restored into separate temporary databases and passed integrity checks. The daily opening backup remains legitimately unfunded; the refreshed ledger backup contains the later £300 declaration.

The revised Windows task was started, stopped through the removal helper, removed, re-registered and restarted. Task action identity is checked before replacement/removal; the helper verifies stopping. Windows PowerShell's default script-file restriction was handled for that one process without changing saved policy. Fresh runtime ticks confirm that the task executes the revised service. Sleep, power loss and actual network outages were not imposed on the user's machine; those recovery paths use controlled fixtures. No power settings changed.

Live primary-source checks again retrieved the three issuer-checked SEC feeds. Unilever UK website pages still return403 and remain a coverage gap. The SEC JSON metadata does not establish full-document reading or comprehensive UK disclosures. The investigation found no verified reliable free local replacement; accessible LSE raw HTML was a JavaScript shell, not functioning RNS discovery.

## Fixed issues

- Ledger snapshots previously could combine cash and holdings from different commits. Consistent read transactions now prevent that mismatch.
- Default Decimal precision could discard tiny fractional fills. Bounded exact inputs and high-precision local arithmetic now reject unsupported representation instead of silently rounding it.
- Sell fees greater than gross proceeds now work only when spare unreserved sleeve cash can cover the deficit.
- Transport rejects unrelated pending transactions, conflicting deduplication content, malformed responses and credential-bearing redirects. Callback acknowledgement follows committed ledger/reply processing.
- Provider-accepted sends with uncertain results are not automatically repeated. Fault tests cover the acceptance/write/crash boundary and retry bounds.
- Immediately before dispatch, a database guard supersedes withdrawn/expired active notices. Withdrawal can still follow that check; messages remain dated history requiring current status. No current notice approves trading.
- Research checkpoints are saved before model calls; raw tool/error transcripts are excluded from the persisted reduced audit. Context mutation, future evidence timestamps and malformed lifecycle output fail safely. Actual model identity remains unknown if not reported.
- Review-ready research jobs require an existing, contained, readable, schema-validated saved draft. Failed finalisation marks claimed work interrupted immediately rather than leaving it running indefinitely.
- HTML source changes now preserve document link targets and track successive transitions, including a return to previously observed content.
- A failed source pass commits its failure record before another HTTP fetch, preventing a prolonged write lock from blocking manual ledger reports.
- Primary-source redirects are checked before contacting their destination. Recovered source coverage sends a separate recovery notice; unchanged failures do not continually repeat alerts.
- Latest-ledger backups refresh after manual record changes while daily opening snapshots remain immutable recovery points.

## Synthetic exit comparison

`short-term-simulations.json` contains four fictional paths comparing stop-market, stop-limit, delayed thesis and time exits. They demonstrate temporary recovery after a stop, deterioration during manual delay, gaps beyond a limit and gradual appreciation. The numerical stops, prices and delays are deliberately constructed fixtures. A separate fee-only example shows repeated round trips reduce capital even at unchanged prices.

These are mechanical illustrations, not historical performance, calibrated probabilities, proposed stop thresholds or a strategy ranking. They assume simplified execution and explicitly preserve unfilled open positions. Real quote quality, liquidity, queue position, broker trigger rules and applicable instrument costs must be checked separately. Trading 212 documents that a stop-limit can remain pending beyond its price range. [Official stop-limit guidance](https://helpcentre.trading212.com/hc/en-us/articles/360007081297-Stop-Limit-Orders).

## Remaining acceptance work

The operational observation period has only begun; tests do not replace fourteen days of actual operation. Telegram configuration and locked-iPhone delivery remain unverified. No unattended quote source, Gemini entitlement/quality acceptance, complete company research or numerical portfolio strategy has been validated. The approved methodology and partial pilots remain unchanged. Current research outputs are drafts and real buy/sell recommendations stay disabled.

`monitoring/IMPROVEMENT-ROADMAP.md` defines the ordered development, short-horizon evidence dossier, prospective exit comparison, cost-aware performance accounting, realistic delayed execution and criteria for later actionable development. The user has already authorised implementation; remaining work concerns evidence and account setup rather than repeated permission questions.

Final additions: per-source outcome/timing history starts at the refinement date, without invented earlier checks. Latest-ledger recovery inspects the backup itself rather than trusting metadata across a crash; corrupted latest copies can be rebuilt from primary state. A real-source Unilever short-horizon screening trial identifies the scheduled event but withholds an investment opportunity because expectations, price and portfolio foundations are absent. See monitoring/studies and monitoring/SUFFICIENCY-REVIEW.md.
