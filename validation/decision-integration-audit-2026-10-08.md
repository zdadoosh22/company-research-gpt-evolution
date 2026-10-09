# Decision integration audit — 8 October 2026

Read-only review by delegated agent `/root/decision_integration_audit`. This report is the only workspace file written. All execution probes used fictional test fixtures and temporary databases; they establish engineering behavior, not analytical approval or permission for real instructions. No credentials, live operational state, delivery or broker access were used.

Reviewed `decision_lane.py`, `alert_contract.py`, `decision_readiness.py`, their tests, `DECISION-SCOPE.md`, the Astra extension review, and project instructions/acceptance/extension documentation. The parent was already correcting the missing decision gate in the contract and adding raw-byte artifact registration; those changes are not outstanding findings here.

## Prioritised findings

### P1 — Persistent issuance is not integrated with current confirmation

`DecisionLane.issue` checks immutable artifacts, the instruction's overall expiry and equality of the local portfolio excluding its own reservation. It does not call `AlertBook.confirm`, consume a confirmation, revalidate reconciled portfolio facts, or require current quote, monitoring, session, activation, phone and operational-trial evidence. `reserve` also has no quote/session validation. The real `ArtifactVerifier` interface accepts `GateEvidence` and returns `VerifiedArtifact`; the lane requires four-argument callbacks returning `ArtifactAcceptance`, with a different scope (`security_key`, without `quote_fingerprint`). There is no production adapter between these interfaces in `tools/`.

Reproduction: use `DecisionLaneTests.setUp`, `prepare(instruction())`, and `reserve(key, portfolio)`; advance `now` by ten minutes; call `lane.issue(key, verify)`. Result: `state='issued'`, while the original executable quote and monitoring timestamp are 600 seconds old. The fixture callbacks are deliberately fictional typed artifact approvals, so this demonstrates that lane issuance itself has no current-confirmation requirement; it does not claim the real verifier approved stale evidence.

Required acceptance: one persistent orchestration path must obtain actual artifact/current-state verification, atomically reserve the exact reviewed capital, bind the confirmation to instruction and ledger versions, and recheck the shortest price/session/event/evidence deadline immediately before issuance. A reservation changes the public portfolio fingerprint, so document whether confirmation binds the pre-reservation view plus its own reservation or the post-reservation view; otherwise composing the modules naïvely makes the confirmation stale on successful reservation. Test current quote changes, session closure, expired refreshed confirmation, changed external reconciliation and restart/duplicate issuance through that integrated path. The dormant lane currently sends nothing, so this is a missing goal component, not a claim of active unsafe delivery.

### P1 — Inconsistent actual fills disappear instead of entering suspense

`report_fill` raises before inserting a raw event for over-reservation, over-quantity, absent broker order, cancellation-followed-by-late-fill and conflicting replay. `_atomic` rolls back the transaction. `reconcile_cancel` only releases an exactly matched remainder; it cannot account for an exceptional execution or adjust cash/shares from broker evidence. This repeats the precise accounting requirement in the Astra extension review. The separate observation ledger's exception handling does not protect the new decision database.

Reproduction: issue a one-share buy with a £100 reservation, report `order1`, then `report_fill(key, 'overrun', '1', '101', '0')`. Result: `ValueError('Actual fill exceeds reserved total; reconciliation exception required')`; zero matching `fills` rows, zero `reconciliation` rows, and £200 still shown as available. The report was rejected, but its content was not retained and new commitments are not globally frozen for this discrepancy. A fill after `reconcile_cancel` is similarly rejected as absent/unresolved order state.

Required acceptance: retain authenticated well-formed execution reports immutably before classifying them, keep inconsistent reports in suspense, expose potential cash/share exposure and block fresh commitments until an evidence-bound adjustment resolves them. Do not charge unrelated ISA funds or silently rewrite the original instruction. Test overrun, cancellation/fill ordering, late report and conflicting execution replay; reconciliation must retain before/after balances and exact broker/execution references.

### P1 — The documented £100 issuer/shared-catalyst budget is not enforced by the lane

`reserve` checks `max_gbp_cost <= per_idea_cap_gbp` and one outstanding instruction for the exact security. A filled instruction drops out of outstanding exposures; holdings have quantities but no issuer/catalyst relationship or capital-budget use. Consequently new identifiers can repeatedly fund the same issuer. `DECISION-SCOPE.md` explicitly adopts no more than £100 exposed to one issuer or shared catalyst, not merely £100 for each separately named order.

Reproduction: using `DecisionLaneTests`, repeat three times with distinct alert IDs and broker/execution IDs but the same `AAA` security: prepare, reserve £100, issue, report order, then fill one share for £90. All three succeed. Final holdings: three `LSE:AAA:ordinary` shares; available cash: £30; aggregate entry spend: £270 in the same issuer. A correctly implemented external portfolio-policy validator could block this, but no actual integrated validator is present and the lane's deterministic controls do not enforce it.

Required acceptance: bind exact listings to issuer and catalyst groups, freeze the policy's exposure basis, and account for held plus pending/reserved commitments against the adopted £100 budgets. Decide explicitly how sale proceeds, realised losses and profits affect the original tranche budget; the addendum currently keeps profits in cash. Test repeat entries, different classes/listings of one issuer, shared catalysts and partial entry/exit. This needs explicit policy semantics, not an invented stop or probability.

## Controls that worked

- Concurrent reservations use `BEGIN IMMEDIATE`; the two-thread fixture permits one reservation and rejects the second stale snapshot. No double-spend was found in this path.
- Artifact version conflicts, scope mismatches, changed content hashes, untyped boolean proofs and stale proof timestamps fail closed.
- Pending and partial fills preserve the remainder; withdrawal/expiry retains unresolved cash/share exposure. Revision creation is blocked while the earlier revision has unresolved exposure.
- Same-ID order/fill replay is idempotent when exact; successful cancellation release requires a typed evidence-bound proof. These are useful controls and should be preserved while adding suspense records.
- The readiness verifier rereads pinned registry/artifact/review/evidence hashes, checks scoped source reading chronology and coverage, and demands current validators for operational facts. Hash equality establishes integrity and identity; the named reviewer and actual validators still own factual truth.

## Verification and limits

Fresh execution: 41 `test_decision*.py` tests passed and 18 `test_alert_contract.py` tests passed, plus the three isolated reproductions above. Concurrent parent edits may add tests afterwards; these counts describe this audit run only. No existing tests exercise a real end-to-end verifier → reservation → current confirmation → persistent issuance path, exceptional-fill reconciliation in the decision lane, or aggregate issuer/catalyst budgets.

The audit does not reopen company analyses or certify a candidate dossier. Independent current prices, reconciled broker evidence, actual device/trial acceptance and a completed reviewed opportunity remain external or analytical dependencies. The three findings above are independently implementable machinery required for the authorised goal; profitable performance, new subscriptions, completion of every historical pilot or additional strategy questionnaires are not proposed gates.
