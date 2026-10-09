import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from observation_core import Store
from observation_monitor import check_sources,due_slot,init_monitor,recover_jobs,normalized_page,approved_url,PrimaryRedirects
from observation_transport import init_transport,ingest_updates,dispatch_outbox
from observation import bridge_notices,telegram_handler,backup,run_one_job,run_job_safely,notification_preflight,tick,get_state,full_status

class Client:
    allowed_chat_id='123'
    def __init__(self,updates=None): self.updates=updates or []; self.messages=[]
    def get_updates(self,offset): return [u for u in self.updates if u['update_id']>=offset]
    def send_message(self,text,reply_markup=None): self.messages.append(text); return len(self.messages)
    def edit_message(self,ident,text,reply_markup=None): self.messages.append('EDIT '+text)

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.store=Store(self.root/'db.sqlite3'); init_monitor(self.store.conn); init_transport(self.store.conn); self.store.conn.commit()
        self.config={'timezone':'Europe/London','check_times':['09:00','18:00'],'watchlist':[{'company':'test','ticker':'T','cik':'0000000001','expected_name':'TEST'}],'pages':[],'sec_user_agent':'test'}
    def tearDown(self): self.store.conn.close(); self.tmp.cleanup()
    def body(self,accessions):
        return json.dumps({'cik':1,'name':'TEST CORP','filings':{'recent':{'accessionNumber':accessions,'filingDate':['2026-01-01']*len(accessions),'form':['10-Q']*len(accessions),'primaryDocument':['test.htm']*len(accessions)}}}).encode()
    def test_status_preserves_unresolved_report_and_operational_gap(self):
        self.store.confirm_funding()
        self.store.capture_reported_fill('unknown','report','1','10')
        with patch('observation.STATE',self.root): result=full_status(self.store)
        self.assertTrue(result['reconciliation_required'])
        self.assertIsNone(result['net_asset_value_gbp'])
        self.assertIsNone(result['gain_loss_gbp'])
        self.store.conn.execute("INSERT INTO monitor_state(key,value) VALUES('reconciliation_required','missed reports')")
        self.store.conn.commit()
        with patch('observation.STATE',self.root): result=full_status(self.store)
        self.assertEqual(result['operational_reconciliation_note'],'missed reports')
    def test_baseline_then_change_and_no_duplicate(self):
        one='0000000001-26-000001'; two='0000000001-26-000002'
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([one]))
        self.assertFalse(result['changed']); self.assertEqual(self.store.conn.execute('SELECT count(*) FROM monitor_jobs').fetchone()[0],0)
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([two,one]))
        self.assertEqual(len(result['changed']),1)
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([two,one]))
        self.assertFalse(result['changed']); self.assertEqual(self.store.conn.execute('SELECT count(*) FROM monitor_jobs').fetchone()[0],1)

    def test_status_distinguishes_partial_coverage_from_total_failure(self):
        self.config['pages']=[{'id':'blocked-page','company':'test','url':'https://www.unilever.com/investors/'}]
        def fetch(url,agent):
            if 'unilever' in url: raise OSError('offline')
            return self.body([])
        check_sources(self.store.conn,self.config,self.root,fetch)
        with patch('observation.STATE',self.root): status=full_status(self.store)
        self.assertIsNone(status['last_successful_source_check'])
        sources={r['source']:r for r in status['source_check_history']['per_source']}
        self.assertIsNotNone(sources['sec-0000000001']['last_success'])
        self.assertIsNone(sources['blocked-page']['last_success'])
        self.assertIsNotNone(sources['blocked-page']['last_failure'])
        self.assertIn('every configured source',status['last_successful_source_check_scope'])
    def test_mismatch_and_fetch_failure_are_not_no_change(self):
        wrong=json.loads(self.body([])); wrong['cik']=2
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:json.dumps(wrong).encode())
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM monitor_failures').fetchone()[0],1)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM source_documents').fetchone()[0],0)

    def test_corrupt_existing_archive_is_exposed_and_never_overwritten(self):
        original=self.body(['0000000001-26-000001'])
        check_sources(self.store.conn,self.config,self.root,lambda *_:original)
        archived=Path(self.store.conn.execute('SELECT archive_path FROM source_documents').fetchone()[0])
        archived.write_bytes(b'corrupted saved bytes')
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:original)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(archived.read_bytes(),b'corrupted saved bytes')
        self.assertFalse(result['checked'])
        self.assertFalse(result['changed'])
    def test_london_daylight_saving_slots(self):
        self.assertEqual(due_slot(self.config,datetime(2026,7,1,8,5,tzinfo=timezone.utc)),'2026-07-01T09:00')
        self.assertEqual(due_slot(self.config,datetime(2026,12,1,8,5,tzinfo=timezone.utc)),'2026-11-30T18:00')
    def test_page_access_challenge(self):
        with self.assertRaises(ValueError): normalized_page(b'<main>verify you are human '+b'x'*150+b'</main>')
    def test_telegram_mutation_and_dedup_atomic(self):
        alert=self.store.create_trial_alert({'id':'a','reason':'test'})
        client=Client([{'update_id':1,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'text':'/ack a'}},
                       {'update_id':2,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'text':'/status'}}])
        self.assertEqual(ingest_updates(self.store.conn,client,telegram_handler),2)
        self.assertEqual(ingest_updates(self.store.conn,client,telegram_handler),0)
        self.assertEqual(self.store.refresh_alert('a')['status'],'acknowledged')
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM transport_outbox').fetchone()[0],2)
    def test_withdrawal_edits_original_and_separate_notice(self):
        self.store.create_trial_alert({'id':'a','reason':'test'}); bridge_notices(self.store.conn)
        client=Client(); dispatch_outbox(self.store.conn,client,now=100)
        self.store.withdraw('a','new evidence'); bridge_notices(self.store.conn)
        operations=[r[0] for r in self.store.conn.execute('SELECT operation FROM transport_outbox')]
        self.assertEqual(operations.count('edit'),1); self.assertEqual(operations.count('send'),2)
        bridge_notices(self.store.conn)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM transport_outbox').fetchone()[0],3)
    def test_telegram_fill_and_cancel_never_places_orders(self):
        self.store.confirm_funding(); self.store.create_trial_alert({'id':'a'})
        updates=[{'update_id':i,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'text':text}} for i,text in enumerate([
          '/order a buy TEST 2 100 o1','/fill o1 e1 1 40 1','/cancel o1'],1)]
        ingest_updates(self.store.conn,Client(updates),telegram_handler)
        status=self.store.status(); self.assertEqual(status['cash_gbp'],'259'); self.assertEqual(status['reserved_gbp'],'0')
        self.assertEqual(status['holdings'],{'TEST':'1'}); self.assertFalse(status['actionable'])
    def test_backup_and_interrupted_recovery(self):
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','test','running','x','x','{}')"); self.store.conn.commit()
        recover_jobs(self.store.conn)
        self.assertEqual(self.store.conn.execute('SELECT status FROM monitor_jobs').fetchone()[0],'interrupted')
        path=backup(self.store.conn,self.root)
        with closing(sqlite3.connect(path)) as conn: self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_latest_ledger_backup_tracks_manual_changes_preserving_daily_snapshot(self):
        path=backup(self.store.conn,self.root)
        self.store.confirm_funding(); backup(self.store.conn,self.root)
        with closing(sqlite3.connect(path)) as saved:
            self.assertEqual(saved.execute("SELECT value FROM meta WHERE key='cash_gbp'").fetchone()[0],'0')
        with closing(sqlite3.connect(path.parent/'latest-ledger.sqlite3')) as saved:
            self.assertEqual(saved.execute("SELECT value FROM meta WHERE key='cash_gbp'").fetchone()[0],'300')
            self.assertEqual(saved.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_backup_rejects_uncommitted_records_without_hanging(self):
        self.store.conn.execute("INSERT INTO events(created_at,kind,payload) VALUES('x','pending','{}')")
        with self.assertRaises(RuntimeError): backup(self.store.conn,self.root)
        self.assertTrue(self.store.conn.in_transaction)
        self.store.conn.rollback()

    def test_backup_does_not_trust_metadata_after_interrupted_replace(self):
        from observation_monitor import set_state
        path=backup(self.store.conn,self.root)
        self.store.confirm_funding()
        # Simulate metadata claiming a newer copy than the file actually holds.
        event=self.store.conn.execute('SELECT max(id) FROM events').fetchone()[0]
        set_state(self.store.conn,'backup_ledger_event',event); self.store.conn.commit()
        backup(self.store.conn,self.root)
        with closing(sqlite3.connect(path.parent/'latest-ledger.sqlite3')) as saved:
            self.assertEqual(saved.execute("SELECT value FROM meta WHERE key='cash_gbp'").fetchone()[0],'300')

    def test_corrupt_latest_backup_is_rebuilt_without_rewriting_daily_snapshot(self):
        path=backup(self.store.conn,self.root); latest=path.parent/'latest-ledger.sqlite3'
        original=path.read_bytes(); latest.write_bytes(b'corrupt fixture')
        backup(self.store.conn,self.root)
        self.assertEqual(path.read_bytes(),original)
        with closing(sqlite3.connect(latest)) as saved:
            self.assertEqual(saved.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_source_failure_rolls_back_seen_and_retries(self):
        one='0000000001-26-000001'; two='0000000001-26-000002'
        check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([one]))
        with patch('observation_monitor.queue_job',side_effect=ValueError('injected')):
            result=check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([two,one]))
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM source_documents').fetchone()[0],1)
        result=check_sources(self.store.conn,self.config,self.root,lambda *_:self.body([two,one]))
        self.assertEqual(len(result['changed']),1)
    def test_withdrawn_pending_original_is_not_sent(self):
        self.store.create_trial_alert({'id':'a'}); bridge_notices(self.store.conn)
        self.store.withdraw('a','invalid'); bridge_notices(self.store.conn)
        rows=self.store.conn.execute('SELECT state,payload FROM transport_outbox').fetchall()
        self.assertEqual(rows[0]['state'],'superseded')
        client=Client(); dispatch_outbox(self.store.conn,client,now=100)
        self.assertIn('withdrawn',client.messages[0])
    def test_concurrent_service_lock_refused(self):
        from observation import engine_lock
        with engine_lock(self.root):
            with self.assertRaises(ValueError):
                with engine_lock(self.root): pass
    def test_successful_draft_is_not_requeued_or_approved(self):
        payload={'company':'applovin-corporation','job_id':'j','question':'test','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','applovin-corporation','queued','x','x',?)",(json.dumps(payload),)); self.store.conn.commit()
        draft=self.root/'draft.json'; draft.write_text(json.dumps({'status':'draft','summary':'No company conclusion','observations':[],'uncertainties':['Evidence unavailable'],'continuation':'Inspect evidence'}))
        with patch('observation.STATE',self.root),patch('observation_research.run_research',return_value={'status':'needs-review','continuation_required':False,'analytical_approval':False,'result_path':str(draft)}):
            run_one_job(self.store,{'research_enabled':True})
        self.assertEqual(self.store.conn.execute('SELECT status FROM monitor_jobs').fetchone()[0],'awaiting-review')
        self.assertFalse(self.store.status()['actionable'])
    def test_missing_company_context_defers_with_saved_reason(self):
        payload={'company':'does-not-exist','job_id':'j','question':'test','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','does-not-exist','queued','x','x',?)",(json.dumps(payload),)); self.store.conn.commit()
        result=run_one_job(self.store,{'research_enabled':True})
        row=self.store.conn.execute('SELECT status,next_attempt FROM monitor_jobs').fetchone()
        self.assertEqual(row['status'],'queued'); self.assertIsNotNone(row['next_attempt'])
        self.assertTrue(result['continuation_required'])

    def test_explicit_discovery_context_does_not_require_fictitious_company_run(self):
        study=self.root/'monitoring/studies/discovery.json'
        study.parent.mkdir(parents=True); study.write_text('{"actionable":false}')
        payload={'company':'new-issuer','job_id':'j','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','new-issuer','queued','x','x',?)",(json.dumps(payload),));self.store.conn.commit()
        config={'research_enabled':True,'watchlist':[{'company':'new-issuer','research_context_paths':['monitoring/studies/discovery.json']}]}
        with patch('observation.ROOT',self.root),patch('observation_research.run_research',return_value={'status':'partial','continuation_required':True}) as model:
            run_one_job(self.store,config)
        job=model.call_args.args[1]
        self.assertIn('monitoring/studies/discovery.json',job['context_paths'])
        self.assertIn('no approved company run',job['research_context_kind'])
        self.assertFalse((self.root/'companies/new-issuer').exists())

    def test_discovery_context_escape_blocks_model_call(self):
        payload={'company':'new-issuer','job_id':'j','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','new-issuer','queued','x','x',?)",(json.dumps(payload),));self.store.conn.commit()
        config={'research_enabled':True,'watchlist':[{'company':'new-issuer','research_context_paths':['../../auth.json']}]}
        with patch('observation.ROOT',self.root),patch('observation_research.run_research') as model:
            result=run_one_job(self.store,config)
        model.assert_not_called()
        self.assertTrue(result['continuation_required'])

    def test_research_success_requires_contained_existing_artifact(self):
        for path in (None,str(self.root/'missing.json'),str(self.root.parent/'outside.json')):
            ident='j'+str(len(list(self.store.conn.execute('SELECT id FROM monitor_jobs'))))
            payload={'company':'applovin-corporation','job_id':ident,'changes':[]}
            self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES(?,?,'queued','x','x',?)",(ident,'applovin-corporation',json.dumps(payload))); self.store.conn.commit()
            with patch('observation.STATE',self.root),patch('observation_research.run_research',return_value={'status':'needs-review','continuation_required':False,'result_path':path}):
                result=run_one_job(self.store,{'research_enabled':True})
            self.assertTrue(result['continuation_required'])
            self.assertEqual(self.store.conn.execute('SELECT status FROM monitor_jobs WHERE id=?',(ident,)).fetchone()[0],'queued')

    def test_page_reversion_is_a_new_transition_and_links_matter(self):
        self.config['watchlist']=[]; self.config['pages']=[{'id':'page','company':'test','url':'https://www.unilever.com/results'}]
        a=b'<main>'+b'A'*150+b'<a href="one.pdf">Results</a></main>'
        b=b'<main>'+b'A'*150+b'<a href="two.pdf">Results</a></main>'
        changes=[]
        for body in (a,b,a,a):
            changes.append(len(check_sources(self.store.conn,self.config,self.root,lambda *_:body)['changed']))
        self.assertEqual(changes,[0,1,1,0])
        self.assertEqual(self.store.conn.execute('SELECT count(*) FROM source_documents').fetchone()[0],3)

    def test_failure_does_not_lock_manual_records_during_next_fetch(self):
        self.config['watchlist'].append({'company':'test2','ticker':'T2','cik':'0000000002','expected_name':'TEST'})
        calls=[]
        def fetcher(*args):
            calls.append(True)
            if len(calls)==1: raise OSError('offline')
            with closing(sqlite3.connect(self.root/'db.sqlite3',timeout=0.1)) as peer:
                with peer: peer.execute("INSERT INTO events(created_at,kind,payload) VALUES('x','manual-peer','{}')")
            body=json.loads(self.body([])); body['cik']=2
            return json.dumps(body).encode()
        result=check_sources(self.store.conn,self.config,self.root,fetcher)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(self.store.conn.execute("SELECT count(*) FROM events WHERE kind='manual-peer'").fetchone()[0],1)

    def test_worker_finalisation_failure_is_immediately_interrupted(self):
        payload={'company':'does-not-exist','job_id':'j','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','does-not-exist','queued','x','x',?)",(json.dumps(payload),)); self.store.conn.commit()
        with patch('observation.enqueue_send',side_effect=OSError('injected')):
            result=run_job_safely(self.store,{'research_enabled':True})
        self.assertEqual(result['status'],'interrupted')
        self.assertEqual(self.store.conn.execute('SELECT status FROM monitor_jobs').fetchone()[0],'interrupted')

    def test_preflight_drops_notice_withdrawn_after_staging(self):
        self.store.create_trial_alert({'id':'a'}); bridge_notices(self.store.conn)
        self.store.withdraw('a','invalidation between passes')
        client=Client()
        dispatch_outbox(self.store.conn,client,now=100,preflight=notification_preflight)
        self.assertFalse(client.messages)
        self.assertEqual(self.store.conn.execute('SELECT state FROM transport_outbox').fetchone()[0],'superseded')

    def test_preflight_drops_expired_but_not_yet_swept_notice(self):
        self.store.create_trial_alert({'id':'a','created_at':'2020-01-01T00:00:00+00:00','expires_at':'2020-01-02T00:00:00+00:00'})
        bridge_notices(self.store.conn); client=Client()
        dispatch_outbox(self.store.conn,client,now=100,preflight=notification_preflight)
        self.assertFalse(client.messages)

    def test_corrupt_saved_draft_cannot_strand_running_job(self):
        draft=self.root/'bad.json'; draft.write_text('{')
        payload={'company':'applovin-corporation','job_id':'j','question':'test','changes':[]}
        self.store.conn.execute("INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES('j','applovin-corporation','queued','x','x',?)",(json.dumps(payload),)); self.store.conn.commit()
        with patch('observation.STATE',self.root), patch('observation_research.run_research',return_value={'status':'needs-review','continuation_required':False,'result_path':str(draft)}):
            result=run_one_job(self.store,{'research_enabled':True})
        self.assertTrue(result['continuation_required'])
        self.assertEqual(self.store.conn.execute('SELECT status FROM monitor_jobs').fetchone()[0],'queued')

    def test_primary_redirects_reject_before_contact(self):
        from urllib.request import Request
        request=Request('https://data.sec.gov/submissions/x.json')
        for destination in ('https://example.com/','http://data.sec.gov/x','https://user@data.sec.gov/x','https://data.sec.gov:444/x'):
            self.assertFalse(approved_url(destination))
            with self.assertRaises(ValueError): PrimaryRedirects().redirect_request(request,None,302,'redirect',{},destination)
        self.assertTrue(approved_url('https://www.sec.gov/Archives/test.htm'))

    def test_offline_extended_downtime_requires_reconciliation(self):
        from observation_monitor import set_state
        set_state(self.store.conn,'last_service_tick','2020-01-01T00:00:00+00:00'); self.store.conn.commit()
        with patch('observation.STATE',self.root),patch('observation.backup',return_value=self.root/'backup'),patch('observation.render_status',return_value={}):
            tick(self.store,self.config,network=False,models=False)
        self.assertIn('extended downtime',get_state(self.store.conn,'reconciliation_required'))

    def test_source_recovery_notice_and_no_repeat_failure_notice(self):
        bad={'failures':[{'source':'test','reason':'offline'}]}
        good={'failures':[]}
        with patch('observation.STATE',self.root),patch('observation.backup',return_value=self.root/'backup'),patch('observation.render_status',return_value={}),patch('observation.check_sources',side_effect=[bad,bad,good]):
            for _ in range(3): tick(self.store,self.config,force=True,models=False)
        texts=[json.loads(r[0])['text'] for r in self.store.conn.execute('SELECT payload FROM transport_outbox')]
        self.assertEqual(sum('MONITORING GAP' in x for x in texts),1)
        self.assertEqual(sum('MONITORING RECOVERY' in x for x in texts),1)

    def test_source_history_records_failures_baselines_changes_and_unchanged(self):
        one='0000000001-26-000001'; two='0000000001-26-000002'
        def unavailable(*args): raise OSError('injected')
        check_sources(self.store.conn,self.config,self.root,unavailable)
        for accessions in ([one],[one,two],[one,two]):
            check_sources(self.store.conn,self.config,self.root,lambda *_:self.body(accessions))
        # Clock resolution may tie; random UUIDs are not a chronology.
        rows=self.store.conn.execute('SELECT outcome,documents_seen,changes_detected,duration_ms FROM monitor_checks ORDER BY rowid').fetchall()
        self.assertEqual([r['outcome'] for r in rows],['failed','baseline','changed','unchanged'])
        self.assertEqual([r['changes_detected'] for r in rows],[0,0,1,0])
        self.assertTrue(all(r['duration_ms']>=0 for r in rows))

if __name__=='__main__': unittest.main()
