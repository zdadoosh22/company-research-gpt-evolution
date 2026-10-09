import sys
import unittest
from decimal import Decimal as D, localcontext, ROUND_UP
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from decision_economics import buy_total,sell_proceeds,derive_entry,price_ceiling,round_trip_break_even,scenario_analysis


def terms(currency='GBP',unit='major',fx='1',fee='0',tax='0',fixed='0'):
    return dict(currency=currency,unit=unit,gbp_per_major_unit=fx,fx_direction='GBP_per_major_unit',fee_rate=fee,tax_rate=tax,fixed_fees_gbp=fixed)


class DecisionEconomicsTests(unittest.TestCase):
    def test_gbx_pence_hundred_factor_and_explicit_units(self):
        result=buy_total('2','150',**terms(currency='GBX',unit='pence'))
        self.assertEqual(D(result['total_gbp']),D('3'))
        with self.assertRaises(ValueError):buy_total('2','150',**terms(currency='GBX'))
        with self.assertRaises(ValueError):buy_total('2','150',**terms(unit='pence'))
        with self.assertRaises(ValueError):buy_total('2','150',**terms(currency='GBX',unit='pence',fx='0.01'))

    def test_foreign_buy_and_asymmetric_sale_with_supplied_charges(self):
        buy=buy_total('3','100',**terms(currency='USD',fx='0.8',fee='0.002',tax='0.01',fixed='1'))
        self.assertEqual(D(buy['gross_gbp']),D('240'))
        self.assertEqual(D(buy['total_gbp']),D('243.88'))
        sell=sell_proceeds('3','110',**terms(currency='USD',fx='0.75',fee='0.003',tax='0.005',fixed='2'))
        self.assertEqual(D(sell['total_gbp']),D('243.52'))

    def test_quantity_step_budget_floor_and_fixed_charge(self):
        quote_terms=terms(fee='0.01',tax='0.005',fixed='2')
        result=derive_entry('300','100','0.1',**quote_terms)
        self.assertEqual(D(result['quantity']),D('2.9'))
        self.assertEqual(D(result['total_gbp']),D('296.35'))
        self.assertEqual(D(result['unspent_gbp']),D('3.65'))
        self.assertGreater(D(buy_total('3','100',**quote_terms)['total_gbp']),300)

    def test_fixed_fees_can_leave_no_affordable_order_and_no_phantom_fee(self):
        for budget in ('0','1','2','2.001'):
            result=derive_entry(budget,'100','1',**terms(fixed='2'))
            self.assertFalse(result['feasible'])
            self.assertEqual(D(result['total_gbp']),0)
            self.assertEqual(D(result['unspent_gbp']),D(budget))

    def test_price_ceiling_rounds_down_native_tick_all_in(self):
        quote_terms=terms(currency='GBX',unit='pence',fee='0.01',fixed='2')
        ceiling=price_ceiling('300','3','0.5',**quote_terms)
        price=D(ceiling['native_price_ceiling'])
        self.assertLessEqual(D(buy_total('3',price,**quote_terms)['total_gbp']),300)
        self.assertGreater(D(buy_total('3',price+D('0.5'),**quote_terms)['total_gbp']),300)
        self.assertFalse(ceiling['actionable'])

    def test_asymmetric_round_trip_break_even_and_next_lower_tick(self):
        buy=terms(currency='USD',fx='0.8',fee='0.01',tax='0.005',fixed='1')
        sell=terms(currency='USD',fx='0.7',fee='0.02',fixed='2')
        result=round_trip_break_even('2','100','0.01',buy,sell)
        target=D(result['exit_native_price'])
        debit=D(buy_total('2','100',**buy)['total_gbp'])
        self.assertGreaterEqual(D(sell_proceeds('2',target,**sell)['total_gbp']),debit)
        self.assertLess(D(sell_proceeds('2',target-D('0.01'),**sell)['total_gbp']),debit)

    def test_no_breakeven_when_proportional_sale_charges_exhaust_proceeds(self):
        result=round_trip_break_even('1','100','0.01',terms(),terms(fee='0.7',tax='0.3'))
        self.assertFalse(result['feasible'])
        self.assertIsNone(result['exit_native_price'])
        self.assertEqual(D(sell_proceeds('1','1',**terms(fixed='2'))['total_gbp']),D('-1'))

    def test_fx_can_turn_native_gain_into_gbp_loss_and_gap_case(self):
        scenarios=[{'name':'native gain GBP loss','entry_native_price':'100','entry_terms':terms(currency='USD',fx='0.8'),'exit_native_price':'110','exit_terms':terms(currency='USD',fx='0.7')},
                   {'name':'gap and expensive exit','entry_native_price':'100','entry_terms':terms(currency='USD',fx='0.8',fixed='1'),'exit_native_price':'70','exit_terms':terms(currency='USD',fx='0.75',fee='0.01',fixed='2')}]
        result=scenario_analysis('3',scenarios)
        self.assertEqual(D(result['scenarios'][0]['gain_loss_gbp']),D('-9'))
        self.assertEqual(D(result['scenarios'][1]['gain_loss_gbp']),D('-87.075'))
        self.assertIsNone(result['probabilities'])

    def test_external_decimal_context_does_not_change_results(self):
        reference=derive_entry('300','7.000000000000000001','0.000000000000000001',**terms(fee='0.0015'))
        with localcontext() as context:
            context.prec=6;context.rounding=ROUND_UP;context.Emax=9;context.Emin=-9
            altered=derive_entry('300','7.000000000000000001','0.000000000000000001',**terms(fee='0.0015'))
        self.assertEqual(reference,altered)
        self.assertLessEqual(D(reference['total_gbp']),D(300))

    def test_invalid_float_bool_nonfinite_extreme_direction_and_steps(self):
        for bad in (1.0,True,'NaN','Infinity','-1','1e1000','1e-1000',None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):buy_total(bad,'100',**terms())
        for step in ('0','-0.01',False):
            with self.assertRaises(ValueError):derive_entry('300','100',step,**terms())
        with self.assertRaises(ValueError):buy_total('1','100',**dict(terms(currency='USD',fx='0.8'),fx_direction='USD_per_GBP'))
        with self.assertRaises(ValueError):buy_total('1','100',**terms(fx='0.8'))
        with self.assertRaises(ValueError):round_trip_break_even('1','100','0.01',terms(currency='USD',fx='0.8'),terms(currency='EUR',fx='0.9'))


if __name__=='__main__':unittest.main()
