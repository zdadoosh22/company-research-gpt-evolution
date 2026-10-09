"""Connected, reservation-backed PAPER decision pipeline.

No delivery or broker endpoints. Trusted current-fact validators and actual
acceptance records remain external inputs, not flags inferred from tests.
The live observation coordinator does not call this module. Confirmations are
dated history; after restart a fresh complete-gate review is required.
"""
import json
from datetime import timedelta
from alert_contract import AlertBook, GateEvidence, GATES, stamp
from decision_lane import ArtifactAcceptance, DecisionLane
from decision_readiness import ArtifactVerifier


class DecisionPipeline:
    def __init__(self, root, registry_path, registry_sha256, *, max_review_age, validators):
        self.root=root; self.registry_path=registry_path; self.registry_sha256=registry_sha256
        self.max_review_age=max_review_age; self.validators=dict(validators)

    def issue_paper(self,lane,instruction,portfolio,*,reconciled_at,snapshot_verifier,
                    allocation_verifier,evidence,quote,last_successful_monitoring,freshness):
        if not isinstance(lane,DecisionLane): raise ValueError('Isolated decision lane required')
        if not isinstance(evidence,tuple) or any(not isinstance(item,GateEvidence) for item in evidence):
            raise ValueError('Complete typed evidence required')
        if len(evidence)!=len(GATES) or {item.gate for item in evidence}!=GATES:
            raise ValueError('Exactly one evidence record per required gate')
        now=lane._now()
        expected={
            'decision_version':instruction.decision.version,'dossier_version':instruction.dossier.version,
            'decision_sha256':instruction.decision.sha256,'dossier_sha256':instruction.dossier.sha256,
            'instruction_fingerprint':instruction.fingerprint,'portfolio_fingerprint':portfolio.fingerprint,
            'quote_fingerprint':quote.fingerprint}
        verifier=ArtifactVerifier(self.root,self.registry_path,self.registry_sha256,now=now,
            expected_scope=expected,max_review_age=self.max_review_age,validators=self.validators)
        book=AlertBook();book.register(instruction)
        # Complete acceptance, current quote and financial conditions are checked
        # before reserving. Lane.issue rechecks scope/time after reservation.
        confirmation=book.confirm(instruction.alert_id,now=now,quote=quote,
            last_successful_monitoring=last_successful_monitoring,freshness=freshness,
            portfolio=portfolio,evidence=evidence,verifier=verifier)
        by_gate={item.gate:item for item in evidence}
        lane_scope=lane.scope(instruction,portfolio)

        def artifact_acceptance(ref,kind,scope,checked_now):
            if scope!=lane_scope or kind not in by_gate or by_gate[kind].artifact!=ref:
                raise ValueError('Lane artifact does not match complete acceptance cycle')
            proof=verifier(by_gate[kind])
            until=min(by_gate[kind].valid_until,now+timedelta(seconds=freshness.verification_seconds))
            if proof.valid_until is not None: until=min(until,stamp(proof.valid_until))
            return ArtifactAcceptance(ref,proof.validation_id,proof.reviewer,proof.checked_at,until,scope,proof.verdict)

        registry=verifier._json(verifier._path(self.registry_path),self.registry_sha256)
        for kind in ('research','dossier','decision','portfolio_policy'):
            ref=getattr(instruction,kind)
            entries=[entry for entry in registry['entries'] if
                (entry.get('artifact_id'),entry.get('version'),entry.get('sha256'))==
                (ref.artifact_id,ref.version,ref.sha256)]
            if len(entries)!=1: raise ValueError('Unique registered lane artifact required')
            raw=verifier._bytes(verifier._path(entries[0]['path']),ref.sha256)
            lane.register_artifact(ref,kind,json.loads(raw.decode('utf-8-sig')),lane_scope,
                artifact_acceptance,raw_bytes=raw)
        key=lane.plan(instruction)['key']
        lane.reserve(key,portfolio,reconciled_at,snapshot_verifier,artifact_acceptance,
            allocation_verifier=allocation_verifier)
        result=lane.issue(key,artifact_acceptance,book=book,confirmation=confirmation,allocation_verifier=allocation_verifier)
        return {'mode':'reservation-backed-paper','actionable':False,'key':key,
                'state':result['state'],'confirmation':confirmation,
                'delivery':'none','broker_execution':'none'}
