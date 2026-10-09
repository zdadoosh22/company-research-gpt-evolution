"""Repeatable engineering checks. Never certifies investment quality or activates alerts."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'state'/'observation'


def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite): yield from flatten(test)
        else: yield test


def verify():
    suite=unittest.TestLoader().discover(str(ROOT/'validation'/'tests'))
    counts={}
    for test in flatten(suite):
        module=type(test).__module__; counts[module]=counts.get(module,0)+1
    log=io.StringIO(); result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
    baseline=json.loads((STATE/'baseline-integrity.json').read_text(encoding='utf-8'))
    mismatches=[]
    for name,expected in baseline.items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT.resolve()): raise ValueError('Invalid integrity baseline path')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected: mismatches.append(name)
    backups=[]
    for path in sorted((STATE/'backups').glob('*.sqlite3')):
        # Restore into a different temporary directory, leaving original backup
        # untouched. No credential file enters this verification.
        with tempfile.TemporaryDirectory() as directory:
            restored=Path(directory)/'restored.sqlite3'; shutil.copyfile(path,restored)
            with closing(sqlite3.connect(restored)) as conn:
                integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
                cash=conn.execute("SELECT value FROM meta WHERE key='cash_gbp'").fetchone()[0]
                events=conn.execute('SELECT count(*) FROM events').fetchone()[0]
            backups.append({'name':path.name,'restored_integrity':integrity,'recorded_cash_gbp':cash,'events':events})
    with closing(sqlite3.connect((STATE/'operations.sqlite3').as_uri()+'?mode=ro',uri=True)) as conn:
        database_integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        funded=conn.execute("SELECT value FROM meta WHERE key='funded'").fetchone()[0]=='1'
        cash=conn.execute("SELECT value FROM meta WHERE key='cash_gbp'").fetchone()[0]
    success=(result.wasSuccessful() and not mismatches and database_integrity=='ok'
             and bool(backups) and all(x['restored_integrity']=='ok' for x in backups))
    return {'verified_at':datetime.now(timezone.utc).isoformat(),'engineering_passed':success,
      'tests_run':result.testsRun,'tests_by_module':counts,'failures':len(result.failures),'errors':len(result.errors),
      'test_log':log.getvalue(),'protected_files_checked':len(baseline),'protected_file_mismatches':mismatches,
      'live_database_integrity':database_integrity,'backup_restore_checks':backups,
      'funding_declared':funded,'recorded_cash_gbp':cash,'broker_cash_independently_verified':False,
      'telegram_credentials_present':(STATE/'telegram.dpapi').exists(),'real_phone_delivery_verified':False,
      'synthetic_ledger_operations':2400,'synthetic_exit_paths':4,
      'analytical_approval':False,'real_recommendations_enabled':False,'broker_orders_placed':0,
      'scope':'Engineering, synthetic fixtures and integrity only; no investment performance or 14-day trial certification'}


if __name__=='__main__':
    report=verify(); path=ROOT/'validation'/'refinement-report.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('engineering_passed','tests_run','protected_files_checked','live_database_integrity','analytical_approval')}))
    raise SystemExit(0 if report['engineering_passed'] else 1)
