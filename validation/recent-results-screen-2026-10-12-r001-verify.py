"""Source-bound arithmetic diagnostics; no normalized forecast or price response acceptance."""
from pathlib import Path
from decimal import Decimal as D
import json,hashlib,re,sys,datetime
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'))
from extract import extract
folder=r/'monitoring/studies/evidence/2026-10-12-recent-results-r001'
rows=json.loads((folder/'source-register.json').read_text(encoding='utf-8'))['records']
projections=[]
for x in rows:
 if x['raw_path']:
  p=r/x['raw_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
  t=re.sub(r'\s+',' ',extract(p))
  anchors=['Adjusted diluted EPS','Adjusted Free Cash Flow'] if x['id']=='levi-q3' else ['Adjusted diluted EPS']
  excerpts=[]
  for a in anchors:
   pos=t.find(a);assert pos>=0,(x['id'],a);excerpts.append({'anchor':a,'brief_excerpt':' '.join(t[pos:].split()[:9])})
  projections.append({'source_id':x['id'],'raw_sha256':x['sha256'],'representation':'Derived whitespace-normalized extracts; not original HTML','excerpts':excerpts})
 else: assert x['error']=='HTTPError' and x['sha256'] is None
assert D('.48')-D('.11')==D('.37')
assert D('15.5')-D('3.3')==D('12.2')
assert D('12.2')-D('11.8')==D('.4')
assert (D('1.46')+D('1.52'))/2==D('1.49')
assert (D('1.54')+D('1.56'))/2==D('1.55')
assert D('102.9')-D('58.6')==D('44.3')
assert D('585.2')-D('157.9')==D('427.3')
assert D('3')-D('4')==D('-1')  # PEP rough attributed-growth diagnostic only; not normalized growth.
(folder/'selected-source-projections.json').write_text(json.dumps(projections,indent=2)+'\n',encoding='utf-8')
out={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issuer_capture_hashes_match':2,'failed_original_capture_preserved':'pepsi-q3 HTTP403','levi_diagnostic_eps_without_attributed_benefit':'.37','levi_diagnostic_ebit_margin_percent':12.2,'levi_guidance_midpoint_change':'.06','levi_q3_reported_fcf_m':'44.3','levi_ytd_reported_fcf_m':'427.3','checks_scope':'Author source/diagnostic consistency, not independent review','limits':['Diagnostics do not create normalized forecasts','FCF includes discontinued operations','No dated analyst consensus, response price, executable quote, return or trade acceptance']}
(r/'validation/recent-results-screen-verification-2026-10-12-r001.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
