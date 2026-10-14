---
status: proposed-awaiting-external-review
version: r001
prepared_date: 2026-10-14
publication_baseline_commit: 5fe2a5c1fb67fbe160a4d8619dcfaf8c697eac1c
source: final implementation brief from the planning conversation
---

> **Review copy, not active instructions.** Published at Aidan's request for Gemini review before implementation. Reading this file does not authorize executing its embedded Goal assignment. The brief below preserves the final planning-chat text; its inspected engineering baseline remains a dated reference. Existing methodology, research dispositions and observation-only controls remain authoritative until implementation is separately requested.

# Company Research 2 — final implementation brief for Goal mode

## 1. Goal, authority and completion standard

**Use this entire brief as one implementation assignment in the main Work chat, with Goal mode enabled and Plan mode disabled. It replaces the previous plan and its addenda.**

**Goal:** Implement, integrate and evaluate the Company Research 2 research engine described below. Deliver a working local dashboard, evidence-linked research memory, bounded model orchestration, reusable research skills and one independently reviewed real decision cycle. Preserve existing evidence and controls. Complete a documented engineering and analytical self-evaluation, repair material implementation defects, and provide a precise handoff for any remaining live-trading prerequisites.

Work autonomously through implementation, testing, review and necessary repairs. Do not stop after producing another plan or completing only the easiest components. Resolve routine implementation decisions from this brief and the actual repository. Ask only when a material decision cannot be resolved within the authorized scope or requires user-controlled access.

A single assignment may require many internal steps and continuation turns. Maintain durable checkpoints so progress survives interruptions and context changes.

### Research objective

Build a reusable researcher that can discover an opportunity, assess whether it merits risking capital, challenge that judgment and eventually support a bounded instruction for manual execution when every applicable gate passes.

The mandate seeks aggressive growth of the isolated **£300 sleeve**, including opportunities held for **several days through to a few months**. Select opportunities on their supported economics, timing and risk. Do not impose a trading-frequency target.

For several-day opportunities, explicitly assess:

- Why repricing could occur within the proposed holding window.
- What expectations are already reflected in the proposed entry price.
- Whether the opportunity survives realistic manual-response delays and costs.
- Overnight gaps, adverse developments, catalyst delays and missed entries.
- Entry, exit, expiry and reassessment conditions.

Intraday strategies, options, borrowing and new leveraged-product capabilities are outside this implementation. Preserve the existing full-thesis workflow for requests that need it.

### What completion means

The goal is complete only when:

1. Required local capabilities are implemented and verified.
2. A real research case has passed through evidence preparation, analysis, independent challenge and a documented supported, rejected or parked disposition.
3. Deterministic tests, integration tests, dashboard checks and the evaluation described below have completed without unresolved material implementation defects.
4. The installed workflow, remaining limitations and exact next actions are documented.

The goal does **not** require a positive trade recommendation, a profitable result, the passage of fourteen days or access to an unavailable private account. Those are separate outcomes or prerequisites, displayed honestly.

A missing required implementation or unperformed required model review means the goal remains incomplete. A reviewed research rejection or justified park can satisfy the real-case requirement.

## 2. Establish the current baseline and protect existing work

The authoritative project is:

`C:\Users\aidan\Documents\Company research 2`

Inspect the actual checkout before changing anything. The planning review observed commit:

`7d12f42de466f169bb19b3c610ba194b9aeb535d`

At that baseline, the existing engineering suite passed **292 tests**. This is a dated reference, not permission to assume later files are identical or tests still pass.

Read the project instructions, current methodology pointer, applicable workflows, latest accepted checkpoints and relevant code. Resolve supersession explicitly. Newer file timestamps alone do not establish approval.

The inspected baseline includes:

- Immutable company runs and source registers.
- Financial and evidence-validation utilities.
- An explicit scoped-model adapter and durable queue.
- A deterministic observation service.
- An artifact verifier, dormant instruction contract and connected paper pipeline.
- Partial company pilots and several parked research cases.
- An offline RSS revision-state prototype whose durable/live integration is not accepted.

Reuse these capabilities where they meet the requirements. Do not rebuild them simply to fit a new architecture diagram.

### Workspace and rollout discipline

- Preserve existing user changes, untracked media, private state and frozen research.
- Prefer an isolated development worktree based on the actual current project commit. Reuse a suitable worktree if one already exists.
- Use a `codex/` branch for implementation. Do not reset the repository or discard unrelated changes.
- Keep test databases and fixtures separate from live observation and portfolio state.
- Integrate reviewed changes into the authoritative checkout only after checking for concurrent changes and verifying compatibility.
- Preserve the existing observation-only configuration and `research_enabled=false`. New bounded research runs use their own explicit orchestration path.
- If integration affects code loaded by the running observation service, use a documented, reversible maintenance procedure that preserves its state and prior configuration. If that cannot be verified safely, retain the tested release branch and report integration as outstanding.
- Do not push, publish, send messages, connect accounts or activate trading as an incidental consequence of this work.

Update project instructions and documentation to match the implemented workflow. Preserve the approved analytical methodology; do not silently rewrite it to make incomplete work pass.

## 3. Architecture and durable interfaces

Use the existing Python environment, SQLite and lightweight local web assets. Add focused modules around existing tools. Do not introduce another agent framework, workflow server, cloud database or competing job queue.

The intended flow is:

**Request → existing-history lookup → source collection → extraction and calculations → frozen evidence packet → authorized model batch → validation and independent review → disposition → memory index and dashboard update.**

Keep these concepts separate throughout the implementation:

- Task execution status.
- Research disposition.
- Review status.
- Current trade-readiness evidence.
- Live capability activation.

A completed task can reject an opportunity. A successful model response can remain unreviewed. A reviewed company finding does not approve a portfolio decision.

### Required records

Use versioned schemas and stable identifiers. Extend existing records where compatible rather than duplicating their meaning.

| Record | Minimum content |
|---|---|
| Research request | Entity/security, question, holding window, mode, evidence cutoff, required coverage and stopping conditions. |
| Evidence packet | Source identities and hashes, exact locations, relevant content, calculation inputs/results, methodology references, retrieved history and unresolved gaps. |
| Batch authorization | Scope, permitted jobs and models, call ceiling, attempt accounting, expiry and permitted continuation conditions. |
| Research result | Claims, supporting and contrary evidence, scenarios, assumptions, limitations and disposition. |
| Review record | Target version/hash, reviewer route, findings, severity, affected conclusions and resolutions. |
| Opportunity dossier | Expectations, price-response mechanism, holding window, costs, adverse cases, entry conditions, exits and reassessment triggers. |
| Task checkpoint | Task/turn identity, execution outcome, work completed, artifacts, verification, blockers, readiness impact and next action. |
| Readiness projection | References to the authoritative acceptance evidence, current status, assessment time, expiry/invalidation and explanation. |

Use exact decimal handling for money and explicit currency/unit metadata. Preserve unknown values as unknown; do not convert missing inputs to zero.

### Storage and recovery

- Keep authoritative sources and research artifacts as immutable, versioned files.
- Keep local operational state and rebuildable indexes under the existing private-state convention.
- Maintain an append-only project-event history; derive current dashboard views from events and authoritative records.
- Use atomic writes and database transactions where partial updates could misrepresent state.
- Make repeated imports and completion events idempotent.
- Record dispatch intent and budget consumption before a model job starts.
- Recover completed jobs from verified checkpoints. When completion is uncertain, record uncertainty and require an explicit retry decision rather than blindly spending again.

Provide a small command surface for preparing cases, indexing/searching records, preparing/running authorized batches, recording checkpoints, inspecting status, evaluating the system and serving the dashboard. Keep commands scriptable and usable by the project skills.

## 4. Deterministic preparation and bounded model work

### Work performed by code

Use code for:

- Approved-source collection, downloading, hashing and deduplication.
- Filing identifiers and entity/security matching.
- Document extraction with retained section/page/table locations.
- Structured search and historical-record filtering.
- Period, scope, unit and currency compatibility checks.
- Established financial calculations and sensitivity calculations.
- Dependency tracking, stale-record detection and status updates.
- Queue management, usage accounting and report assembly.

Retain source bytes alongside derived text. Extracted figures are candidate facts until their definitions and provenance are checked.

Improve extraction where needed to preserve table headings, columns, periods, units and footnotes. Do not flatten a table into prose and then treat its numerical relationships as reliable.

Use existing tested calculation functions or reviewed calculation recipes. Models supply justified assumptions and interpret results; they do not create arbitrary executable formulas that bypass validation.

### Model roles

Use the existing routes:

- **Sol High:** bounded research analysis and corrections.
- **Astra High:** material independent challenge.

Record requested model, reported model, reasoning setting and actual verification limitations. Do not claim backend identity that the runtime does not expose. Do not silently substitute another model when a required route is unavailable.

Independent review receives the frozen source packet and the exact target artifact in a fresh review context. It must challenge economics and contrary evidence, not merely polish the author’s prose.

Model workers must have only the capabilities necessary for their assignment. Prefer preparing the required content before invocation and disabling tools that could retrieve unrelated information, execute commands or mutate state. Verify those restrictions in the actual runtime; a read-only filesystem setting alone is insufficient evidence of full isolation.

If material evidence is missing, return a specific acquisition request. Collection and validation occur before the next authorized reasoning pass.

### Authorization for this implementation goal

Submitting this brief authorizes the bounded model work required for the following:

1. The chosen case’s scoped company foundation.
2. Its opportunity assessment, including a justified early rejection or park if the foundation prevents further conclusions.
3. One held-out evaluation question run through the baseline preparation route.
4. The equivalent question run through the new retrieval/preparation route.

Each batch permits at most:

**analysis → independent review → one correction → one necessary material recheck.**

These are ceilings, not required call counts. Skip unnecessary stages. Count attempted inference calls, including failed inference attempts, against the batch ceiling.

Also authorize one separate engineering-review pass over the completed integration and one targeted recheck of material corrections. This makes a maximum of **18 bounded worker calls** for the initial implementation and evaluation. Deterministic tests use fixtures or fake workers and do not spend live calls. Normal implementation turns are separate from these worker calls.

Create explicit batch manifests before dispatch. This brief supplies the user authorization for these named purposes; do not ask for approval again before each job. It does not authorize unrelated research or indefinite review loops.

After this implementation, further research uses explicit user-approved batch scope. The observation service must not begin consuming model allowance merely because it detects a new source.

### Usage boundaries

Use existing subscriptions. Do not introduce paid APIs, external assistant accounts, credit purchases or allowance-reset actions.

The extra credits authorized in the planning chat were for preparing this brief; they are not a standing operating budget for the engine or the main Work goal.

Inspect the main Work chat’s applicable allowance and spending controls. Record actual token usage where supplied, with unavailable measurements marked unavailable. Do not equate tokens, subscription percentages and monetary credits.

If an authorized spending boundary cannot be enforced, checkpoint before unsupervised paid continuation. Continue useful deterministic work where possible. Quota exhaustion or model unavailability must not trigger silent fallback.

## 5. Research selection and the first decision cycle

Use the existing candidate set initially. Reassess current dates, source availability and material developments before selecting one. Historical research priority is not a current investment ranking.

Choose the candidate with the best combination of:

- An available source capable of changing the decision.
- A plausible several-day to several-month mechanism.
- Evidence that can be evaluated within this assignment.
- Compatibility with realistic manual execution.
- Potential economics that warrant investigation after costs and adverse cases.

Record the selection rationale and why the other candidates were deferred. Keep one deep investigation active.

For the selected case, produce a decision brief before broad research. Identify the essential claims, material unknowns, decisive source steps and stopping conditions.

Classify gaps as:

- **Resolve:** an available source or calculation could materially change the decision.
- **Bound:** uncertainty can be represented through justified ranges.
- **Park:** a material unknown prevents a defensible conclusion and cannot currently be resolved.

A park must identify what would reopen it. Closed audits and unchanged evidence must not trigger repetitive investigation.

Do not impose proprietary customer economics, a perfect daily balance sheet or a full five-year valuation as universal prerequisites. Apply the approved scoped-company coverage to the actual decision.

Conversely, a short holding period does not excuse missing security identity, financial resilience, ownership claims, material limitations or contrary evidence.

The opportunity assessment must connect:

**Event or development → business consequences → market expectations → plausible price response → feasible entry and exit.**

Include no repricing, adverse surprise, delayed catalyst, overnight gaps and “correct thesis, too late” outcomes. Explain why the opportunity would be preferable to cash at the proposed entry conditions.

If an expectation measure is definitionally incompatible, withhold that comparison. Investigate a different justified mechanism only if the evidence supports it.

Do not invent a positive case to exercise the paper pipeline. A properly reviewed rejection or park is a valid real-case result. Exercise otherwise unreachable software branches with clearly labelled synthetic fixtures.

## 6. Persistent research memory

### Purpose

Implement **project research retrieval**, not changes to Codex’s personal memory settings or model training.

Original evidence, dated outputs, accepted review dispositions and approved methodology remain authoritative. The memory index is derived and rebuildable.

Use SQLite metadata and FTS5 full-text search first. Embeddings and vector databases remain deferred until measured retrieval failures justify them.

### What to retain

Index:

- Source-backed findings and calculations.
- Assumptions and hypotheses, explicitly labelled.
- Review findings, corrections and supersession.
- Rejected and parked cases, including reopening conditions.
- Confirmed methodological lessons and their applicable scope/version.

Reuse structured research outputs. Do not add a separate model call after every run to manufacture a summary.

Each record retains the entity/security, type, provenance, original location, relevant dates, originating run, review disposition, limitations and superseding relationships.

Keep conflicting and superseded records for audit. Retrieval must not silently select the most favorable claim or delete the record of a correction.

Methodological lessons remain proposals until confirmed through the existing process. A remembered lesson cannot amend approved methodology by itself.

### Retrieval contract

Support filters for entity/security, question, record type, evidence cutoff and review status. Return a bounded packet with reasons for inclusion and source references.

Check period, accounting basis, scope and applicability before reuse. Retrieve material contrary evidence alongside supporting evidence.

A shared supplier or industry relationship is a research lead. It does not prove that two companies have equivalent exposure.

Track dependencies so changed evidence marks affected conclusions for reassessment. Retrieval today does not make an old finding current. Apply event- and claim-specific freshness rules rather than a universal expiration date.

### Historical integrity

Distinguish:

- When an underlying event occurred.
- When its source became publicly available.
- When the project captured/read it.
- When an analytical conclusion or review was produced.

For historical tests, exclude information unavailable at the cutoff, including later analytical findings that introduce hindsight.

A source fetched today may support a clearly labelled retrospective reconstruction if earlier public availability is verifiable. It must not be presented as a contemporaneously captured record.

Historical replay can validate software and research controls. It cannot by itself establish an unbiased trading edge, particularly where a model may already know later events. Prospective paper records remain separate.

### Obsidian

Preserve stable identifiers, ordinary Markdown outputs and portable links now. Defer the generated Obsidian vault until the first audited cycle provides useful content.

The later integration begins as a one-way readable export. Personal annotations remain separate from generated records. The engine must work when Obsidian is closed.

## 7. Dashboard and task-by-task progress

Build a local dashboard using lightweight HTML/CSS/JavaScript and the existing Python runtime. Serve it on the local loopback interface. Provide a simple launcher and stop/restart instructions. It must be usable without editing code.

The dashboard reads a sanitized status projection and approved artifacts. It has no order-entry, account-connection or portfolio-mutation controls.

### Required views

| View | Required content |
|---|---|
| Overview | Current stage, active task, next bounded step, main blockers and last update. |
| Roadmap | Implementation milestones, dependencies, completion evidence and reopened work. |
| Trade readiness | Candidate, intended holding window, gate status, supporting evidence, limitations and expiry. |
| Activity | Completed, partial, failed and interrupted tasks with their actual effect on the project. |
| Research history | Active, rejected and parked cases, corrections, reopening triggers and retrieved evidence. |
| Resources | Available usage measurements, model-call counts and source/worker health. |

Bring up a basic dashboard during the first implementation stage. Extend it as the actual workflow develops.

Use separate statuses for:

- Implementation: not started, in progress, blocked, complete.
- Readiness: not assessed, evidence incomplete, awaiting review, satisfied, invalidated.
- Research disposition: active, supported, rejected, parked.

Show counts and named milestones rather than an invented “confidence percentage” or probability of profit. Work can improve reliability without improving the current investment case. Readiness can move backwards.

### Preserve the actual gate model

The existing instruction contract has ten gates:

**research, dossier, decision, portfolio_policy, quote, phone, monitoring, operational_trial, strategy_validation, activation.**

Preserve them and their existing verifier requirements.

The six user-facing categories—Company, Opportunity, Challenge, Portfolio, Execution and Operations—are display groupings. They must not replace the ten gates or hide an unsatisfied requirement. Show activation separately and prominently.

Derive readiness from actual version-bound acceptance evidence and current validators. A dashboard checkbox, task summary, successful test or model confidence label cannot satisfy a gate.

### Automatic task updates

Implement a project completion command and require it in project instructions and the two research skills.

At the end of every project-related Codex turn and engine task, record:

- Request and work actually performed.
- Complete, partial, failed or interrupted outcome.
- Supporting artifacts and checks.
- Blockers resolved, introduced or unchanged.
- Proposed readiness impact and the verified gate changes.
- Next bounded action.

The agent writes the brief explanation within its existing turn. Code validates the referenced artifacts, records the event and refreshes the projection. Do not make an extra model call to summarize activity.

Use impact labels **improved, unchanged, reduced, not assessed**. Any claimed improvement must identify the underlying evidence or requirement resolved.

Integrate checkpoint recording directly into engine task completion. For ordinary Work turns, execute the completion command before the final response.

Verify support for project-scoped Codex lifecycle hooks in the installed desktop/runtime. Where supported and trusted, use prompt, stop and interruption events to reconcile activity. Follow the documented [Codex hook behavior](https://developers.openai.com/codex/hooks).

Hooks must not launch another model call, continue the goal or bypass trust requirements. A stop event means a turn ended, not that the task succeeded. If no checkpoint exists, show **“turn ended; outcome not recorded.”**

Scope capture to this project. Do not ingest unrelated chats. Imported planning decisions retain their origin and acceptance status.

### Reliability

- Deduplicate repeated events using stable task/turn identities.
- Preserve an append-only history and atomically update the current view.
- Poll for changes every ten seconds while the page is open.
- Show last successful refresh and disconnected/stale status.
- Recover after restart without inventing completion.
- Escape source text and serve only allowlisted artifacts; do not expose arbitrary filesystem paths, credentials or raw account databases.
- Keep dashboard operation separate from the observation service’s research and trading controls.

## 8. Trade-readiness and paper boundaries

Preserve the isolated £300 capital boundary, manual broker execution and separation between research, allocation and execution.

The existing £100 paper per-idea ceilings are experimental ceilings. They are not automatically approved live position sizes. Retain the documented comparison of allocation and exit approaches without selecting the best historical result as if it had been chosen prospectively.

A scoped company review must cover the security/claims, financial resilience through the holding window, business drivers, assumptions, limitations and contrary evidence.

A separate opportunity dossier addresses expectations and price response. A separate portfolio decision addresses reconciled cash, outstanding orders, exposure, costs and joint adverse outcomes.

The execution envelope must bind the accepted versions to the exact security, quantity, ceiling, expiry and current quote.

Preserve the existing fourteen-day operational observation requirement and its fault-case evidence. Elapsed time alone does not pass it. The refreshed-confirmation ceiling is a communication safeguard, not proof that a quote or thesis remains valid for that duration.

For paper evaluation:

- Freeze the protocol and decision rules before outcomes.
- Include cash as an alternative.
- Record actual source/quote times and manual-response delays.
- Retain accepted, rejected and missed opportunities.
- Model real supplied costs, FX and partial fills.
- Never infer a fill solely from a touched limit.
- Keep missing marks and inputs unknown.
- Separate retrospective examples from prospective observations.

A foreign-currency share limit does not guarantee a fixed sterling commitment. Whole-account available cash is not sleeve cash. Alert withdrawal does not cancel a broker order. Preserve these distinctions in calculations and tests.

This implementation does not activate real instructions, connect a broker, create a new phone account or send external messages. Prepare and test the integration paths; record user-controlled prerequisites separately.

## 9. Selective open-source reuse and skills

### EdgarTools

Perform one bounded evaluation of [EdgarTools](https://github.com/dgunning/edgartools) against saved evidence for the selected candidate.

Compare filing access, section extraction, financial-data definitions and provenance with the current implementation. Adopt it behind the existing evidence interface only if it reduces bespoke work while preserving the required evidence properties.

Do not trust standardized figures merely because a library produced them. Pin an adopted version and record its licence and provenance.

If adoption is not justified, preserve the evaluation and retain the existing implementation. Do not let this become a library migration project.

### Two project skills

Use Skill Creator to implement:

1. **Company research:** bounded decision questions and thesis updates, applicable-methodology routing, preparation/retrieval tools, dispositions, reopening conditions and completion checkpoints.
2. **Opportunity review:** independent challenge of evidence, assumptions, expectations, price response and the cash alternative, with version-bound findings and review checkpoints.

Make them available in the actual main Work context. Verify discovery instead of assuming that saving a file in a nested repository makes it available to a chat started elsewhere.

The skills reference authoritative methodology and existing tools. They do not duplicate calculations, create another scheduler or grant trading authority.

Adapt useful thesis-tracking and catalyst-calendar ideas from [Anthropic’s financial-services repository](https://github.com/anthropics/financial-services). Preserve attribution and licence notices. Remove unavailable connector dependencies, prescribed report lengths and conviction-based action shortcuts.

Do not install the complete financial-services bundle.

### Deferred dependencies

- Docling: reconsider only for a material extraction failure.
- OpenBB: reconsider when multiple approved providers create repeated integration work.
- TradingAgents: reference selected checkpoint/date-integrity patterns without adopting its agent framework.
- Obsidian: compatible output now; vault integration later.
- Embeddings and autonomous relationship graphs: require measured retrieval benefit.
- The existing RSS prototype: do not promote it into the live service without satisfying its outstanding integration requirements.

## 10. Execution stages and required evidence

Create a durable requirement-to-evidence checklist before implementation. Give each requirement an identifier and record its implementation, tests, status and limitations. Use this checklist for the dashboard and final audit.

### Stage 1 — Baseline, authority and visibility

- Inspect current state and resolve superseded records.
- Run the existing test suite and preserve the result.
- Record protected artifacts/configuration and the development baseline.
- Establish task checkpoints, requirement tracking and the first dashboard.
- Import historical progress with explicit dates and origin labels.

**Exit evidence:** reproducible baseline, accurate initial status and a working local dashboard showing real blockers.

### Stage 2 — Evidence preparation and memory

- Implement source/record indexing, filtered retrieval and packet construction.
- Preserve table structure and financial definitions.
- Add dependency and supersession handling.
- Evaluate EdgarTools.
- Implement the two skills and their command integration.

**Exit evidence:** a reproducible packet from saved sources, correct retrieval of relevant history, rejection of stale/incompatible material and verified skill discovery.

### Stage 3 — Orchestration and the real decision cycle

- Extend the existing queue for explicit job selection and authorized batches.
- Separate process completion from analytical disposition.
- Verify worker restrictions, model-route reporting and failure recovery.
- Select the real case and run its bounded analysis/review cycle.
- Save corrections and the final supported, rejected or parked disposition.

**Exit evidence:** an actual reviewed case, an audit trail for the worker calls and no unsupported promotion into trade readiness.

### Stage 4 — Paper, operational and dashboard integration

- Connect the new records to the existing paper and readiness machinery.
- Preserve all ten gates and current-state validation requirements.
- Validate delays, costs, expiry, partial fills and capital boundaries.
- Complete dashboard evidence navigation and task/review history.
- Test normal completion, interruption, stale state and restart behavior.

**Exit evidence:** connected end-to-end behavior, accurate gate displays and explicit outstanding external prerequisites.

### Stage 5 — Evaluation, repair and release

- Run the held-out comparison.
- Complete a separate engineering review.
- Repair material defects and rerun affected tests.
- Run the complete regression suite on the final code.
- Integrate the reviewed release, verify the installed workflow and provide rollback instructions.
- Complete the final acceptance matrix and handoff.

**Exit evidence:** a tested release, measured evaluation, resolved material implementation findings and an honest final capability/readiness assessment.

Do not require every older company pilot to be completed before releasing this scoped workflow.

## 11. Verification and self-evaluation

Tests must challenge behavior and failure conditions, not merely mirror implementation or assert that a field exists.

### Required test coverage

| Area | Required scenarios |
|---|---|
| Evidence | Wrong entity/security, incompatible periods/units, conflicting sources, missing locations, tampered files and incomplete extraction. |
| Calculations | Missing versus zero inputs, exact currency handling, adjustments, dated flows, sensitivity checks and independent arithmetic. |
| Memory | Superseded claims, contradictory findings, rejected/parked cases, relevant lessons, inappropriate cross-company reuse and index rebuild. |
| Time integrity | Future sources, unknown publication dates, later analytical conclusions, expired evidence and correctly labelled retrospective reconstruction. |
| Queue and batches | Explicit job selection, unrelated queued work, duplicate submission, exhausted call budget, unavailable model, timeout and uncertain completion. |
| Worker boundaries | Unauthorized tools, source instructions attempting to redirect the worker, invalid output, model substitution and false identity claims. |
| Review | Unsupported economic conclusions, incorrect expectation comparisons, unresolved material findings and targeted re-review after corrections. |
| Readiness | Exact artifact/version binding, missing current attestations, simulated evidence, stale quotes and all ten gates remaining enforced. |
| Paper/execution | Delayed response, missed entry, partial fill, FX movement, outstanding orders, unrelated account cash and withdrawal versus broker cancellation. |
| Dashboard | Completed/partial/failed/interrupted tasks, missing checkpoints, repeated events, stale/disconnected view, readiness regression and source-text escaping. |
| Migration | Preserved originals, retained configuration, compatible old records, recoverable state and a working rollback. |

Use temporary state and fake model/network transports for engineering tests. No live model call should be needed to exercise routine queue, parser, dashboard or failure behavior.

### Research and retrieval evaluation

Use existing cases as regression fixtures. Select one relevant question or document set held out from implementation tuning.

Freeze an evaluation rubric before comparing the baseline and new preparation routes. Assess:

- Material evidence found and missed.
- Citation and definition accuracy.
- Handling of uncertainty and contrary evidence.
- Unsupported or stale-memory reuse.
- Quality of the final disposition.
- Model usage including review and corrections.

Use equivalent questions, cutoffs and model settings. Label any difference in available evidence. Do not claim percentage savings if measurements are incomplete or incomparable.

Do not impose an arbitrary token-reduction target. Accept measured efficiency gains only when research quality is preserved.

### Independent challenge and repair

After integration, perform a fresh engineering review focused on:

- Whether the goal has actually been implemented end to end.
- Missing or bypassable acceptance controls.
- Recovery and duplicate-dispatch risks.
- Unjustified promotion of historical records.
- Dashboard claims that overstate evidence.
- Scope creep and unnecessary dependencies.

Record findings with severity, evidence and disposition. Repair material implementation defects and rerun the affected checks. Use the permitted targeted recheck where needed.

Do not relabel failed tests, weaken assertions or redefine completion to obtain a pass. Equally, stop repeating broad verification once the relevant checks pass and no new changes justify another run.

Visually inspect the working dashboard in the available browser tooling, including a normal case, blocked case and readiness regression. Record what was actually tested.

## 12. Checkpoints, stopping rules and final delivery

At every stage boundary, and before any interruption, preserve:

- Current goal and stage.
- Code revision and relevant artifact hashes.
- Requirements completed and outstanding.
- Tests and reviews performed, with limitations.
- Worker calls consumed and remaining authorization.
- Current case disposition and live gates.
- Exact next command or bounded action.

Resume from these records rather than reconstructing the project from chat history.

If a source route fails, retain the failure and try a genuinely different approved route only when it could resolve the same material question. Do not repeat overlapping searches merely to consume allowance.

If a research case lacks decisive evidence, park or reject it and complete the remaining implementation/evaluation work. Do not expand into an unlimited search for a tradable company.

If account access, native hook trust, a model route or another external prerequisite is unavailable:

1. Complete independent work that remains possible.
2. Test the relevant interface with clearly labelled fixtures.
3. Record the missing live verification and its consequence.
4. Do not claim that the unavailable behavior was tested.
5. Follow the actual Goal lifecycle rules for completion, budget limits and blocking.

Native lifecycle hooks are an enhancement; the explicit project completion command is the required update path. Phone setup, broker reconciliation, real activation and elapsed prospective observation are separately tracked live prerequisites. Required core model reviews and local functionality cannot be replaced by placeholders.

### Final deliverables

Provide:

- The implemented and integrated code with reproducible launch instructions.
- The working local dashboard and its URL/launcher.
- The two verified project skills.
- Versioned schemas, command documentation and state/recovery guidance.
- The real case’s evidence packet, analysis, independent review and disposition.
- The retrieval/usage comparison.
- Test results, engineering review and repair dispositions.
- A requirement-to-evidence acceptance matrix.
- A concise handoff listing remaining live prerequisites and the next highest-value task.

Use Markdown/HTML and structured JSON for routine outputs. Produce PDF or Excel artifacts only where the existing full-thesis workflow or a substantive model requires them.

The final report must state separately:

1. **Software implemented and tested.**
2. **Research conclusions supported, rejected or parked.**
3. **Operational prerequisites demonstrated or outstanding.**
4. **Whether live trading remains disabled.**
5. **What specifically stands between the current system and a first defensible trade.**

Complete the Goal only when its implementation and evaluation requirements are evidenced. A budget limit is a checkpoint, not completion; a functioning research engine is not automatic trading approval.
