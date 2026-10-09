# Market-data routes investigated

Verified official documentation on 7 October 2026. No data account was created, key connected, service purchased or automatic quote adapter enabled.

| Route | Documented cost/capability | Limit for this sleeve |
|---|---|---|
| Manually supplied Trading 212 snapshot and broker price alert | Existing account; structured manual quote input already implemented | No independent watchlist-price discovery; execution still requires the current order preview. |
| Alpha Vantage standard API | Free standard access is limited to 25 requests/day. Global Quote defaults to end-of-day updates; real-time and 15-minute delayed US data require premium entitlement. | Could support dated discovery/paper work, but cannot be labelled a fresh intraday quote. Selected listing coverage and timestamps require actual tests; no account/key exists here. |
| Twelve Data Basic | Official individual pricing lists free Basic at 8 API credits/minute and 800/day, real-time US equities/FX, international trial symbols and internal non-display usage. | Candidate for a narrow US paper-monitoring test. Complete market coverage, price-versus-bid/ask semantics, timestamps and permitted private-phone display must be verified. Basic must not be assumed to cover UK watchlists. |
| Twelve Data paid global/display packages | Pricing advertises Grow from US$29/month and Pro from US$99/month; the page also shows higher selected-credit packages. Paid Grow includes broader/end-of-day global coverage; UK real-time appears under higher coverage. | Actual selected credits, listing feed, display/non-display entitlement and any exchange add-ons determine the relevant price. No paid package selected; recurring data cost would be material relative to £300. |

Sources: [Alpha Vantage support](https://www.alphavantage.co/support/), [Global Quote documentation](https://www.alphavantage.co/documentation/), [Twelve Data individual pricing](https://twelvedata.com/pricing), [Twelve Data stock/market coverage](https://twelvedata.com/stocks).

These documented tiers are candidates, not verified live integrations. A useful free discovery feed may still be insufficient for an execution instruction. The initial manual-only implementation remains honest about that boundary. Do not use a search result, inferred price, inaccessible chart or JavaScript shell as a live feed, and do not weaken freshness checks to make an end-of-day price pass.

Recommended next investigation: test a selected free US data route only after checking account entitlement and permitted personal monitoring/display. Compare repeated timestamped snapshots with the broker for the same exchange/class and trading session; test market-close/weekend handling, corporate actions, rate limits, units, missing data and malformed responses. Preserve source/received timestamps and distinguish last trade from executable bid/ask. Later UK/global coverage needs its own route rather than presumed free US coverage.

No broker trading access is required to evaluate a market-data source. Do not buy a security merely to make its price visible through a holdings endpoint. Provider keys belong in locally protected credential storage, never research files or SQLite backups. Paid upgrades or overage purchases must never occur automatically.
