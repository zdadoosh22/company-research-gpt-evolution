"""Conditional pro-forma January 2027 cash-franchise component, not current value.
All money USD millions, shares millions. Run from project root. No model calls.
"""
from decimal import Decimal as D,getcontext
from pathlib import Path
import json
getcontext().prec=34
def s(v):return format(v,'f') if isinstance(v,D) else v
def encode(v):
 if isinstance(v,D):return s(v)
 if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
 if isinstance(v,list):return [encode(x) for x in v]
 return v
checks=[]
def check(n,c):
 if not c:raise AssertionError(n)
 checks.append(n)
R0=D('51200');OI0=R0*D('.315');A0=D('18064.3826');assets0=D('33837.573')
shares=D('4289.843791');actual_shares=D('4163.939676')
wc2025=D('790.661')+D('8.039')-D('881.218')-D('254.917')+D('793.655')
netcap2025=D('688.220')-D('333.389');wc_intensity=wc2025/D('6182.321')
netcap_ratio=netcap2025/D('45183.036');da_ratio=D('333.389')/D('45183.036')
cash_interest=D('.06');k=D('.0507')+D('1.25')*D('.0442')
debt0=D('14372');maturities={2027:D('1486'),2028:D('3500'),2029:D('4329'),2030:D('2257'),2034:D('1000'),2036:D('1000')}
principal_tranches={2027:[(D('1486'),D(5)/12)],2028:[(D('1600'),D(1)+D(4)/12),(D('1900'),D(1)+D(11)/12)],2029:[(D('2057'),D(2)+D(5)/12),(D('2272'),D(2)+D(11)/12)],2030:[(D('2257'),D('3.5'))],2034:[(D('1000'),D(7)+D(8)/12)],2036:[(D('1000'),D(9)+D(8)/12)]}
historical_conversion=D('9092.604')/D('10981.201')
check('FY2025 noncontent working capital net uses',wc2025==D('456.220'))
check('FY2025 depreciation/capex net uses',netcap2025==D('354.831'))
check('remaining debt beyond explicit horizon',debt0-sum(maturities.values())==D('800'))
check('independent rate construction',k==D('.105950'))
# Empirical aggregate conversion; analyst use is conditional, not causal identification.
inc_h1=D('1027.914')/D('3187.728');inc_annual=D('2908.989')/D('6182.321')
cases={
 'downside':{'growth':[D(x) for x in ['0','.03','.03','.02','.01','0','0','0','0','0']],'initial_margin':D('10417.614')/D('39000.715'),'incremental_oi':inc_h1,'tax':D('.30'),'initial_content_excess':D('.16200904444949115445523729105477425'),'asset_growth_intensity':D('1'),'acquisition_drag':D('585.744'),'terminal_growth':D('0')},
 'central':{'growth':[D(x) for x in ['.1118','.08','.06','.04','.03','.02','.02','.02','.02','.02']],'initial_margin':D('.315'),'incremental_oi':inc_h1,'tax':D('.25'),'initial_content_excess':D('.10'),'asset_growth_intensity':D('1'),'acquisition_drag':D('0'),'terminal_growth':D('.02')},
 'upside':{'growth':[D(x) for x in ['.1336','.1118','.10','.08','.06','.04','.03','.02','.02','.02']],'initial_margin':D('.315'),'incremental_oi':inc_annual,'tax':D('.20'),'initial_content_excess':D('17707.455')/D('16422.166')-1,'asset_growth_intensity':D('.5'),'acquisition_drag':D('0'),'terminal_growth':D('.02')}
}
coverage={
 'covered':{},
 'partial_uncovered':{2027:D('500'),2028:D('1000'),2029:D('500')},
 'full_uncovered_range_endpoint':{2027:D('1000'),2028:D('2000'),2029:D('1000')},
 'beyond_management_range_stress':{2027:D('1500'),2028:D('3000'),2029:D('1500')}
}
def calculate(case,coverage_name,rate=k):
 cfg=cases[case];schedule=coverage[coverage_name];R=R0;OI=R0*cfg['initial_margin'];assets=assets0;noncontent_assets=D('2004.350')*R0/D('45183.036');debt=debt0;rows=[];pv=D(0);earnings_pv=D(0);liquid=D('9127.910');minimum_liquid=liquid
 for n,year in enumerate(range(2027,2037),1):
  growth=cfg['growth'][n-1];newR=R*(1+growth)
  # Downside resets profitability before the first year; later increments remain constrained.
  delta_R=newR-R;OI+=cfg['incremental_oi']*delta_R;R=newR;A=A0*R/R0
  required_net_asset_growth=cfg['asset_growth_intensity']*growth*assets
  timing_excess=cfg['initial_content_excess']*A*D(10-n)/9
  excess=max(required_net_asset_growth,timing_excess);cash_content=A+excess;assets+=excess
  principal=maturities.get(year,D(0));interest=(debt-principal/2)*cash_interest
  tax=max(D(0),OI-interest)*cfg['tax']
  wc=max(delta_R,D(0))*wc_intensity
  net_capex=max(netcap_ratio*R*D(10-n)/9,growth*noncontent_assets)
  noncontent_assets+=net_capex;other_da=R*da_ratio;capex=other_da+net_capex
  noncontent=wc+net_capex;acq=cfg['acquisition_drag']*R/R0;C=schedule.get(year,D(0))
  recurring_cash=OI-interest-tax-excess-noncontent-acq
  fcfe=recurring_cash-C-principal;debt-=principal
  # All positive yearly FCFE is available for distribution; negatives draw pro-forma liquidity.
  distribution=max(fcfe,D(0));liquid+=fcfe-distribution;minimum_liquid=min(minimum_liquid,liquid)
  C_time=D('2.5') if year==2029 else D(n)
  principal_pv=sum(amount/(1+rate)**time for amount,time in principal_tranches.get(year,[]))
  pv_cf=recurring_cash/(1+rate)**n-C/(1+rate)**C_time-principal_pv;pv+=pv_cf
  earnings_pv+=(OI-interest-tax)*historical_conversion/(1+rate)**n-C/(1+rate)**C_time-principal_pv
  rows.append({'year':year,'revenue':R,'operating_income_core':OI,'content_amortization':A,'cash_content_planned':cash_content,'content_assets_end':assets,'cash_interest':interest,'cash_tax':tax,'noncontent_net_capex_and_wc':noncontent,'noncontent_depreciation':other_da,'noncontent_capex':capex,'noncontent_working_capital_uses':wc,'noncontent_assets_end':noncontent_assets,'recurring_acquisition_stress':acq,'cash_before_uncovered_content_and_principal':recurring_cash,'incremental_uncovered_content_cash':C,'principal_repayment':principal,'fcfe':fcfe,'debt_end':debt,'liquidity_end_after_available_distribution':liquid,'discounted_fcfe':pv_cf})
 g=cfg['terminal_growth'];Rterm=R*(1+g);OIterm=(OI/R)*Rterm;Aterm=A0*Rterm/R0
 # Mature operating assets grow at g and their cash cost is funded, not free terminal growth.
 content_growth=g*assets
 terminal_noncontent_growth=g*noncontent_assets+g*R*wc_intensity
 terminal_operating_cash=OIterm*(1-cfg['tax'])-content_growth-terminal_noncontent_growth-cfg['acquisition_drag']*Rterm/R0
 operating_terminal=terminal_operating_cash/(rate-g)
 # Remaining 2054 principal and post-2036 interest are deducted once, using this equity-cash rate.
 remaining_interest=debt*cash_interest*(1-cfg['tax'])
 terminal_debt_claim=sum(remaining_interest/(1+rate)**t for t in range(1,19))+debt/(1+rate)**18
 terminal_equity=operating_terminal-terminal_debt_claim
 terminal_pv=terminal_equity/(1+rate)**10;component=pv+terminal_pv
 # Algebraic consistency check only: same terminal cash expressed via adjusted earnings.
 mature_earnings=OIterm*(1-cfg['tax'])
 capitalization_multiple=(1-(content_growth+terminal_noncontent_growth+cfg['acquisition_drag']*Rterm/R0)/mature_earnings)/(rate-g)
 capitalized_earnings=mature_earnings*capitalization_multiple-terminal_debt_claim
 check(case+'/'+coverage_name+'/'+s(rate)+' earnings/cash terminal consistency',abs(capitalized_earnings-terminal_equity)<D('1e-25'))
 check(case+'/'+coverage_name+'/'+s(rate)+' funded annual path',minimum_liquid>=0 and debt==D('800'))
 check(case+'/'+coverage_name+'/'+s(rate)+' terminal positive and g below equity rate',terminal_operating_cash>0 and g<rate)
 earnings_component=earnings_pv+(mature_earnings*historical_conversion/(rate-g)-terminal_debt_claim)/(1+rate)**10
 return {'case':case,'coverage':coverage_name,'rate':rate,'rows':rows,'terminal':{'growth':g,'revenue':Rterm,'core_operating_income':OIterm,'recurring_unlevered_after_tax_earnings':mature_earnings,'content_growth_cash_reinvestment':content_growth,'cash_content':Aterm+content_growth,'remaining_debt':debt,'remaining_after_tax_interest_per_year':remaining_interest,'remaining_debt_claim_at_2036':terminal_debt_claim,'operating_cash':terminal_operating_cash,'terminal_equity_cash_value':terminal_equity,'pv':terminal_pv,'terminal_percent_of_component':terminal_pv/component*100,'earnings_capitalization_multiple_after_reinvestment':capitalization_multiple,'same_input_algebraic_check_value':capitalized_earnings},'earnings_power_diagnostic':{'historical_cash_conversion':historical_conversion,'per_gross_claim_component':earnings_component/shares,'difference_from_cash_component_percent':(earnings_component/component-1)*100,'scope':'Historical FY25 FCF-minus-SBC / GAAP NI applied to prospective cash-tax earnings proxy, so definitions/timing differ. A rough conversion and duration cross-check, not a second approved valuation. No averaging.'},'cash_franchise_component':component,'per_known_gross_claim_component':component/shares,'per_actual_common_component':component/actual_shares,'minimum_proforma_liquidity':minimum_liquid,'opening_surplus_cash_added':D(0),'total_equity_value':None,'current_intrinsic_value':None,'entry_ceiling':None,'actionable':False}
outputs=[calculate(c,cover) for c in cases for cover in coverage]
sensitivity=[{'case':c,'coverage':cover,'rate':rate,'per_known_gross_claim_component':calculate(c,cover,rate)['per_known_gross_claim_component']} for c in cases for cover in ['covered','full_uncovered_range_endpoint'] for rate in [D('.0949'),D('.1170')]]
# Historical owner-cash check with an explicitly unallocated reconciling remainder, not a forecast plug.
historical_formula=D('13326.603')-D('718.611')-D('2220.384')+D('16422.166')-D('17707.455')-netcap2025-wc2025
reported_owner=D('10149.273')-D('688.220')-D('368.449')
historical_remainder=reported_owner-historical_formula
check('reported FY2025 FCF minus SBC',reported_owner==D('9092.604'))
reconciling_components={'cash_vs_accrued_interest':D('718.611')-D('776.510'),'accrued_interest_and_other_income':D('172.459'),'cash_vs_provision_tax':D('2220.384')-D('1741.351'),'deferred_income_tax_adjustment':D('-442.056'),'debt_FX_non_cash_adjustment':D('72.348'),'other_non_cash_adjustment':D('577.451')}
check('FY2025 cash bridge residual fully decomposed',sum(reconciling_components.values())==historical_remainder)
result={'schema':'netflix-conditional-framework-v2','reference_date':'2027-01-01 pro forma, not actual January balance or October intrinsic value','information_cutoff':'2026-10-09','units':'USD million and million split-adjusted shares; rates decimal','assumption_status':'Transparent analyst cases and stress parameters, not probabilities, certified bounds or management scenarios','seed':{'FY26_revenue':R0,'FY26_OI':OI0,'conditional_FY26_amortization':A0,'dated_June_content_assets':assets0,'proforma_January_principal':debt0,'June_gross_known_claims':shares,'proforma_opening_liquidity_condition':'9127.910; not an actual January statement; no opening cash value added','equity_rate':k,'historical_noncontent_WC_uses':wc2025,'historical_net_noncontent_capex':netcap2025},'cases':cases,'uncovered_schedules':coverage,'outputs':outputs,'rate_sensitivity':sensitivity,'historical_cash_check':{'reported_FY25_FCF_minus_SBC':reported_owner,'specified_cash_bridge':historical_formula,'reconciling_remainder':historical_remainder,'components':reconciling_components,'scope':'Fully decomposed historical population/timing differences; no positive remainder imported into forecast. Underlying other-noncash recurrence is not assumed.'},'checks':checks,'check_count':len(checks),'current_value':None,'portfolio_decision':None,'execution_instruction':None,'actionable':False}
Path('validation/netflix-framework-calculations-r002.json').write_text(json.dumps(encode(result),indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'main_components_USD_per_gross_claim':[{k:encode(x[k]) for k in ['case','coverage','per_known_gross_claim_component']} for x in outputs if x['coverage'] in ['covered','full_uncovered_range_endpoint']]}))
