# Company research 2

A local Python/SQLite equity research and swing-trading workspace for:
1. **Deep Company Valuations**: Primary-source fundamental analysis following `methodology/company-research-v1.0.0.md`.
2. **Short-Horizon Opportunity Dossiers & £300 Model Sleeve Signals**: Actionable trade signals (Buy / Watch Trigger / Pass) for Aidan's isolated £300 Trading 212 Stocks ISA sleeve, delivered to iPhone via Telegram (`tools/observation.py`) with 100% manual order execution.

## Authority & Execution Rules
`AGENTS.md` and `CLAUDE.md` are the authoritative rules for this workspace:
- **Single-Pass Execution**: Complete analyses directly in a single reasoning pass without spawning multi-worker queues (`scoped_research_queue.py`) or running checkpoint ceremonies (`research_checkpoint.py`).
- **Pragmatic Completion**: Never "park" a company indefinitely over minor missing disclosures or HTTP 403 pages. Use primary filings, bound missing inputs with explicit Bear/Base/Bull sensitivity ranges, and deliver a concrete price-trigger verdict.

## Where Things Live
- `AGENTS.md` / `CLAUDE.md`: Master instructions, accounting rules, £300 risk rules, and output contract.
- `methodology/`: Permanent valuation principles (`principles.md`) and full specification (`company-research-v1.0.0.md`).
- `companies/`: Per-company indexes, historical runs, and model inputs.
- `monitoring/`: Model portfolio configuration (`config.json`), decision scope (`DECISION-SCOPE.md`), and prior event studies (`monitoring/studies/`).
- `tools/`:
  - `finance.py` & `decision_economics.py`: Deterministic Decimal math for DCF/XIRR, TTM bridges, FX conversion, and round-trip break-even hurdles.
  - `research_memory.py`: SQLite FTS5 search across saved runs and studies.
  - `observation.py`, `observation_core.py`, `observation_transport.py`: SQLite ledger for the £300 sleeve and DPAPI-protected Telegram alert dispatch.

## Day-to-Day CLI Quick Reference
Run commands via PowerShell from the repository root:
- **Configure Telegram credentials (one-time)**: `python tools/observation.py configure-telegram`
- **Initialize & fund £300 sleeve (one-time)**: `python tools/observation.py fund --amount 300`
- **Send a Model Signal / Alert to iPhone**: `python tools/observation.py send-signal --text "BUY NFLX ..."` (or pass `--json <file.json>`)
- **Check Sleeve Status**: `python tools/observation.py status`
- **Log a Manual Order & Fill**:
  - `python tools/observation.py order <alert_id> buy <EXCHANGE:TICKER> <qty> --reserve-gbp <gbp> --order-id <ord_id>`
  - `python tools/observation.py fill <ord_id> <exec_id> <qty> <gbp_value> --fees-gbp <fees>`
