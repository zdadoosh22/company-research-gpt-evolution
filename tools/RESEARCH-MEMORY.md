# Project research memory

`research_memory.py` is a local, derived SQLite/FTS5 index. Original project artifacts, source registers and review dispositions remain authoritative. There are no workers, network requests, embedding services, credentials, queues or readiness writes in this module.

## Invocation

Use the bundled Python runtime used by `tools/run.ps1`, invoking `tools/research_memory.py` directly. `--root` and optional `--state-root` precede the command.

```text
python tools/research_memory.py --help
python tools/research_memory.py import --records validation/example/records.json --manifest validation/example/sources.json
python tools/research_memory.py query --entity example-plc --security EXAMPLE --term revenue --cutoff 2026-10-09T16:02:01Z --review-status partial-provisional
python tools/research_memory.py rebuild
python tools/research_memory.py evaluate --protocol validation/engine-slice-2026-10-15-r001/RETRIEVAL-PROTOCOL.json --output-root validation/engine-slice-2026-10-15-r001/retrieval-results-next
```

Evaluation refuses an existing nonempty output directory. The unchanged frozen comparison and subsequent explicitly identified verification runs are preserved independently. Import/rebuild never alter source bytes. An empty database requires explicit reimport; the database is safe to delete and reconstruct from the same supplied manifests.

Rebuild obtains a SQLite write lock before reading the import registry or validating its sources, then deletes and restores records, FTS passages, sources and the registry in one transaction. Imports likewise lock before validation/collision checks. This prevents a competing import from being erased between validation and replacement. An insertion failure or process exit during restoration rolls back to the preceding index and registry. This local fault-recovery behavior is tested with temporary databases; it does not claim protection against lost disks or missing original source files. Keep the immutable input bundles independently of the derived database.

## Input and Python interface

`ResearchMemory(project_root, state_root=None)` supports context management, `import_bundle(records_path, manifest_path, source_root=None, frozen=False)`, `query(query_terms, **filters)`, `rebuild()`, and `close()`. Paths are relative to the project root. State stays inside `state/research-memory` or `state/research-engine`. The record family is deliberately limited to `entity`, `disposition` and `claim`; lessons are methodology-labelled claims, not a parallel taxonomy or company facts.

An explicit records document contains a `records` array. A source manifest contains a `files` array of `{source_id, repository_path, sha256, bytes?}`. Frozen copies additionally name `frozen_path` relative to `source_root`; those copies must live in `validation/<named-case>/frozen-inputs`. Actual resolved paths cannot alias private state or secrets. Permitted artifact families are company indexes, named run records/reports/observations/source registers/reviews/research records, run text/JSON source extracts, dated monitoring studies and `lessons/confirmed.md`. No directory crawl or automatic ingestion occurs. These are authorized *families*, not a claim that each artifact's research is approved.

Required record fields are `id`, `record_type`, `entity_id`, `question_scope`, `source_id`, `source_path`, `source_sha256`, `location`, `text`, `text_sha256`, `review_status` and a nonblank `originating_run`. A legacy absent originating run is inferred from the explicit source path; a supplied null/blank value is refused. Security is explicit or null. Locations are exact JSON pointers, combined top-level JSON pointers (`/status and /continuation`), or inclusive one-based line ranges. Text must equal the resolved location exactly, including internal line endings. Hashes are SHA-256 of source bytes and UTF-8 passage text. JSON objects selected by a pointer use sorted-key JSON with standard spacing, matching the existing frozen normalization. No fuzzy matching, sentence rewriting or model summarization occurs.

Retained metadata includes originating run/artifact, origin kind, event period/date, public source date, capture date, analysis creation date, analysis date, review date, versioned availability upper bound, expiry, review scope/status, accounting basis, unit, currency, scope, polarity, assumptions, claim kind, limitations, rejected/parked disposition, reopening conditions, explicit contradiction/affected-record links and supersession/effective date. Missing dates and scope fields remain null; no `as_of` value becomes a creation date. Source register dependencies bind publication dates and source hashes. For example, an unknown-date annual source also withholds a dependent TTM claim.

Confirmed lesson applicability includes entities, methodology version, methodological scope and `company_fact=false`. Unknown methodology version is not silently supplied from today's methodology. A requested version must match. A lesson does not amend the approved methodology.

## Retrieval and limits

Required filters: explicit `entities` and `evidence_cutoff`. Optional filters: `security_id`, `question_scope`, `record_types`, `review_statuses`, `period`, `accounting_basis`, `unit`, `scope`, `methodology_version`, `include_superseded`, `retrospective`. A requested period/basis/unit/scope must match; unknown metadata fails that filter. This component does no aggregation, currency conversion, normalisation of accounting measures, semantic equivalence inference or numerical approval.

Public-source extracts require known publication no later than cutoff. Project conclusions require a creation date or versioned upper bound no later than cutoff; later analysis/review is excluded separately. Date-only disclosures are conservatively assigned the end of the stated date. Capturing a previously public source after cutoff requires `retrospective=True` and an explicit reconstruction label. Superseded records remain indexed and can be retrieved for audit; a known later successor does not rewrite earlier history. Rejected, parked and contradictory records are retained.

Ordinary query results include explicit contrary, uncertain/unknown-polarity, limited and linked conflicting/affected records in the selected entity/question scope even where their words do not match the search. Affected links work in either direction. Whole passages are bounded by record count and canonical UTF-8 packet bytes. If caps would omit that contextual evidence, ordinary answer passages are withheld to prevent a favorable-only packet. Exclusions are returned separately from answer evidence; exclusions can exceed the answer-packet byte limit. Semantic discovery of unlabelled opposing evidence is outside this narrow deterministic index. This conservative extension was implemented after the failed frozen evaluation; its independent synthetic tests do not turn that evaluation into a pass.

The frozen comparison is a separate mode: evaluator-only polarity/expected-exclusion labels are removed before import; no gold data enters ranking. It applies the prescribed substring baseline and text-only FTS5/BM25 ranking, then the frozen eligibility and whole-passage caps. Its ranking is not supplemented using evaluator labels. Unknown and incomplete outcomes remain visible. Neither route produces an investment conclusion.

Query returns `packet`, `excluded`, `selected_record_ids`, `packet_sha256`, `packet_utf8_bytes`, `record_count`, `complete_within_bounds`, and zero worker/network counts. Every selected record has an inclusion reason and common `{source_id, path, sha256, location}` reference. Packet hashes cover canonical sorted-key compact JSON. Exclusions are separately sorted by stable ID. The SQLite file itself need not have identical bytes after rebuild; selected records, packet bytes/hash and exclusions must match.

## Validation

Independent synthetic fixtures live in `validation/tests/test_research_memory.py`; they do not use the historical gold corpus. The historical r001 evaluation is intentionally failed on preservation-limit recall: the fixed GOLD-C3 passage contains none of the fixed query phrases. See the dated retrieval finding and retained route reports. No query, source, gold or ranking was altered to improve that result. This module makes no latency, token/cost saving, research-completion, live-readiness or trading-edge claim.
