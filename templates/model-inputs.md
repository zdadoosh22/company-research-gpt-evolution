# Explicit company model contract

`model.json` is an analyst-built input record, not an automatic forecast generator. Include the selected method, research and price dates, currency, provenance-bearing source_actuals, assumptions, economic scenario explanations and limitations. `reviewed-results.json` is the independent calculation result used for report figures.

The initial operating helper uses an equity dividend/retention model. Include opening revenue, ownership and excess cash; dated forecast periods; and explicit cost-of-equity, terminal-growth, growth, after-compensation EBIT margin, tax, D&A, capex, incremental working capital, interest, net borrowing, payout, repurchases, separately justified dilution, repurchase prices and cash yields for each period. Current value discounts the identical dated receipts used for shareholder returns. It requires positive terminal FCFE and a funded path; it is unsuitable for a loss-making/pre-revenue perpetuity.

Include `input_bindings` for base_revenue and diluted_shares: arrays of `{metric, period, source_id, coefficient}` identifying unique observations, plus a `cash` observation reference. The source cells feed Excel formulas; do not replace them with disconnected totals. Check compatible periods/scope before constructing the bindings. Policy choices such as operating cash reserve must be explicit. Missing mandatory inputs prevent supported numerical outputs.

The validated Excel helper currently supports five dated operating forecast periods. Longer transitions, SOTP/NAV, finite life, insurers, other regulated sectors and conditional pipeline models require a separately constructed workbook with equivalent checks. The financial calculator supports any explicitly dated number of periods; that does not validate new sector economics. The bank pilot is a steady-state tangible-book check, not a full bank distribution model.

Scenarios are company-specific economic narratives and inputs, with separate What-if values. Reported scenario comparison and market-implied-growth results are dated snapshots. The active forecast, valuation, dated returns, sensitivities and entry-hurdle calculations recalculate in Excel. Rebuild reported snapshots through the assistant after an approved model/research update. Never claim changing Excel updates the PDF or qualitative judgement.

For a holder, record cost basis and portfolio weight in request.json/run request only. Neither belongs in intrinsic-value calculation inputs. Prices, currency conversion and share/ADS ratios require dated security evidence.
