import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from observation_core import Store, initialize


class ObservationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'sleeve.db'
        initialize(self.path)
        self.store = Store(self.path)
        self.alert = self.store.create_trial_alert({'id': 'trial', 'description': 'fixture'})['id']

    def tearDown(self):
        self.store.conn.close()
        self.tmp.cleanup()

    def buy(self, quantity='2', reserve='100', order_id='b1', ticker='TEST_US_EQ'):
        return self.store.report_order(self.alert, 'buy', ticker, quantity, reserve, order_id)

    def test_unfunded_default_and_fixed_cap(self):
        self.assertFalse(self.store.status()['funded'])
        with self.assertRaises(ValueError):
            self.buy()
        with self.assertRaises(ValueError):
            self.store.confirm_funding('301')
        self.store.confirm_funding()
        self.store.confirm_funding()
        self.assertEqual(self.store.status()['cash_gbp'], '300')
        with self.assertRaises(ValueError):
            self.store.confirm_funding('200')

    def test_partial_fill_reservations_idempotency_and_fees(self):
        self.store.confirm_funding()
        order = self.buy()
        self.assertEqual(self.store.status()['available_gbp'], '200')
        self.store.report_fill(order['id'], 'f1', '0.5', '24', '1')
        self.store.report_fill(order['id'], 'f1', '0.5', '24', '1')
        self.assertEqual(self.store.status()['cash_gbp'], '275')
        self.assertEqual(self.store.status()['reserved_gbp'], '75')
        self.assertEqual(self.store.status()['holdings']['TEST_US_EQ'], '0.5')
        with self.assertRaises(ValueError):
            self.store.report_fill(order['id'], 'f1', '0.5', '25')
        with self.assertRaises(ValueError):
            self.store.report_fill(order['id'], 'f2', '1.5', '76')
        self.assertEqual(self.store.status()['cash_gbp'], '275')
        self.store.report_fill(order['id'], 'f2', '1.5', '73', '1')
        self.assertEqual(self.store.status()['reserved_gbp'], '0')
        self.assertEqual(self.store.status()['cash_gbp'], '201')

    def test_other_cash_and_shares_cannot_be_used(self):
        self.store.confirm_funding()
        self.buy(reserve='250')
        with self.assertRaises(ValueError):
            self.buy(reserve='51', order_id='b2')
        with self.assertRaises(ValueError):
            self.store.report_order(self.alert, 'sell', 'UNRELATED', '1')
        self.store.report_fill('b1', 'bfill', '2', '240')
        sell = self.store.report_order(self.alert, 'sell', 'TEST_US_EQ', '1.5', order_id='s1')
        with self.assertRaises(ValueError):
            self.store.report_order(self.alert, 'sell', 'TEST_US_EQ', '1', order_id='s2')
        self.store.report_fill(sell['id'], 'sfill', '0.5', '70', '0.1')
        self.assertEqual(self.store.status()['cash_gbp'], '129.9')
        self.store.cancel_order(sell['id'])
        self.store.report_order(self.alert, 'sell', 'TEST_US_EQ', '1.5', order_id='s2')

    def test_cancellation_and_duplicate_orders(self):
        self.store.confirm_funding()
        self.buy()
        self.buy()
        self.assertEqual(self.store.status()['reserved_gbp'], '100')
        with self.assertRaises(ValueError):
            self.buy(reserve='101')
        self.store.cancel_order('b1')
        self.store.cancel_order('b1')
        self.assertEqual(self.store.status()['available_gbp'], '300')
        with self.assertRaises(ValueError):
            self.store.report_fill('b1', 'late', '1', '40')

    def test_observation_gate_and_withdrawal_outbox(self):
        with self.assertRaises(ValueError):
            self.store.create_trial_alert({'actionable': True})
        self.store.acknowledge(self.alert)
        self.assertFalse(self.store.refresh_alert(self.alert)['actionable'])
        self.store.withdraw(self.alert, 'New evidence')
        self.store.withdraw(self.alert, 'Repeat')
        self.assertEqual(self.store.refresh_alert(self.alert)['status'], 'withdrawn')
        self.assertEqual(self.store.conn.execute('SELECT COUNT(*) FROM outbox').fetchone()[0], 2)
        with self.assertRaises(ValueError):
            self.store.acknowledge(self.alert)

    def test_quote_identity_and_time_validation(self):
        quote = {'ticker': 'TEST_US_EQ', 'exchange': 'NASDAQ', 'currency': 'USD', 'unit': 'USD/share', 'price': '40', 'quote_type': 'last', 'source': 'manual fixture', 'quote_timestamp': '2020-01-01T12:00:00Z', 'delay_seconds': '900'}
        self.assertFalse(self.store.quote(quote)['actionable'])
        with self.assertRaises(ValueError):
            self.store.quote(dict(quote, unit=''))
        with self.assertRaises(ValueError):
            self.store.quote(dict(quote, quote_timestamp='2999-01-01T00:00:00Z'))
        with self.assertRaises(ValueError):
            self.store.quote(dict(quote, price=float('nan')))
        with self.assertRaises(ValueError):
            self.store.quote(dict(quote, currency='GBP', unit='pence'))
        with self.assertRaises(ValueError):
            self.store.quote(dict(quote, delay_seconds='0.5'))
        self.assertEqual(self.store.quote(quote)['freshness'], 'stale')
        self.assertFalse(self.store.quote(dict(quote, currency='GBX', unit='pence'))['actionable'])

    def test_reopen_durability(self):
        self.store.confirm_funding()
        self.buy()
        self.store.report_fill('b1', 'persisted', '1', '40')
        with Store(self.path) as reopened:
            self.assertEqual(reopened.status()['cash_gbp'], '260')
            self.assertEqual(reopened.status()['reserved_gbp'], '60')
            self.assertFalse(reopened.refresh_alert(self.alert)['actionable'])

    def test_cash_events_idempotence_and_reservations(self):
        self.store.confirm_funding()
        self.buy(reserve='300')
        with self.assertRaises(ValueError):
            self.store.record_cash_event('fee1', 'fee', '1')
        with self.assertRaises(ValueError):
            self.store.record_cash_event('other', 'dividend', '10', 'UNRELATED')
        self.store.report_fill('b1', 'bfill', '2', '100')
        self.store.record_cash_event('div1', 'dividend', '0.25', 'TEST_US_EQ')
        self.store.record_cash_event('div1', 'dividend', '0.25', 'TEST_US_EQ')
        self.store.record_cash_event('fee1', 'fee', '0.10')
        self.assertEqual(self.store.status()['cash_gbp'], '200.15')
        with self.assertRaises(ValueError):
            self.store.record_cash_event('div1', 'dividend', '1', 'TEST_US_EQ')
        with self.assertRaises(ValueError):
            self.store.record_cash_event('deposit', 'deposit', '300')

    def test_nested_transaction_rolls_back_all_and_recovers(self):
        self.store.conn.execute('BEGIN IMMEDIATE')
        self.store.confirm_funding()
        self.buy()
        with self.assertRaises(ValueError):
            self.buy(reserve='301', order_id='bad')
        self.assertTrue(self.store.conn.in_transaction)
        self.assertEqual(self.store.status()['reserved_gbp'], '100')
        self.store.conn.rollback()
        self.assertFalse(self.store.status()['funded'])
        self.assertEqual(self.store.status()['reserved_gbp'], '0')

    def test_expiry_never_creates_trade_authority(self):
        self.store.create_trial_alert({'id': 'old', 'created_at': '2020-01-01T00:00:00Z', 'expires_at': '2020-01-02T00:00:00Z'})
        self.assertEqual(self.store.expire_alerts(), ['old'])
        self.assertEqual(self.store.expire_alerts(), [])
        refreshed = self.store.refresh_alert('old')
        self.assertEqual(refreshed['status'], 'expired')
        self.assertFalse(refreshed['actionable'])
        self.assertIsNone(refreshed['confirmation_expires_at'])
        with self.assertRaises(ValueError):
            self.store.acknowledge('old')
        with self.assertRaises(ValueError):
            self.store.create_trial_alert({'expires_at': '2020-01-01T00:00:00'})
        self.store.create_trial_alert({'id': 'trial', 'description': 'fixture'})

    def test_nav_unknown_without_reliable_gbp_marks(self):
        self.store.confirm_funding()
        self.assertEqual(self.store.status()['net_asset_value_gbp'], '300')
        self.buy()
        self.store.report_fill('b1', 'f1', '2', '100')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.assertIsNone(self.store.status()['weights'])

    def mark(self, currency='GBP', unit='major', price='60', ticker='TEST:TEST_US_EQ', timestamp=None, exchange='TEST'):
        return self.store.quote({'ticker': ticker, 'exchange': exchange, 'currency': currency,
                                 'unit': unit, 'price': price, 'quote_type': 'manual-broker',
                                 'source': 'Manual fixture snapshot', 'delay_seconds': '0',
                                 'quote_timestamp': timestamp or datetime.now(timezone.utc).isoformat()})

    def test_nav_and_cash_weights_from_gbp_and_gbx_marks(self):
        self.store.confirm_funding()
        self.buy(ticker='TEST:TEST_US_EQ')
        self.store.report_fill('b1', 'f1', '2', '100')
        quote = self.mark()
        status = self.store.status()
        self.assertEqual(Decimal(status['net_asset_value_gbp']), Decimal('320'))
        self.assertEqual(Decimal(status['weights']['TEST:TEST_US_EQ']), Decimal('37.5'))
        self.assertEqual(Decimal(status['weights']['cash']), Decimal('62.5'))
        self.assertEqual(status['valuations']['TEST:TEST_US_EQ']['quantity'], '2')
        self.assertEqual(status['valuations']['TEST:TEST_US_EQ']['quote_timestamp'], quote['quote_timestamp'])
        self.mark(currency='GBX', unit='pence', price='6000')
        self.assertEqual(Decimal(self.store.status()['net_asset_value_gbp']), Decimal('320'))
        self.assertEqual(Decimal(self.store.status()['valuations']['TEST:TEST_US_EQ']['price_gbp']), Decimal('60'))

    def test_nav_stale_foreign_and_wrong_security_block(self):
        self.store.confirm_funding()
        self.buy(ticker='TEST:TEST_US_EQ')
        self.store.report_fill('b1', 'f1', '2', '100')
        self.mark(ticker='OTHER')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.mark(currency='USD', unit='USD/share')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.mark(timestamp=(datetime.now(timezone.utc)-timedelta(minutes=31)).isoformat())
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.mark()
        self.assertIsNotNone(self.store.status()['net_asset_value_gbp'])
        self.mark(currency='USD', unit='USD/share')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.assertIsNone(self.store.status()['weights'])

    def test_fx_conversion_is_explicit_and_dated(self):
        self.store.confirm_funding()
        self.buy(ticker='TEST:TEST_US_EQ')
        self.store.report_fill('b1','f1','2','100')
        self.mark(currency='USD',unit='USD/share',price='60')
        fx={'currency':'USD','gbp_per_unit':'0.8','quote_timestamp':datetime.now(timezone.utc).isoformat(),
            'delay_seconds':'0','source':'Synthetic fixture','quote_type':'mid'}
        self.store.fx_quote(dict(fx,currency='EUR'))
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.assertFalse(self.store.fx_quote(fx)['actionable'])
        status=self.store.status()
        self.assertEqual(Decimal(status['net_asset_value_gbp']),Decimal('296'))
        self.assertEqual(status['valuations']['TEST:TEST_US_EQ']['fx']['gbp_per_unit'],'0.8')
        self.store.fx_quote(dict(fx,quote_timestamp=(datetime.now(timezone.utc)-timedelta(minutes=31)).isoformat()))
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        for changed in ({'gbp_per_unit':'0'},{'currency':'GBP'},{'delay_seconds':'0.5'},
                        {'quote_timestamp':'2999-01-01T00:00:00Z'}):
            with self.assertRaises(ValueError): self.store.fx_quote(dict(fx,**changed))

    def test_unexpected_report_is_durable_and_nav_unknown(self):
        self.store.confirm_funding()
        result=self.store.capture_reported_fill('missing','unexpected','1','20')
        self.assertFalse(result['accounted'])
        self.assertTrue(self.store.status()['reconciliation_required'])
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.assertEqual(self.store.status()['cash_gbp'],'300')
        self.store.capture_reported_fill('missing','unexpected','1','20')
        self.assertEqual(len(self.store.status()['reported_fill_exceptions']),1)
        self.store.create_trial_alert({'id':'late-report','description':'fixture'})
        self.store.report_order('late-report','buy','TEST:ABC','1','20',order_id='missing')
        self.assertTrue(self.store.capture_reported_fill('missing','unexpected','1','20')['accounted'])
        self.assertFalse(self.store.status()['reconciliation_required'])
        self.assertEqual(self.store.status()['cash_gbp'],'280')

    def test_over_budget_report_preserved_without_charging_other_cash(self):
        self.store.confirm_funding()
        self.buy(ticker='TEST:ABC')
        result=self.store.capture_reported_fill('b1','excess','2','150')
        self.assertFalse(result['accounted'])
        self.assertEqual(self.store.status()['cash_gbp'],'300')
        self.assertEqual(self.store.status()['holdings'],{})
        self.assertEqual(len(self.store.status()['reported_fill_exceptions']),1)
        with self.assertRaises(ValueError): self.store.capture_reported_fill('b1','invalid','nan','5')
        self.assertEqual(len(self.store.status()['reported_fill_exceptions']),1)

    def test_zero_nav_has_no_weights(self):
        self.assertEqual(self.store.status()['net_asset_value_gbp'], '0')
        self.assertIsNone(self.store.status()['weights'])

    def test_crosslisting_exchange_identity_must_match(self):
        self.store.confirm_funding()
        self.buy(ticker='LSE:ABC:ordinary')
        self.store.report_fill('b1', 'f1', '2', '100')
        self.mark(ticker='NASDAQ:ABC:ordinary', exchange='NASDAQ')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.mark(ticker='LSE:ABC:ordinary', exchange='NASDAQ')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.mark(ticker='LSE:ABC:ordinary', exchange='lse')
        self.assertEqual(Decimal(self.store.status()['net_asset_value_gbp']), Decimal('320'))

    def test_unqualified_holdings_remain_unvalued(self):
        self.store.confirm_funding()
        self.buy()
        self.store.report_fill('b1', 'f1', '2', '100')
        self.mark(ticker='TEST_US_EQ')
        self.assertIsNone(self.store.status()['net_asset_value_gbp'])
        self.assertIn('exchange:ticker', self.store.status()['valuation_unavailable_reasons'][0])

    def test_sell_fees_may_exceed_proceeds_only_with_free_cash(self):
        self.store.confirm_funding()
        self.buy()
        self.store.report_fill('b1', 'bfill', '2', '100')
        self.store.report_order(self.alert, 'sell', 'TEST_US_EQ', '1', order_id='s1')
        self.store.report_order(self.alert, 'buy', 'OTHER', '1', '200', order_id='b2')
        with self.assertRaises(ValueError):
            self.store.report_fill('s1', 'sfill', '1', '0.10', '0.20')
        self.assertEqual(self.store.status()['holdings']['TEST_US_EQ'], '2')
        self.store.cancel_order('b2')
        self.store.report_fill('s1', 'sfill', '1', '0.10', '0.20')
        self.assertEqual(self.store.status()['cash_gbp'], '199.90')
        self.assertEqual(self.store.status()['holdings']['TEST_US_EQ'], '1')

    def test_high_precision_partial_shares_are_never_rounded_away(self):
        self.store.confirm_funding()
        total = '99999999999999999.000000000000000001'
        self.buy(quantity=total)
        self.store.report_fill('b1', 'f1', '99999999999999999', '50')
        self.store.report_fill('b1', 'f2', '0.000000000000000001', '50')
        self.assertEqual(self.store.status()['holdings']['TEST_US_EQ'], total)
        order = self.store.conn.execute("SELECT * FROM orders WHERE id='b1'").fetchone()
        self.assertEqual(order['status'], 'filled')
        self.assertEqual(order['filled_quantity'], total)
        with self.assertRaises(ValueError):
            self.buy(quantity='0.0000000000000000001', order_id='too_precise')

    def test_identifiers_are_validated_before_ledger_write(self):
        self.store.confirm_funding()
        self.buy()
        for bad in (None, '', ' ', 4, ' id '):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.store.report_fill('b1', bad, '1', '40')
        self.assertEqual(self.store.status()['cash_gbp'], '300')
        with self.assertRaises(ValueError):
            self.store.quote({'ticker': [], 'exchange': 'LSE', 'currency': 'GBP', 'unit': 'major',
                              'price': '1', 'quote_type': 'last', 'source': 'manual',
                              'quote_timestamp': '2020-01-01T00:00:00Z', 'delay_seconds':'0'})


if __name__ == '__main__':
    unittest.main()
