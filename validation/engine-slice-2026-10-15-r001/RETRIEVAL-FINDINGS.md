# Retrieval implementation and frozen comparison findings

The explicit local index and deterministic routes are implemented in `tools/research_memory.py`. Independent synthetic fixtures passed before the frozen comparison was first executed. Frozen protocol, source manifest, normalized records and original source bytes were not edited.

## Unresolved frozen retrieval failure — preservation-limit recall

Both prescribed routes return the same six-record set with different rank order. Each passes four of the five historical gold items. `GOLD-C3` / `UL-PRESERVATION-LIMIT` is excluded with `no-query-match` by both routes. Its exact text is:

> Original issuer PDFs returned HTTP403 to local preservation. Verified numerical extracts and precise links retained; complete PDFs remain online.

The frozen phrases are `turnover`, `operating profit`, `CFO`, `GBp`, `GBP`, `EUR`, `partial`, `missing`, `Ice Cream`, `withheld`, `source`. None appears in that passage, including case-insensitive matching. The baseline requires at least one phrase substring; the new route searches only the `text` FTS5 column using those phrases. Returning this passage would require changing the frozen query, searchable columns, input passage or selection algorithm. No such change was made. The gold remains failed, with primary retrieval acceptance incomplete. The unused `UL-SCREEN-WITHHELD` record also has no query match; this is not a gold failure.

This is measured retrieval failure under the frozen contract, not authority to claim that all contrary evidence was retrieved. A later non-held-out protocol could test a different retrieval design, preserving r001; it cannot retroactively change this result. No efficiency improvement or edge is claimed.

## Controls that passed

- Both routes preserve the six-row H1 table, normalized labels, exact periods/units/scope/source locations and source-header/footnote limitations.
- Both correctly exclude all six historical negative controls, including unknown publication and dependent annual/TTM claims, superseded records, a later conclusion, and another entity.
- Each returned passage carries exact references, dates, status and inclusion reason; both packets stay within the frozen bounds.
- All seven separate synthetic controls pass: future publication, unknown publication, expiry, later analysis, changed text retaining original hash, conflicting currency/unit metadata, and missing exact location.
- New-index rebuild reproduces selected IDs, packet hash and exclusions.
- Worker calls and network calls are zero. Tokens, monetary cost and timing comparisons are unavailable/not applicable; no savings estimate was made.

`retrieval-results/` preserves the first execution. Any subsequent code-verification execution uses a different output directory. Evaluation records contain the implementation-file SHA-256, frozen hashes and per-route packet hashes/sizes. The frozen case is retrospective reconstruction from incomplete archived project extracts, not a fresh verification of issuer PDFs or an approved company valuation.

## Scope and residual limitations

Imports are explicit manifests, not automatic whole-project ingestion. Exact locations currently support JSON pointers and text line ranges; PDF parsing/OCR is not implemented. Claim classification, publication assertions and scope labels are inherited from preserved project metadata; no new source verification or semantic classification occurs. Generic retrieval preserves explicitly labelled contrary records and links, but cannot discover unlabelled opposing meaning without source structure. Known missing fields remain unknown. Database checks and cutoff controls validate software behaviour, not the analytical truth of the original records.

The final engineering review remains with the main Goal agent.
