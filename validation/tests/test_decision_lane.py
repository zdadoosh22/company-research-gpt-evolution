import sys
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from alert_contract import AlertBook,AlertInstruction,ArtifactRef,PortfolioSnapshot,Quote,Security,FreshnessPolicy,GateEvidence,GATES,VerifiedArtifact
from decision_lane import DecisionLane,LanePolicy,ArtifactAcceptance,PortfolioAcceptance,AllocationAcceptance,artifact_hash


class DecisionLaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'lane.db'
        self.now=datetime(2026,10,8,12,tzinfo=timezone.utc)
        self.policy=LanePolicy(D(300),D(100),1,120,120)
        self.lane=DecisionLane(self.path,self.policy,clock=lambda:self.now)
        self.initial=PortfolioSnapshot(D(300),(),())
        self.lane.initialize_portfolio(self.initial,self.now,self.snapshot_verify)

    def tearDown(self):self.lane.conn.close();self.tmp.cleanup()

    def snapshot_verify(self,portfolio,reconciled_at,now):
        return PortfolioAcceptance(portfolio.fingerprint,'fixture-reconciliation','fixture reviewer',now,now+timedelta(seconds=120))

    def verify(self,ref,kind,scope,now):
        return ArtifactAcceptance(ref,'fixture-reviewed','fixture reviewer',now,now+timedelta(seconds=120),scope,'accepted')

    def allocation_verify(self,instruction,portfolio,now):
        # Fictional fixed £90 current marks and explicit exact-security issuer
        # mapping. This is never used for real securities or claimed price data.
        issuer=instruction.security.key
        exposure=dict(portfolio.holdings).get(issuer,D(0))*D(90)
        exposure+=sum((o.reserved_gbp for o in portfolio.orders if o.security_key==issuer and o.side=='buy' and o.status in ('pending','unknown')),D(0))
        return AllocationAcceptance(instruction.fingerprint,portfolio.fingerprint,issuer,(issuer,),
            (('issuer:'+issuer,exposure),('catalyst:'+issuer,exposure)),
            (ArtifactRef('fixture-current-marks','1','b'*64),ArtifactRef('fixture-issuer-catalyst-mapping','1','c'*64)),
            'fixture-allocation-review','fixture reviewer',now,now+timedelta(seconds=120))

    def instruction(self,id='a',ticker='AAA',action='buy',quantity='1',cap='100',revision=1):
        security=Security('LSE',ticker,'ordinary','GBP','currency')
        refs={kind:ArtifactRef(kind,'1',artifact_hash({'kind':kind})) for kind in ('research','dossier','decision','portfolio_policy')}
        quote=Quote(security,D(90),'ask' if action=='buy' else 'bid',self.now,ArtifactRef('quote','1','a'*64))
        return AlertInstruction(id,revision,refs['research'],refs['dossier'],refs['decision'],refs['portfolio_policy'],security,action,D(quantity),D(cap),quote,self.now,self.now+timedelta(hours=1),('fixture invalidation',),self.now,max_buy_price=D(95) if action=='buy' else None,sell_condition=None if action=='buy' else 'fixture deterioration')

    def prepare(self,instruction,portfolio=None):
        portfolio=portfolio or self.lane.portfolio()
        scope=self.lane.scope(instruction,portfolio)
        for kind in ('research','dossier','decision','portfolio_policy'):
            self.lane.register_artifact(getattr(instruction,kind),kind,{'kind':kind},scope,self.verify)
        return self.lane.plan(instruction)['key'],portfolio

    def reserve(self,key,portfolio):
        return self.lane.reserve(key,portfolio,self.now,self.snapshot_verify,self.verify,self.allocation_verify)

    def resolve_report(self,report,outcome='rejected-report-confirmed',id='report-resolution'):
        before=self.lane._portfolio()
        payload={'outcome':outcome,'report_id':report['id'],'before_portfolio_fingerprint':before.fingerprint,
            'reason':'fictional broker exception reconciliation','evidence_refs':[{'artifact_id':'fixture-broker','version':'1','sha256':'d'*64}]}
        if outcome in ('execution-confirmed','execution-correction-confirmed'):payload['broker_order_id']=self.lane.get(report['key'])['order_id']
        if outcome=='execution-correction-confirmed':
            latest=self.lane.conn.execute('SELECT payload FROM fill_adjustments WHERE execution_id=? ORDER BY id DESC LIMIT 1',(report['execution_id'],)).fetchone()
            prior=latest or self.lane.conn.execute('SELECT payload FROM fills WHERE id=?',(report['execution_id'],)).fetchone()
            import json
            payload['prior_execution_sha256']=artifact_hash(json.loads(prior[0]))
        ref=ArtifactRef('exception-proof',id,artifact_hash(payload))
        return self.lane.reconcile_execution(report['id'],id,ref,payload,self.verify)

    def issued(self):
        key,portfolio=self.prepare(self.instruction());self.reserve(key,portfolio);self.issue(key)
        return key

    def issue(self,key):
        from decision_lane import _instruction
        instruction=_instruction(self.lane.get(key)['payload'])
        portfolio=self.lane._portfolio(exclude=key)
        book=AlertBook();book.register(instruction)
        refs={kind:getattr(instruction,kind) for kind in ('research','dossier','decision','portfolio_policy')}
        refs['quote']=instruction.quote.source
        evidence=tuple(GateEvidence(gate,refs.get(gate,ArtifactRef('fixture-'+gate,'1','a'*64)),
            self.now,self.now+timedelta(seconds=120),instruction.decision.version,instruction.dossier.version,
            portfolio.fingerprint,instruction.decision.sha256,instruction.dossier.sha256,instruction.fingerprint,
            instruction.quote.fingerprint if gate in ('quote','activation') else None) for gate in sorted(GATES))
        def verify(item):
            return VerifiedArtifact(item.artifact,'fixture-all-gates','fixture reviewer',self.now,'accepted',
                item.decision_version,item.dossier_version,item.portfolio_fingerprint,item.decision_sha256,
                item.dossier_sha256,item.instruction_fingerprint,'satisfied' if item.gate=='activation' else 'not-applicable',item.quote_fingerprint)
        confirmation=book.confirm(instruction.alert_id,now=self.now,quote=instruction.quote,
            last_successful_monitoring=instruction.last_successful_monitoring,freshness=FreshnessPolicy(120,120,120),
            portfolio=portfolio,evidence=evidence,verifier=verify)
        return self.lane.issue(key,self.verify,book=book,confirmation=confirmation,allocation_verifier=self.allocation_verify)

    def cancel(self,key,id='cancel'):
        row=self.lane.get(key)
        payload={'outcome':'cancelled-confirmed','broker_order_id':row['order_id'],'filled_quantity':row['filled_quantity'],'evidence':'fixture cancellation checked'}
        ref=ArtifactRef('cancel-proof','1',artifact_hash(payload))
        return self.lane.reconcile_cancel(key,id,ref,payload,self.verify)

    def test_reserve_before_issue_and_exact_replay(self):
        key,portfolio=self.prepare(self.instruction())
        with self.assertRaises(ValueError):self.lane.issue(key,self.verify)
        self.reserve(key,portfolio);self.reserve(key,portfolio)
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        self.issue(key);self.issue(key)
        self.lane.acknowledge(key);self.lane.acknowledge(key)
        self.assertEqual(self.lane.get(key)['state'],'acknowledged')
        self.assertEqual(self.lane.conn.execute("SELECT COUNT(*) FROM audit WHERE kind='paper_instruction_issued'").fetchone()[0],1)

    def test_no_flags_hash_scope_or_expired_proofs(self):
        key,portfolio=self.prepare(self.instruction())
        with self.assertRaises(ValueError):self.lane.reserve(key,portfolio,self.now,lambda *args:True,self.verify)
        with self.assertRaises(ValueError):self.lane.reserve(key,portfolio,self.now,self.snapshot_verify,lambda *args:True)
        with self.assertRaises(ValueError):self.lane.reserve(key,portfolio,self.now,self.snapshot_verify,lambda ref,kind,scope,now:replace(self.verify(ref,kind,scope,now),scope={}))
        with self.assertRaises(ValueError):self.lane.reserve(key,portfolio,self.now,self.snapshot_verify,lambda ref,kind,scope,now:replace(self.verify(ref,kind,scope,now),checked_at=now-timedelta(seconds=121)))
        self.assertEqual(self.lane.portfolio().available_gbp,D(300))
        with self.assertRaises(ValueError):self.lane.register_artifact(ArtifactRef('x','1','0'*64),'review',{'x':1},{},self.verify)

    def test_withdraw_and_expiry_retain_unknown_cash_until_reconciliation(self):
        key=self.issued();self.now+=timedelta(hours=2)
        self.assertEqual(self.lane.expire(),[key]);self.assertEqual(self.lane.expire(),[])
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        self.assertEqual(self.lane.get(key)['state'],'withdrawn-awaiting-reconciliation')
        self.cancel(key);self.cancel(key)
        self.assertEqual(self.lane.portfolio().available_gbp,D(300))

    def test_pending_partial_fill_and_withdraw_preserve_remainder(self):
        key=self.issued();self.lane.report_order(key,'broker-1')
        self.lane.report_fill(key,'fill1','0.4','35','1')
        self.lane.report_fill(key,'fill1','0.4','35','1')
        self.assertEqual(self.lane.get(key)['state'],'partial_fill')
        self.assertEqual(self.lane.get(key)['cash_remaining'],'64')
        self.lane.withdraw(key,'new evidence')
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))
        with self.assertRaises(ValueError):self.lane.report_fill(key,'bad','0.6','65','0')
        self.resolve_report(next(r for r in self.lane.execution_reports() if r['execution_id']=='bad'))
        self.cancel(key)
        self.assertEqual(self.lane.portfolio().available_gbp,D(264))
        self.assertEqual(dict(self.lane.portfolio().holdings)['LSE:AAA:ordinary'],D('0.4'))

    def test_report_order_after_withdraw_accepts_late_full_fill(self):
        key=self.issued();self.lane.withdraw(key,'withdrawn while phone unread')
        self.lane.report_order(key,'broker-late')
        self.lane.report_fill(key,'latefill','1','90','1')
        self.assertEqual(self.lane.get(key)['state'],'filled')
        self.assertEqual(self.lane.portfolio().available_gbp,D(209))
        with self.assertRaises(ValueError):self.lane.report_fill(key,'latefill','1','91','1')

    def test_new_revision_requires_reconciled_old_exposure(self):
        key=self.issued()
        with self.assertRaises(ValueError):self.lane.plan(self.instruction(revision=2))
        self.lane.report_order(key,'broker1');self.lane.withdraw(key,'revision needed')
        with self.assertRaises(ValueError):self.lane.plan(self.instruction(revision=2))
        self.cancel(key)
        newkey,portfolio=self.prepare(self.instruction(revision=2));self.reserve(newkey,portfolio)
        self.assertEqual(self.lane.get(newkey)['state'],'reserved')

    def test_stale_snapshot_never_resets_filled_capital(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f','1','90','0')
        with self.assertRaises(ValueError):self.lane.initialize_portfolio(PortfolioSnapshot(D(299),(),()),self.now,self.snapshot_verify)
        newkey,_=self.prepare(self.instruction(id='b',ticker='BBB'))
        with self.assertRaises(ValueError):self.reserve(newkey,self.initial)
        self.assertEqual(self.lane.portfolio().available_gbp,D(210))

    def test_same_security_and_global_unreported_limits(self):
        key=self.issued();portfolio=self.lane.portfolio()
        b,p=self.prepare(self.instruction(id='b',ticker='BBB'),portfolio)
        with self.assertRaises(ValueError):self.reserve(b,p)
        self.lane.report_order(key,'broker1')
        c,p=self.prepare(self.instruction(id='c',ticker='AAA'))
        with self.assertRaises(ValueError):self.reserve(c,p)
        # A reported different-security order permits a new instruction if cash is sufficient.
        d,p=self.prepare(self.instruction(id='d',ticker='DDD'))
        self.reserve(d,p)
        self.assertEqual(self.lane.portfolio().available_gbp,D(100))

    def test_sell_only_owns_sleeve_shares_and_reserves_quantity(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f','1','90','0')
        sell,p=self.prepare(self.instruction(id='sell',action='sell',quantity='0.5',cap='0'));self.reserve(sell,p);self.issue(sell);self.lane.report_order(sell,'broker-sell')
        self.lane.report_fill(sell,'sf','0.5','55','1')
        self.assertEqual(self.lane.portfolio().available_gbp,D(264))
        self.assertEqual(dict(self.lane.portfolio().holdings)['LSE:AAA:ordinary'],D('0.5'))
        too_much,p=self.prepare(self.instruction(id='bad',action='sell',quantity='1',cap='0'))
        with self.assertRaises(ValueError):self.reserve(too_much,p)

    def test_concurrent_reservations_cannot_double_spend(self):
        first,p=self.prepare(self.instruction(id='a',ticker='AAA'))
        second,_=self.prepare(self.instruction(id='b',ticker='BBB'),p)
        barrier=threading.Barrier(2);results=[]
        def run(key):
            with DecisionLane(self.path,self.policy,clock=lambda:self.now) as lane:
                barrier.wait()
                try:lane.reserve(key,p,self.now,self.snapshot_verify,self.verify,self.allocation_verify);results.append('reserved')
                except ValueError:results.append('blocked')
        threads=[threading.Thread(target=run,args=(key,)) for key in (first,second)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=15)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(sorted(results),['blocked','reserved'])
        self.assertEqual(self.lane.portfolio().available_gbp,D(200))

    def test_database_isolation_and_immutable_policy(self):
        with self.assertRaises(ValueError):DecisionLane(Path(self.tmp.name)/'operations.sqlite3',self.policy)
        path=Path(self.tmp.name)/'other.db'
        with closing(sqlite3.connect(path)) as conn:conn.execute('CREATE TABLE other(x)');conn.commit()
        with self.assertRaises(ValueError):DecisionLane(path,self.policy)
        with self.assertRaises(ValueError):DecisionLane(self.path,replace(self.policy,per_idea_cap_gbp=D(75)))

    def test_repeat_issuer_entries_cannot_spend_three_tranches(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f1','1','90','0')
        for identifier in ('second','third'):
            key,p=self.prepare(self.instruction(id=identifier))
            with self.assertRaisesRegex(ValueError,'Aggregate'):self.reserve(key,p)
        self.assertEqual(self.lane.portfolio().available_gbp,D(210))
        self.assertEqual(dict(self.lane.portfolio().holdings)['LSE:AAA:ordinary'],D(1))

    def test_shared_catalyst_two_issuers_blocked(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f1','1','90','0')
        key,p=self.prepare(self.instruction(id='second',ticker='BBB'))
        def correlated(instruction,portfolio,now):
            proof=self.allocation_verify(instruction,portfolio,now)
            return replace(proof,catalyst_groups=('same-event',),exposure_gbp=(('issuer:'+proof.issuer_id,D(0)),('catalyst:same-event',D(90))))
        with self.assertRaisesRegex(ValueError,'Aggregate'):self.lane.reserve(key,p,self.now,self.snapshot_verify,self.verify,correlated)

    def test_missing_untyped_stale_or_wrong_mark_scope_rejected(self):
        key,p=self.prepare(self.instruction())
        proof=self.allocation_verify(self.instruction(),p,self.now)
        for callback in (None,lambda *args:True,lambda *args:replace(proof,evidence_refs=()),
                lambda *args:replace(proof,portfolio_fingerprint='0'*64),
                lambda *args:replace(proof,checked_at=self.now-timedelta(seconds=121)),
                lambda *args:replace(proof,exposure_gbp=(('issuer:'+proof.issuer_id,None),('catalyst:'+proof.issuer_id,D(0))))):
            with self.subTest(callback=callback),self.assertRaises(ValueError):self.lane.reserve(key,p,self.now,self.snapshot_verify,self.verify,callback)

    def test_overlimit_current_marks_do_not_block_sell_reduction(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f1','1','90','0')
        key,p=self.prepare(self.instruction(id='reduce',action='sell',cap='0'))
        self.lane.reserve(key,p,self.now,self.snapshot_verify,self.verify,lambda *args:True)
        self.assertEqual(self.lane.get(key)['state'],'reserved')

    def test_exception_reports_durable_deduplicated_and_freeze_portfolio(self):
        key=self.issued();self.lane.report_order(key,'broker1')
        for unused in range(2):
            with self.assertRaises(ValueError):self.lane.report_fill(key,'overrun','1','101','0')
        reports=self.lane.execution_reports();self.assertEqual(len(reports),1)
        self.assertEqual(self.lane.conn.execute('SELECT COUNT(*) FROM fills').fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,'NAV unknown'):self.lane.portfolio()
        # Immutable raw report survives restart and does not mutate cash.
        with DecisionLane(self.path,self.policy,clock=lambda:self.now) as reopened:
            self.assertEqual(len(reopened.execution_reports()),1)
            with self.assertRaises(ValueError):reopened.portfolio()
        self.assertEqual(self.lane._portfolio().available_gbp,D(200))
        self.resolve_report(reports[0],'execution-confirmed')
        self.assertEqual(self.lane.portfolio().available_gbp,D(199))
        self.assertEqual(dict(self.lane.portfolio().holdings)['LSE:AAA:ordinary'],D(1))

    def test_unknown_instruction_and_conflicting_variants_retained(self):
        with self.assertRaises(ValueError):self.lane.report_fill('unknown:1','unknown-execution','1','20','0')
        report=self.lane.execution_reports()[0];self.resolve_report(report)
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f1','1','90','0')
        with self.assertRaises(ValueError):self.lane.report_fill(key,'f1','1','91','0')
        self.assertEqual(len(self.lane.execution_reports()),3)
        with self.assertRaises(ValueError):self.lane.portfolio()
        # Original exact replay resolves only the original, never its variant.
        self.lane.report_fill(key,'f1','1','90','0')
        with self.assertRaises(ValueError):self.lane.portfolio()
        conflict=next(r for r in self.lane.execution_reports() if r['reason']=='Conflicting execution replay')
        self.resolve_report(conflict,id='conflict-resolution')
        self.assertEqual(self.lane.portfolio().available_gbp,D(210))

    def test_late_fill_after_cancel_is_preserved_and_adjusted(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.withdraw(key,'cancel requested');self.cancel(key)
        with self.assertRaises(ValueError):self.lane.report_fill(key,'late','1','90','1')
        report=self.lane.execution_reports()[0]
        self.resolve_report(report,'execution-confirmed')
        self.assertEqual(self.lane.portfolio().available_gbp,D(209))
        self.assertEqual(self.lane.get(key)['state'],'filled')
        self.assertEqual(report['payload'],self.lane.execution_reports()[0]['payload'])

    def test_unrelated_isa_shortfall_cannot_be_silently_charged(self):
        key=self.issued();self.lane.report_order(key,'broker1')
        with self.assertRaises(ValueError):self.lane.report_fill(key,'breach','1','301','0')
        with self.assertRaisesRegex(ValueError,'isolated sleeve'):self.resolve_report(self.lane.execution_reports()[0],'execution-confirmed')
        with self.assertRaises(ValueError):self.lane.portfolio()
        self.assertEqual(self.lane.conn.execute("SELECT value FROM lane_meta WHERE key='cash'").fetchone()[0],'300')

    def test_confirmation_receipt_durable_but_not_restart_authority(self):
        key=self.issued()
        self.assertEqual(self.lane.conn.execute('SELECT COUNT(*) FROM lane_confirmations WHERE key=?',(key,)).fetchone()[0],1)
        with DecisionLane(self.path,self.policy,clock=lambda:self.now) as reopened:
            with self.assertRaisesRegex(ValueError,'confirmation'):reopened.issue(key,self.verify)

    def test_verified_conflicting_execution_correction_preserves_original(self):
        key=self.issued();self.lane.report_order(key,'broker1');self.lane.report_fill(key,'f1','1','90','0')
        original=self.lane.conn.execute('SELECT payload FROM fills WHERE id=?',('f1',)).fetchone()[0]
        with self.assertRaises(ValueError):self.lane.report_fill(key,'f1','1','91','1')
        report=next(r for r in self.lane.execution_reports() if r['reason']=='Conflicting execution replay')
        self.resolve_report(report,'execution-correction-confirmed')
        self.assertEqual(self.lane.portfolio().available_gbp,D(208))
        self.assertEqual(dict(self.lane.portfolio().holdings)['LSE:AAA:ordinary'],D(1))
        self.assertEqual(self.lane.conn.execute('SELECT payload FROM fills WHERE id=?',('f1',)).fetchone()[0],original)
        self.assertEqual(self.lane.conn.execute('SELECT count(*) FROM fill_adjustments').fetchone()[0],1)
        self.lane.report_fill(key,'f1','1','91','1')
        self.assertEqual(self.lane.portfolio().available_gbp,D(208))


if __name__=='__main__':unittest.main()
