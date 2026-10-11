"""Targeted new-source estimate arithmetic and preservation. No valuation update or execution simulation."""
from pathlib import Path
import hashlib,json,datetime
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parents[1];E='monitoring/studies/evidence/2026-10-11-netflix-readiness-r001/'
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
checks=[]
def check(n,c,e):checks.append({'name':n,'passed':bool(c),'evidence':e})
b=load('validation/netflix-readiness-baseline-2026-10-11-r001.json');check('559 predecessors unchanged',len(b['files'])==559 and all(sha(r['path'])==r['sha256'] for r in b['files']),559)
p=load(E+'web-inspected-evidence.json')['prospectus'];face=D(p['new_principal']);gross=face*D(p['offering_price_percent'])/100;discount=face*D(p['underwriting_percent'])/100;before=gross-discount;net=before-D(p['other_offering_expenses_estimated']);gap=D(p['old_principal'])-net
check('Public-price principal distinction',gross==D(p['gross_public_proceeds']) and gross!=face,{'principal':str(face),'public_gross':str(gross)})
check('Underwriting deducted once',discount==D(p['underwriting_discount']) and before==D(p['issuer_proceeds_before_other_expenses']),{'discount':str(discount),'before_other_expenses':str(before)})
check('Estimated expenses and rounded net estimate',net==D('986.050') and net.quantize(D('1'))==D(p['issuer_net_proceeds_rounded_estimate']),{'estimate':str(net),'source_rounded':p['issuer_net_proceeds_rounded_estimate'],'not_final_paid_amount':True})
check('Principal repayment cash friction',gap==D('13.950'),str(gap))
illustrative=D('9099.232')+net-D(p['old_principal']);investment_case=illustrative+D('28.678')
check('As-adjusted rounded table reconciliation',illustrative==D('9085.282') and illustrative.quantize(D('1'))==D(p['cash_as_adjusted_rounded']),{'hypothetical_cash':str(illustrative),'not_current_cash':True})
check('Investment inclusion remains explicitly hypothetical',investment_case==D('9113.960') and D('9127.910')-investment_case==gap,{'unchanged_other_flows_condition':True,'illustrative_cash_plus_investments':str(investment_case),'no_new_reserve_input':True})
check('Debt replacement distinct from overlap',D(p['debt_actual_principal_rounded'])+face-D(p['old_principal'])==D(p['debt_as_adjusted_principal_rounded']),{'illustrative_completed_replacement':p['debt_as_adjusted_principal_rounded'],'repayment_not_observed':True,'overlap_not_current_balance':str(D(p['debt_actual_principal_rounded'])+face)})
check('Gross June claims arithmetic not weighted EPS denominator',D('4163.939676')+D('123.891603')+D('2.012512')==D('4289.843791') and D('4289.843791')!=D('4261.300'),'June dated counts only; no October claims or exercise-proceeds forecast')
m=load(E+'freshness-inspection.json');check('Fresh metadata raw hash matches actual bytes',sha(m['raw_path'])==m['sha256'],m['sha256'])
register=load(E+'source-register.json')['records'];check('Failed captures remain failed',all(r['raw_path'] is None and r['sha256'] is None and r['access_error']=='HTTPError' for r in register if r['id']!='event'),'HTTP403 not replaced with reconstructed rawsource')
event=next(r for r in register if r['id']=='event');raw=(ROOT/event['raw_path']).read_text(encoding='utf-8');check('Primary future schedule actually present in captured notice',sha(event['raw_path'])==event['sha256'] and 'October 20th, 2026' in raw and '1:01 p.m. Pacific Time' in raw and '1:45 p.m. Pacific Time' in raw,'Rawbytes differ from predecessor; relevant future schedule agrees, no event result generated')
config=load('monitoring/config.json');check('Observation boundary retained',config['mode']=='observation-only' and config['quote_acquisition']=='manual-only','All config/model/previous protocol bytes included in preserved559 check')
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'passed':all(c['passed'] for c in checks),'scope':'Author estimate arithmetic/definitions/sourcecapture truthfulness/preservation only. Official websource reading and independent challenge separate. No model replay, currentvaluation, investmentperformance, eventoutcomes or fills.'}
(ROOT/'validation/netflix-readiness-verification-2026-10-11-r001.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'passed':result['passed'],'checks':len(checks),'failed':[c['name'] for c in checks if not c['passed']]}));raise SystemExit(0 if result['passed'] else 1)
