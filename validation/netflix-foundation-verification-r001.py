"""Independent source-period/scale checks and preservation; no operational writes.
Outputs one JSON record to stdout. Run from the project root after author freeze.
"""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal as D
import json, hashlib, subprocess, sys, re
from datetime import datetime, timezone

class Facts(HTMLParser):
    def __init__(self):
        super().__init__(); self.current=None; self.facts=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'ix:nonfraction': self.current=[dict(attrs), '']
    def handle_data(self, text):
        if self.current is not None: self.current[1] += text
    def handle_endtag(self, tag):
        if tag == 'ix:nonfraction' and self.current is not None:
            self.facts.append(self.current); self.current=None

root=Path.cwd()
checks=[]
def check(name, passed, evidence):
    checks.append({'name':name,'passed':bool(passed),'evidence':evidence})

baseline=json.loads(Path('validation/netflix-foundation-r001-baseline.json').read_text(encoding='utf-8-sig'))
for group, members in [('predecessor',baseline['predecessor_files']),('review_input',json.loads(Path('validation/netflix-foundation-review-input-r001.json').read_text())['files'])]:
    failures=[m['path'] for m in members if not (root/m['path']).is_file() or hashlib.sha256((root/m['path']).read_bytes()).hexdigest()!=m['sha256']]
    check(group+'_preservation',not failures,{'count':len(members),'changed_or_missing':failures})

raw=next(Path('monitoring/studies/evidence/2026-10-09-netflix-foundation-r001').glob('nflx-cash-*q2-2026-sec-*.html')).read_text(encoding='utf-8')
p=Facts();p.feed(raw)
context=re.search(r'<xbrli:context\b[^>]*id="c-1".*?</xbrli:context>',raw,re.S).group(0)
check('source_context_h1_2026', '2026-01-01' in context and '2026-06-30' in context,context)
expected={'us-gaap:NetIncomeLoss':'8684.205','us-gaap:NetCashProvidedByUsedInOperatingActivities':'7034.017','us-gaap:PaymentsToAcquirePropertyPlantAndEquipment':'414.774','nflx:AdditionstoStreamingContentAssets':'9774.440','nflx:CostofServicesAmortizationofStreamingContentAssets':'8529.209'}
for name,value in expected.items():
    found=[]
    for attrs,text in p.facts:
        if attrs.get('name')==name and attrs.get('contextref')=='c-1':
            amount=D(text.replace(',',''))*(D(10)**int(attrs.get('scale','0')))/D(1000000)
            if attrs.get('sign')=='-': amount=-amount
            found.append(str(amount))
    check('source_value_'+name, bool(found) and all(D(v)==D(value) for v in found),{'expected_usdm':value,'raw_ix_values_converted_to_usdm':found})

calc=json.loads(subprocess.check_output([sys.executable,'validation/netflix-foundation-calculations-r001.py'],text=True))
saved=json.loads(Path('validation/netflix-foundation-calculations-r001.json').read_text(encoding='utf-8-sig'))
check('saved_calculation_replay',calc==saved,'Executed actual frozen calculation program; JSON matches saved output')
cashnote=json.loads(Path('validation/netflix-foundation-cash-note-r001.json').read_text())
check('separate_cash_source_checks',len(cashnote['checks'])==19 and all(c.get('pass') is True for c in cashnote['checks']),{'count':len(cashnote['checks']),'scope':'Independent cash researcher Decimal/source-hash checks; no engineering-suite rerun'})
check('no_entry_or_valuation',calc['actionable'] is False and calc['valuation'] is None and calc['entry_ceiling'] is None,'No accepted opportunity or valuation produced')
prior_h2=D('16422.166')-D('7655.186')
conditional_h2=D(calc['content']['conditional_h2_amortization'])
check('h2_guidance_growth_consistency',0 < conditional_h2/prior_h2-1 < D('0.10'),{'prior_h2_amort_usdm':str(prior_h2),'conditional_growth_percent':str(100*(conditional_h2/prior_h2-1)),'interpretation':'Rounded management guidance; verifies slower H2 growth relative to its own prior-year period, not sustainable forecast'})
result={'schema':'targeted-verification-v1','verified_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':all(c['passed'] for c in checks),'engineering_suite_rerun':False,'analytical_approval':False,'limitations':['Extracts inspected financially; not all PDF pages rendered.','No operational outage, phone delivery, broker execution or portfolio performance test.','Source/scale/replay integrity and arithmetic cannot establish forecasts or investment quality.']}
print(json.dumps(result,indent=2))
if not result['passed']:sys.exit(1)
