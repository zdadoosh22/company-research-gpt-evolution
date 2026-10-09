# Trading Shadow Agent: selective reuse assessment

Reference: C:/Users/aidan/Documents/TradingAgent/trading-shadow-agent. Inspect read-only; no runtime imports or edits.

| Component | Decision |
|---|---|
| SEC connector | Defer adoption. Needs as-of publication filters, taxonomy/unit/entity selection, amendment handling, source identity and freshness verification. Public filing review remains primary. |
| DCF arithmetic | Reimplement a small transparent calculator with independent tests. Existing code uses simplified FCF inputs and heuristic scenario changes that cannot establish company-specific FCFF forecasts. |
| Bank model | Use the economic concept of equity/excess-return valuation; rebuild calculations with explicitly justified returns, capital and distribution assumptions. |
| Sensitivity arithmetic | Reimplement against the same explicit forecast, testing that the base combination reproduces the valuation. |
| Thesis ingestion | Adopt only filename matching and text extraction ideas, preserving source identity and attributed opinion. No target-injection or inherited conclusions. |
| Data reconciliation | Retain conflict visibility; reject the existing optional LLM explanation as proof. Select evidence through period/definition reconciliation. |
| Quality engine | Borrow test categories only. Reject market-price-driven valuation adjustment, fixed high-growth assumptions and unsupported generic thesis output. |
| Frontend / technical / paper trading | Outside initial scope. |

No wholesale code has been copied. New utilities are intentionally independent and require no paid APIs, Groq pipeline or source repository dependencies.

Concrete inspection findings: quality_checker.py reweights valuation components after a sufficiently large negative gap versus market price (including 15% DCF / 45% multiples / 40% analyst consensus, or 20% / 80%). It also uses fixed growth thresholds and a static ticker blacklist. These are rejected as defaults. data_reconciliation.py chooses the first available source value and can request a likely explanation from an external model; this is not verified reconciliation. sec_edgar_client.py selects recent filing values but needs an explicit historical publication boundary before as-of reuse. These findings are based on source inspection, not Gemini's summary or a successful prior test count.

The new evidence helper keeps incomparable periods/scopes/currencies separate and leaves conflicts unresolved until supported by evidence. The independent financial helper and Excel models were tested against explicit fixtures. reference-hashes.json and reference-integrity.json record the inspected files; the reference remains unchanged.
