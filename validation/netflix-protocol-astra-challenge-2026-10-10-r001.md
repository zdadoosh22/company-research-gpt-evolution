# Independent Netflix pre-event protocol challenge — 10 October 2026, r001

**Disposition: corrections required before acceptance.** Three medium findings concern the new protocol only. Limited daily descriptive research remains feasible in principle; none requires a paid source, a model revision or a repeated foundation audit.

Review performed by the independently delegated task `/root/netflix_protocol_astra_r001` through the actual requested `gpt-6-astra`, `high`, fresh-context route, confirmed by the parent dispatch. Backend model identity, actual reasoning setting and service tier were not exposed to this reviewer and remain unknown. This is separate from author arithmetic checks.

## Exact reviewed inputs

- `monitoring/studies/2026-10-10-netflix-pre-event-protocol-r001.md` — SHA-256 `1a130711a2b971c448eaeab5dd27472820471f3275e756792a9c1e5fa1f65ebf`.
- `monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/frozen-reference-r001.json` — SHA-256 `9d2ea88cc2ea978d053346752f6f711d2d8f0150819522718ef85bc2dec56eec`.
- `monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/source-retrieval-register.json` — SHA-256 `bd1af15a9e12b8641e849875ab85ef968596148dc160d4810d599baf905fb48a`.
- `validation/netflix-protocol-baseline-2026-10-10-r001.json` — SHA-256 `6339a7555b8dc404e08dcd9dfd0450490c06401f0ca73f2aaca4dcd708b0e546`.

The companion JSON also binds inspected contextual predecessors, the user objective and all ten raw captures. All 534 baseline predecessor hashes were independently recomputed unchanged. Hash agreement confirms preservation, not analytic validity.

## Findings

### NFLX-PROTOCOL-ASTRA-001 — medium / P2

The frozen NFLX and SPY timestamp snippets join a regular-session timestamp to the following after-hours price, while XLC loses an available timestamp. The history tables explicitly identify S&P Global Market Intelligence and daily after-close updates; the general Nasdaq UTP 15-minute quote description does not establish the history tables are that feed or available 15 minutes after close.

Evidence:
- NFLX raw header: regular close 70.30 at October 9 16:00 EDT; separately after-hours 70.32 at 19:59 EDT. Daily Close is 70.30.
- SPY raw header: regular close 778.57 at October 9 16:00; separately after-hours 778.59 at 19:51 EDT. Daily Close is 778.57.
- XLC raw header: 110.38, October 9 16:00 EDT, market closed. Daily Close is 110.38.
- All three history footers identify S&P Global and daily after-close updates. General data-sources page separately discusses CBOE real-time quotes and delayed consolidated Nasdaq UTP open/close.

**Required correction:** In a preserved-input amendment, record each regular close value, timestamp/time-zone basis and separate after-hours value/time where supplied. Mark no observed regular-close disagreement in these samples. Attribute historical rows to their explicit S&P footer and keep general quote-feed information separate. Retain historical session dates and actual retrieval/first-observed availability; make no 15-minute historical-row publication guarantee. Explicitly reject a future same-session same-basis conflict pending resolution rather than treating after-hours as conflicting close.

**Outcome:** open; author amendment and parent resolution are separate.

### NFLX-PROTOCOL-ASTRA-002 — medium / P2

The economic forecast horizon FY2027-2029 is specified, but H has no fixed adjudication date or eligible-evidence cutoff. D20 is called the primary price persistence/reversal endpoint only. Recording availability timestamps without defining the information set eligible to decide H leaves an investigator free to use later favourable disclosures to settle the original Q3 hypothesis or move its assessment date.

Evidence:
- H requires forward source support and permits the interview to change classification, but specifies neither a final economic classification time nor frozen intermediate classification records.
- D1/D2/D5 mark information sets and D20 is a price endpoint; no instruction excludes information first available after a chosen economic cutoff from the primary H adjudication.

**Required correction:** Predeclare the primary H adjudication cutoff and the allowed source/availability boundary. One adequate design is primary H as of D1 close using release/interview and genuinely available follow-on evidence, with separately labelled D2/D5/D20 updates; another is explicitly designate D20 final H with frozen prior classifications. Choose before the event, preserve unresolved at the cutoff when evidence is insufficient, and exclude later evidence from retroactively changing the primary label. Any later economic change must distinguish Q3 evidence from intervening new developments. No numerical model update is required.

**Outcome:** open; author amendment and parent resolution are separate.

### NFLX-PROTOCOL-ASTRA-003 — medium / P2

The displayed interface ends after recurring acquisition cash and deducts interest but no principal or refinancing/funding requirement, yet calls itself the accepted reference interface for owner cash. The accepted r002 cash-franchise framework deducts scheduled principal and tests an explicit opening-liquidity condition. The broad reference to financing offsets and a later current-value bridge does not expressly require that funding reconciliation before classifying a durable per-claim owner-cash improvement.

Evidence:
- Protocol formula: recurring OI through acquisition cash, including cash interest, but omitting scheduled principal/net financing and liquidity reconciliation.
- Accepted r002 specifies 2027-2029 principal payments, no assumed refinancing or new borrowing to fund distributions, and the conditional opening reserve. Those are unchanged baseline constraints, not newly proposed economic assumptions.
- A positive recurring pre-principal cash direction can coexist with a larger debt-service need or failed funding condition; the latter cannot be labelled funded distributable owner-cash improvement solely from the displayed formula.

**Required correction:** Label the displayed interface as recurring pre-principal operating-to-equity cash, then explicitly carry the existing debt-principal/service schedule, any independently evidenced refinancing costs and claims, liquidity reserves and funding continuity into H support. If debt/funding changes are unknown and could overturn the per-claim conclusion, classify unresolved. Do not subtract debt twice, add borrowing as free owner cash, or rebuild the accepted model. It is enough to demonstrate baseline financing/funding still holds for the claimed revision or document the bounded offset.

**Outcome:** open; author amendment and parent resolution are separate.

## Checks and sound requirements

- **All 10 freshly captured raw source hashes and byte lengths recomputed — pass.** Actual recomputation recorded in JSON.
- **Predecessor preservation independently recomputed — pass.** Actual recomputation recorded in JSON.
- **Actual raw source passages inspected — pass.** Terms/robots; all three history headers, first rows and provenance footers; data-sources quote and time-zone sections; annual forecast financial table/adjusted-EPS statement/contributor counts/update date; Yahoo revenue/EPS values and checked GAAP control; issuer event notice; latest SEC 10-Q metadata. Source defects reported above, not waived by hash matches.
- **Management references and arithmetic — pass.** Existing July PDF hash matches frozen authority; relevant archived derived passages confirm Q3 revenue12860/OI4268/EPS0.82, FY revenue51000-51400/margin31.5%, FCF approximately12500/cash-content-amortisation approximately1.1x. Independent FY implied OI calculation:16065-16191. No closed foundation calculation audit repeated.
- **Prospective event and session calendar — pass.** Issuer September14 notice schedules October20 13:01 Pacific release and13:45 interview; both are after16:00 New York regular close. Official Nasdaq calendar freshly opened shows no scheduled full/early closure October20-November17. Weekday count independently yields D1 October21,D2 October22,D5 October27,D20 November17.
- **Named-zone close conversion — pass.** Independently evaluated all five scheduled closes using America/New_York, UTC, Europe/London. All frozen offsets/times match, including October27 UK-only DST change and November17 US standard time.
- **Rights boundary — pass_with_limits.** Actual archived terms contain explicit exception for robot-compliant AI agents; robots wildcard disallows unrelated paths and specific other bots. Intended public paths allowed for declared agent. Limited factual snippets and local raw preservation match stated scope; no blanket future licence or legal opinion inferred.
- **Economic support and opposing cases — pass_subject_to_findings_002_003.** OI trigger and no-trigger category separate from revenue/EPS; positive operating profit alone insufficient; anticipated advertising/content/termination effects excluded; bounded offsets and per-claim evidence required; unknown offset magnitude defaults unresolved. Do not read plausibly fully reverse as contradiction without the following demonstrably-decisive condition.
- **Manual-delay and confound boundaries — pass.** D1/D2/D5 fixed prospectively; C20/Cdelay price-only ratios are not paper fills or ranking/optimisation. SPY/XLC are descriptive; sector self-inclusion, dividends, intervening news/interview, missing rows, intraday timing, postponement, reversal and no repricing are expressly addressed.
- **Current-value and authority boundary — pass.** January2027 conditional cash-franchise component remains separate from current equity value; cash/debt/claims/compensation/stub bridge and double-count exclusions stated. No approved numeric model revisions, expected return, allocation, entry or execution. Funding-interface finding concerns H definition, not reopening the valuation audit.

Calendar verification used the [official Nasdaq schedule](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule). The first, second, fifth and twentieth sessions after October20 are October21, October22, October27 and November17. All five New York/UTC/London close conversions match. No event outcome was queried.

The apparent sample close conflicts are rejected as a mistaken interpretation: regular close matches history for NFLX, SPY and XLC. The correction concerns extracted labels and distinct data-provider semantics. General future conflict/adjustment/missing-data gates remain appropriate.

The hypothesis is otherwise a defensible conditional research test: OI is the initial trigger, anticipated items cannot create a surprise by themselves, operating profit is not sufficient proof of owner cash, and unknown offsets leave the result unresolved. An interested management narrative is not enough without bounded economic constraints. The missing cutoff and debt/funding link must be closed before this test is frozen as ready.

## Remaining limits and endpoint

- Unknown backend settings; requested Astra High route recorded honestly.
- October10 frozen external context is not event-time consensus; actual estimator update timestamps unknown.
- S&P historical row availability timing is not guaranteed by general quote-feed documentation.
- No price outcomes, actual future disclosures, returns, backtests, paper fills, broker actions or monitoring changes were retrieved/performed.
- No numerical economic assumptions changed; complete current valuation and executable advantage remain unapproved.
- Parent disposition and any author amendment are separate and have not been approved by this original-input review.

No author protocol, frozen reference, model, operational configuration or predecessor was edited. No disposition or goal state was changed. Preserve these reviewed bytes and address the three findings in a dated amendment or new version; acceptance applies only after the corrections are inspected.
