import copy
from contextlib import closing
import hashlib
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from paper_study import PaperStudy


class ProspectivePaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.time=datetime(2026,10,8,12,tzinfo=timezone.utc)
        self.study=PaperStudy(Path(self.tmp.name)/'paper.db',clock=lambda:self.time)
        self.protocol={'capital_gbp':'300','arms':{'thesis':{'rule':'explicit fixture event'},'price':{'rule':'explicit fixture price condition'}},'quote_max_age_seconds':120,'response_delay_seconds':60,'benchmark':{'name':'user supplied reference'},'cash_reference':{'method':'supplied unchanged cash, zero interest fixture'}}
        self.study.create_cohort('c',self.protocol)

    def tearDown(self):
        self.study.conn.close();self.tmp.cleanup()

    def tick(self,seconds=1):
        self.time+=timedelta(seconds=seconds)

    def idea(self,id='idea',quantity='2',budget='200',status='accepted',wait_for_response=True):
        payload={'status':status,'security':'LSE:ABC','reason':'fixture reason','evidence':['dated fixture'],'evidence_asof':self.time.isoformat(),'deadline':(self.time+timedelta(hours=1)).isoformat(),'entry_quantity':quantity,'entry_budget_gbp':budget}
        result=self.study.register_opportunity('c',id,payload)
        if wait_for_response:self.tick(60)
        return result

    def quote(self,id='q',price='90',kind='ask',**changes):
        payload={'security':'LSE:ABC','currency':'GBP','unit':'major','native_price':price,'gbp_per_unit':'1','asof':self.time.isoformat(),'source':'manual dated fixture','quote_type':kind,'delay_seconds':0}
        payload.update(changes)
        return self.study.record_quote(id,payload)

    def snapshot(self,marks=None,**kwargs):
        return self.study.snapshot('c',self.time.isoformat(),marks or {},**kwargs)

    def request(self,arm='price',id='exit',quantity='1'):
        return self.study.request_exit('idea',arm,id,{'quantity':quantity,'reason':'fixture condition observed now','evidence':['dated fixture'],'evidence_asof':self.time.isoformat()})

    def test_protocol_is_frozen_amendment_creates_new_cohort(self):
        initial=self.study.create_cohort('c',self.protocol)
        changed=copy.deepcopy(self.protocol);changed['response_delay_seconds']=120
        with self.assertRaises(ValueError):self.study.create_cohort('c',changed)
        amended=self.study.create_cohort('c2',changed)
        self.assertNotEqual(initial['hash'],amended['hash'])
        self.assertEqual(initial['hash'],hashlib.sha256(initial['protocol'].encode()).hexdigest())

    def test_partial_entries_identical_arms_cost_caps_and_replays(self):
        self.idea();self.tick();self.quote()
        self.study.entry_fill('idea','e1','1','q','1')
        self.study.entry_fill('idea','e1','1','q','1')
        snap=self.snapshot({'LSE:ABC':'q'})
        for outcome in snap['arms'].values():
            self.assertEqual(D(outcome['cash_gbp']),D(209))
            self.assertEqual(D(outcome['available_gbp']),D(100))
            self.assertEqual(outcome['open_marks'][0]['quantity'],'1')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e1','1','q','2')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e2','1','q','30')
        self.study.entry_fill('idea','e2','1','q','1')
        self.assertEqual(D(self.snapshot({'LSE:ABC':'q'})['arms']['price']['cash_gbp']),D(118))

    def test_entry_delay_requires_new_executable_quote_after_response(self):
        self.idea(wait_for_response=False);self.quote(id='early')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e','1','early','0')
        self.tick(60)
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e','1','early','0')
        self.quote(id='after_response')
        self.study.entry_fill('idea','e','1','after_response','0')
        self.assertEqual(D(self.snapshot({'LSE:ABC':'after_response'})['arms']['price']['cash_gbp']),D(210))

    def test_hours_days_delays_can_expire_opportunity(self):
        for delay in (3600,86400,259200):
            protocol=copy.deepcopy(self.protocol);protocol['response_delay_seconds']=delay
            cohort='delay-'+str(delay);idea=cohort+'-idea';quote=cohort+'-quote'
            self.study.create_cohort(cohort,protocol)
            payload={'status':'accepted','security':'LSE:ABC','reason':'Synthetic delayed-reading experiment',
                     'evidence':['fictional evidence'],'evidence_asof':self.time.isoformat(),
                     'deadline':(self.time+timedelta(days=2)).isoformat(),'entry_quantity':'1','entry_budget_gbp':'100'}
            self.study.register_opportunity(cohort,idea,payload)
            self.tick(delay);self.quote(id=quote)
            if delay>172800:
                with self.assertRaises(ValueError):self.study.entry_fill(idea,cohort+'-fill','1',quote,'0')
                self.assertEqual(self.study.conn.execute('SELECT spent FROM ideas WHERE id=?',(idea,)).fetchone()[0],'0')
            else:
                self.study.entry_fill(idea,cohort+'-fill','1',quote,'0')
                self.assertEqual(D(self.study.conn.execute('SELECT spent FROM ideas WHERE id=?',(idea,)).fetchone()[0]),D(90))

    def test_overlapping_entries_cannot_use_unlimited_paper_capital(self):
        self.idea(budget='200')
        with self.assertRaises(ValueError):self.idea(id='other',budget='101')
        self.study.cancel_entry('idea')
        self.idea(id='other',budget='300')

    def test_no_backdated_quote_entry_or_expired_commitment(self):
        self.quote(id='old');self.tick();self.idea()
        with self.assertRaises(ValueError):self.study.entry_fill('idea','retro','1','old','0')
        self.tick(3601);self.quote()
        with self.assertRaises(ValueError):self.study.entry_fill('idea','late','1','q','0')

    def test_rejected_and_missed_are_persistent_ineligible_records(self):
        for status in ('rejected','missed'):
            self.idea(id=status,status=status)
            self.quote(id=status)
            with self.assertRaises(ValueError):self.study.entry_fill(status,status,'1',status,'0')
        self.assertEqual(self.study.conn.execute('SELECT COUNT(*) FROM ideas').fetchone()[0],2)

    def test_delayed_exit_partial_fill_cash_lock_and_identical_entry_freeze(self):
        self.idea();self.quote();self.study.entry_fill('idea','e','1','q','0')
        self.request();self.quote(id='too_early',price='70',kind='bid')
        with self.assertRaises(ValueError):self.study.exit_fill('exit','s','0.5','too_early','1')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','late_entry','1','q','0')
        self.tick(60);self.quote(id='sell',price='70',kind='bid')
        self.study.exit_fill('exit','s','0.5','sell','1')
        self.study.exit_fill('exit','s','0.5','sell','1')
        snap=self.snapshot({'LSE:ABC':'sell'})
        self.assertEqual(D(snap['arms']['price']['cash_gbp']),D(244))
        self.assertEqual(D(snap['arms']['price']['available_gbp']),D(210))
        self.assertEqual(snap['arms']['price']['open_marks'][0]['quantity'],'0.5')
        self.assertEqual(snap['arms']['thesis']['open_marks'][0]['quantity'],'1')
        with self.assertRaises(ValueError):self.idea(id='reinvest',budget='211')
        self.tick(3601)
        self.idea(id='reinvest',budget='210')

    def test_exit_quantity_reservation_and_cancelled_request(self):
        self.idea();self.quote();self.study.entry_fill('idea','e','2','q','0')
        self.request(quantity='1.5')
        with self.assertRaises(ValueError):self.request(id='overlap',quantity='1')
        self.study.cancel_exit('exit');self.study.cancel_exit('exit')
        self.request(id='replacement',quantity='2')
        self.tick(60);self.quote(id='sell',kind='bid')
        with self.assertRaises(ValueError):self.study.exit_fill('exit','cancelled','1','sell','0')

    def test_missing_stale_foreign_quotes_are_not_invented(self):
        self.idea();self.quote();self.study.entry_fill('idea','e','1','q','0')
        self.assertIsNone(self.snapshot()['arms']['price']['marked_nav_gbp'])
        self.tick(121)
        self.assertIsNone(self.snapshot({'LSE:ABC':'q'})['arms']['price']['marked_nav_gbp'])
        with self.assertRaises(ValueError):self.quote(id='no_fx',currency='USD')
        self.quote(id='fx',currency='USD',native_price='100',gbp_per_unit='0.80',fx_source='dated FX fixture',fx_asof=self.time.isoformat())
        self.assertEqual(D(self.snapshot({'LSE:ABC':'fx'})['arms']['price']['marked_nav_gbp']),D(290))

    def test_last_price_never_proves_fill_and_wrong_side_rejected(self):
        self.idea();self.quote(kind='last')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e','1','q','0')
        self.quote(id='bid',kind='bid')
        with self.assertRaises(ValueError):self.study.entry_fill('idea','e','1','bid','0')

    def test_references_same_capital_asof_or_missing(self):
        self.assertEqual(self.snapshot()['references']['benchmark']['status'],'missing')
        record={'asof':self.time.isoformat(),'capital_gbp':'300','net_value_gbp':'299','source':'dated reference fixture'}
        self.assertEqual(self.snapshot(benchmark=record)['references']['benchmark']['status'],'supplied')
        with self.assertRaises(ValueError):self.snapshot(benchmark=dict(record,capital_gbp='301'))
        with self.assertRaises(ValueError):self.snapshot(benchmark=dict(record,asof=(self.time-timedelta(seconds=1)).isoformat()))

    def test_open_mark_excludes_exit_fee_and_history_not_reconstructed(self):
        self.idea();self.quote();before=self.time.isoformat();self.tick()
        self.study.entry_fill('idea','e','1','q','1')
        snap=self.snapshot({'LSE:ABC':'q'})
        self.assertEqual(D(snap['arms']['price']['marked_nav_gbp']),D(299))
        self.assertTrue(snap['arms']['price']['future_liquidation_costs_excluded'])
        with self.assertRaises(ValueError):self.study.snapshot('c',before,{'LSE:ABC':'q'})

    def test_database_isolation_and_transaction_failure(self):
        path=Path(self.tmp.name)/'live.db'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE meta(value TEXT)');db.commit()
        with self.assertRaises(ValueError):PaperStudy(path)
        with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='cohorts'").fetchone()[0],0)
        self.idea();self.quote()
        audit=self.study._audit
        def fail(kind,payload):
            if kind=='paired_entry_fill':raise RuntimeError('fixture crash')
            audit(kind,payload)
        self.study._audit=fail
        with self.assertRaises(RuntimeError):self.study.entry_fill('idea','e','1','q','1')
        self.study._audit=audit
        self.assertEqual(D(self.snapshot()['arms']['price']['cash_gbp']),D(300))
        self.study.entry_fill('idea','e','1','q','1')


if __name__=='__main__':unittest.main()
