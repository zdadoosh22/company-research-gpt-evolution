"""Targeted changed-model checks, no operational or whole-suite work."""
from pathlib import Path
from decimal import Decimal as D
import hashlib,json,subprocess,sys
root=Path.cwd();results=[]
def check(n,c,detail=None):
 results.append({'name':n,'pass':bool(c),'detail':detail})
 if not c:raise AssertionError(n)
for manifest in ['validation/netflix-feasibility-review-input-r001.json','validation/netflix-framework-review-input-r002.json']:
 rows=json.loads((root/manifest).read_text())['files']
 check('frozen inputs '+manifest,all(hashlib.sha256((root/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in rows),len(rows))
baseline=json.loads((root/'validation/netflix-feasibility-baseline-2026-10-10-r001.json').read_text())['predecessors']
check('466 original predecessors preserved',len(baseline)==466 and all(hashlib.sha256((root/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in baseline))
p=root/'validation/netflix-framework-calculations-r002.json';saved=p.read_bytes()
subprocess.run([sys.executable,'validation/netflix-framework-calculations-r002.py'],capture_output=True,check=True)
check('changed-model deterministic replay',p.read_bytes()==saved)
x=json.loads(saved);check('78 model checks',x['check_count']==78)
check('historical cash population bridge fully decomposed',sum(D(v) for v in x['historical_cash_check']['components'].values())==D(x['historical_cash_check']['reconciling_remainder']))
check('no current value or action produced',x['current_value'] is None and x['actionable'] is False and x['portfolio_decision'] is None and x['execution_instruction'] is None)
check('12 combined business/coverage paths',len(x['outputs'])==12)
check('explicit 10-year paths',all([r['year'] for r in a['rows']]==list(range(2027,2037)) for a in x['outputs']))
check('scheduled principal pays all except2054notes',all(sum(D(r['principal_repayment']) for r in a['rows'])==D('13572') and D(a['terminal']['remaining_debt'])==D('800') for a in x['outputs']))
check('all paths funded under named proforma condition',all(D(a['minimum_proforma_liquidity'])>=0 for a in x['outputs']))
check('mature growth has content reinvestment',all(D(a['terminal']['content_growth_cash_reinvestment'])>0 if D(a['terminal']['growth'])>0 else D(a['terminal']['content_growth_cash_reinvestment'])==0 for a in x['outputs']))
check('future values do not import historical2026 cash',all(a['rows'][0]['year']==2027 and D(a['opening_surplus_cash_added'])==0 and a['current_intrinsic_value'] is None and a['total_equity_value'] is None for a in x['outputs']))
rate=D(x['seed']['equity_rate']);pv4=D('1000')/(1+rate)+D('2000')/(1+rate)**2+D('1000')/(1+rate)**D('2.5')
for case in ['downside','central','upside']:
 a=next(a for a in x['outputs'] if a['case']==case and a['coverage']=='covered');b=next(a for a in x['outputs'] if a['case']==case and a['coverage']=='full_uncovered_range_endpoint')
 check('independent scheduled uncovered PV '+case,abs(D(a['cash_franchise_component'])-D(b['cash_franchise_component'])-pv4)<D('1e-22'))
 check('content asset roll '+case,all(abs(D(r['content_assets_end'])-(D(x['seed']['dated_June_content_assets']) if n==0 else D(a['rows'][n-1]['content_assets_end']))-D(r['cash_content_planned'])+D(r['content_amortization']))<D('1e-22') for n,r in enumerate(a['rows'])))
check('rate sensitivity lowers component at higher equity return',all(D(next(z['per_known_gross_claim_component'] for z in x['rate_sensitivity'] if z['case']==case and z['coverage']==cover and z['rate']=='0.0949'))>D(next(z['per_known_gross_claim_component'] for z in x['rate_sensitivity'] if z['case']==case and z['coverage']==cover and z['rate']=='0.1170')) for case in ['downside','central','upside'] for cover in ['covered','full_uncovered_range_endpoint']))
report={'schema':'targeted-framework-verification-v1','scope':'Preservation, arithmetic, future-date/funding and conditional stress checks; no investment/operational acceptance','passed':len(results),'failed':0,'results':results,'full_engineering_suite_rerun':False}
(root/'validation/netflix-framework-verification-r002.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'passed':len(results),'scope':report['scope']}))
