"""Connected fictional evidence test. No actual research/account/phone approval."""
import hashlib
import json
import tempfile
import unittest
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import test_decision_readiness as fixtures
from alert_contract import AlertInstruction,ArtifactRef,Security,Quote,PortfolioSnapshot,GateEvidence,GATES,FreshnessPolicy
from decision_lane import DecisionLane,LanePolicy,PortfolioAcceptance,AllocationAcceptance
from decision_readiness import CurrentAcceptance
from decision_pipeline import DecisionPipeline


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReadinessTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.now=self.f.now;self.root=self.f.root
        self.refs={'research':self.f.scoped()}
        for gate in ('dossier','decision','portfolio_policy','quote','monitoring','activation','strategy_validation'):
            self.refs[gate]=self.f.add(gate,gate)
        for gate in ('phone','operational_trial'):
            old=self.f.operational_fixture(gate);entry=self.f.entries[-1]
            artifact=json.loads((self.root/entry['path']).read_text());artifact['artifact_id']=gate
            path='monitoring/readiness/'+gate+'.json';digest=self.f.save(path,artifact)
            review=json.loads((self.root/entry['review_path']).read_text())
            review['artifact']={'artifact_id':gate,'version':'1','sha256':digest}
            reviewpath='validation/reviews/'+gate+'.json'
            entry.update(artifact_id=gate,sha256=digest,path=path,review_path=reviewpath,
                         review_sha256=self.f.save(reviewpath,review))
            self.refs[gate]=ArtifactRef(gate,'1',digest)
        security=Security('LSE','TEST','ordinary','GBP','currency')
        self.quote=Quote(security,D('90'),'ask',self.now,self.refs['quote'])
        self.portfolio=PortfolioSnapshot(D('300'),(),())
        self.instruction=AlertInstruction('paper-complete',1,self.refs['research'],self.refs['dossier'],
            self.refs['decision'],self.refs['portfolio_policy'],security,'buy',D('1'),D('100'),self.quote,
            self.now,self.now+timedelta(hours=1),('Fictional material contrary evidence',),self.now,max_buy_price=D('95'))
        self.scope=dict(decision_version='1',dossier_version='1',decision_sha256=self.refs['decision'].sha256,
            dossier_sha256=self.refs['dossier'].sha256,instruction_fingerprint=self.instruction.fingerprint,
            portfolio_fingerprint=self.portfolio.fingerprint,quote_fingerprint=self.quote.fingerprint)
        for entry in self.f.entries:
            review=json.loads((self.root/entry['review_path']).read_text())
            scope=dict(self.scope)
            if not any(gate in ('quote','activation') for gate in entry['gates']):scope['quote_fingerprint']=None
            review['scope']=scope;entry['review_sha256']=self.f.save(entry['review_path'],review)
        self.registry='monitoring/readiness/registry.json'
        self.registry_hash=self.f.save(self.registry,{'schema_version':1,'entries':self.f.entries})
        self.evidence=tuple(GateEvidence(gate,self.refs[gate],self.now,self.now+timedelta(seconds=120),
            **dict(self.scope,quote_fingerprint=self.quote.fingerprint if gate in ('quote','activation') else None)) for gate in sorted(GATES))
        policy=LanePolicy(D(300),D(100),1,120,120)
        self.lane=DecisionLane(self.root/'paper-lane.db',policy,clock=lambda:self.now)
        self.addCleanup(self.lane.conn.close)
        self.lane.initialize_portfolio(self.portfolio,self.now,self.snapshot_verify)
        validators={gate:self.current_verify for gate in ('quote','monitoring','activation','portfolio_policy','phone','operational_trial')}
        self.pipeline=DecisionPipeline(self.root,self.registry,self.registry_hash,max_review_age=timedelta(days=1),validators=validators)

    def current_verify(self,artifact,review,evidence):
        return CurrentAcceptance('fictional-current-'+evidence.gate,self.now,review['scope'],
            'satisfied' if evidence.gate=='activation' else 'not-applicable')

    def snapshot_verify(self,portfolio,reconciled_at,now):
        return PortfolioAcceptance(portfolio.fingerprint,'fictional-cash-check','fictional reviewer',now,now+timedelta(seconds=120))

    def allocation_verify(self,instruction,portfolio,now):
        return AllocationAcceptance(instruction.fingerprint,portfolio.fingerprint,'fictional-issuer',('fictional-event',),
            (('issuer:fictional-issuer',D('0')),('catalyst:fictional-event',D('0'))),(self.refs['portfolio_policy'],),
            'fictional-exposure-check','fictional reviewer',now,now+timedelta(seconds=120))

    def run_cycle(self):
        return self.pipeline.issue_paper(self.lane,self.instruction,self.portfolio,reconciled_at=self.now,
            snapshot_verifier=self.snapshot_verify,allocation_verifier=self.allocation_verify,
            evidence=self.evidence,quote=self.quote,last_successful_monitoring=self.now,freshness=FreshnessPolicy(120,120,120))

    def test_reviewed_bytes_reservation_receipt_and_withdrawal_connected(self):
        result=self.run_cycle()
        self.assertFalse(result['actionable']);self.assertEqual(result['state'],'issued')
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        self.assertEqual(self.lane.conn.execute('SELECT count(*) FROM lane_confirmations').fetchone()[0],1)
        self.lane.withdraw(result['key'],'Fictional new contrary disclosure')
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        self.assertEqual(self.lane.get(result['key'])['state'],'withdrawn-awaiting-reconciliation')

    def test_dossier_tamper_blocks_before_any_commitment(self):
        (self.root/'monitoring/readiness/dossier.json').write_text('{}')
        with self.assertRaises(ValueError):self.run_cycle()
        self.assertEqual(self.lane.portfolio().available_gbp,D(300))
        self.assertEqual(self.lane.conn.execute('SELECT count(*) FROM instructions').fetchone()[0],0)

    def test_partial_execution_then_withdrawal_preserves_remainder(self):
        result=self.run_cycle();key=result['key']
        self.lane.report_order(key,'fictional-order')
        self.lane.report_fill(key,'fictional-fill','0.4','35','1')
        self.assertEqual(self.lane.get(key)['cash_remaining'],'64')
        self.lane.withdraw(key,'Fictional adverse announcement')
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        self.lane.report_fill(key,'fictional-late-fill','0.6','54','1')
        self.assertEqual(self.lane.get(key)['state'],'filled')
        self.assertEqual(self.lane.portfolio().available_gbp,D(209))
        self.assertEqual(dict(self.lane.portfolio().holdings)[self.instruction.security.key],D(1))

    def test_absent_real_fact_validator_or_allocation_proof_blocks(self):
        self.pipeline.validators.pop('phone')
        with self.assertRaises(ValueError):self.run_cycle()
        self.assertEqual(self.lane.portfolio().available_gbp,D(300))
        self.pipeline.validators['phone']=self.current_verify
        self.allocation_verify=lambda *args:True
        with self.assertRaises(ValueError):self.run_cycle()
        self.assertEqual(self.lane.portfolio().available_gbp,D(300))

    def test_delayed_quote_and_expired_receipt_never_issue(self):
        self.now+=timedelta(minutes=10)
        with self.assertRaises(ValueError):self.run_cycle()
        self.assertEqual(self.lane.conn.execute('SELECT count(*) FROM lane_confirmations').fetchone()[0],0)

if __name__=='__main__':unittest.main()
