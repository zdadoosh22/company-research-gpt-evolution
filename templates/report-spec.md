# Reviewed report specification

Write `report.json` within the active run after the evidence and model review. The presentation helper never invents analysis or changes assumptions.

Full thesis: `title`, `status`, `standalone` section array, `supporting` section array. Other modes: `title`, `status`, `sections` array. Each section has `title`, optional `page_break`, and `blocks`. A block contains `text`, `heading`, or a `table` matrix including its header. All table values must come from reviewed model results or traceable observations. Avoid manually rounded arithmetic as a model input.

Use three to five readable standalone pages. Include legal entity and selected security, date and quote timestamp, clear judgement or withheld judgement, decisive evidence, assumptions, four separate numerical concepts, opposing case, material uncertainties and three company-specific learning questions. The full report begins with this exact content and expands all material methodology areas. Cite source IDs in prose; the helper appends the precise linked source register. Source IDs do not substitute for actually reading sources.

Run `tools/reports.py RUN_PATH` with the configured bundled Python after applying the PDF skill. Render every resulting page and review it visually. The initial version uses 10.5pt body text, readable tables and linked sources. Do not shrink text to force a five-page short thesis; edit repetition instead.

The supporting workbook builder supports the validated operating equity/retention pattern, a focused bank steady-state check and a global evidence reconciliation. It is not a universal sector engine. Other sector workbooks require explicit construction and validation using the spreadsheet skill. A full bank thesis needs a capital-constrained path beyond the focused substitution fixture.
