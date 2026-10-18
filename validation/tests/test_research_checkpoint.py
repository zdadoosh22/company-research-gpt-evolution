import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from alert_contract import GATES
from research_checkpoint import (canonical, make_reference, record_checkpoint, rebuild_projection,
                                 render_html, load_checkpoint_input, requirements_snapshot, EVENT_DIRECTORY, _atomic)

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


class CheckpointTests(unittest.TestCase):
    def assessment(self, *, duplicate=False, defer_required=False):
        def save(path,value):
            p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8')
            return make_reference(self.root,path)
        inventory=save('validation/inventory.json',dict(requirements=[dict(id='COMMAND-ONE',requirement='Explicit prepare',required_for_software_acceptance=True),
            dict(id='BRIEF-TWO',requirement='Real review',required_for_software_acceptance=True)]))
        rows=[dict(id='COMMAND-ONE',status='deferred' if defer_required else 'implemented-fixture-tested',evidence=[self.ref]),
              dict(id='COMMAND-ONE' if duplicate else 'BRIEF-TWO',status='not-assessed',evidence=[])]
        assessment=save('validation/assessment.json',dict(schema_version=1,created_at='2026-10-15T10:00:00Z',inventory=inventory,requirements=rows))
        save('monitoring/research-engine/requirements/current.json',dict(assessment=assessment))

    def long_atomic_target(self):
        name = "target-processing-failure_projection.json"
        # Resolve a real temporary path and keep its destination below the
        # classic Windows MAX_PATH limit while the former temporary exceeds it.
        padding = 240 - len(str(self.root.resolve())) - len(name) - 2
        if padding < 1:
            self.skipTest("Temporary directory is too long to construct this bounded fixture")
        parent = self.root.resolve() / ("p" * padding)
        parent.mkdir()
        target = parent / name
        self.assertEqual(len(str(target)), 240)
        self.assertGreater(len(str(target.with_name(name + "." + "a" * 32 + ".tmp"))), 260)
        return target

    def test_atomic_long_path_create_and_overwrite_use_short_same_directory_temp(self):
        target = self.long_atomic_target()
        with patch("research_checkpoint.os.replace", wraps=os.replace) as replace:
            _atomic(target, b"original bytes")
            self.assertEqual(target.read_bytes(), b"original bytes")
            _atomic(target, b"replacement bytes")
        self.assertEqual(target.read_bytes(), b"replacement bytes")
        for call in replace.call_args_list:
            source, destination = call.args
            self.assertEqual(source.parent, target.parent)
            self.assertEqual(destination, target)
            self.assertRegex(source.name, r"^[0-9a-f]{32}\.tmp$")
            self.assertLess(len(str(source)), 260)
        self.assertEqual(list(target.parent.iterdir()), [target])

    def test_atomic_replace_failure_preserves_long_destination_and_cleans_temp(self):
        target = self.long_atomic_target()
        target.write_bytes(b"immutable prior destination bytes")
        def failed_replace(source, destination):
            self.assertEqual(source.read_bytes(), b"new unpublished bytes")
            self.assertEqual(destination.read_bytes(), b"immutable prior destination bytes")
            self.assertEqual(source.parent, destination.parent)
            self.assertLess(len(str(source)), 260)
            raise PermissionError("Engineering fixture: replacement unavailable")
        with patch("research_checkpoint.os.replace", side_effect=failed_replace):
            with self.assertRaises(PermissionError):
                _atomic(target, b"new unpublished bytes")
        self.assertEqual(target.read_bytes(), b"immutable prior destination bytes")
        self.assertEqual(list(target.parent.iterdir()), [target])

    def test_requirement_counts_are_version_bound_not_completion(self):
        self.assessment();p=requirements_snapshot(self.root,now=NOW)
        self.assertEqual(p['total'],2);self.assertEqual(p['counts']['not-assessed'],1)
        (self.root/self.ref['path']).write_text('changed proof',encoding='utf-8')
        self.assertEqual(requirements_snapshot(self.root,now=NOW)['counts']['invalidated'],1)

    def test_requirement_matrix_cannot_omit_work_by_duplicate_or_deferral(self):
        self.assessment(duplicate=True)
        self.assertEqual(requirements_snapshot(self.root,now=NOW)['status'],'unavailable')
        self.assessment(defer_required=True)
        self.assertEqual(requirements_snapshot(self.root,now=NOW)['status'],'unavailable')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'validation').mkdir()
        (self.root / 'validation/result.txt').write_text('one actual local test result', encoding='utf-8')
        self.ref = make_reference(self.root, 'validation/result.txt')
        self.start = dict(schema_version=1, id='stage-one-start', task_id='stage-one', turn_id='turn-one',
            phase='start', created_at='2026-10-15T10:00:00Z', observed_at='2026-10-15T10:00:00Z',
            origin='explicit test fixture, not real project acceptance', request='Verify checkpoint recovery',
            work=[], outcome=None, artifacts=[], checks=[], blockers=dict(resolved=[], introduced=[], unchanged=['No live account acceptance']),
            readiness_impact=dict(label='not assessed', requirements=[], artifact_paths=[], explanation='A start proves no outcome'),
            verified_gate_changes=[], next_action='Run bounded task', unknowns=['Live acceptance'], supersedes=[])

    def completion(self, outcome='partial'):
        event = copy.deepcopy(self.start)
        event.update(id='stage-one-complete', phase='complete', created_at='2026-10-15T11:00:00Z',
                     observed_at='2026-10-15T11:00:00Z', outcome=outcome,
                     work=['Executed a fictional test scenario'], artifacts=[self.ref],
                     checks=[dict(id='fixture-check', method='synthetic unit test', outcome='passed', artifact_paths=[self.ref['path']])],
                     next_action='Continue implementation')
        return event

    def record(self, event):
        return record_checkpoint(self.root, event, now=NOW)

    def test_invalid_release_blocks_software_without_minting_live_gates(self):
        self.assertEqual(rebuild_projection(self.root,now=NOW)['software_completion'],'not started')
        self.record(self.start)
        folder=self.root/'monitoring/research-engine/releases';folder.mkdir(parents=True)
        (folder/'current.json').write_text(json.dumps({'assessment':{'path':'state/observation/private.json','sha256':'0'*64}}),encoding='utf-8')
        view=rebuild_projection(self.root,now=NOW)
        self.assertEqual(view['software_completion'],'blocked')
        self.assertFalse(view['live_recommendations_enabled'])
        self.assertTrue(all(g['status']=='not assessed' for g in view['gates']))
        self.assertNotIn('private.json',json.dumps(view.get('software_release',{})))

    def test_crash_after_start_does_not_invent_running_or_complete(self):
        self.record(self.start)
        p = rebuild_projection(self.root, now=NOW)
        self.assertEqual(p['tasks'][0]['outcome'], 'turn ended; outcome not recorded.')
        self.assertEqual(p['tasks'][0]['work'], [])
        self.assertEqual(p['activation'], 'disabled')

    def test_all_execution_outcomes_stay_distinct_from_trade_acceptance(self):
        for outcome in ('complete', 'partial', 'failed', 'interrupted'):
            with self.subTest(outcome=outcome):
                start = copy.deepcopy(self.start)
                start.update(turn_id=outcome, id=outcome + '-start')
                end = self.completion(outcome)
                end.update(turn_id=outcome, id=outcome + '-end')
                self.record(start)
                p = self.record(end)['projection']
                self.assertEqual(p['counts']['outcomes'][outcome], 1)
                self.assertEqual(set(x['gate'] for x in p['gates']), GATES)
                self.assertTrue(all(x['status'] == 'not assessed' for x in p['gates']))
                self.assertFalse(p['live_recommendations_enabled'])
                self.assertNotEqual(p['software_completion'], 'complete')

    def test_duplicate_events_are_idempotent_but_changed_payload_is_rejected(self):
        self.assertTrue(self.record(self.start)['recorded'])
        self.assertFalse(self.record(copy.deepcopy(self.start))['recorded'])
        changed = copy.deepcopy(self.start); changed['request'] = 'Different request'
        with self.assertRaises(ValueError): self.record(changed)
        self.assertEqual(len(list((self.root / EVENT_DIRECTORY).glob('*.json'))), 1)

    def test_complete_requires_start_and_chronology(self):
        with self.assertRaises(ValueError): self.record(self.completion())
        self.record(self.start)
        end = self.completion(); end.update(created_at='2026-10-15T09:00:00Z', observed_at='2026-10-15T09:00:00Z')
        with self.assertRaises(ValueError): self.record(end)

    def test_delete_projection_rebuild_is_identical_at_same_cutoff(self):
        self.record(self.start); original = self.record(self.completion())['projection']
        state = self.root / 'state/research-engine'
        (state / 'status.json').unlink(); (state / 'status.html').unlink()
        self.assertEqual(canonical(original), canonical(rebuild_projection(self.root, now=NOW)))

    def test_referenced_evidence_tamper_regresses_completion(self):
        self.record(self.start); self.record(self.completion('complete'))
        (self.root / self.ref['path']).write_text('changed after checkpoint', encoding='utf-8')
        p = rebuild_projection(self.root, now=NOW)
        self.assertEqual(p['counts']['invalid_events'], 1)
        self.assertEqual(p['tasks'][0]['outcome'], 'invalidated checkpoint; outcome unverified')
        self.assertEqual(p['counts']['outcomes']['complete'], 0)
        self.assertEqual(p['tasks'][0]['artifacts'], [])

    def test_corrupt_event_is_visible_and_not_reported_complete(self):
        self.record(self.start)
        path = next((self.root / EVENT_DIRECTORY).glob('*.json'))
        path.write_text('{broken', encoding='utf-8')
        p = rebuild_projection(self.root, now=NOW)
        self.assertEqual(p['counts']['invalid_events'], 1)
        self.assertEqual(p['counts']['outcomes']['complete'], 0)

    def test_private_and_escaping_inputs_are_refused(self):
        for path in ('../outside.json', 'state/ledger.json', 'C:/secret', 'validation/../private.json', 'validation/auth.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                load_checkpoint_input(self.root, path)
        for path in ('validation/private.db', 'validation/.env', 'validation/secrets/data.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                make_reference(self.root, path)

    def test_checkpoint_cannot_mint_verified_gates_or_unsupported_improvement(self):
        self.record(self.start)
        end = self.completion(); end['verified_gate_changes'] = [{'gate': 'activation', 'status': 'satisfied'}]
        with self.assertRaises(ValueError): self.record(end)
        end = self.completion(); end['readiness_impact']['label'] = 'improved'
        with self.assertRaises(ValueError): self.record(end)
        end['readiness_impact'].update(requirements=['REQ-CHECKPOINT'], artifact_paths=[self.ref['path']])
        self.assertTrue(self.record(end)['recorded'])

    def test_xss_and_remote_resource_text_are_rendered_as_text(self):
        evil = '<script>alert(1)</script><img src="https://example.test/leak">'
        self.start['request'] = evil
        p = self.record(self.start)['projection']; rendered = render_html(p)
        self.assertNotIn('<script>', rendered); self.assertNotIn('<img ', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn("default-src 'none'", rendered)

    def test_future_records_and_boolean_schema_version_are_rejected(self):
        for field,value in [('created_at','2026-10-16T00:00:00Z'),('observed_at','2026-10-16T00:00:00Z'),('schema_version',True)]:
            event = copy.deepcopy(self.start); event[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.record(event)

    def test_symlink_artifact_cannot_escape_allowlist(self):
        external = self.root / 'outside.txt'; external.write_text('excluded', encoding='utf-8')
        link = self.root / 'validation/link.txt'
        try: link.symlink_to(external)
        except OSError: self.skipTest('OS does not permit creating symlinks in this test')
        with self.assertRaises(ValueError): make_reference(self.root, 'validation/link.txt')


if __name__ == '__main__':
    unittest.main()
