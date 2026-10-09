"""Temporary fictional artifacts test integrity controls, never real readiness."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from alert_contract import ArtifactRef, GateEvidence
from decision_readiness import ArtifactVerifier, CurrentAcceptance, SCOPED_COVERAGE, TRIAL_CASES, PHONE_CASES


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
        self.scope = {k: ('1' if k.endswith('version') else 'a' * 64) for k in
            ('decision_version', 'dossier_version', 'decision_sha256', 'dossier_sha256',
             'instruction_fingerprint', 'portfolio_fingerprint', 'quote_fingerprint')}
        self.scope['quote_fingerprint'] = None
        self.entries = []
        self.save('methodology/method.md', 'approved fictional method')
        self.methodhash = self.digest('methodology/method.md')
        self.save('methodology/current.json', {'version': '1', 'file': 'methodology/method.md', 'sha256': self.methodhash})

    def save(self, path, value):
        dest = self.root / path; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding='utf-8')
        return self.digest(path)

    def digest(self, path): return hashlib.sha256((self.root / path).read_bytes()).hexdigest()

    def add(self, identity='dossier', gate='dossier', **extra):
        path = 'monitoring/readiness/' + identity + '.json'
        artifact = dict(artifact_id=identity, version='1', kind=identity, **extra)
        ref = ArtifactRef(identity, '1', self.save(path, artifact))
        evpath = 'validation/evidence/' + identity + '.txt'
        evidence = {'id': identity + '-findings', 'path': evpath, 'sha256': self.save(evpath, 'Substantive fictional arithmetic and contrary-evidence findings')}
        review = dict(id='review-' + identity, reviewer='fictional test reviewer', status='accepted',
            artifact=dict(artifact_id=identity, version='1', sha256=ref.sha256),
            accepted_at=self.now.isoformat(), valid_until=(self.now + timedelta(hours=2)).isoformat(),
            scope=self.scope.copy(), findings=[], evidence_refs=[evidence],
            check_records=[dict(id='check-' + identity, method='independent source and arithmetic review', outcome='accepted', evidence_ids=[evidence['id']])])
        rp = 'validation/reviews/' + identity + '.json'
        self.entries.append(dict(artifact_id=identity, version='1', sha256=ref.sha256, path=path,
                                 review_path=rp, review_sha256=self.save(rp, review), gates=[gate]))
        return ref

    def evidence(self, ref, gate='dossier'):
        return GateEvidence(gate, ref, self.now, self.now + timedelta(hours=1), **self.scope)

    def verifier(self, **kwargs):
        digest = self.save('monitoring/readiness/registry.json', dict(schema_version=1, entries=self.entries))
        return ArtifactVerifier(self.root, 'monitoring/readiness/registry.json', digest, now=self.now,
            expected_scope=self.scope, max_review_age=timedelta(days=1), **kwargs)

    def review_mutation(self, **changes):
        entry = self.entries[-1]; path = entry['review_path']
        review = json.loads((self.root / path).read_text()); review.update(changes)
        entry['review_sha256'] = self.save(path, review)

    def scoped(self):
        add = self.add('scoped-method', 'extension_methodology', base_methodology_sha256=self.methodhash,
                       required_coverage=sorted(SCOPED_COVERAGE))
        entry = self.entries[-1]; payload = json.loads((self.root / entry['path']).read_text())
        payload['kind'] = 'extension-methodology'; entry['sha256'] = self.save(entry['path'], payload)
        add = ArtifactRef('scoped-method', '1', entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id=add.artifact_id, version='1', sha256=add.sha256))
        srcpath = 'companies/test/sources/filing.txt'
        source = dict(id='filing', path=srcpath, sha256=self.save(srcpath, 'Fictional source numbers'),
                      read_at=self.now.isoformat(), publication_at=self.now.isoformat(), locations=['p1'])
        ref = self.add('scoped', 'research', methodology_sha256=self.methodhash,
            extension_methodology=dict(artifact_id=add.artifact_id, version=add.version, sha256=add.sha256),
            coverage={key: 'Fictional reviewed coverage' for key in SCOPED_COVERAGE},
            label='Scoped short-horizon company review, not full long-term thesis', status='accepted-scoped',
            window=dict(reviewed_at=self.now.isoformat(), expires_at=(self.now + timedelta(hours=1)).isoformat()),
            findings=[], evidence_refs=[source], check_records=[dict(id='scoped-check', method='window financial resilience and adverse claims review', outcome='accepted', evidence_ids=['filing'])], source_facts=[source])
        entry = self.entries[-1]; payload = json.loads((self.root / entry['path']).read_text()); payload['kind'] = 'scoped-company-review'
        entry['sha256'] = self.save(entry['path'], payload); ref = ArtifactRef('scoped', '1', entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id='scoped', version='1', sha256=ref.sha256))
        return ref

    def full(self, status='complete', mode='full'):
        base = 'companies/test/runs/r001/'
        run = dict(id='r001', as_of='2026-10-08', status=status, mode=mode, continuation='',
            methodology_sha256=self.methodhash, methodology_version='1', review_findings=[])
        self.save(base + 'run.json', run)
        self.save(base + 'sources.json', [dict(id='s1', publication_date='2026-10-07', read=True)])
        self.save(base + 'observations.json', [dict(status='verified-reported', source_id='s1', value=3, location='p2')])
        for output in ('full-report.pdf', 'thesis.pdf', 'valuation.xlsx'): self.save(base + 'outputs/' + output, 'fictional output')
        files = {str(p.relative_to(self.root / base)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root / base).rglob('*') if p.is_file()}
        pub = self.save(base + 'publication.json', dict(published=self.now.isoformat(), files=files))
        indexhash = self.save('companies/test/index.json', dict(latest='r001', runs=[dict(id='r001', status=status)]))
        ref = self.add('full', 'research', company_index='companies/test/index.json', company_index_sha256=indexhash,
            run_record=base + 'run.json', run_record_sha256=self.digest(base + 'run.json'), publication_sha256=pub, methodology_sha256=self.methodhash)
        entry = self.entries[-1]; payload = json.loads((self.root / entry['path']).read_text()); payload['kind'] = 'published-company-research'
        entry['sha256'] = self.save(entry['path'], payload); ref = ArtifactRef('full', '1', entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id='full', version='1', sha256=ref.sha256))
        return ref

    def test_accepts_reviewed_hash_bound_artifact(self):
        ref = self.add(); result = self.verifier()(self.evidence(ref))
        self.assertEqual(result.artifact, ref); self.assertEqual(result.verdict, 'accepted')

    def test_tamper_artifact_and_registry(self):
        ref = self.add(); verify = self.verifier()
        self.save(self.entries[0]['path'], 'tampered')
        with self.assertRaisesRegex(ValueError, 'hash'): verify(self.evidence(ref))
        self.save('monitoring/readiness/registry.json', '{}')
        with self.assertRaisesRegex(ValueError, 'hash'): verify(self.evidence(ref))

    def test_escape_and_secret_paths(self):
        ref = self.add()
        for path in ('../outside.json', 'state/observation/telegram.dpapi', 'C:/secret.json', '/outside.json'):
            with self.subTest(path=path):
                self.entries[0]['path'] = path
                with self.assertRaises(ValueError): self.verifier()(self.evidence(ref))

    def test_unreviewed_bare_flags_and_missing_check_records(self):
        ref = self.add()
        for changes in ({'status':'pending'}, {'check_records':[]}, {'evidence_refs':[]}, {'check_records':[dict(id='x', method='checked', outcome=True, evidence_ids=[])]}):
            with self.subTest(changes=changes):
                self.review_mutation(**changes)
                with self.assertRaises(ValueError): self.verifier()(self.evidence(ref))

    def test_scope_and_future_stale_reviews(self):
        ref = self.add()
        self.review_mutation(scope={**self.scope, 'portfolio_fingerprint':'b'*64})
        with self.assertRaisesRegex(ValueError,'scope'): self.verifier()(self.evidence(ref))
        self.review_mutation(scope=self.scope)
        for delta in (timedelta(seconds=1), -timedelta(days=2)):
            self.review_mutation(accepted_at=(self.now + delta).isoformat())
            with self.assertRaisesRegex(ValueError,'future, stale'): self.verifier()(self.evidence(ref))

    def test_current_validator_required_and_typed(self):
        self.scope['quote_fingerprint']='b'*64
        ref = self.add('quote', 'quote'); ev = self.evidence(ref, 'quote')
        with self.assertRaisesRegex(ValueError,'validator'): self.verifier()(ev)
        with self.assertRaisesRegex(ValueError,'Typed'): self.verifier(validators={'quote': lambda *args:True})(ev)
        verify = self.verifier(validators={'quote': lambda *args:CurrentAcceptance('current-test', self.now, self.scope.copy())})
        self.assertEqual(verify(ev).verdict, 'accepted')

    def test_activation_condition_and_scope(self):
        self.scope['quote_fingerprint']='b'*64
        ref = self.add('activation', 'activation'); ev = self.evidence(ref, 'activation')
        for result in (CurrentAcceptance('x', self.now, self.scope, 'not-satisfied'), CurrentAcceptance('x', self.now, {}, 'satisfied')):
            with self.assertRaises(ValueError): self.verifier(validators={'activation':lambda *args: result})(ev)

    def test_full_complete_package_and_partial_rejection(self):
        ref = self.full(); self.assertEqual(self.verifier()(self.evidence(ref, 'research')).verdict, 'accepted')
        self.entries=[]; ref=self.full(status='partial', mode='pilot')
        with self.assertRaises(ValueError): self.verifier()(self.evidence(ref, 'research'))

    def test_missing_or_tampered_publication(self):
        ref=self.full(); path=self.root/'companies/test/runs/r001/publication.json'; path.unlink()
        with self.assertRaises(ValueError): self.verifier()(self.evidence(ref,'research'))
        self.entries=[]; ref=self.full(); self.save('companies/test/runs/r001/outputs/thesis.pdf','changed')
        with self.assertRaisesRegex(ValueError,'hash'): self.verifier()(self.evidence(ref,'research'))

    def test_scoped_route_without_legacy_full_report(self):
        ref=self.scoped(); self.assertEqual(self.verifier()(self.evidence(ref,'research')).verdict,'accepted')
        self.assertFalse(list(self.root.rglob('full-report.pdf')))

    def test_scoped_missing_addendum_or_source_tamper(self):
        ref=self.scoped(); self.entries=self.entries[1:]
        with self.assertRaisesRegex(ValueError,'allowlisted'): self.verifier()(self.evidence(ref,'research'))
        self.entries=[]; ref=self.scoped(); self.save('companies/test/sources/filing.txt','changed')
        with self.assertRaisesRegex(ValueError,'hash'): self.verifier()(self.evidence(ref,'research'))

    def test_simulated_phone_and_short_trial_rejected(self):
        ref=self.add('phone','phone',execution_mode='simulation')
        with self.assertRaises(ValueError): self.verifier()(self.evidence(ref,'phone'))
        observation_hash=self.save('validation/evidence/trial-observation.txt','fictional operation record')
        ref=self.add('trial','operational_trial',execution_mode='actual', observations=[dict(id='obs',path='validation/evidence/trial-observation.txt',sha256=observation_hash)], started_at=(self.now-timedelta(days=1)).isoformat(),ended_at=self.now.isoformat())
        entry=self.entries[-1]; data=json.loads((self.root/entry['path']).read_text()); data['kind']='actual-operation-trial'
        entry['sha256']=self.save(entry['path'],data); ref=ArtifactRef('trial','1',entry['sha256']); self.review_mutation(artifact=dict(artifact_id='trial',version='1',sha256=ref.sha256))
        with self.assertRaisesRegex(ValueError,'Fourteen'): self.verifier()(self.evidence(ref,'operational_trial'))

    def test_methodology_tamper_and_material_limitation(self):
        ref=self.scoped(); self.save('methodology/method.md','silent change')
        with self.assertRaisesRegex(ValueError,'hash'): self.verifier()(self.evidence(ref,'research'))
        self.save('methodology/method.md','approved fictional method')
        self.review_mutation(findings=[dict(id='margin',assessment='Unsupported decisive margin',material=True,status='limits-conclusion')])
        with self.assertRaises(ValueError): self.verifier()(self.evidence(ref,'research'))

    def test_review_evidence_tamper_and_expiry(self):
        ref=self.add(); self.save('validation/evidence/dossier.txt','changed findings')
        with self.assertRaisesRegex(ValueError,'hash'): self.verifier()(self.evidence(ref))
        self.save('validation/evidence/dossier.txt','Substantive fictional arithmetic and contrary-evidence findings')
        self.review_mutation(valid_until=self.now.isoformat())
        with self.assertRaisesRegex(ValueError,'expired'): self.verifier()(self.evidence(ref))

    def test_scoped_missing_coverage_rejected(self):
        ref=self.scoped(); entry=self.entries[-1]; artifact=json.loads((self.root/entry['path']).read_text())
        del artifact['coverage']['financial_resilience']
        entry['sha256']=self.save(entry['path'],artifact); ref=ArtifactRef('scoped','1',entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id='scoped',version='1',sha256=ref.sha256))
        with self.assertRaisesRegex(ValueError,'scope missing'): self.verifier()(self.evidence(ref,'research'))

    def test_current_attestation_cannot_be_old(self):
        ref=self.add('monitor','monitoring'); ev=self.evidence(ref,'monitoring')
        callback=lambda *args:CurrentAcceptance('old',self.now-timedelta(seconds=1),self.scope)
        with self.assertRaisesRegex(ValueError,'scope/time'): self.verifier(validators={'monitoring':callback})(ev)

    def operational_fixture(self, gate):
        kind='actual-device-test' if gate=='phone' else 'actual-operation-trial'
        start=self.now-timedelta(days=14)
        evidence=dict(id='execution-record',path='validation/evidence/execution.txt',
            sha256=self.save('validation/evidence/execution.txt','fictional recorded device and fault observations'))
        cases=PHONE_CASES if gate=='phone' else TRIAL_CASES
        records=[dict(id=case,case=case,method='fictional executed test',observed_outcome='expected result recorded',
            control_response='control verified by fictional reviewer',execution_mode='actual' if gate=='phone' else 'fault-injection',
            executed_at=self.now.isoformat(),evidence_refs=[evidence],recipient_receipt_id='fictional-device-receipt',received_at=self.now.isoformat()) for case in sorted(cases)]
        ref=self.add('operations',gate,device='iPhone',execution_mode='actual',observations=[evidence],
            started_at=start.isoformat(),ended_at=self.now.isoformat(),executed_cases=records,
            coverage_evaluation=dict(assessment='fictional coverage assessment',reviewer='fictional reviewer',gaps=[],evidence_refs=[evidence]))
        entry=self.entries[-1]; artifact=json.loads((self.root/entry['path']).read_text()); artifact['kind']=kind
        entry['sha256']=self.save(entry['path'],artifact); ref=ArtifactRef('operations','1',entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id=ref.artifact_id,version='1',sha256=ref.sha256))
        return ref

    def test_full_operational_records_still_need_trusted_validator(self):
        ref=self.operational_fixture('operational_trial'); ev=self.evidence(ref,'operational_trial')
        with self.assertRaisesRegex(ValueError,'validator'): self.verifier()(ev)
        accepted=lambda *args:CurrentAcceptance('fictional-actual-record-check',self.now,self.scope)
        self.assertEqual(self.verifier(validators={'operational_trial':accepted})(ev).verdict,'accepted')

    def test_missing_executed_fault_case_blocks_trial(self):
        ref=self.operational_fixture('operational_trial'); entry=self.entries[-1]; artifact=json.loads((self.root/entry['path']).read_text())
        artifact['executed_cases'].pop(); entry['sha256']=self.save(entry['path'],artifact); ref=ArtifactRef('operations','1',entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id=ref.artifact_id,version='1',sha256=ref.sha256))
        with self.assertRaisesRegex(ValueError,'cases incomplete'): self.verifier()(self.evidence(ref,'operational_trial'))

    def test_phone_device_receipts_required(self):
        ref=self.operational_fixture('phone'); entry=self.entries[-1]; artifact=json.loads((self.root/entry['path']).read_text())
        artifact['executed_cases'][0]['recipient_receipt_id']=''; entry['sha256']=self.save(entry['path'],artifact); ref=ArtifactRef('operations','1',entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id=ref.artifact_id,version='1',sha256=ref.sha256))
        with self.assertRaises(ValueError): self.verifier()(self.evidence(ref,'phone'))

    def test_scoped_source_read_after_review_rejected(self):
        ref=self.scoped(); entry=self.entries[-1]; artifact=json.loads((self.root/entry['path']).read_text())
        artifact['window']['reviewed_at']=(self.now-timedelta(minutes=1)).isoformat()
        entry['sha256']=self.save(entry['path'],artifact); ref=ArtifactRef('scoped','1',entry['sha256'])
        self.review_mutation(artifact=dict(artifact_id=ref.artifact_id,version='1',sha256=ref.sha256))
        with self.assertRaisesRegex(ValueError,'dated actual'): self.verifier()(self.evidence(ref,'research'))


if __name__ == '__main__': unittest.main()
