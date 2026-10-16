"""Synthetic bridge controls. No inference or investment acceptance."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from research_records import envelope, save_record, translate_scoped, project_case, project_cases, validate_record
from decision_readiness import SCOPED_COVERAGE
from research_packet import prepare_packet
from scoped_research_adapter import SCHEMA, validate_output


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.when = self.now.isoformat()
        self.base = self.file('methodology/base.md', 'Approved synthetic methodology')
        self.file('methodology/current.json', {'file': self.base['path'], 'sha256': self.base['sha256']})
        self.scoped = self.file('monitoring/DECISION-SCOPE.md', 'Synthetic scoped contract')
        self.origin = self.file('validation/origin.md', 'Synthetic test origin; not accepted research')
        self.request_content = dict(entity='Example plc', security=dict(legal_entity='Example plc',
            identifier='EXAMPLE:ORD', exchange='Example Exchange', share_class='Ordinary',
            trading_currency='GBP', price_unit='GBp', reporting_currency='GBP'), question='Is the event economics defensible?',
            holding_window='several days to three months', mode='focused-opportunity',
            evidence_cutoff='2026-10-01T12:00:00Z', required_coverage=sorted(SCOPED_COVERAGE),
            stopping_conditions=['Park if material expectations cannot be aligned'])
        self.request = self.save('request', self.request_content, 'request')
        source = self.file('validation/filing.txt', 'Reported revenue GBP million 10. Material uncertainty remains.')
        source.update(source_id='filing', published_at='2026-10-01T10:00:00Z', accessed_at='2026-10-01T11:00:00Z', read_locations=['Revenue and limitations'])
        context = dict(entity='Example plc', security='EXAMPLE:ORD', period='Q3', basis='reported', unit='million', currency='GBP')
        self.job = dict(schema_version=2, job_id='analysis', role='analysis', as_of=self.request_content['evidence_cutoff'],
            scope=dict(required_categories=sorted(SCOPED_COVERAGE)), methodology=dict(base=self.base, scoped=self.scoped),
            sources=[source], target=self.origin, packet=dict(schema_version=1, context=context, max_utf8_bytes=65536, passages=[dict(
                source_id='filing', location='Revenue and limitations', text_file={k:source[k] for k in ('path','sha256')},
                range=dict(start_byte=0, end_byte=len((self.root/source['path']).read_bytes()), sha256=source['sha256']),
                metadata=context, extraction=dict(method='utf8-byte-range', version='1', status='complete', original_sha256=source['sha256']),
                table_context=dict(kind='prose', headers=[], footnotes=[]))]))
        ref = dict(source_id='filing', location='Revenue and limitations')
        self.output = dict(status='scoped-analysis-complete', summary='Synthetic foundation only', sources=[ref],
            coverage=[dict(category=k, status='covered', evidence=[ref]) for k in sorted(SCOPED_COVERAGE)], findings=[], gaps=[],
            conclusions=[dict(id='c1',claim='No supported price advantage is established.', status='supported', evidence=[ref],blocking_issues=[],numerical_inputs=[])],
            continuation='No trade acceptance; independent challenge required.')
        self.analysis = self.translate(self.job, self.output, 'analysis-record')
        review_job = copy.deepcopy(self.job); review_job.update(job_id='review',role='review',target=self.analysis_result)
        self.review_output = copy.deepcopy(self.output); self.review_output['status']='review-complete'
        self.review = self.translate(review_job,self.review_output,'review-record',self.analysis)
        self.dossier_content = dict(request=self.request, research=self.analysis, expectations='Unknown same-basis consensus.',
            price_response='No demonstrated delay-resistant repricing advantage.', holding_window=self.request_content['holding_window'],
            costs=dict(schedule=None,currency='GBP',round_trip=None,limitations=['Cost schedule unverified']),
            adverse_cases={k:'Explicitly unresolved; no executable case asserted.' for k in ('no-repricing','adverse-surprise','delayed-catalyst','overnight-gap','too-late')},
            entry_conditions='Withheld pending evidence.',exits='No instruction proposed.',reassessment_triggers='New dated evidence.',cash_comparison='Cash retained; advantage unestablished.')
        self.dossier=self.save('opportunity-dossier',self.dossier_content,'dossier',unknowns=['Costs and price-response unknown'])
        self.disposition_content=dict(research=self.analysis, review=self.review, dossier=self.dossier,status='parked',
            rationale='Material expectations and entry economics unavailable.',reopening_conditions=['New same-basis source and quote/cost evidence'],expires_at=None)

    def file(self, path, value):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(value) if isinstance(value,dict) else value,encoding='utf-8')
        return dict(path=path,sha256=hashlib.sha256(target.read_bytes()).hexdigest())

    def record(self,kind,content,rid,unknowns=None):
        return envelope('example-case',kind,content,record_id=rid,created_at=self.when,origin='fixture',
            provenance_refs=[self.origin],unknowns=unknowns or [])

    def save(self,kind,content,rid,unknowns=None):
        return save_record(self.root,self.record(kind,content,rid,unknowns))

    def translate(self,job,output,rid,target=None,version=1,supersedes=None):
        j=self.file('validation/'+rid+'-job.json',job); result=self.file('validation/'+rid+'-output.json',output)
        meta=self.file('validation/'+rid+'-execution.json',dict(job_id=job['job_id'],role=job['role'],
            model_requested='gpt-6-astra' if job['role']=='review' else 'gpt-6.1-sol',reasoning_effort='high',speed='standard',
            selected_route_completed=True,execution_outcome='completed',output_sha256=result['sha256'],
            target_sha256=job['target']['sha256'],actual_model=None,dispatch_id=rid,authentication='chatgpt-subscription',
            started_at=self.when,completed_at=self.when,engineering_test=True,runtime_verified_live=False))
        if job['role']=='analysis': self.analysis_result=result
        return translate_scoped(self.root,request=self.request,job=j,result=result,execution=meta,case_id='example-case',
            record_id=rid,created_at=self.when,unknowns=['Synthetic worker; no live verification'],target_record=target,version=version,supersedes=supersedes)

    def test_full_parked_fixture_is_not_trade_acceptance(self):
        ref=self.save('disposition',self.disposition_content,'disposition')
        p=project_case(self.root,ref)
        self.assertEqual(p['research_disposition'],'parked'); self.assertEqual(p['review_status'],'fixture-only')
        self.assertEqual(len(p['gates']),10); self.assertFalse(p['live_recommendations_enabled'])
        self.assertTrue(all(g['status']!='satisfied' for g in p['gates']))
        self.assertFalse(list(self.root.rglob('*registry*')))

    def test_translated_artifact_cannot_self_promote_to_accepted(self):
        record=json.loads((self.root/self.analysis['path']).read_text(encoding='utf-8'))
        self.assertEqual(record['content']['artifact']['kind'],'scoped-company-review')
        self.assertIsNone(record['content']['artifact']['scenarios'])
        record['content']['artifact']['status']='accepted-scoped'
        with self.assertRaisesRegex(ValueError,'Translated readiness artifact differs'):
            validate_record(self.root,record)

    def test_tampered_dependency_regresses_projection(self):
        ref=self.save('disposition',self.disposition_content,'disposition')
        (self.root/self.analysis_result['path']).write_text('{}',encoding='utf-8')
        p=project_case(self.root,ref)
        self.assertEqual(p['review_status'],'invalidated'); self.assertEqual(p['research_disposition'],'active')

    def test_request_identity_and_coverage_cannot_be_relaxed(self):
        for key in ('entity','required_coverage'):
            value=copy.deepcopy(self.request_content); value[key]='Other entity' if key=='entity' else ['business_drivers']
            with self.assertRaises(ValueError): self.save('request',value,'different-request')

    def test_backdated_disposition_cannot_use_later_analysis(self):
        record=self.record('disposition',self.disposition_content,'backdated')
        earlier=(self.now-timedelta(minutes=5)).isoformat()
        record.update(created_at=earlier,observed_at=earlier)
        with self.assertRaisesRegex(ValueError,'chronology'):
            save_record(self.root,record)

    def test_review_wrong_target_and_same_dispatch_refused(self):
        bad=copy.deepcopy(self.job);bad.update(job_id='bad-review',role='review',target=self.origin)
        with self.assertRaises(ValueError):self.translate(bad,self.review_output,'bad-review',self.analysis)

    def test_unknown_cost_is_null_and_decimal_not_float(self):
        value=copy.deepcopy(self.dossier_content); value['costs']['round_trip']='0'
        with self.assertRaises(ValueError): self.save('opportunity-dossier',value,'bad-costs')
        value['costs']['schedule']=self.origin;value['costs']['round_trip']=0.1
        with self.assertRaises(ValueError): self.save('opportunity-dossier',value,'bad-costs')
        value['costs']['round_trip']='0.10';self.save('opportunity-dossier',value,'decimal-costs')

    def test_unsupported_promotion_and_immutable_versions(self):
        value=copy.deepcopy(self.disposition_content);value['status']='supported';value['expires_at']=(self.now+timedelta(hours=1)).isoformat()
        with self.assertRaises(ValueError):self.save('disposition',value,'unsupported')
        ref=self.save('disposition',self.disposition_content,'disposition')
        self.assertEqual(ref,self.save('disposition',self.disposition_content,'disposition'))
        value=copy.deepcopy(self.disposition_content);value['rationale']='Different'
        with self.assertRaises(ValueError):self.save('disposition',value,'disposition')

    def test_review_can_finish_with_material_negative_findings(self):
        output=copy.deepcopy(self.review_output)
        output['findings']=[dict(id='material-gap',severity='material',claim='Expectation definition unsupported',evidence=[],
            proposed_correction='Withhold affected comparison.',outcome='withheld',affected_conclusions=['c1'])]
        output['conclusions'][0].update(status='withheld',blocking_issues=['material-gap'])
        job=copy.deepcopy(self.job);job.update(job_id='negative-review',role='review',target=self.analysis_result)
        ref=self.translate(job,output,'negative-review',self.analysis)
        self.assertTrue(ref['sha256'])
        job['role']='analysis';output['status']='scoped-analysis-complete'
        with self.assertRaises(ValueError):validate_output(output,job,self.root)

    def test_packet_reproduced_and_schema_tamper_rejected(self):
        job=self.file('validation/job.json',self.job);p=prepare_packet(self.root,self.job,SCHEMA)
        packet_path=self.root/'validation/packet.json';packet_path.write_bytes(p['bytes'])
        ref=dict(path='validation/packet.json',sha256=p['sha256'])
        content=dict(request=self.request,job=job,packet=ref,packet_utf8_bytes=p['utf8_bytes'],original_bytes=p['original_bytes'])
        self.save('evidence-packet',content,'packet')
        content['packet_utf8_bytes']+=1
        with self.assertRaises(ValueError):self.save('evidence-packet',content,'bad-packet')

    def test_projection_never_falls_back_from_broken_newer_disposition(self):
        first=self.save('disposition',self.disposition_content,'disposition')
        successor=self.record('disposition',self.disposition_content,'disposition')
        successor.update(version=2,supersedes=[first])
        second=save_record(self.root,successor)
        self.assertEqual(project_cases(self.root)[0]['research_disposition'],'parked')
        (self.root/second['path']).write_text('{}',encoding='utf-8')
        self.assertEqual(project_cases(self.root)[0]['review_status'],'invalidated')

    def test_ambiguous_disposition_lineages_require_reconciliation(self):
        self.save('disposition',self.disposition_content,'first-disposition')
        self.save('disposition',self.disposition_content,'second-disposition')
        self.assertEqual(project_cases(self.root)[0]['review_status'],'invalidated')

    def test_targeted_correction_requires_material_review(self):
        review_job=copy.deepcopy(self.job);review_job.update(job_id='material-review',role='review',target=self.analysis_result)
        output=copy.deepcopy(self.review_output)
        output['findings']=[dict(id='f1',severity='material',claim='Unsupported comparison.',evidence=[],
            proposed_correction='Withhold it.',outcome='withheld',affected_conclusions=['c1'])]
        output['conclusions'][0].update(status='withheld',blocking_issues=['f1'])
        review=self.translate(review_job,output,'material-review',self.analysis)
        review_record=json.loads((self.root/review['path']).read_text(encoding='utf-8'))
        correction=copy.deepcopy(self.job);correction.update(job_id='correction',target=review_record['content']['result'])
        corrected=self.translate(correction,self.output,'analysis-correction',review)
        self.assertTrue(corrected['sha256'])
        original_review=json.loads((self.root/self.review['path']).read_text(encoding='utf-8'))
        correction['target']=original_review['content']['result']
        with self.assertRaisesRegex(ValueError,'requires material'):
            self.translate(correction,self.output,'unnecessary-correction',self.review)


if __name__=='__main__': unittest.main()
