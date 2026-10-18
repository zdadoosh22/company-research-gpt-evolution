# Second review amendment: bounded engineering implementation

Scope: DEV queue and queue tests only. No production database writes, model calls, installation, research acceptance or trading authority.

Before editing, both DEV queue and queue-test files matched the installed source byte-for-byte. Existing dirty work was preserved. The accompanying installed-to-dev.patch isolates this task from earlier dirty changes.

## Persistence and budget

A separate case-keyed scoped_review_second_amendments table appends one immutable, hash-checked manifest. The first scoped_review_exceptions row and original four-attempt case ceiling are unchanged. There is no generic exception counter or third amendment API. Effective maximum becomes six only for the same existing frozen Astra review job. Other jobs continue to use the original ceiling. All five old dispatches remain consumed; one explicit retry decision must still precede the sixth dispatch. A failed sixth consumes the final slot and a seventh is rejected.

The second manifest contains schema_version, case_id, batch_id, job_id, created_at, authorization_sha256, package_sha256, prior_exception_sha256, failed_dispatch_id, failed_dispatch_sha256, failed_job_terminal and authority (relative Markdown path/hash).

## Authority and failure proof

The manifest chains the original immutable first-exception digest and same original authorization, case, batch, package and job. Existing authorization validation verifies frozen authorization hash, expiry interval, permitted successor continuity and exact current named review spec/model/stage. Registration independently rejects expired authorization. New authority must resolve within validation, have Markdown extension, match its hash and differ in both resolved path and content hash from first authority. A second registration, including an identical replay, is rejected.

The failed fifth must be an unclaimed worker-interrupted review dispatch with null metadata_path, terminal needs-retry-decision state, completed_at, exact Astra model/stage/role, consumed original-plus-first-exception ordinal, next review attempt and linked consumed retry decision. The entire durable dispatch row, including original completed_at, is hash-bound. Failure chronology must follow first authority and precede second authority. Terminal job proof binds job ID, attempt, package hash, state and reason and must match the live job at initial registration. Historical validation retains that frozen proof after the sixth changes the current job. No failure metadata is invented; no absent usage evidence is presented as observed usage. Invocation-not-claimed is the durable local evidence that queue-authorized inference was not begun.

Historical status remains readable after authorization expiry. Dispatch and retry remain expiry-gated. Mutation of either authority, either manifest, first failure proof or the frozen fifth row fails closed.

## Validation and limits

New tests exercise successful sixth, failed sixth, immutable first exception and five-dispatch history, restart persistence, explicit retry, analysis rejection, seventh rejection, duplicate registration, scope/hash/chronology changes, claimed/metadata-bearing/incorrect-model fifth rejection, terminal job mismatch, authority reuse/copy/escape/hash mutation, expiry, successor authorization and second-record tampering. Focused test evidence and exact source hashes accompany this design. Parent owns lifecycle checkpoints and the subsequent complete source-bound regression.

Authority record supplied by parent: validation/engine-slice-2026-10-18-r001/USER-REVIEW-EXTENSION-20261018-r002.md, SHA256 83c92086fffd3aca7f186b9053d59bf8bfb47f5bbcbfe29258ae3fe5129a7db6. This implementation does not register it or dispatch anything. Operator provenance is not a cryptographic human signature.
