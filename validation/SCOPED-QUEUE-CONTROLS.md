# Explicit scoped queue controls

The existing `state/scoped-research/queue.sqlite` and `worker.lock` are retained.
No observation service, scheduler, timer, or oldest-due selection calls this queue.
Tests use temporary projects and fake workers only.

## Python and command interfaces

`ScopedQueue(root).enqueue(job)` validates and freezes a named package. Existing
job IDs cannot be reused with changed bytes. Enqueueing does not authorize a call.

`authorize_batch(manifest)` persists an authorization. The JSON contract has
exactly these fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1` |
| `batch_id`, `case_id` | Stable named identifiers; one batch per case |
| `version` | Consecutive positive integer; existing versions are immutable |
| `created_at`, `expires_at` | Timezone-aware times; expired batches cannot dispatch |
| `purpose` | Explicit nonempty research purpose |
| `provenance_refs` | Nonempty list identifying originating authority |
| `call_limit` | Integer 1–4, shared by every job and retry in the case |
| `permitted_continuation` | List drawn from `explicit-retry`, `material-correction`, `material-recheck` |
| `jobs` | Fixed list of one to four job specifications |

Each job specification contains exactly `job_id`, `stage`, `role`, `model`,
`scope_sha256`, `package_sha256`, and `target_from_job_id`.
Stages are unique `analysis`, `review`, `correction`, `recheck` in dependency order.
Analysis/correction require role `analysis` and model `gpt-6.1-sol`;
review/recheck require role `review` and model `gpt-6-astra`. No aliases or fallback
models are accepted. Review targets analysis; correction targets review; recheck
targets correction. A correction requires material unresolved review findings.

Use the module's `package_sha256(job)` and `scope_sha256(job)` helpers, which hash
canonical JSON. Scope freezes every field except the top-level target. Initial
analysis must be enqueued and fully bound. Predeclare later jobs using a null
`package_sha256` and the exact predecessor job ID. Once a predecessor has a
validated saved output, enqueue the successor with that exact result path/hash,
then append the next authorization version with its full package hash. No other
field, job ID, scope, expiry, provenance, or ceiling may change. Binding never
restores spent attempts. A second batch for an existing case is rejected, as is
assigning an already scoped job ID to another case.

`run_one(job_id=..., batch_id=..., adapter=...)` runs only the selected named job.
It commits authorization identity, dispatch intent, job attempt, and budget
consumption before entering the adapter. It passes `state_root`, `attempt`, and
`dispatch` as queue-owned keyword arguments. The adapter calls
`verify_dispatch(root, dispatch, job)` once immediately before inference; that
function atomically claims the persisted dispatch, validates bindings and expiry,
and rejects replay. It returns the original dispatch dictionary. This is a local
consistency/capability check, not cryptographic model or user authentication.

The adapter must save `request.json`, `metadata.json`, and, for validated output,
`result.json` in one immediate child of the supplied checkpoint root. Metadata
must identify the job, attempt, dispatch, requested model, completion time and
saved paths; a validated result also needs its output hash, selected route flag,
status and continuation flag. Returned metadata must equal the saved metadata.
The queue revalidates package bytes, target/source hashes, result shape and
source references. A metadata-only success claim is rejected. A validated route
with unavailable backend identity remains honestly recorded as unavailable;
the attempt is charged and no independent backend attestation is inferred.

`retry(job_id=..., batch_id=..., decision_id=..., rationale=...,
provenance_refs=[...])` records an explicit retry of a frozen package. Decision
IDs are idempotent and single-use. Recording a decision does not spend allowance;
the next named dispatch spends a fresh attempt. Failures, timeouts, interruptions,
identity uncertainty, and pre-inference adapter rejection never refund attempts.

CLI commands are `enqueue PACKAGE`, `authorize-batch MANIFEST`, `status`,
`recover`, `run-one --job-id ID --batch-id ID`, and
`retry --job-id ID --batch-id ID --decision-id ID --rationale TEXT
--provenance-ref REF`. `--project-root` precedes the command. No inference is
implied by authorization, retry decision, recovery, or status inspection.

## Migration and recovery

The first migration snapshots every existing queue row in `scoped_legacy_jobs`
before changing statuses. Original package bytes, hashes, metadata pointers,
attempt counts, timestamps and retry suggestions remain in that snapshot.
Legacy deferred rows become `needs-retry-decision` with no active retry timer.
Queued jobs still require a named authorization. Legacy attempt counts are
charged when their jobs first enter a case; a history beyond the four-attempt
ceiling cannot be reauthorized through this interface.

Recovery runs only under the existing worker lock. It never dispatches a model.
A unique completed checkpoint matching request, output hash, schema, role,
attempt and dispatch can repair an interrupted `running` job idempotently.
Missing, conflicting, malformed or uncertain checkpoints become
`needs-retry-decision`. Historical running jobs without a dispatch ledger may
recover only from their existing fully validated checkpoint; they do not acquire
permission to invoke a new worker. Valid partial analytical results become
`needs-input`, and also require an explicit authorized retry before rerunning.

The legacy `retry_not_before` status column remains for compatibility but has no
dispatch meaning. Database schema migration was exercised on temporary state;
production/private queue migration has not been performed by these tests.

Preserve the migrated database and ledger if rolling back code. An older queue
implementation does not understand these authorization controls; do not run its
automatic dispatch command against migrated operational state.
