import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from evidence import normalize_amount,compare_observations,available_filings

class EvidenceTests(unittest.TestCase):
 def test_units_and_sign(self):self.assertEqual(normalize_amount(125,1000,currency='USD',sign=-1),-125000)
 def test_missing_never_zero(self):
  with self.assertRaises(ValueError):normalize_amount(None,1000,currency='USD')
 def fact(self,value):return dict(metric='Revenue',period='2026-H1',scope='continuing',currency='USD',unit='million',value=value)
 def test_conflict_not_average(self):
  result=compare_observations(self.fact(100),self.fact(120));self.assertEqual(result['status'],'conflict');self.assertIsNone(result['selected_value'])
 def test_scope_mismatch(self):
  changed=self.fact(100);changed['scope']='total';self.assertEqual(compare_observations(self.fact(100),changed)['status'],'incomparable')
 def test_currency_mismatch(self):
  changed=self.fact(100);changed['currency']='EUR';self.assertEqual(compare_observations(self.fact(100),changed)['status'],'incomparable')
 def test_period_mismatch(self):
  changed=self.fact(100);changed['period']='2026-Q2';self.assertEqual(compare_observations(self.fact(100),changed)['status'],'incomparable')
 def test_agreement(self):self.assertEqual(compare_observations(self.fact(100),self.fact(100))['status'],'agreement')
 def test_amendment_asof(self):
  records=[dict(filed='2026-07-01',form='10-Q',accession='a'),dict(filed='2026-10-07',form='10-Q/A',accession='b')]
  self.assertEqual(len(available_filings(records,'2026-10-06')),1)

if __name__=='__main__':unittest.main()
