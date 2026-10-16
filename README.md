# Company research 2

A local research workspace for detailed company theses, focused questions, comparisons and requested updates.

## Start a research chat
Open this folder as a local project in the desktop app, then start a chat there. This makes AGENTS.md the entry point for shared instructions. A folder on disk is not automatically a registered sidebar project. If working from another folder, explicitly ask the assistant to load this folder's AGENTS.md first.

You can simply say: **Research [company / ticker].** Optional context: listing, buyer/holder, concerns, horizon, return hurdle or source limits. See templates/ for copyable requests. Full theses run unattended with dated work checkpoints. Ask questions or request an update after delivery.

## What you receive
A full PDF, a standalone thesis PDF of at most five readable pages, and an editable Excel workbook. The PDF records the original dated judgement; What-if edits to Excel do not rewrite the research. Material evidence and calculation inputs stay with each dated run so a future chat can audit or update it.

## Where things live
- methodology/: permanent principles, the complete versioned research specification and change history.
- workflows/: research, updates, evidence handling and model-review procedures.
- templates/: initial requests and research-record structures.
- companies/: one folder per legal entity, with an index and dated run folders.
- lessons/: confirmed lessons and proposed methodology changes.
- tools/: research utilities and the optional local observation service; no separately billed model API is required.
- monitoring/: observation configuration, setup instructions and manual-record examples.
- validation/: acceptance criteria, tests, reference assessment and pilot findings.
- work/: scratch files and rendered previews; not a source of approved research.

## Status
See validation/status.json for the current implementation and pilot status. Read any limitations before relying on numerical outputs. Pilots are validation research, not personalised investment recommendations.

## Continuity

The bounded engine extension is in development. [Engine workflow](workflows/research-engine.md) documents the explicit checkpoint and status commands; implementing them does not complete the required research cycle or approve a trade. [The authorised r002 brief](planning/2026-10-14-research-engine-goal-brief-r002.md) defines the full acceptance boundary.
The next chat loads the current methodology, relevant company index and run records. Completed runs are immutable by convention and protected by publication hashes. An update creates a new version and preserves the prior assessment. Methodology changes require a documented reason and approval when consequential. We have not archived the pasted historical conversation.

The company index distinguishes `latest` (published/approved) from `latest_active` (unfinished or partial). Load run.json before using either. The focused Astra audit is complete, with corrections preserved in r002. The pilots remain partial and must not be treated as approved valuations; the remaining analytical foundations and model workflow validation are recorded in validation/status.json.

## Local tools
Use tools/run.ps1 to launch the bundled Python runtime, for example `./tools/run.ps1 test` or `./tools/run.ps1 list`. The assistant handles these utilities during research; you do not need to write code.

## £300 observation extension

The user-authorised extension adds an isolated £300 ledger, primary-source monitoring, read-only subscription-funded research drafts and optional Telegram delivery. The allocation is user-declared; broker cash remains unverified. Its objective is aggressive growth over days to a few months. It currently never places broker orders or enables real recommendations. See [monitoring/START-HERE.md](monitoring/START-HERE.md), [improvement roadmap](monitoring/IMPROVEMENT-ROADMAP.md) and validation/observation-status.json for setup, staged development and verified limits. The Windows task is `CompanyResearch2-Observation`; it requires a signed-in, awake computer. Existing pilot research and methodology approvals are unchanged.
