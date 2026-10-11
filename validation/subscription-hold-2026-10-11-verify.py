"""Verify the model hold with a queued job; never invokes a model or reads credentials."""
from pathlib import Path
import datetime,json,sqlite3,sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from observation import read_config,run_one_job
config=read_config(ROOT)
assert config['research_enabled'] is False
assert config['mode']=='observation-only'
db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
db.execute('CREATE TABLE monitor_jobs (id TEXT, status TEXT, next_attempt TEXT, created_at TEXT, attempts INTEGER, updated_at TEXT)')
db.execute("INSERT INTO monitor_jobs VALUES ('hold-fixture','queued',NULL,'2026-10-01',0,NULL)")
before=dict(db.execute('SELECT * FROM monitor_jobs').fetchone())
assert run_one_job(SimpleNamespace(conn=db),config) is None
after=dict(db.execute('SELECT * FROM monitor_jobs').fetchone())
assert before==after
assert config['check_times']==['09:00','18:00'] and len(config['watchlist'])==6
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'queued_job_unchanged':True,'no_model_call_or_claim':True,'configured_source_checks_retained':True,'observation_only_retained':True,'fixture':'In-memory queue with a due queued job and actual current config; actual run_one_job returned before claiming or invoking research','scope':'Held launch path, not uptime, phone delivery or account-wide billing enforcement'}
(ROOT/'validation/subscription-hold-verification-2026-10-11-r001.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'hold_fixture_passed':True,'source_cadence_retained':True}))
