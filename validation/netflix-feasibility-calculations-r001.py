"""Bounded feasibility arithmetic; deliberately produces no Netflix valuation.
Run with Python from the project root. Outputs are deterministic, USD million
except split-adjusted million shares, ratios, percentage points and rates.
"""
from decimal import Decimal as D, getcontext
from pathlib import Path
import json
getcontext().prec=34
def s(x): return format(x,'f')
checks=[]
def check(name,condition):
    if not condition: raise AssertionError(name)
    checks.append(name)
j=json.loads(Path('validation/netflix-foundation-calculations-r002.json').read_text())
g_jan=D('11000');g_apr=D('12500');fee=D('2800')
delta=g_apr-g_jan;residual=fee-delta
check('guide increase',delta==D('1500'))
check('unallocated residual not an actual tax amount',residual==D('1300'))
intercept=g_apr-fee
check('conditional FY receipt exclusion agrees with reviewed foundation',intercept==D('9700'))
common=D('4163.939676');options=D('123.891603');awards=D('2.012512')
gross=common+options+awards;dilution=gross/common-1
check('claims are positive and gross denominator larger',gross>common>0)
check('gross known-award dilution below 3.1 percent',D('.03')<dilution<D('.031'))
check('anti-dilutive options not added again',gross==D('4289.843791'))
# Analytical envelope conditional on fee-specific cash tax in [0, gross fee].
# It is NOT a proved tax bound or sustainable cash bound; other cash movements absent.
receipt_envelope={'tax_assumption':[s(D(0)),s(fee)],'fcf_ex_receipt':[s(intercept),s(intercept+fee)],'economic_owner_cash':None}
check('cash tax envelope order',intercept<intercept+fee)
# Unknown-title range belongs to total three-year cash, not an annual subtraction.
content=D('4000');ad_increment=D('1500')
content_to_ref=content/g_jan
check('three-year upper magnitude/ref comparison',D('.36')<content_to_ref<D('.37'))
check('ad increment pre-tax contribution cannot exceed sales under stated assumption',ad_increment<D('4000'))
# Inputs: issuer approximate ads FY2025 1500, FY2026 3000. FY2026 guide already includes doubling.
guide_low=D('51000');guide_high=D('51400');margin=D('.315')
oi_low=guide_low*margin;oi_high=guide_high*margin
check('guided OI bounds',oi_low==D('16065') and oi_high==D('16191'))
check('matched provider OI is inside guide interval',oi_low<=D('16120')<=oi_high)
need=D(j['stress_interfaces'].get('unused','0'))
burden=D('4268')-D(j['comparators']['prior_period_only_sensitivity']['profit'])
check('prior-period-only comparator burden',burden==D('524.553'))
matched_growth_cases=[D('1'),D('1.05'),D('1.10'),D('1.20')]
responses=[]
for growth in matched_growth_cases:
    break_even=1/growth
    responses.append({'per_share_earnings_ratio':s(growth),'break_even_multiple_ratio':s(break_even),'support_ratio_at_10pct_compression':s(growth*D('.9')),'support_ratio_at_20pct_compression':s(growth*D('.8'))})
    check('multiple break-even '+s(growth),abs(growth*break_even-1)<D('1e-32'))
check('ten percent improvement insufficient for ten percent compression',D('1.1')*D('.9')<1)
check('twenty percent improvement insufficient for twenty percent compression',D('1.2')*D('.8')<1)
# Source author's market illustrative beta=1; beta is not selected for Netflix.
rf=D('5.29');erp=D('4.20');default=D('.22')
check('author market sum beta one invariant',rf+erp==(rf-default)+(erp+default))
check('default adjustment not invariant at beta two',(rf-default)+2*(erp+default)-(rf+2*erp)==default)
result={
 'schema':'netflix-feasibility-arithmetic-v1','revision':'r001','units':'USD million; shares million on post-Nov2025 split basis; source rates percent',
 'guidance_bridge':{'january_2026_fcf':s(g_jan),'april_july_2026_fcf':s(g_apr),'gross_termination_receipt':s(fee),'increase':s(delta),'unallocated_tax_and_other_changes_residual':s(residual),'receipt_cash_tax':None,'scope':'Approximate, changed management projections; primarily after-tax fee impact does not isolate taxes or freeze every other component.'},
 'conditional_receipt_envelope':receipt_envelope,
 'claims_june_30':{'actual_common':s(common),'known_options':s(options),'known_unvested_awards':s(awards),'gross_potential_claims':s(gross),'gross_dilution_percent':s(dilution*100),'per_share_ratio_no_proceeds':s(common/gross),'scope':'Dated gross known-award sensitivity; all exercises/no exercise proceeds; not current fully diluted shares and not a cap on future issuance.'},
 'content_commitments':{'management_range_total_three_years':['1000','4000'],'incremental_uncovered_cash_conditional_range':['0','4000'],'upper_total_divided_by_one_year_january_guide_percent':s(content_to_ref*100),'scope':'Magnitude comparison across different periods only; not annual burden. Could overlap entirely with planned spend; exact timing, tax effect, replacement and forecast coverage unknown; management estimate not a contractual maximum.'},
 'ad_guidance':{'approx_2025_revenue':'1500','approx_2026_revenue':'3000','already_expected_sales_increment':'1500','scope':'Issuer interested guidance, in July revenue/margin baseline; not additional upside; no incremental margin chosen.'},
 'issuer_fy_oi_interval':[s(oi_low),s(oi_high)],'provider_fy_oi':'16120','q3_comparator_burden':s(burden),
 'response_sensitivities':responses,'response_scope':'Algebra for positive consistently defined per-share earnings and positive multiples. Chosen percentage changes are stress examples, not forecasts/probabilities/actual price returns; cash/FX/costs excluded.',
 'discount_source':{'as_of':'2026-10-01','author_treasury_reference_percent':'5.29','trailing_adjusted_payout_erp_percent':'4.20','default_spread_percent':'.22','adjusted_rf_percent':'5.07','adjusted_erp_percent':'4.42','illustrative_market_return_beta_one_percent':s(rf+erp),'netflix_beta':None,'netflix_discount_rate':None,'scope':'NYU author estimates and reference inputs, not independently obtained Treasury quote; beta-one sum is arithmetic, not Netflix required return.'},
 'valuation':None,'normalized_owner_cash':None,'entry_ceiling':None,'actionable':False,'checks':checks,'check_count':len(checks)
}
out=Path('validation/netflix-feasibility-calculations-r001.json')
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'valuation':None,'gross_dilution_percent':s(dilution*100),'unallocated_residual':s(residual)}))
