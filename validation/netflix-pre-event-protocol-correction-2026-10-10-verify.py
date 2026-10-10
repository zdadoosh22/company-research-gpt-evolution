"""Targeted author checks for preserved-input protocol corrections, no event observations."""
from pathlib import Path
import json,hashlib,re,datetime
from html import unescape
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'monitoring/studies/evidence/2026-10-10-netflix-protocol-r001'
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
checks=[]
def check(n,c,e):checks.append({'name':n,'passed':bool(c),'evidence':e})
r1=load('validation/netflix-protocol-review-input-2026-10-10-r001.json')
check('Original frozen seven inputs preserved',all(sha(r['path'])==r['sha256'] for r in r1['new_inputs']),r1['new_inputs'])
r2=load('validation/netflix-protocol-correction-review-input-2026-10-10-r003.json')
check('Three correction input hashes match',all(sha(r['path'])==r['sha256'] for r in r2['files']),r2['files'])
base=load('validation/netflix-protocol-baseline-2026-10-10-r001.json')
check('All534 predecessors still preserved',len(base['predecessors'])==534 and all(sha(r['path'])==r['sha256'] for r in base['predecessors']),534)
reg=load('monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/source-retrieval-register.json');src={r['id']:r for r in reg['records']}
cor=load('monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/frozen-reference-clarifications-r002.json')
times=load('monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/price-panel-times-r003.json')
for p in cor['corrected_price_panels']:
 raw=(ROOT/src[p['id']]['local_raw_path']).read_text(encoding='utf-8');txt=re.sub(r'\s+',' ',unescape(re.sub('<[^>]+>',' ',raw)))
 ref=load('monitoring/studies/evidence/2026-10-10-netflix-protocol-r001/frozen-reference-r001.json')
 sample=next(x for x in ref['price_feasibility_samples'] if x['id']==p['id'])
 check(p['id']+' regular history/quote sample consistent',p['regular_close']==sample['sample_row'][4] and p['regular_close'] in txt and 'S&P Global Market Intelligence' in txt and 'Last updated: Oct 9, 2026' in txt,{'regular':p['regular_close'],'history':sample['sample_row'][4],'provenance':'S&P historical footer; no UTP latency assumption'})
 if p['after_hours'] is not None:
  t=times[p['id'].split('-')[0]+'_after_hours'];d=datetime.datetime.fromisoformat(t['utc']).astimezone(ZoneInfo('America/New_York'))
  check(p['id']+' separate afterhours price/time actually present',('After-hours: '+t['displayed_timestamp']) in txt and p['after_hours']==t['price_usd'] and d.strftime('%H:%M') in ['19:59','19:51'],t)
cut=cor['primary_hypothesis_cutoff'];d=datetime.datetime.fromisoformat(cut['utc'])
check('Fixed D2 cutoff zones agree',d.astimezone(ZoneInfo('America/New_York')).isoformat()==cut['eastern'] and d.astimezone(ZoneInfo('Europe/London')).isoformat()==cut['london'],cut)
check('All protocol revisions pre-event',datetime.datetime.fromisoformat(r2['frozen_at_utc'])<datetime.datetime(2026,10,20,20,1,tzinfo=datetime.timezone.utc),r2['frozen_at_utc'])
check('Funding correction leaves existing economic model untouched',all(sha(r['path'])==r['sha256'] for r in base['predecessors'] if 'netflix' in r['path']) and cor['no_financial_values_or_price_rows_changed'],'Historical baseline and closed model/reviews retained; no economic numeric revision')
result={'schema':'netflix-protocol-author-correction-checks-v1','verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'passed':all(c['passed'] for c in checks),'scope':'Actual raw-source panel/provenance checks, time arithmetic and preservation. Independent correction review and analytical adjudication remain separate.'}
(ROOT/'validation/netflix-pre-event-protocol-correction-verification-2026-10-10-r002.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':result['passed'],'checks':len(checks),'failed':[c['name'] for c in checks if not c['passed']]}));raise SystemExit(0 if result['passed'] else 1)
