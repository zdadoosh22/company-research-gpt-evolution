# Planning and external review

This section preserves versioned implementation briefs. Authority depends on the user's assignment, not publication alone. Publishing a brief does not amend the approved methodology, complete research pilots, enable automatic research or activate trading.

## Current authorised assignment

- [Research engine implementation brief, r002](2026-10-14-research-engine-goal-brief-r002.md).
- Prepared: 14 October 2026; copied without content changes from the user-supplied active Goal assignment on 15 October 2026.
- Status: authorised implementation assignment; the active goal was verified on 15 October. Implementation and acceptance remain incomplete.
- Supersedes r001 and its earlier planning addenda for this bounded engine assignment. It removes the ordinary Chat handoff loop from the implementation critical path, preserves methodology 1.0.0 and observation-only controls, and requires a bounded real case with independent review.
- The publication baseline recorded inside the brief is historical. The actual checkout before this publication was `6bcbaf491aab1d0940d50e8fcfd956876766e080`.
- Current publication check: [15 October record](../validation/publication-checkpoint-2026-10-15-r001.md).

## Historical proposal — superseded by r002

- [Company Research 2 — final implementation brief for Goal mode, r001](2026-10-14-research-engine-goal-brief-r001.md)
- Prepared: 14 October 2026.
- Historical status at publication: proposed; awaiting Gemini review before the user sends the implementation assignment to Work. This waiting state is superseded by the authorised r002 assignment above.
- Publication baseline: `5fe2a5c1fb67fbe160a4d8619dcfaf8c697eac1c`.
- The twelve-section brief preserves the final planning-chat text, with a publication-status header added. It includes several-day trades, evidence-linked memory, a local progress dashboard, bounded model work, selective open-source reuse, testing, self-evaluation and recovery.
- Older planning-chat drafts and addenda are consolidated into this proposal. Existing accepted project records and standing instructions remain authoritative until implementation is separately requested.

## Historical review request for Gemini

Review the linked brief against the actual repository, rather than only assessing the prose. First report the repository identity, exact commit inspected and plan file retrieved. If private-repository access fails, say so and request the necessary files; do not infer access from a URL or substitute another repository.

Assess whether this is a feasible, sufficiently complete single Goal-mode implementation assignment that advances an evidence-first company researcher toward a defensible first manual trade from the isolated £300 sleeve. Challenge scope, integration with existing code, state/recovery behavior, memory provenance and historical leakage, dashboard readiness claims, model-call limits, evaluation quality and the distinction between software completion and live-trading acceptance. Prioritize material omissions, contradictions and unnecessary infrastructure. Give concrete proposed edits and explain their consequences; do not execute the plan or automatically overwrite it.

Useful starting points are the root project instructions and README, `REPOSITORY.md`, the approved methodology and research workflows, `monitoring/DECISION-SCOPE.md`, `monitoring/SUFFICIENCY-REVIEW.md`, the latest LEVI and RSS checkpoints under `validation/`, and the scoped-research, decision-readiness, paper and observation tools/tests. The brief's older baseline and test results are dated observations, not claims that the project can already trade.

## Evidence and privacy boundary

The repository contains versioned source evidence, research, code and review checkpoints. Credentials, raw operational databases, private account state and unrelated media are excluded from this publication. A reviewer cannot verify those live prerequisites from repository files alone. No Gemini access or review has been performed by publishing these files.

Keep this revision intact. Save later review findings and revised proposals separately with explicit dates, versions and dispositions.
