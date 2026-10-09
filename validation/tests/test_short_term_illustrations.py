import sys
from pathlib import Path
from decimal import Decimal
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from simulate_short_term import illustrate,report

class ExitIllustrationTests(unittest.TestCase):
    def test_gap_stop_is_not_a_loss_cap(self):
        result=illustrate(['100','70','65'],policy='stop-market',entry_cost_rate='0',exit_cost_rate='0')
        self.assertEqual(result['cash_gbp'],'210'); self.assertEqual(result['exit_observation'],1)
    def test_stop_limit_does_not_fabricate_fill_below_limit(self):
        result=illustrate(['100','70','65'],policy='stop-limit',entry_cost_rate='0',exit_cost_rate='0')
        self.assertEqual(result['status'],'open'); self.assertEqual(result['cash_gbp'],'0')
        self.assertEqual(result['open_marked_value_gbp'],'195')
    def test_stop_limit_can_fill_only_after_recovery(self):
        result=illustrate(['100','70','65','92'],policy='stop-limit',entry_cost_rate='0',exit_cost_rate='0')
        self.assertEqual(result['exit_observation'],3); self.assertEqual(result['cash_gbp'],'276')
    def test_delayed_thesis_exit_uses_future_available_quote(self):
        result=illustrate(['100','98','90','80'],policy='thesis',deterioration_at=2,entry_cost_rate='0',exit_cost_rate='0')
        self.assertEqual(result['cash_gbp'],'240')
    def test_missing_manual_response_price_keeps_position_open(self):
        result=illustrate(['100','90'],policy='thesis',deterioration_at=1,response_delay=2)
        self.assertEqual(result['status'],'open'); self.assertTrue(result['future_liquidation_cost_excluded'])
    def test_costs_match_independent_round_trip_arithmetic(self):
        result=illustrate(['100','100'],policy='time')
        expected=Decimal('300')/Decimal('1.0015')*Decimal('0.9985')
        self.assertAlmostEqual(Decimal(result['cash_gbp']),expected,places=24)
        self.assertLess(Decimal(result['cash_gbp']),Decimal(300))
    def test_invalid_policy_delay_rates_and_event_are_rejected(self):
        cases=[{'policy':'invalid'},{'policy':'thesis','response_delay':-1},{'policy':'time','exit_cost_rate':'1'},
               {'policy':'thesis','deterioration_at':8},{'policy':'stop-limit','stop_limit':'96'}]
        for case in cases:
            with self.assertRaises(ValueError): illustrate(['100','99'],**case)
    def test_report_does_not_present_synthetic_paths_as_returns(self):
        result=report(); self.assertIn('not backtest',result['kind'])
        self.assertEqual(len(result['scenarios']),4)
        self.assertTrue(all(not o['actionable'] for s in result['scenarios'] for o in s['outcomes']))

if __name__=='__main__': unittest.main()
