"""Source-bound financing arithmetic and predecessor integrity, not valuation acceptance."""
from pathlib import Path
from decimal import Decimal as D
import hashlib,json,subprocess,datetime
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline_commit='fd4e5c9d500055b116632d8c891eb45abf9b8ad7'
entries=[]
for row in subprocess.check_output(['git','ls-tree','-rz',baseline_commit],cwd=ROOT).split(b'\0'):
 if row:
  info,path=row.split(b'\t',1);entries.append((path.decode(),info.split()[2]))
assert len(entries)==604
blobstream=subprocess.run(['git','cat-file','--batch'],input=b''.join(h+b'\n' for _,h in entries),stdout=subprocess.PIPE,check=True,cwd=ROOT).stdout
offset=0
for p,h in entries:
 end=blobstream.index(b'\n',offset);header=blobstream[offset:end].split();assert header[0]==h and header[1]==b'blob'
 size=int(header[2]);start=end+1;original=blobstream[start:start+size];offset=start+size+1
 assert sha(ROOT/p)==hashlib.sha256(original).hexdigest(),p
paths=[p for p,_ in entries]
folder=ROOT/'monitoring/studies/evidence/2026-10-12-uber-funding-r001'
facts=json.loads((folder/'web-inspection.json').read_text(encoding='utf-8'))
u=next(x for x in facts['sources'] if x['id']=='underwriting')
p=[D(str(x)) for x in u['principal_m']]
prices=[D(str(x)) for x in u['underwriter_purchase_percent']]
rates=[D(str(x)) for x in u['rate_percent']]
purchase=sum(a*b/100 for a,b in zip(p,prices))
coupon=sum(a*b/100 for a,b in zip(p,rates))
assert sum(p)==D('4500') and purchase==D('4464.4325') and coupon==D('200')
assert sum(p)-purchase==D('35.5675')
assert u['payment_frequency']=='annual' and u['first_nominal_payment']=='2027-09-15'
capture=json.loads((folder/'capture-register.json').read_text(encoding='utf-8'))
for r in capture['records']:
 if r['raw_path']:assert sha(ROOT/r['raw_path'])==r['sha256']
 else:assert r['sha256'] is None and r['error']=='HTTPError'
meta=next(r for r in capture['records'] if r['id']=='submissions')
sub=json.loads((ROOT/meta['raw_path']).read_text(encoding='utf-8'))['filings']['recent']
material=[{k:sub[k][i] for k in ['accessionNumber','form','filingDate','reportDate','primaryDocument']} for i,f in enumerate(sub['form']) if f in ('10-Q','10-K','8-K','424B2','424B5')]
assert material[0]['accessionNumber']=='0001552781-26-000486', 'Newer material filing exists: reconcile before retaining cutoff'
assert not json.loads((ROOT/'monitoring/config.json').read_text(encoding='utf-8'))['research_enabled']
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_commit':baseline_commit,'predecessors_unchanged':len(paths),'source_fact_register_sha256':sha(folder/'web-inspection.json'),'principal_eur_m':str(sum(p)),'issuer_purchase_before_other_expenses_eur_m':str(purchase),'face_less_purchase_eur_m':str(sum(p)-purchase),'annual_nominal_coupon_eur_m':str(coupon),'first_nominal_coupon':u['first_nominal_payment'],'direct_capture_failures_preserved':5,'fresh_metadata_latest_accession':material[0]['accessionNumber'],'research_job_hold_retained':True,'status':'author checks passed; independent economic review pending','limits':['No original HTML captured for five failed SEC requests','No final net proceeds, USD FX, blocked-account proof or current bridge balance','No investment or execution acceptance']}
(ROOT/'validation/uber-funding-verification-2026-10-12-r001.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
