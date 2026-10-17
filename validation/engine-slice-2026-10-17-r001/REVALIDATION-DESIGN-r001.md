# Retained output: bounded revalidation design, 17 October 2026

Status: inspected design, not implemented. The pure helper is installed; no worker, queue or exporter calls it. No candidate is accepted by this document.

The third Sol response is retained byte-for-byte and remains rejected by the unchanged strict validator. The inspection script demonstrates that 19 edits to `conclusions[*].blocking_issues` alone can produce a strictly valid copy: exact known `ID: label` strings become IDs, and reverse edges are added only where an existing unresolved material issue already names an already-withheld conclusion. Claims, sources, numbers, issue declarations, coverage and statuses remain identical. Unknown IDs, ambiguity, duplicate IDs and material issues targeting supported conclusions are rejected. No automatic downgrade or substantive repair is allowed.

Parent review inspected the complete helper and eight tests, then reproduced the transformation on the actual retained response. This establishes a possible repair route, not research acceptance. `NORMALIZATION-INSPECTION-r001.json` records exact raw bytes, code/job hashes, edits, strict in-memory validation and idempotence. It writes neither a normalized result nor queue state.

## Required implementation before use

Add one explicit deterministic revalidation operation under the existing worker lock and database transaction. It must recheck the current job/package/target/source/packet hashes, exact active authorization/version/expiry, existing claimed dispatch, attempt/model/role/stage, return code, subscription route, runtime-verification and engineering flags. Reconstruct removed staging inputs deterministically and compare their manifests. Revalidate sanitized events and preserve their usage objects without invented totals. Reject stale or inconsistent inputs before writing.

Preserve byte-identical failed metadata separately and retain `unaccepted-output.json`. Save a versioned processing receipt binding failed metadata, raw output, events, normalized bytes, packet, catalog, algorithm and dispatch hashes. Stage `result.json` and replace the active metadata atomically last, without inserting a new dispatch, refunding an attempt or changing original timestamps. A separate normalization timestamp is required. Run existing checkpoint validation and completion logic afterwards. Recovery must remain unambiguous and idempotent if interrupted at every write boundary; an extra attempt directory with a second `metadata.json` would violate current recovery assumptions.

Extend export and research-record provenance to retain the failed original, failure metadata and receipt, alongside the processed result. The exact Astra target must expose the processing lineage while remaining within the already-authorized review scope. Do not silently add new issuer evidence, change the frozen schema or conceal the original failure. Review the design against actual export/translation contracts before implementation; the read-only delegate did not inspect private attempt files.

Required tests include stale/expired authorization, mismatched hashes/dispatch, unclaimed or engineering invocation, unsafe transformation, no-op replay, immutable raw/failure preservation, interrupted writes/recovery, unchanged attempt count, exported lineage and strict validator rejection of unrelated defects. Direct parent engineering review is required before applying it to the real response.

## Budget and stopping boundary

Three actual Sol attempts have been consumed. One actual inference attempt remains, reserved for fresh Astra High review at standard speed. No further Sol inference, correction/recheck call, new batch, budget reset or credit spending is authorized. A normalization operation consumes no model call and must not refund prior calls. If the protocol cannot be verified or Astra cannot complete within the existing authorization/allowance, preserve the partial case and exact blocker. Do not manufacture an accepted analysis or a review disposition.

Even successful revalidation and review would not repair the frozen retrieval evaluation's retained 4/5 result, discharge all 419 requirements, approve a company thesis or enable a trading gate.
