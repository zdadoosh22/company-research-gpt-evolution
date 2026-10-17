"""Real queue-path fixtures for deterministic retained-output revalidation.

These run the adapter with an in-process fixture transport. They make no
claim about a real model, subscription, or company review.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent.parent / "tools"))
sys.path.insert(0, str(TESTS))
import scoped_research_queue as queue_module
from scoped_research_queue import ScopedQueue, package_sha256, scope_sha256, verify_dispatch
import scoped_research_adapter as adapter_module
from scoped_research_adapter import MODELS
import test_scoped_research_adapter as adapter_tests


class RetainedRevalidationTests(unittest.TestCase):
    def setUp(self):
        fixture = adapter_tests.ScopedAdapterTests()
        fixture.setUp()
        self.fixture = fixture
        self.addCleanup(fixture.tearDown)
        self.root = fixture.root
        self.install_fixture_catalog(self.root)
        self.queue = ScopedQueue(self.root, fixture_only=True)
        self.base_output = copy.deepcopy(fixture.output)
        self.bad_output = copy.deepcopy(fixture.output)
        self.bad_output["status"] = "withheld"
        self.bad_output["conclusions"][0].update(status="withheld", blocking_issues=["f1: retained label"])
        self.bad_output["findings"] = [{"id": "f1", "severity": "material", "claim": "Fixture limitation",
            "evidence": [], "proposed_correction": "Review the stated limitation", "outcome": "withheld",
            "affected_conclusions": ["c1"]}]
        self.queue.enqueue(fixture.job)
        self.analysis_spec = self.spec(fixture.job, "analysis", None, True)
        self.review_job = None

    def tearDown(self):
        patch.stopall()

    def spec(self, job, stage, predecessor, bound):
        return {"job_id": job["job_id"], "stage": stage, "role": job["role"], "model": MODELS[job["role"]],
            "scope_sha256": scope_sha256(job), "package_sha256": package_sha256(job) if bound else None,
            "target_from_job_id": predecessor}

    def install_fixture_catalog(self, root):
        pinned_path = adapter_module.PINNED_CATALOG_PATH
        source = TESTS.parent / "engine-slice-2026-10-17-r001" / "MODEL-CAPABILITIES.json"
        destination = root / pinned_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        fixture_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        path_patch = patch.object(adapter_module, "PINNED_CATALOG_SHA256", fixture_hash)
        self.addCleanup(path_patch.stop)
        path_patch.start()

    def manifest(self, *, version=1, jobs=None, expires=None):
        now = datetime.now(timezone.utc)
        return {"schema_version": 1, "batch_id": "b1", "case_id": "case1", "version": version,
            "created_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (expires or now + timedelta(hours=1)).isoformat(),
            "purpose": "Temporary deterministic revalidation fixture", "provenance_refs": ["engineering-fixture"],
            "call_limit": 4, "permitted_continuation": ["explicit-retry", "material-correction", "material-recheck"],
            "jobs": jobs or [self.analysis_spec]}

    def run_failed_attempt(self):
        def runner(args, **kwargs):
            if args[1] == "login":
                return subprocess.CompletedProcess(args, 0, "", "Logged in using ChatGPT")
            output_path = Path(args[args.index("--output-last-message") + 1])
            output_path.write_text(json.dumps(self.bad_output), encoding="utf-8")
            stdout = json.dumps({"type": "thread.started"}) + "\n" + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10}})
            return subprocess.CompletedProcess(args, 0, stdout, "")
        def adapter(root, job, **kwargs):
            return self.fixture.run_job(job=job, runner=runner, environ={}, **kwargs)
        # The adapter fixture normally substitutes dispatch verification. Restore
        # the real persisted-intent claim while still using its fake transport.
        with patch.object(queue_module, "verify_dispatch", verify_dispatch):
            first = self.queue.run_one(job_id="j1", batch_id="b1", adapter=adapter, executable="fixture-cli")
        self.assertEqual(first["reason"], "invalid-output-input-or-unauthorized-event")
        self.assertEqual(first["status"], "needs-retry-decision")
        return first

    def prepare(self, *, with_review=False):
        if with_review:
            self.review_job = copy.deepcopy(self.fixture.job)
            self.review_job["job_id"] = "j2"
            self.review_job["role"] = "review"
            self.analysis_spec = self.spec(self.fixture.job, "analysis", None, True)
            review_spec = self.spec(self.review_job, "review", "j1", False)
            jobs = [self.analysis_spec, review_spec]
        else:
            jobs = [self.analysis_spec]
        self.initial_manifest = self.manifest(jobs=jobs)
        self.queue.authorize_batch(self.initial_manifest)
        return self.run_failed_attempt()

    def revalidate(self):
        with patch.object(queue_module, "verify_dispatch", verify_dispatch):
            return self.queue.revalidate_failed_output(job_id="j1", batch_id="b1")

    def test_real_success_path_is_idempotent_and_preserves_original_bytes(self):
        self.prepare()
        status_before = self.queue.status()
        meta_path = Path(status_before["jobs"][0]["metadata_path"])
        raw_before = (meta_path.parent / "unaccepted-output.json").read_bytes()
        failure_before = meta_path.read_bytes()
        result = self.revalidate()
        self.assertTrue(result["revalidated"])
        self.assertEqual(result["attempt"], 1)
        status_after = self.queue.status()
        self.assertEqual(status_after["cases"][0]["consumed_attempts"], 1)
        self.assertEqual(len(status_after["dispatches"]), 1)
        final_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual((meta_path.parent / "unaccepted-output.json").read_bytes(), raw_before)
        self.assertEqual((meta_path.parent / "failure-metadata.json").read_bytes(), failure_before)
        self.assertEqual(final_meta["completed_at"], json.loads(failure_before)["completed_at"])
        self.assertEqual(final_meta["usage"], [{"input_tokens": 10}])
        self.assertTrue(final_meta["engineering_test"])
        self.assertFalse(final_meta["runtime_verified_live"])
        with self.queue._db() as db:
            row = db.execute("SELECT * FROM scoped_jobs WHERE job_id='j1'").fetchone()
            self.queue._checkpoint(row, meta_path, db=db)
        again = self.revalidate()
        self.assertFalse(again["revalidated"])
        self.assertEqual(again["reason"], "already-revalidated")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)

    def test_every_atomic_write_boundary_recovers_or_replays_without_new_attempt(self):
        for interrupted_name in ("failure-metadata.json", "failure-projection.json", "processing-receipt.json", "result.json", "metadata.json"):
            with self.subTest(boundary=interrupted_name):
                temp = tempfile.TemporaryDirectory()
                self.addCleanup(temp.cleanup)
                fixture = adapter_tests.ScopedAdapterTests()
                fixture.setUp()
                self.addCleanup(fixture.tearDown)
                self.install_fixture_catalog(fixture.root)
                q = ScopedQueue(fixture.root, fixture_only=True)
                job = fixture.job
                q.enqueue(job)
                spec = {"job_id": job["job_id"], "stage": "analysis", "role": job["role"], "model": MODELS[job["role"]],
                    "scope_sha256": scope_sha256(job), "package_sha256": package_sha256(job), "target_from_job_id": None}
                now = datetime.now(timezone.utc)
                q.authorize_batch({"schema_version": 1, "batch_id": "b1", "case_id": "case1", "version": 1,
                    "created_at": (now-timedelta(minutes=1)).isoformat(), "expires_at": (now+timedelta(hours=1)).isoformat(),
                    "purpose": "Fixture crash boundary", "provenance_refs": ["engineering-fixture"], "call_limit": 4,
                    "permitted_continuation": ["explicit-retry", "material-correction", "material-recheck"], "jobs": [spec]})
                bad = copy.deepcopy(fixture.output)
                bad["status"] = "withheld"
                bad["conclusions"][0].update(status="withheld", blocking_issues=["f1: label"])
                bad["findings"] = [{"id":"f1","severity":"material","claim":"Fixture","evidence":[],
                    "proposed_correction":"Review","outcome":"withheld","affected_conclusions":["c1"]}]
                def runner(args, **kwargs):
                    if args[1] == "login":
                        return subprocess.CompletedProcess(args, 0, "", "Logged in using ChatGPT")
                    Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(bad), encoding="utf-8")
                    stdout = json.dumps({"type":"thread.started"})+"\n"+json.dumps({"type":"turn.completed","usage":{"input_tokens":10}})
                    return subprocess.CompletedProcess(args, 0, stdout, "")
                def adapter(root, package, **kwargs):
                    return fixture.run_job(job=package, runner=runner, environ={}, **kwargs)
                with patch.object(queue_module, "verify_dispatch", verify_dispatch):
                    q.run_one(job_id="j1", batch_id="b1", adapter=adapter, executable="fixture-cli")
                original_atomic = queue_module.__dict__.get("_atomic")
                if original_atomic is None:
                    import research_checkpoint
                    original_atomic = research_checkpoint._atomic
                import research_checkpoint
                raised = {"done": False}
                def crash_after_write(path, data):
                    original_atomic(path, data)
                    if Path(path).name == interrupted_name and not raised["done"]:
                        raised["done"] = True
                        raise OSError("fixture crash after atomic replacement")
                with patch.object(research_checkpoint, "_atomic", crash_after_write):
                    with self.assertRaises(OSError):
                        q.revalidate_failed_output(job_id="j1", batch_id="b1")
                self.assertTrue(raised["done"])
                status = q.status()
                self.assertEqual(status["cases"][0]["consumed_attempts"], 1)
                self.assertEqual(len(status["dispatches"]), 1)
                if interrupted_name == "metadata.json":
                    recovered = q.recover()
                    self.assertEqual(recovered["jobs"][0]["status"], "needs-input")
                else:
                    with patch.object(queue_module, "verify_dispatch", verify_dispatch):
                        retry = q.revalidate_failed_output(job_id="j1", batch_id="b1")
                    self.assertIn(retry["status"], {"needs-input", "complete"})
                self.assertEqual(q.status()["cases"][0]["consumed_attempts"], 1)
                self.assertEqual(len(q.status()["dispatches"]), 1)

    def test_expired_current_authority_rejected_but_successor_binding_preserves_history(self):
        self.prepare(with_review=True)
        before = self.queue.status()
        dispatch = before["dispatches"][0]
        expired_now = datetime.now(timezone.utc) + timedelta(days=2)
        with patch.object(queue_module, "datetime") as clock:
            clock.now.return_value = expired_now
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.assertRaisesRegex(ValueError, "expired"):
                self.revalidate()
        self.assertEqual(self.queue.status()["jobs"][0]["status"], "needs-retry-decision")
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        with patch.object(queue_module, "verify_dispatch", verify_dispatch):
            self.queue.revalidate_failed_output(job_id="j1", batch_id="b1")
        meta = json.loads(Path(self.queue.status()["jobs"][0]["metadata_path"]).read_text())
        self.review_job["target"] = {"path": Path(meta["result_path"]).relative_to(self.root).as_posix(), "sha256": meta["output_sha256"]}
        archived = self.queue.export_result('j1', case_id='case1')
        public_execution = json.loads((self.root / archived['execution']['path']).read_text(encoding='utf-8'))
        self.review_job['target']['processing'] = public_execution['processing']
        self.queue.enqueue(self.review_job)
        # The initial version already included this unbound review, so version 2
        # binds only the exact validated predecessor output.
        auth2 = copy.deepcopy(self.initial_manifest)
        auth2["version"] = 2
        auth2["jobs"][1]["package_sha256"] = package_sha256(self.review_job)
        self.queue.authorize_batch(auth2)
        with self.queue._db() as db:
            row = db.execute("SELECT * FROM scoped_jobs WHERE job_id='j1'").fetchone()
            checked = self.queue._checkpoint(row, Path(row["metadata_path"]), db=db)
        self.assertEqual(checked["normalization_timestamp"], json.loads((Path(checked["metadata_path"]).parent / "processing-receipt.json").read_text())["normalization_timestamp"])
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)
        # Authority expiry blocks new normalization but does not revoke a
        # previously validated, timestamp-bound output during later reads.
        with patch.object(queue_module, "datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(days=2)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.queue._db() as db:
                row = db.execute("SELECT * FROM scoped_jobs WHERE job_id='j1'").fetchone()
                historical = self.queue._checkpoint(row, Path(row["metadata_path"]), db=db)
        self.assertEqual(historical["reason"], "analytical-output-validated")

    def test_authorization_widening_and_dispatch_mutation_rejected(self):
        self.prepare()
        changed = self.manifest(jobs=[self.analysis_spec])
        changed["call_limit"] = 5
        with self.assertRaises(ValueError):
            self.queue.authorize_batch(changed)
        with self.queue._db() as db:
            db.execute("UPDATE scoped_dispatches SET authorization_sha256=? WHERE job_id='j1'", ("0"*64,))
        with self.assertRaises(ValueError):
            self.revalidate()
        self.assertEqual(self.queue.status()["cases"][0]["consumed_attempts"], 1)

    def test_checkpoint_rejects_retained_hash_and_attempt_identity_tampering(self):
        self.prepare()
        self.revalidate()
        status = self.queue.status()
        meta_path = Path(status["jobs"][0]["metadata_path"])
        raw_path = meta_path.parent / "unaccepted-output.json"
        raw_original = raw_path.read_bytes()
        raw_path.write_bytes(raw_original + b" ")
        with self.queue._db() as db:
            row = db.execute("SELECT * FROM scoped_jobs WHERE job_id='j1'").fetchone()
            with self.assertRaisesRegex(ValueError, "hashes|bindings|differs"):
                self.queue._checkpoint(row, meta_path, db=db)
        raw_path.write_bytes(raw_original)
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata["attempt"] = 2
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.queue._db() as db:
            row = db.execute("SELECT * FROM scoped_jobs WHERE job_id='j1'").fetchone()
            with self.assertRaisesRegex(ValueError, "identity differs"):
                self.queue._checkpoint(row, meta_path, db=db)

    def test_fixture_mode_cannot_be_enabled_outside_temporary_root(self):
        with self.assertRaisesRegex(ValueError, "temporary project root"):
            ScopedQueue(TESTS.parents[1], fixture_only=True)

    def test_repaired_analysis_review_export_translation_and_park_remain_fixture_only(self):
        from decision_readiness import SCOPED_COVERAGE
        from research_records import envelope, save_record, translate_scoped, project_case, validate_record
        self.fixture.job['scope']['required_categories'] = sorted(SCOPED_COVERAGE)
        self.fixture.job['packet']['max_utf8_bytes'] = 100000
        self.bad_output['coverage'] = [dict(category=c, status='covered', evidence=[self.fixture.ref])
                                       for c in sorted(SCOPED_COVERAGE)]
        # Reset the initial queued fixture before dispatch; no attempt exists.
        with self.queue._db() as db:
            db.execute('DELETE FROM scoped_jobs')
        self.queue.enqueue(self.fixture.job)
        self.prepare(with_review=True)
        self.revalidate()
        analysis = self.queue.export_result('j1', case_id='case1')
        execution = json.loads((self.root/analysis['execution']['path']).read_text(encoding='utf-8'))
        self.assertNotIn('failure_metadata', execution)
        self.assertTrue(execution['engineering_test'])
        self.assertEqual(len(execution['processing']), 4)
        meta = json.loads(Path(self.queue.status()['jobs'][0]['metadata_path']).read_text(encoding='utf-8'))
        self.review_job['target'] = dict(path=Path(meta['result_path']).relative_to(self.root).as_posix(),
            sha256=meta['output_sha256'], processing=execution['processing'])
        self.queue.enqueue(self.review_job)
        auth2 = copy.deepcopy(self.initial_manifest)
        auth2['version'] = 2
        auth2['jobs'][1]['package_sha256'] = package_sha256(self.review_job)
        self.queue.authorize_batch(auth2)
        request_content = dict(entity='Example plc', security=dict(legal_entity='Example plc', identifier='EXAMPLE:ORD',
            exchange='Example Exchange', share_class='Ordinary', trading_currency='GBP', price_unit='GBp', reporting_currency='GBP'),
            question='Fixture bounded assessment', holding_window='days to months', mode='focused-opportunity',
            evidence_cutoff=self.fixture.job['as_of'], required_coverage=sorted(SCOPED_COVERAGE),
            stopping_conditions=['Park for missing economic evidence'])
        def save(kind, content, ident, unknowns):
            return save_record(self.root, envelope('case1', kind, content, record_id=ident,
                created_at=datetime.now(timezone.utc).isoformat(), origin='Fictional engineering test only',
                provenance_refs=[self.fixture.job['methodology']['base']], unknowns=unknowns))
        request = save('request', request_content, 'request', [])
        research = translate_scoped(self.root, request=request, **{k:analysis[k] for k in ('job','result','execution')},
            case_id='case1', record_id='analysis', created_at=datetime.now(timezone.utc).isoformat(),
            unknowns=['Fictional fixture, not actual research'])
        review_output = copy.deepcopy(json.loads((self.root/analysis['result']['path']).read_text(encoding='utf-8')))
        review_output['status'] = 'review-complete'
        def runner(args, **kwargs):
            if args[1] == 'login':
                return subprocess.CompletedProcess(args, 0, '', 'Logged in using ChatGPT')
            self.assertIn('deterministic-reference-formatting-only', kwargs['input'])
            self.assertIn('original_private_metadata_sha256', kwargs['input'])
            Path(args[args.index('--output-last-message')+1]).write_text(json.dumps(review_output),encoding='utf-8')
            return subprocess.CompletedProcess(args, 0, json.dumps({'type':'turn.completed'}), '')
        def adapter(root, job, **kwargs):
            return self.fixture.run_job(job=job, runner=runner, environ={}, **kwargs)
        with patch.object(queue_module, 'verify_dispatch', verify_dispatch):
            result = self.queue.run_one(job_id='j2',batch_id='b1',adapter=adapter,executable='fixture-cli')
        self.assertEqual(result['status'], 'needs-input')
        review = self.queue.export_result('j2',case_id='case1')
        challenged = translate_scoped(self.root, request=request, **{k:review[k] for k in ('job','result','execution')},
            target_record=research, case_id='case1',record_id='review',created_at=datetime.now(timezone.utc).isoformat(),
            unknowns=['Fictional review only'])
        dossier = save('opportunity-dossier', dict(request=request,research=research, expectations='Unknown.',
            price_response='Unestablished.',holding_window='days to months',costs=dict(schedule=None,currency='GBP',
            round_trip=None,limitations=['Unknown costs']),adverse_cases={k:'Unresolved.' for k in
            ('no-repricing','adverse-surprise','delayed-catalyst','overnight-gap','too-late')}, entry_conditions='Withheld.',
            exits='No instruction.',reassessment_triggers='New evidence.',cash_comparison='Cash retained.'), 'dossier',['Fixture only'])
        disposition = save('disposition',dict(research=research,review=challenged,dossier=dossier,status='parked',
            rationale='Fixture evidence incomplete.',reopening_conditions=['New evidence'],expires_at=None),'park',['Fixture only'])
        projection = project_case(self.root,disposition)
        self.assertEqual(projection['review_status'],'fixture-only')
        self.assertFalse(projection['live_recommendations_enabled'])
        self.assertEqual(self.queue.status()['cases'][0]['consumed_attempts'],2)
        # A changed receipt must invalidate the saved research chain, not just
        # the operational checkpoint. There is no database trust shortcut here.
        receipt_path = self.root/execution['processing']['receipt']['path']
        receipt_path.write_bytes(receipt_path.read_bytes()+b' ')
        record = json.loads((self.root/research['path']).read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            validate_record(self.root,record)

    def test_review_without_processing_context_cannot_bind(self):
        self.prepare(with_review=True)
        self.revalidate()
        meta = json.loads(Path(self.queue.status()['jobs'][0]['metadata_path']).read_text(encoding='utf-8'))
        self.review_job['target'] = dict(path=Path(meta['result_path']).relative_to(self.root).as_posix(),sha256=meta['output_sha256'])
        self.queue.enqueue(self.review_job)
        auth2 = copy.deepcopy(self.initial_manifest)
        auth2['version'] = 2
        auth2['jobs'][1]['package_sha256'] = package_sha256(self.review_job)
        with self.assertRaisesRegex(ValueError,'processing context'):
            self.queue.authorize_batch(auth2)
        self.assertEqual(self.queue.status()['cases'][0]['consumed_attempts'],1)


if __name__ == "__main__":
    unittest.main()
