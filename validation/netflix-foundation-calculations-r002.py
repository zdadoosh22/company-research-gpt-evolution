"""Bounded financial reconciliation, r002 label corrections; r001 preserved. No valuation, service imports or operational writes.

Run with bundled Python from the project root. Output is JSON to stdout.
USD millions except margins/ratios. Decimal inputs preserve reported precision;
Fraction independently recomputes comparator arithmetic without binary floats.
Sources: issuer Q2 2026 letter pp.1-2,6,9-12; Q3 2025 letter pp.1-2,11.
Approximate $619m and 20% attribution are sensitivity inputs, not exact normalization.
"""
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import json

getcontext().prec = 36

def calculate():
    q3_profit, q3_revenue, charge, current_fraction = map(D, ('3248.247','11510.307','619','0.20'))
    future_profit, future_revenue = D('4268'), D('12860')
    prior_charge = charge * (1-current_fraction)
    cases = {}
    for name, adjustment in [('reported', D(0)), ('prior_period_only_sensitivity', prior_charge), ('full_charge_sensitivity', charge)]:
        comparator = q3_profit + adjustment
        cases[name] = {'profit': comparator, 'margin_percent': 100*comparator/q3_revenue,
                       'guided_profit_growth_percent': 100*(future_profit/comparator-1),
                       'guided_margin_delta_pp': 100*(future_profit/future_revenue-comparator/q3_revenue)}
        independent = F(str(comparator))/F(str(q3_revenue))*100
        assert abs(cases[name]['margin_percent']-D(independent.numerator)/D(independent.denominator)) < D('1e-30')
    cash26, cash25 = D('9774.440')+D('136.578'), D('7385.470')+D('625.305')
    amort26, amort25 = D('8529.209'), D('7655.186')
    cfo, capex, receipt, brazil_cash, sbc = map(D, ('7034.017','414.774','2800','729','271.717'))
    fcf = cfo-capex
    assert fcf == D('6619.243')
    assert D('5094.075')+D('1525.168') == fcf
    assert cash26 == D('9911.018') and cash25 == D('8010.775')
    cashchange = cfo-D('1000.518')-D('5900.441')-D('69.466')
    assert cashchange == D('9102.786')-D('9039.194')
    financing = D('109.290')-D('5984.991')-D('35.861')+D('11.121')
    assert financing == D('-5900.441')
    operating_profit = D('4192.610')+D('3956.997')
    assert operating_profit == D('8149.607')
    assert operating_profit-D('437.762')+D('2903.827') == D('10615.672')
    assert D('10615.672')-D('1931.467') == D('8684.205')
    return {'schema':'netflix-foundation-calculations-v1','revision':'r002','units':'USD million; percentages and ratios labelled',
      'inputs_source':'Q2 2026 and Q3 2025 shareholder letters; H1 Brazil and financing-cost observations from June 10-Q, separately archived in cash note',
      'comparators': cases, 'approx_prior_period_charge': prior_charge,
      'q3_2026_guided_margin_percent':100*future_profit/future_revenue,
      'content':{'cash_2026_h1':cash26,'cash_2025_h1':cash25,'amortization_2026_h1':amort26,'amortization_2025_h1':amort25,
        'cash_growth_percent':100*(cash26/cash25-1),'amortization_growth_percent':100*(amort26/amort25-1),
        'cash_to_amort_2026':cash26/amort26,'cash_to_amort_2025':cash25/amort25,
        'cash_minus_amort_2026':cash26-amort26,'cash_minus_amort_2025':cash25-amort25,
        'full_year_guidance_identity':'H2 cash content ~= 1.1*A_FY - 9911.018; H2 amortization = A_FY - 8529.209; H2 cash-amort ~= 0.1*A_FY - 1381.809',
        'fy2025_amortization':D('16422.166'),
        'conditional_fy2026_amortization':D('16422.166')*D('1.10'),
        'conditional_fy2026_cash_content':D('16422.166')*D('1.10')*D('1.1'),
        'conditional_h2_cash_content':D('16422.166')*D('1.10')*D('1.1')-cash26,
        'conditional_h2_amortization':D('16422.166')*D('1.10')-amort26,
        'conditional_h2_cash_minus_amort':D('16422.166')*D('1.10')*D('0.1')-(cash26-amort26),
        'guidance_caution':'2025 audited annual amortization corroborated by annual SEC 10-K cash flow/Note 5; Q4 letter p14 is an unaudited matching display; applying issuer approximately 10% growth and approximately 1.1x cash ratio compounds rounded guidance, not a precise forecast or sustainable spending floor',
        'asset_rollforward_residual':D('33837.573')-D('32778.392')-(D('9774.440')-amort26),
        'asset_residual_caution':'cash-flow additions need not equal balance-sheet asset additions; FX/other movements unresolved; do not plug residual into sustainable cash'},
      'cash':{'reported_h1_fcf':fcf,'gross_receipt_subtraction_intercept':fcf-receipt,
        'prior_brazil_payment_exclusion_intercept':fcf-receipt+brazil_cash,
        'same_with_sbc_cost_intercept':fcf-receipt+brazil_cash-sbc,
        'h1_receipt_tax_identity':'FCF ex receipt and related paid taxes = 3819.243 + T_cash_H1; not normalized FCF',
        'h1_brazil_sensitivity_identity':'If excluding all disclosed prior-period Brazil cash as nonrecurring: 4548.243 + T_cash_H1; recurrence and claim status remain uncertain',
        'sbc_identity':'Cash-equivalent SBC sensitivity = 4276.526 + T_cash_H1, before other recurring adjustments; alternative claims treatment must not deduct SBC again',
        'fy_identity':'FY guidance ex receipt and associated FY cash taxes ~= 9700 + T_cash_FY; do not add 729 again unless known included and deliberately excluded',
        'h2_guided_fcf':D('12500')-fcf,'cash_including_restricted_change':cashchange,
        'unrestricted_cash_change':D('9099.232')-D('9033.681'),
        'restricted_component_change':cashchange-(D('9099.232')-D('9033.681')),
        'financing_cash_flow':financing,'cash_plus_st_investments_june':D('9099.232')+D('28.678'),
        'debt_carrying_june':D('2483.758')+D('11825.548'),
        'dated_net_debt_carrying_june':D('2483.758')+D('11825.548')-D('9099.232')-D('28.678')},
      'earnings':{'reported_h1_pretax':D('10615.672'),
        'receipt_exclusion_pretax':D('10615.672')-receipt,
        'plus_approx_transaction_financing_expense_sensitivity':D('10615.672')-receipt+D('85'),
        'tax_identity':'Net income excluding receipt = 5884.205 + T_provision_receipt. Adding 85 issuance amortization also needs its own associated tax provision. Total effective tax rate cannot allocate either.',
        'expense_warning':'85 is approximate accounting amortization, not an additional cash addback to already reconciled CFO'},
      'expectations':{'external_fy_operating_margin_percent':100*D('16120')/D('51220'),
        'issuer_fy_op_profit_low':D('51000')*D('0.315'),'issuer_fy_op_profit_high':D('51400')*D('0.315'),
        'external_fcf_gap_to_guide':D('12810')-D('12500'),
        'scope':'Displayed FY2026 figures, provider last-updated Oct8; GAAP/adjusted/tax/termination FCF definitions not reconciled; no quarterly consensus'},
      'stress_interfaces':{
        'demand':'Delta OI = contribution_rate * Delta revenue - Delta fixed/content expense; contribution_rate unquantified, so no numerical demand-loss forecast',
        'content':'Incremental cash payments C reduce CFO-minus-capex by C absent offsetting liability/tax/cash changes; a repeat of observed H1 cash-amort excess is a burden, not an incremental forecast',
        'tax':'Repeat of disclosed 729 prior-period cash payment reduces otherwise identical cash by 729; illustrative historical-sized shock, not probability or same-claim double counting',
        'no_repricing':'E1=E0 and M1=M0 imply unchanged earnings-capitalization support; no positive return inferred',
        'compression':'Support ratio = (E1/E0)*(M1/M0); no M or expected return selected',
        'late':'Positive thesis does not imply value > actual delayed response price; refresh evidence, claims and quote before any future decision',
        'gap_halt_delay':'No executable quote or changed event date => no assumed fill; gaps can pass stops and limits can remain unfilled'},
      'checks':'Comparator Decimal/Fraction agreement and issuer cash/profit identities asserted; analytical review separate',
      'actionable':False,'valuation':None,'entry_ceiling':None}

if __name__ == '__main__':
    print(json.dumps(calculate(), default=lambda x: str(x) if isinstance(x,D) else x, indent=2))
