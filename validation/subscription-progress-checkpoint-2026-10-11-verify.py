"""Bounded source/arithmetic/integrity checks; not investment acceptance."""
from pathlib import Path
import datetime, hashlib, json
root = Path(__file__).resolve().parents[1]
def digest(p): return hashlib.sha256((root/p).read_bytes()).hexdigest()
base=json.loads((root/'validation/subscription-progress-baseline-2026-10-11-r001.json').read_text(encoding='utf-8'))
changed=[x['path'] for x in base['files'] if digest(x['path'])!=x['sha256']]
assert changed==['monitoring/config.json'], changed
manifest=json.loads((root/'validation/amd-funding-claims-review-input-2026-10-11-r001.json').read_text(encoding='utf-8'))
assert all(digest(x['path'])==x['sha256'] for x in manifest['files'])
review=json.loads((root/'validation/amd-funding-claims-astra-review-2026-10-11-r001.json').read_text(encoding='utf-8'))
assert digest('validation/amd-funding-claims-astra-review-2026-10-11-r001.md')==review['narrative_sha256']
assert not json.loads((root/'monitoring/config.json').read_text(encoding='utf-8'))['research_enabled']
from decimal import Decimal as D
principal=[D('750'),D('1000'),D('1000'),D('1000'),D('750')]
coupon=[D('.03750'),D('.04125'),D('.04375'),D('.04750'),D('.05250')]
assert sum(principal)==D('4500')
assert sum(p*r for p,r in zip(principal,coupon))==D('200')
assert D('7700')-D('324')==D('7376')
fresh=json.loads((root/'monitoring/studies/evidence/2026-10-11-uber-cash-definitions-r001/filing-freshness.json').read_text(encoding='utf-8'))
assert digest(fresh['raw_path'])==fresh['sha256']
assert fresh['filings'][0]['accessionNumber']=='0001552781-26-000486'
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unchanged_predecessors':len(base['files'])-1,'only_changed_predecessor':changed,'amd_frozen_inputs':len(manifest['files']),'review_narrative_hash_matches':True,'research_model_jobs_held':True,'uber_eur_principal_m':4500,'uber_annual_eur_coupon_m':200,'uber_august_closing_headroom_usd_m':7376,'uber_metadata_hash_matches':True,'limits':['Author checks only; not independent Uber review','Historical closing headroom is not current cash or guaranteed availability','No current equity valuation, executable quote, trading authority or investment performance validated']}
out=root/'validation/subscription-progress-checkpoint-verification-2026-10-11-r001.json'
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
