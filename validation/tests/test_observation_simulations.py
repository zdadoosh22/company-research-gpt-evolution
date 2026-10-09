"""Deterministic economic simulations, fault injection and SQLite recovery."""
import random
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
from observation_core import Store

D = Decimal


class SleeveSimulations(unittest.TestCase):
    def assert_reference(self, store, cash, holdings, orders):
        status = store.status()
        reserve = sum((o['reserve'] - o['spent'] for o in orders.values()
                       if o['side'] == 'buy' and o['status'] == 'open'), D(0))
        self.assertEqual(D(status['cash_gbp']), cash)
        self.assertEqual(D(status['reserved_gbp']), reserve)
        self.assertEqual(D(status['available_gbp']), cash-reserve)
        self.assertGreaterEqual(cash-reserve, 0)
        actual = {k: D(v) for k, v in status['holdings'].items() if D(v)}
        self.assertEqual(actual, {k: v for k, v in holdings.items() if v})
        for ticker, quantity in holdings.items():
            sell_reserved = sum((D(o['remaining'])/4 for o in orders.values()
                                 if o['side'] == 'sell' and o['ticker'] == ticker and o['status'] == 'open'), D(0))
            self.assertGreaterEqual(quantity-sell_reserved, 0)
        self.assertFalse(status['actionable'])

    def test_eight_seed_manual_sleeve_simulations(self):
        # 2,400 deterministic mixed operations; no market strategy is inferred.
        for seed in range(8):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as tmp:
                rng = random.Random(seed)
                path = Path(tmp)/'simulation.db'
                store = Store(path)
                store.confirm_funding()
                store.create_trial_alert({'id': 'trial'})
                cash, holdings, orders, executions = D(300), {}, {}, []
                try:
                    for step in range(300):
                        action = rng.choice(('buy', 'sell', 'fill', 'cancel', 'replay', 'fee', 'dividend', 'reject'))
                        opened = [(k, o) for k, o in orders.items() if o['status'] == 'open']
                        reserved = sum((o['reserve']-o['spent'] for _, o in opened if o['side']=='buy'), D(0))
                        available = cash-reserved
                        ticker = rng.choice(('LSE:AAA', 'LSE:BBB', 'LSE:CCC'))
                        units, price = rng.randint(1, 8), D(rng.randint(1, 20))
                        oid = f'o{step}'
                        if action == 'buy':
                            reserve = D(units)/4*price+D('0.50')
                            if reserve <= available:
                                store.report_order('trial', 'buy', ticker, str(D(units)/4), str(reserve), oid)
                                orders[oid] = dict(side='buy', ticker=ticker, remaining=units, price=price, reserve=reserve, spent=D(0), status='open')
                        elif action == 'sell':
                            shares_reserved = sum((D(o['remaining'])/4 for _, o in opened if o['side']=='sell' and o['ticker']==ticker), D(0))
                            if D(units)/4 <= holdings.get(ticker, D(0))-shares_reserved:
                                store.report_order('trial', 'sell', ticker, str(D(units)/4), '0', oid)
                                orders[oid] = dict(side='sell', ticker=ticker, remaining=units, price=price, reserve=D(0), spent=D(0), status='open')
                        elif action == 'fill' and opened:
                            oid, order = rng.choice(opened)
                            fill_units = rng.randint(1, order['remaining'])
                            quantity, fees = D(fill_units)/4, D('0.01')
                            gross = quantity*order['price']
                            args = (oid, f'e{step}', str(quantity), str(gross), str(fees))
                            store.report_fill(*args)
                            executions.append(args)
                            sign = 1 if order['side']=='buy' else -1
                            holdings[order['ticker']] = holdings.get(order['ticker'], D(0))+sign*quantity
                            cash += -(gross+fees) if sign==1 else gross-fees
                            if sign==1:
                                order['spent'] += gross+fees
                            order['remaining'] -= fill_units
                            if not order['remaining']:
                                order['status'] = 'filled'
                        elif action == 'cancel' and opened:
                            oid, order = rng.choice(opened)
                            store.cancel_order(oid)
                            store.cancel_order(oid)
                            order['status'] = 'cancelled'
                        elif action == 'replay' and executions:
                            args = rng.choice(executions)
                            store.report_fill(*args)
                            with self.assertRaises(ValueError):
                                store.report_fill(*args[:-1], '999')
                        elif action == 'fee' and available >= D('0.01'):
                            store.record_cash_event(f'fee{step}', 'fee', '0.01')
                            cash -= D('0.01')
                        elif action == 'dividend' and holdings.get(ticker, D(0)):
                            store.record_cash_event(f'div{step}', 'dividend', '0.05', ticker)
                            store.record_cash_event(f'div{step}', 'dividend', '0.05', ticker)
                            cash += D('0.05')
                        elif action == 'reject':
                            with self.assertRaises(ValueError):
                                store.report_order('trial', 'sell', 'LSE:UNRELATED', '1')
                            with self.assertRaises(ValueError):
                                store.report_order('trial', 'buy', ticker, '1', str(available+1))
                        if step % 37 == 0:
                            store.conn.close()
                            store = Store(path)
                        self.assert_reference(store, cash, holdings, orders)
                finally:
                    store.conn.close()

    def test_fault_after_fill_writes_rolls_back_all_state(self):
        with tempfile.TemporaryDirectory() as tmp, Store(Path(tmp)/'fault.db') as store:
            store.confirm_funding()
            store.create_trial_alert({'id':'trial'})
            store.report_order('trial','buy','LSE:ABC','1','100','b')
            before = store.status()
            event = store._event
            def fail(kind, payload):
                if kind == 'manual_fill_reported':
                    raise RuntimeError('Injected failure after accounting writes')
                event(kind, payload)
            store._event = fail
            with self.assertRaises(RuntimeError):
                store.report_fill('b','fill','1','90','1')
            self.assertEqual(store.status(), before)
            self.assertEqual(store.conn.execute('SELECT COUNT(*) FROM fills').fetchone()[0],0)
            store._event = event
            store.report_fill('b','fill','1','90','1')
            store.report_fill('b','fill','1','90','1')
            self.assertEqual(store.status()['cash_gbp'],'209')

    def test_process_exit_with_uncommitted_fill_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'crash.db'
            with Store(path) as store:
                store.confirm_funding()
                store.create_trial_alert({'id':'trial'})
                store.report_order('trial','buy','LSE:ABC','1','100','b')
            script = 'import os,sys;sys.path.insert(0,sys.argv[1]);from observation_core import Store;s=Store(sys.argv[2]);s.conn.execute("BEGIN IMMEDIATE");s.report_fill("b","fill","1","90","1");os._exit(17)'
            result = subprocess.run([sys.executable,'-B','-c',script,str(TOOLS),str(path)],capture_output=True)
            self.assertEqual(result.returncode,17, result.stderr)
            with Store(path) as store:
                self.assertEqual(store.status()['cash_gbp'],'300')
                self.assertEqual(store.status()['holdings'],{})
                self.assertEqual(store.status()['reserved_gbp'],'100')
                store.report_fill('b','fill','1','90','1')
                self.assertEqual(store.status()['cash_gbp'],'209')

    def test_status_is_consistent_when_other_connection_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'snapshot.db'
            with Store(path) as reader, Store(path) as writer:
                reader.confirm_funding()
                reader.create_trial_alert({'id':'trial'})
                reader.report_order('trial','buy','LSE:ABC','2','100','b')
                fired = []
                def commit_during_read(sql):
                    if sql == 'SELECT * FROM holdings' and not fired:
                        fired.append(True)
                        writer.report_fill('b','f','1','40')
                reader.conn.set_trace_callback(commit_during_read)
                snapshot = reader.status()
                reader.conn.set_trace_callback(None)
                self.assertTrue(fired)
                self.assertEqual(snapshot['cash_gbp'],'300')
                self.assertEqual(snapshot['reserved_gbp'],'100')
                self.assertEqual(snapshot['holdings'],{})
                self.assertEqual(reader.status()['cash_gbp'],'260')


if __name__ == '__main__':
    unittest.main()
