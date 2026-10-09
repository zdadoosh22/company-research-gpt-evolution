# Observation implementation verification — 7 October 2026

The local foundation is implemented and running through Windows Task Scheduler. This is engineering verification, not research acceptance or permission to treat pilots as trading signals. This document preserves initial implementation checks; subsequent refinement now passes 165 tests. See refinement-report.md/json for the current checks, declared £300 funding and aggressive days-to-months mandate.

## Verified

- 112 tests pass: 51 pre-existing checks and 61 new ledger/adapter/transport/service checks.
- Real Codex subscription smoke run returned an unapproved observation draft. ChatGPT authentication was verified; model identity was requested/pinned but not returned in CLI events. No company thesis or Gemini comparison was validated by that smoke.
- Windowless Windows task registered and started; runtime tick observed. It runs as the signed-in user, with startup recovery at sign-in and scheduled 09:00/18:00 triggers. No power settings changed.
- APP, JPM and Unilever SEC submission baselines fetched and issuer identities checked. First retrieval does not queue historical documents as new events.
- 110 pre-existing company/methodology files match the recorded integrity baseline. Company indexes, partial pilots and approved methodology are unchanged.
- Actual Windows DPAPI encryption/decryption was tested using temporary fake credentials. No Telegram account was connected and no real notification sent.

## Tests with practical consequences

Tests exercise funding limits, isolation from unrelated shares/cash, duplicate execution IDs, partial fills and fees, sell reservations, cancellation, cash events, invalid/missing quote metadata, stale and exchange-mismatched marks, and unknown NAV when conversion is unsupported.

Service tests cover first-source baseline, deduplication, source failure rollback, daylight-saving slots, access challenges, incoming command transactions, pending-alert withdrawal, recovery of interrupted jobs, SQLite backups, overlapping engine exclusion, failed context preparation and unapproved draft job completion.

Transport tests cover recipient/sender authorization, atomic command/reply/offset processing, uncertain send outcomes, interrupted delivery, retry bounds, idempotent edits, response redaction and credential protection. They do not establish iPhone delivery.

## Review corrections

Independent implementation review found and prompted fixes for early Telegram ledger commits, concurrent daemon/manual ticks, stranded research jobs, partially committed source passes, group-chat permissions, ambiguous cross-listing valuation and concurrent snapshot writes. This review is separate from the project's Astra analytical review.

## Limits

Unilever's two configured UK website pages returned HTTP 403. The gap remains visible; SEC availability does not establish complete UK disclosure coverage. Price acquisition is manual. Phone credentials, real iPhone checks, policy, funding and analytical acceptance remain incomplete. The 14-day observation period has only begun. No elapsed-time or config-only route enables real recommendations, broker access or orders.

Runtime database, source archives, research drafts and status snapshots are in `state/observation/`. Daily database backups exclude credentials and are local rather than off-device backups. See monitoring/START-HERE.md for setup, commands and reconciliation.
