"""Targeted source-bound funding/ownership diagnostics; no valuation or trades."""
from pathlib import Path
from decimal import Decimal as D,getcontext
import datetime,hashlib,json
getcontext().prec=40
ROOT=Path(__file__).resolve().parents[1];E='monitoring/studies/evidence/2026-10-11-amd-funding-claims-r001/'
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
checks=[]
def check(name,condition,evidence):
 checks.append({'name':name,'passed':bool(condition),'evidence':evidence})
b=load('validation/subscription-progress-baseline-2026-10-11-r001.json')
preserved=[x for x in b['files'] if x['path']!='monitoring/config.json']
check('All577 research/method/code predecessors unchanged except authorised config hold',len(preserved)==577 and all(sha(x['path'])==x['sha256'] for x in preserved),577)
old=load('monitoring/studies/2026-10-09-amd-discovery-screen.json')
q=next(x for x in old['sources'] if x['source_id']=='q2-10q')
check('Original primary quarter archive matches bound source',sha(q['path'])==q['sha256'],q['sha256'])
captures=load(E+'source-capture-register.json')['records']+load(E+'financing-source-register.json')['records']
check('All9 fresh captures match actual raw bytes',len(captures)==9 and all(x['sha256'] and sha(x['raw_path'])==x['sha256'] for x in captures),[x['id'] for x in captures])
fresh=next(x for x in captures if x['id']=='q2-filing')
check('Fresh issuer quarter is original-byte-identical',fresh['sha256']==q['sha256'],'No source facts silently updated')
projection=load(E+'selected-source-passages.json')
check('Material selected passages are present in actual projections',all(x['found'] and x['excerpt'] for r in projection['records'] for x in r['passages']),len(projection['records']))
principal=[D('1250'),D('1500'),D('1000'),D('1000')]
prices=[D('99.889'),D('99.921'),D('99.919'),D('99.757')]
discounts=[D('0.140'),D('0.150'),D('0.180'),D('0.230')]
coupons=[D('0.046'),D('0.05'),D('0.0525'),D('0.055')]
gross=sum(p*x/100 for p,x in zip(principal,prices))
underwriting=sum(p*x/100 for p,x in zip(principal,discounts))
before=gross-underwriting;net=before-D('9.7');friction=sum(principal)-net
check('Principal and exact public-price proceeds',sum(principal)==4750 and gross==D('4744.1875'),{'face':str(sum(principal)),'gross':str(gross)})
check('Underwriting deducted once; before expenses agrees with cover',underwriting==D('8.1') and before==D('4736.0875'),{'underwriting':str(underwriting),'before_expenses':str(before)})
check('Estimated offering costs and cash table',net==D('4726.3875') and friction==D('23.6125') and (D('5086')+net).quantize(D('1'))==D('9812'),{'estimated_net':str(net),'face_less_net':str(friction),'not_final_actual_costs':True})
coupon=sum(p*r for p,r in zip(principal,coupons))
check('New contractual annual/normal half-year coupon',coupon==D('240') and coupon/2==D('120'),{'annual':str(coupon),'normal_half_year':str(coupon/2),'first_nominal_payment':'2027-02-17','accrual_start':'2026-08-17','conditional_not_observed':True})
liq=D('5086')+D('8025');liq_issue=liq+net;principal_issue=D('3250')+sum(principal)
check('Illustrative capitalization distinguishes carrying/principal debt',principal_issue==8000 and principal_issue-48==7952,{'principal':str(principal_issue),'estimated_carrying':'7952','not_current_debt':True})
check('Restricted cash excluded from illustrative usable liquidity',liq==13111 and liq_issue==D('17837.3875'),{'illustrative_unrestricted':str(liq_issue),'restricted_excluded':'11','not_current_liquidity':True})
check('Hypothetical old-principal settlement reduces both sides once',liq_issue-875==D('16962.3875') and principal_issue-875==7125 and (liq_issue-principal_issue)==(liq_issue-875-(principal_issue-875)),{'settlement_unverified':True,'no_equity_gain_from_principal_payment_alone':True})
commitments=list(map(D,['17386','5474','2851','2528','1471','566']))
check('Unconditional payment buckets sum to source total',sum(commitments)==30276,{'periods':['remainder2026','2027','2028','2029','2030','2031+'],'total':'30276','not_debt_sum':True})
check('Reported CFO/capex and single-variable payable sensitivity',D('5321')-D('1197')==4124 and D('5321')-D('1197')-D('2170')==1954,{'reported_continuing_cfo_less_cash_capex':'4124','one_variable_sensitivity':'1954','not_normalized_owner_cash':True})
n=D('1632.475042');w=D('320');total=n+w;fraction=n/total;growth=w/n
check('Warrant face exercise cash and dated owner-fraction identity',w*D('0.01')==D('3.2') and abs(fraction*(1+growth)-1)<D('1e-38'),{'denominator_date':'2026-07-29','shares_m':str(n),'hypothetical_total_m':str(total),'old_owner_fraction':str(fraction),'share_addition_fraction':str(growth),'ownership_reduction_fraction':str(1-fraction),'exercise_cash_m':'3.2','not_current_vesting':True})
check('World Labs variable-share relation is dimensional, not market-priced',D('8200')/D('200')==D('41'),'Only arithmetic identity tested at a fictional200USD VWAP; no current price adopted or numerical acquisition share forecast published')
config=load('monitoring/config.json');before_config=next(x for x in b['files'] if x['path']=='monitoring/config.json')
check('Intentional model hold rather than a hidden trading activation',config['research_enabled'] is False and config['mode']=='observation-only' and config['quote_acquisition']=='manual-only',{'before_sha256':before_config['sha256'],'after_sha256':sha('monitoring/config.json')})
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'passed':all(x['passed'] for x in checks),'scope':'Author source-byte and definition/arithmetic checks only; actual new financing source reading and independent challenge separate. No current full cash valuation, future observation, investment performance, broker or phone acceptance.'}
(ROOT/'validation/amd-funding-claims-verification-2026-10-11-r001.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'passed':result['passed'],'failed':[x['name'] for x in checks if not x['passed']]}))
raise SystemExit(0 if result['passed'] else 1)
