# Bounded research engine

Implementation follows the authorised r002 brief and its dated user clarification. This document records implemented interfaces while the larger slice remains incomplete. Company judgement, opportunity economics, portfolio policy and execution remain separate. The existing observation service retains `research_enabled=false`.

## Explicit checkpoint commands

From the project root:

```powershell
.\tools\run.ps1 checkpoint --start --record validation/engine-slice-2026-10-15-r001/checkpoint-start.json
.\tools\run.ps1 checkpoint --complete --record validation/engine-slice-2026-10-15-r001/checkpoint-complete.json
.\tools\run.ps1 engine-status
```

The example input paths must contain the actual dated event before use; the commands do not invent a completed task. A checkpoint has schema version1, stable lowercase `id`, `task_id` and `turn_id`, `phase`, timezone-aware creation/observation times, origin, request, work, outcome, bound artifacts and check records, blocker changes, proposed readiness impact, next action, unknowns and supersession references. Each artifact is an exact project-relative path/SHA256 pair. Check evidence must be included among those bound artifacts. Input files and evidence use explicit nonprivate project families; operational databases and credentials are rejected.

`--start` uses `outcome=null` and empty completed work/check lists. `--complete` requires a matching valid start and an outcome of `complete`, `partial`, `failed` or `interrupted`. Proposed impact is `improved`, `unchanged`, `reduced` or `not assessed`; an improvement/reduction requires a named requirement and evidence. It is a recorded explanation, not a trusted gate attestation. The checkpoint writer rejects nonempty `verified_gate_changes`; a separate current-state verifier must establish actual gate changes.

Events are immutable, deduplicated by task/turn/phase, and stored under `monitoring/research-engine/checkpoints/`. Repeating the identical event is idempotent; reusing its identity with different contents is rejected. Corrections use new dated identities and preserve predecessors. A missing completion renders exactly “turn ended; outcome not recorded.” Invalid or changed evidence invalidates the displayed completion rather than silently retaining success.

## Rebuilding and inspection

`engine-status` reconstructs `state/research-engine/status.json` and `status.html` from checkpoint files. These are derived views. The HTML is static, escapes source text, loads no remote resources and serves no arbitrary filesystem routes. No polling server, model summary, hook or scheduled task is installed.

The projection displays all ten gates separately and live recommendations as disabled. It revalidates saved case chains on every rebuild, showing their disposition, review status and limitations. A broken newer record does not silently revive an older disposition. Multiple unresolved disposition lineages are ambiguous. A `complete` task outcome does not claim the entire engine is complete. Final release acceptance and the real model cycle remain required.

For recovery, retain immutable event files and their referenced artifacts, then rerun `engine-status`. Deleting only the two derived status files loses no authoritative event history. Do not delete or rewrite an event to conceal an unsuccessful outcome. Output updates use an exclusive writer lock and atomic replacement; a crash after event persistence can be repaired by rebuilding the view.

## Development and rollback boundary

Development is isolated in `C:/Users/aidan/cr2-engine` on `codex/research-engine-slice-r001`, based on `ccd49d083c0e6921917a5d0b813b10b4955a6d72`. The running observation service uses the original checkout. The development slice was installed there on16October: see the version-bound `INTEGRATION-20261016-r001.json` and r002 records under `validation/engine-slice-2026-10-15-r001/`. No changed module was in the observation import closure, so no service restart or live queue migration was performed. Retain the branch and checkpoint files if blocked; do not reset or clean the user's original checkout. Further changes need their own compatibility check. Development installation does not establish final goal/release acceptance.

The deterministic baseline and frozen held-out protocol are under `validation/engine-slice-2026-10-15-r001/`. The latest tested installed-code regression at the r004 continuation ran397 tests:396 passed and one symlink-permission test skipped (`REGRESSION-20261016-r005.txt`). Subsequent changes require their own dated evidence; use the newest continuation and integration records rather than treating this historical total as a perpetual pass. Tests verify behavior in temporary state, not live worker restrictions, analytical quality or investment performance. Core real-case analysis/review, final engineering acceptance and the complete requirement audit remain outstanding. Do not rerun the held-out comparison with tuned gold or claim historical retrieval performance proves trading edge.

## Explicit case commands

`tools/run.ps1 engine --help` exposes the case commands; each subcommand has `--help`. Inputs are explicit, project-relative public artifacts with size/path/hash checks. Nothing scans unrelated chats, queues new research on a timer or changes an acceptance registry.

| Command | Effect |
|---|---|
| `engine record --input <record.json>` | Validate and append a versioned request, dossier or other supported record. |
| `engine prepare --request <saved-request.json> --job <job.json> --record-id <id> --created-at <timestamp>` | Freeze the exact packet and save its reproducible evidence record. |
| `engine archive-result --job-id <id> --case-id <id>` | Revalidate a completed queue result, archive only its research output and selected execution metadata, and replace its private target path with identical archived bytes. |
| `engine translate --request <path> --job <path> --result <path> --execution <path> --case-id <id> --record-id <id> --created-at <timestamp>` | Translate the adapter's existing schema to a version-bound research record. A review also supplies `--target-record <analysis-record.json>`. |
| `engine case-status --disposition <path>` | Re-read and verify the whole research chain; report disposition and all ten gates without activating any capability. |
| `engine memory-export --disposition <path>` | Export only the chosen structured case records and their source manifest for explicit history indexing, with no model summary call. |

The existing `tools/scoped_research_queue.py` command handles explicit enqueue, batch authorization, named run, retry decision, status and recovery. See `validation/SCOPED-QUEUE-CONTROLS.md`. Enqueue/prepare are deterministic; running a model requires a separately persisted authorized batch and verified runtime restrictions. The installed runtime currently fails that restriction gate. Do not replace the verifier with a ready flag or use a fictional test transport for real acceptance.

Optional correction uses the full replacement schema. Supply the exact material review as `--target-record`. A successor of an existing record adds `--version <previous+1> --supersedes <previous-record.json>`. Required recheck targets the corrected analysis. Predecessors remain immutable; unnecessary correction without material review findings is refused. JSON Patch is omitted.

## Record contract and status boundaries

`tools/research_records.py` validates schema1 envelopes with stable `id`, `case_id`, positive consecutive `version`, `record_type`, timezone-aware `created_at`/`observed_at`, `origin`, exact `provenance_refs`, explicit `unknowns`, exact older-version `supersedes` references and typed `content`. Dependencies cannot be dated after the record that uses them. Authoritative records live in `monitoring/research-engine/cases/<case>/`; derived database/view files stay in ignored `state/`.

Requests bind the legal entity and exact security, exchange, class, trading currency/unit, reporting currency, question, holding window, evidence cutoff, all nine existing scoped coverage categories and stopping conditions. Evidence records bind the request, compact job, frozen packet, original byte count and packet byte count/hash. Research/review records retain raw adapter output, requested/reported route information, actual verification limitations and exact target identity. They do not replace the adapter schema with another LLM response format.

Dossiers separately record expectations, the price-response mechanism, window, entry/exits/reassessment, cash alternative and all five adverse mechanisms (no repricing, adverse surprise, delayed catalyst, overnight gap and too late). Costs require explicit currency and exact decimal strings or null. Without a verified schedule reference, numerical costs remain null and the limitation is mandatory. A source hash alone is not substantive fee verification.

Disposition is supported, rejected or parked and binds matching analysis, review and dossier versions. A park names reopening conditions. Supported opportunities require completed research, no review continuation blockers (including material gaps, withheld conclusions or coverage), resolved material findings, known costs and an explicit expiry; this still does not satisfy any trading gate. A review may complete while exposing decisive defects. Fictional workers remain labelled fixture-only and cannot demonstrate an actual review.

`decision_readiness.project_gates` is a separate read-only view over the existing `ArtifactVerifier`. It preserves all exact instruction/portfolio/version bindings and current-state validator requirements. It cannot accept a checkbox or insert early scoped research into a trading registry. The ordinary engine case view retains scoped research/dossier evidence as incomplete gate evidence; missing account, quote, phone, monitoring, trial, strategy and activation acceptance stays visible.

## Retrieval and cost limits

See `tools/RESEARCH-MEMORY.md`. Ordinary retrieval retains uncertain, limited and affected-record context within the explicit scope, even without a keyword match; insufficient bounds withhold the answer rather than omit that context. Unlabelled semantic opposition still needs source review. The original frozen text-only A/B remains failed on one required preservation-limit passage. It is preserved as an unsuccessful evaluation, not recast as a success of the newer ordinary route.

No complete verified transaction-cost schedule is available. The optional friction pre-screen is omitted; FX/spread/fees/taxes/rounding inputs and economic advantage remain unverified. No rate or minimum practical position size is invented. Optional companyfacts, patch deltas, dashboard platform, hooks and skills remain deferred.

The paper-study path refuses newly registered accepted ideas above the existing experimental £100 per-idea ceiling, alongside the £300 aggregate capital boundary. Neither ceiling approves live sizing. Exact replays of earlier records remain unchanged; a grandfathered pending idea retains its frozen budget and can still receive manual paper fills under those earlier terms. That legacy experiment is not a newly approved allocation or evidence of compliance with today's new-idea ceiling. Do not rewrite its history or silently use it to establish a current policy. The decision lane has its separate experimental policy and acceptance requirements.

## Structured reuse and rollback limits

Case memory export retains whole structured claims, limitations, exact locations and review dispositions without asserting new company facts. Import its returned records/sources paths explicitly with `tools/research_memory.py import`. The index validates the originating case's evidence graph again on reuse. Successor records can mark earlier imported records superseded through exact same-entity/security/question links; a later conclusion cannot rewrite an earlier cutoff. These links do not require mutation of older imports. No ongoing ingestion or freshness daemon is installed.

The deterministic readiness translation reuses `scoped-company-review` vocabulary with status `unaccepted-scoped`, the existing coverage keys and source-fact references. It retains the raw adapter output. Unstructured scenarios remain explicit null rather than invented bear/base/bull cases. A separate disposition binds the final research outcome. This early artifact is insufficient for the existing accepted-scoped gate contract.

The rollback fixture verifies SQLite backup/restore and baseline status-reader compatibility. Actual deployment still requires quiescent queue state, a consistent private database backup, unchanged observation configuration and a recorded maintenance/restore procedure. Never copy an open SQLite database or run the old dispatch command against newly created engine jobs. No actual production rollback has been performed.

## Usage and model responsibilities — 16 October clarification

The user resumed on Sol6.1 and requested selective lower/higher-tier delegation. Routine coordination, implementation and engineering review remain with Sol. Bounded mechanical repairs/inspection may use a lower-tier agent. The required real-case analysis remains Sol High and independent analytical review Astra High; standard speed and the shared four-attempt ceiling are preserved. No broad Astra implementation delegation is needed. Record actual visible/requested identity and unavailable backend measurements honestly.

The previous500-credit authorization is spent and does not replenish on a subscription reset. The16October resumption verified ordinary usage available; no new credits are authorized. Check ordinary capacity with conservative headroom before new model work or long continuation, and stop before paid continuation. Purchases, top-ups, allowance resets, paid APIs and model fallback remain prohibited.
