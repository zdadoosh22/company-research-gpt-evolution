import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from finance import ttm, dated_years, discounted_cashflows, xirr, shareholder_path, bank_excess_return, financing_runway


def fixture():
    model = dict(as_of='2026-10-06', forecast_dates=['2027-10-06', '2028-10-06'], base_revenue=100, diluted_shares=10, excess_cash=20, price=10)
    case = dict(cost_of_equity=.12, terminal_growth=.03)
    for k, v in dict(growth=.05, operating_margin=.30, tax_rate=.20, da_ratio=.02, capex_ratio=.02, working_capital_ratio=.10, interest=1, net_borrowing=0, dividend_payout=0, buybacks=0, gross_dilution=0, repurchase_price=10, cash_yield=0).items():
        case[k] = [v, v]
    return model, case


class FinanceTests(unittest.TestCase):
    def test_ttm(self):
        self.assertEqual(ttm(100, 60, 40), 120)
    def test_ttm_incompatible(self):
        with self.assertRaises(ValueError): ttm(100, 60, 40, compatible=False)
    def test_missing_is_not_zero(self):
        with self.assertRaises(ValueError): ttm(100, None, 40)
    def test_dates_are_real(self):
        self.assertAlmostEqual(dated_years('2026-10-06', '2027-10-06'), 1)
        self.assertGreater(dated_years('2027-10-06', '2028-10-06'), 1)
    def test_xirr(self):
        self.assertAlmostEqual(xirr([-100, 110], ['2026-10-06', '2027-10-06']), .1, places=9)
    def test_xirr_dividends(self):
        cf, dates = [-100, 5, 115], ['2026-10-06', '2027-10-06', '2028-10-06']
        result = xirr(cf, dates)
        self.assertAlmostEqual(discounted_cashflows(cf, dates, dates[0], result), 0, places=7)
    def test_xirr_deep_loss_is_bracketed(self):
        dates=['2026-10-06','2027-10-06'];flows=[-100,.00001]
        result=xirr(flows,dates)
        self.assertAlmostEqual(result,-.9999999,places=13)
        self.assertAlmostEqual(discounted_cashflows(flows,dates,dates[0],result),0,places=6)
    def test_xirr_unrepresentable_loss_is_rejected(self):
        with self.assertRaises(ValueError):xirr([-100,1e-30],['2026-10-06','2027-10-06'])
    def test_xirr_rejects_multiple_sign_changes(self):
        with self.assertRaises(ValueError): xirr([-100, 20, -10], ['2026-01-01', '2027-01-01', '2028-01-01'])
    def test_present_horizon_bridge(self):
        model, case = fixture()
        result = shareholder_path(model, case)
        expected = result['horizon_value'] / (1 + case['cost_of_equity']) ** result['holding_years']
        self.assertAlmostEqual(result['current_value'], expected)
    def test_dividend_retention_counted_once(self):
        model, case = fixture()
        case['dividend_payout'] = [.5, .5]
        r = shareholder_path(model, case)
        cash = model['excess_cash'] + sum(x['fcfe'] - x['dividends'] for x in r['rows'])
        self.assertAlmostEqual(r['rows'][-1]['excess_cash'], cash)
        self.assertAlmostEqual(r['current_value'], discounted_cashflows(r['receipts'], model['forecast_dates'], model['as_of'], .12))
    def test_entry_price_reproduces_hurdle(self):
        model, case = fixture()
        r = shareholder_path(model, case)
        price = r['entry_prices']['0.12']
        self.assertAlmostEqual(xirr([-price] + r['receipts'], [model['as_of']] + model['forecast_dates']), .12)
    def test_whatif_preserves_reported_inputs(self):
        model, case = fixture()
        original = copy.deepcopy(case)
        edited = copy.deepcopy(case)
        edited['operating_margin'][1] = .4
        self.assertNotEqual(shareholder_path(model, case)['current_value'], shareholder_path(model, edited)['current_value'])
        self.assertEqual(case, original)
    def test_g_equals_k_rejected(self):
        model, case = fixture()
        case['terminal_growth'] = case['cost_of_equity']
        with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_insufficient_funding_rejected(self):
        model, case = fixture()
        case['buybacks'] = [10000, 0]
        with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_missing_assumption_rejected(self):
        model, case = fixture()
        case['operating_margin'][0] = None
        with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_no_price_withholds_return(self):
        model, case = fixture()
        model['price'] = None
        self.assertIsNone(shareholder_path(model, case)['annualised_return'])
    def test_quote_date_return_and_valuation_date_separate(self):
        model,case=fixture();normal=shareholder_path(model,case);model['price_date']='2026-10-05';earlier=shareholder_path(model,case)
        self.assertEqual(normal['current_value'],earlier['current_value'])
        self.assertLess(earlier['annualised_return'],normal['annualised_return'])
    def test_future_quote_rejected(self):
        model,case=fixture();model['price_date']='2026-10-07'
        with self.assertRaises(ValueError):shareholder_path(model,case)
    def test_buyback_and_separate_claims(self):
        model,case=fixture();case['buybacks']=[5,5];case['gross_dilution']=[.01,.01];r=shareholder_path(model,case)
        expected=10
        for row in r['rows']:expected=expected*1.01**row['fraction']-.5
        self.assertAlmostEqual(r['rows'][-1]['shares'],expected)
        self.assertAlmostEqual(r['rows'][-1]['excess_cash'],20+sum(x['fcfe']-5 for x in r['rows']))
    def test_nonpositive_terminal_fcfe_rejected(self):
        model, case = fixture()
        case['operating_margin'] = [-.3, -.3]
        model['excess_cash'] = 1000
        with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_terminal_fixed_interest_matches_explicit_cashflows(self):
        model, case = fixture()
        r = shareholder_path(model, case)
        # Independent long series: only operating cash grows; coupon stays fixed.
        operating = r['terminal_pre_interest_fcfe']
        interest = case['interest'][-1] * (1-case['tax_rate'][-1])
        explicit = sum((operating*1.03**(t-1)-interest)/1.12**t for t in range(1,501))
        self.assertAlmostEqual(r['terminal_operating_equity'], explicit, places=7)
    def test_borrowing_cannot_manufacture_value(self):
        for amount in [1, -1]:
            model, case = fixture(); case['net_borrowing'][0] = amount
            with self.assertRaisesRegex(ValueError, 'debt, service and claims'):
                shareholder_path(model, case)
    def test_fixed_debt_negative_terminal_growth_rejected(self):
        model, case = fixture(); case['terminal_growth'] = -.01
        with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_negative_capital_inputs_rejected(self):
        for key in ['da_ratio','capex_ratio','working_capital_ratio','interest']:
            model, case = fixture(); case[key][0] = -.01
            with self.assertRaises(ValueError): shareholder_path(model, case)
    def test_nonpositive_security_price_rejected(self):
        for price in [0,-1]:
            model,case = fixture(); model['price']=price
            with self.assertRaises(ValueError): shareholder_path(model,case)
    def test_bank_excess_return(self):
        self.assertAlmostEqual(bank_excess_return(100, .15, .10, .03), 100*.12/.07)
    def test_bank_invalid_capital_assumptions(self):
        with self.assertRaises(ValueError): bank_excess_return(100, .02, .10, .03)
    def test_bank_nonfinite_and_boolean_inputs_rejected(self):
        for i in range(4):
            for bad in [float('inf'),float('nan'),True,None]:
                args=[100,.15,.10,.03];args[i]=bad
                with self.assertRaises(ValueError):bank_excess_return(*args)
    def test_biotech_runway(self):
        self.assertEqual(financing_runway(120, 60, 20), 20)
    def test_biotech_missing_burn(self):
        with self.assertRaises(ValueError): financing_runway(120, None)
    def test_biotech_unfunded(self):
        with self.assertRaises(ValueError): financing_runway(20, 60, 30)


if __name__ == '__main__': unittest.main()
