"""Real queue/adapter/record bridge integration with a fictional transport."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import test_research_records as fixtures
from scoped_research_adapter import run_scoped_job, MODELS
from scoped_research_queue import ScopedQueue, package_sha256, scope_sha256
from research_checkpoint import make_reference
from research_records import translate_scoped, project_case
from research_engine import prepare, main, export_memory
from research_memory import ResearchMemory


class EngineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RecordTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.root;self.queue=ScopedQueue(self.root);self.calls=[]
        self.cap=patch('scoped_research_adapter.runtime_capabilities',return_value=dict(status='verified',verified_live=False,origin='synthetic engineering verifier'))
        self.cap.start();self.addCleanup(self.cap.stop)
        self.analysis=copy.deepcopy(self.f.job);self.analysis['job_id']='cycle-analysis'
        self.review=copy.deepcopy(self.analysis);self.review.update(job_id='cycle-review',role='review')
        self.correction=copy.deepcopy(self.analysis);self.correction['job_id']='cycle-correction'
        self.recheck=copy.deepcopy(self.review);self.recheck['job_id']='cycle-recheck'
        self.negative_first_review=False;self.reviews_seen=0
        self.queue.enqueue(self.analysis)
        now=datetime.now(timezone.utc)
        self.manifest=dict(schema_version=1,batch_id='cycle-batch',case_id='example-case',version=1,
            created_at=(now-timedelta(seconds=1)).isoformat(),expires_at=(now+timedelta(hours=1)).isoformat(),
            purpose='Synthetic full vertical slice',provenance_refs=['validation/origin.md'],call_limit=4,
            permitted_continuation=['explicit-retry','material-correction','material-recheck'],jobs=[
                dict(job_id=j['job_id'],stage=stage,role=j['role'],model=MODELS[j['role']],scope_sha256=scope_sha256(j),
                    package_sha256=package_sha256(j) if stage=='analysis' else None,target_from_job_id=previous)
                for j,stage,previous in ((self.analysis,'analysis',None),(self.review,'review',self.analysis['job_id']),
                    (self.correction,'correction',self.review['job_id']),(self.recheck,'recheck',self.correction['job_id']))])
        self.queue.authorize_batch(self.manifest)

    def runner(self,args,**kw):
        self.calls.append(args)
        if args[1]=='login':return subprocess.CompletedProcess(args,0,'','Logged in using ChatGPT')
        output=copy.deepcopy(self.f.output)
        if args[args.index('--model')+1]=='gpt-6-astra':
            output['status']='review-complete';self.reviews_seen+=1
            if self.negative_first_review and self.reviews_seen==1:
                output['findings']=[dict(id='material',severity='material',claim='Unsupported expectation comparison',evidence=[],
                    proposed_correction='Remove the comparison and narrow the conclusion.',outcome='withheld',affected_conclusions=['c1'])]
                output['conclusions'][0].update(status='withheld',blocking_issues=['material'])
        Path(args[args.index('--output-last-message')+1]).write_text(json.dumps(output),encoding='utf-8')
        events=[dict(type='thread.started',model=args[args.index('--model')+1]),dict(type='turn.completed',usage=dict(input_tokens=10,output_tokens=10))]
        return subprocess.CompletedProcess(args,0,'\n'.join(json.dumps(x) for x in events),'')

    def translate(self,job,record_id,target=None,expected_status='complete',version=1,supersedes=None):
        result=self.queue.run_one(job_id=job['job_id'],batch_id='cycle-batch',runner=self.runner,environ={})
        self.assertEqual(result['status'],expected_status)
        public=self.queue.export_result(job['job_id'],case_id='example-case')
        meta=json.loads((self.root/public['execution']['path']).read_text(encoding='utf-8'))
        self.assertNotIn('metadata_path',meta);self.assertNotIn('input_manifest',meta)
        self.assertTrue(meta['engineering_test']);self.assertFalse(meta['runtime_verified_live'])
        self.assertEqual(public,self.queue.export_result(job['job_id'],case_id='example-case'))
        ref=translate_scoped(self.root,request=self.f.request,**{k:public[k] for k in ('job','result','execution')},
            case_id='example-case',record_id=record_id,created_at=datetime.now(timezone.utc).isoformat(),
            unknowns=['Synthetic transport only'],target_record=target,version=version,supersedes=supersedes)
        return ref,result

    def test_explicit_two_stage_cycle_archive_and_projection(self):
        analysis,result=self.translate(self.analysis,'cycle-analysis-result')
        meta=json.loads(Path(result['metadata_path']).read_text(encoding='utf-8'))
        self.review['target']=dict(path=Path(meta['result_path']).relative_to(self.root).as_posix(),sha256=meta['output_sha256'])
        self.queue.enqueue(self.review)
        self.manifest['version']=2;self.manifest['jobs'][1]['package_sha256']=package_sha256(self.review)
        self.queue.authorize_batch(self.manifest)
        review,_=self.translate(self.review,'cycle-review-result',analysis)
        self.f.when=datetime.now(timezone.utc).isoformat()
        d=copy.deepcopy(self.f.dossier_content);d['research']=analysis
        dossier=self.f.save('opportunity-dossier',d,'cycle-dossier',unknowns=['Cost and execution unavailable'])
        disposition=copy.deepcopy(self.f.disposition_content);disposition.update(research=analysis,review=review,dossier=dossier)
        ref=self.f.save('disposition',disposition,'cycle-disposition')
        p=project_case(self.root,ref)
        self.assertEqual(p['research_disposition'],'parked');self.assertEqual(p['review_status'],'fixture-only')
        self.assertEqual(len(self.calls),4)  # two auth checks, two fictional inference calls
        state=self.queue.status()
        self.assertEqual(state['cases'][0]['remaining_attempts'],2)
        self.assertTrue(all(g['status']!='satisfied' for g in p['gates']))
        exported=export_memory(self.root,ref['path'])
        self.assertEqual(exported,export_memory(self.root,ref['path']))
        with ResearchMemory(self.root) as memory:
            memory.import_bundle(exported['records.json']['path'],exported['sources.json']['path'])
            retrieved=memory.query(['No supported price advantage'],entities=['Example plc'],security_id='EXAMPLE:ORD',
                question_scope='request',evidence_cutoff=datetime.now(timezone.utc).isoformat())
            self.assertEqual(retrieved['record_count'],4)
            self.assertTrue(all(r['readiness_effect']=='none' for r in retrieved['packet']['records']))

    def test_archive_refuses_incomplete_or_tampered_state(self):
        with self.assertRaises(ValueError):self.queue.export_result(self.analysis['job_id'],case_id='example-case')
        _,result=self.translate(self.analysis,'cycle-result')
        with self.assertRaisesRegex(ValueError,'Export case differs'):
            self.queue.export_result(self.analysis['job_id'],case_id='another-case')
        Path(result['metadata_path']).write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):self.queue.export_result(self.analysis['job_id'],case_id='example-case')

    def test_four_stage_material_correction_and_recheck_use_exact_shared_budget(self):
        self.negative_first_review=True
        analysis,analysis_run=self.translate(self.analysis,'cycle-analysis-result')
        def bind(job,index,predecessor_run):
            meta=json.loads(Path(predecessor_run['metadata_path']).read_text(encoding='utf-8'))
            job['target']=dict(path=Path(meta['result_path']).relative_to(self.root).as_posix(),sha256=meta['output_sha256'])
            self.queue.enqueue(job);self.manifest['version']+=1
            self.manifest['jobs'][index]['package_sha256']=package_sha256(job)
            self.queue.authorize_batch(self.manifest)
        bind(self.review,1,analysis_run)
        review,review_run=self.translate(self.review,'cycle-review-result',analysis,expected_status='needs-input')
        bind(self.correction,2,review_run)
        corrected,correction_run=self.translate(self.correction,'cycle-analysis-result',review,version=2,supersedes=[analysis])
        bind(self.recheck,3,correction_run)
        rechecked,_=self.translate(self.recheck,'cycle-review-result',corrected,version=2,supersedes=[review])
        self.assertTrue(rechecked['sha256'])
        state=self.queue.status()
        self.assertEqual(state['cases'][0]['consumed_attempts'],4)
        self.assertEqual(state['cases'][0]['remaining_attempts'],0)
        repeated=self.queue.run_one(job_id=self.recheck['job_id'],batch_id='cycle-batch',runner=self.runner,environ={})
        self.assertEqual(repeated['job_attempts_started'],0)
        self.assertEqual(len(self.calls),8)

    def test_prepare_command_freezes_reproducible_packet(self):
        job=self.f.file('validation/case-job.json',self.analysis)
        ref=prepare(self.root,request_path=self.f.request['path'],job_path=job['path'],record_id='prepared-packet',created_at=datetime.now(timezone.utc).isoformat())
        self.assertTrue((self.root/ref['path']).is_file())
        with self.assertRaises(SystemExit):main(['--root',str(self.root),'prepare'])


if __name__=='__main__':unittest.main()
