"""Fictional public provenance, never evidence of actual model execution."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from research_output import normalize_issue_references
from research_processing import processing_context
from research_packet import prepare_packet
import test_research_packet as packet_fixture


def encoded(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = packet_fixture.ResearchPacketTests()
        self.packet_fixture.setUp()
        self.addCleanup(self.packet_fixture.tearDown)
        self.root = self.packet_fixture.root
        self.raw = {'findings': [{'id': 'F1', 'severity': 'material', 'outcome': 'unresolved',
                                  'affected_conclusions': ['C1']}], 'gaps': [],
                    'conclusions': [{'id': 'C1', 'status': 'withheld', 'claim': 'Fixture claim',
                                     'blocking_issues': ['F1: existing issue']}]}
        normalized, edits = normalize_issue_references(self.raw)
        self.target = encoded(normalized)
        self.events = [{'type': 'thread.started'}, {'type': 'item.completed', 'item_type': 'agent_message'},
                       {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 2}}]
        self.failure = dict(schema_version=1, job_id='analysis1', dispatch_id='fixture-dispatch', attempt=1,
            role='analysis', model_requested='gpt-6.1-sol', authentication='chatgpt-subscription',
            reasoning_effort='high', speed='standard', engineering_test=False, runtime_verified_live=True,
            returncode=0, selected_route_completed=False, reason='invalid-output-input-or-unauthorized-event',
            validation_stage='output-schema-and-provenance', actual_model=None,
            actual_model_verification='not-reported', models_observed=[], backend_independently_verified=False,
            started_at='2020-02-01T01:00:00Z', completed_at='2020-02-01T01:02:00Z',
            unaccepted_output_sha256=digest(encoded(self.raw)), original_private_metadata_sha256='a'*64,
            target_sha256='b'*64, packet_sha256='c'*64, input_manifest_sha256='d'*64, staged_input_manifest={})
        self.receipt = dict(schema_version=1, job_id='analysis1', dispatch_id='fixture-dispatch', attempt=1,
            role='analysis', model='gpt-6.1-sol', raw_output_sha256=digest(encoded(self.raw)),
            processed_result_sha256=digest(self.target), events_sha256=digest(encoded(self.events)),
            failure_projection_sha256=digest(encoded(self.failure)), failure_metadata_sha256='a'*64,
            target_sha256='b'*64, packet_sha256='c'*64, input_manifest_sha256='d'*64, staged_input_manifest={},
            algorithm_sha256=digest((Path(__file__).resolve().parents[2]/'tools/research_output.py').read_bytes()),
            normalization=edits, normalization_timestamp='2020-02-01T01:03:00Z')
        self.failure['staged_input_manifest'] = self.receipt['staged_input_manifest'] = {
            'packet.json':'c'*64,'schema.json':'e'*64,'model_catalog.json':'f'*64}
        self.binding = self.publish()

    def publish(self, prefix='validation/processing-fixture'):
        self.receipt['failure_projection_sha256'] = digest(encoded(self.failure))
        result = {}
        for key, value in [('raw_output', self.raw), ('failure_projection', self.failure),
                           ('events', self.events), ('receipt', self.receipt)]:
            path = self.root / (prefix + '/' + key + '.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
            result[key] = {'path': path.relative_to(self.root).as_posix(), 'sha256': digest(path.read_bytes())}
        return result

    def test_public_replay_and_path_independent_context(self):
        first = processing_context(self.root, self.binding, self.target)
        second = processing_context(self.root, self.publish('validation/relocated'), self.target)
        self.assertEqual(first['context'], second['context'])
        self.assertNotEqual(first['input_manifest'], second['input_manifest'])
        self.assertEqual(len(first['input_manifest']), 4)
        self.assertIn('not independently proven', first['context']['limitations'][-1])
        self.assertEqual(set(first['context']['artifacts']), {'receipt','failure_projection'})
        self.assertIn('raw_output', first['context']['artifact_hashes'])

    def test_changed_claim_is_not_a_formatting_repair_even_with_updated_hash(self):
        changed = json.loads(self.target)
        changed['conclusions'][0]['claim'] = 'Invented replacement economics'
        bad_target = encoded(changed)
        self.receipt['processed_result_sha256'] = digest(bad_target)
        with self.assertRaisesRegex(ValueError, 'permitted deterministic repair'):
            processing_context(self.root, self.publish(), bad_target)

    def test_tampered_artifact_rejected_before_replay(self):
        path = self.root / self.binding['raw_output']['path']
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            processing_context(self.root, self.binding, self.target)

    def test_false_route_and_future_processing_rejected(self):
        for mutate in [lambda: self.failure.update(engineering_test=True),
                       lambda: self.failure.update(actual_model='different-model'),
                       lambda: self.receipt.update(normalization_timestamp='2999-01-01T00:00:00Z')]:
            with self.subTest(mutate=mutate):
                old_failure, old_receipt = copy.deepcopy(self.failure), copy.deepcopy(self.receipt)
                mutate()
                with self.assertRaises(ValueError):
                    processing_context(self.root, self.publish(), self.target)
                self.failure, self.receipt = old_failure, old_receipt

    def test_private_and_missing_explicit_refs_rejected(self):
        private = copy.deepcopy(self.binding)
        private['receipt']['path'] = 'state/private.json'
        for bad in [private, {}, {'receipt': self.binding['receipt']}]:
            with self.assertRaises(ValueError):
                processing_context(self.root, bad, self.target)

    def test_packet_opt_in_and_archived_path_reproduction(self):
        job = copy.deepcopy(self.packet_fixture.job)
        baseline = prepare_packet(self.root, job, self.packet_fixture.schema)
        (self.root/'target.md').write_bytes(self.target)
        job['target'] = {'path':'target.md', 'sha256':digest(self.target), 'processing':self.binding}
        enriched = prepare_packet(self.root, job, self.packet_fixture.schema)
        self.assertIn('processing', enriched['content']['target'])
        self.assertEqual(enriched['content']['sources'], baseline['content']['sources'])
        job['target']['processing'] = self.publish('validation/archived')
        relocated = prepare_packet(self.root, job, self.packet_fixture.schema)
        self.assertEqual(enriched['bytes'], relocated['bytes'])

    def test_processed_execution_preserves_original_identity_and_usage(self):
        meta = dict(self.failure, normalization_timestamp=self.receipt['normalization_timestamp'],
                    output_sha256=digest(self.target), usage=[self.events[-1]['usage']])
        processing_context(self.root, self.binding, self.target, execution=meta)
        meta['actual_model'] = 'gpt-6.1-sol'
        with self.assertRaisesRegex(ValueError, 'original route facts'):
            processing_context(self.root, self.binding, self.target, execution=meta)


if __name__ == '__main__':
    unittest.main()
