"""Targeted preservation, source-location and arithmetic replay checks.
Run from repository root, without changing research or operational state.
"""
from pathlib import Path
import json,hashlib,subprocess,sys,re,html
from fractions import Fraction as F
from pypdf import PdfReader
root=Path.cwd();results=[]
def check(name,passed,details=None):
    results.append({'name':name,'pass':bool(passed),'details':details})
    if not passed:raise AssertionError(name)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((root/'validation/netflix-feasibility-baseline-2026-10-10-r001.json').read_text())
rows=baseline['predecessors'];check('all predecessor bytes preserved',all(digest(root/x['path'])==x['sha256'] for x in rows),{'files':len(rows)})
frozen=json.loads((root/'validation/netflix-feasibility-review-input-r001.json').read_text())
check('all frozen review inputs preserved',all(digest(root/x['path'])==x['sha256'] for x in frozen['files']),{'files':len(frozen['files'])})
current=json.loads((root/'methodology/current.json').read_text())
check('approved method 1.0.0 unchanged',current['version']=='1.0.0' and digest(root/current['file'])==current['sha256'])
output=root/'validation/netflix-feasibility-calculations-r001.json';old=output.read_bytes()
subprocess.run([sys.executable,'validation/netflix-feasibility-calculations-r001.py'],check=True,capture_output=True)
check('calculation replay byte-identical',old==output.read_bytes())
j=json.loads(old)
common=F('4163.939676');gross=common+F('123.891603')+F('2.012512')
check('independent Fraction claims check',gross==F(j['claims_june_30']['gross_potential_claims']) and abs(float((gross/common-1)*100)-float(j['claims_june_30']['gross_dilution_percent']))<1e-12)
check('independent conditional response identity',F('1.1')*F('.9')==F('.99') and F('1.2')*F('.8')==F('.96'))
check('numeric valuation and actionable conclusions withheld',all(j[k] is None for k in ['valuation','normalized_owner_cash','entry_ceiling']) and j['actionable'] is False)
reg=json.loads((root/'monitoring/studies/evidence/2026-10-10-netflix-feasibility-r001/source-retrieval-register.json').read_text())
raw=[x for x in reg if x.get('path')]
check('new source bytes and retrieval outcomes verified',all(digest(root/x['path'])==x['sha256'] and x['status']=='archived-raw' for x in raw),{'raw_files':len(raw),'sec_direct_raw_failure_retained':reg[0]['status']})
q1=next(x for x in reg if x['id']=='q1-letter-issuer-pdf')
text=' '.join(PdfReader(root/q1['path']).pages[4].extract_text().split())
check('Q1 archived primary actual passage',all(t in text for t in ['previous projection of $11B','after-tax','approximately $12.5B','~1.1x']),{'location':'Q1 issuer PDF p5, visually reviewed separately'})
cash=json.loads((root/'validation/netflix-foundation-cash-note-r001.json').read_text())
q4=next(x for x in cash['sources'] if x['id']=='q4-2025-letter')
q4text=' '.join(' '.join(p.extract_text() for p in PdfReader(root/q4['path']).pages).split())
check('January pre-fee guide and Brazil timing primary passages',all(t in q4text for t in ['$11B','$700','Brazil']),{'location':'Q4 2025 issuer cash-flow section'})
home=next(x for x in reg if x['id']=='valuation-input-home')
h=(root/home['path']).read_text(encoding='utf-8',errors='replace')
h=' '.join(html.unescape(re.sub('<[^>]+>',' ',h)).split())
h=re.sub(r'(?<=\d)\.\s+(?=\d)','.',h)
check('author rate reference dated October not cached September',all(t in h for t in ['October 1, 2026','4.20%','5.29%','5.07%']))
sub=json.loads((root/next(x['path'] for x in reg if x['id']=='sec-submissions')).read_text())['filings']['recent']
i=sub['form'].index('10-Q');check('latest listed financial quarter not presumed October',sub['filingDate'][i]=='2026-07-17' and sub['primaryDocument'][i]=='nflx-20260630.htm')
out={'schema':'targeted-verification-v1','scope':'Preservation, exact source passages and reproducible bounded arithmetic only; no investment/forecast or operational acceptance','results':results,'passed':len(results),'failed':0,'full_engineering_suite_rerun':False}
(root/'validation/netflix-feasibility-verification-r001.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':len(results),'predecessor_files':len(rows),'frozen_inputs':len(frozen['files'])}))
