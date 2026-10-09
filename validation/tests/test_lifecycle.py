import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from research import init_run, read_json, save_json, sha256, within, check_run, publish, verify_publication


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'methodology').mkdir()
        (self.root / 'methodology' / 'method.md').write_text('test methodology')
        save_json(self.root / 'methodology' / 'current.json', {'version':'test','file':'methodology/method.md'})
        self.run = init_run('test-co', 'Test Co', 'TEST', as_of='2026-10-06', root=self.root)
    def tearDown(self): self.temp.cleanup()
    def test_no_overwrite(self):
        second = init_run('test-co', 'Test Co', 'TEST', as_of='2026-10-06', root=self.root)
        self.assertNotEqual(self.run, second)
    def test_entity_conflict(self):
        with self.assertRaises(ValueError): init_run('test-co','Other Co','T',as_of='2026-10-06',root=self.root)
    def test_path_escape(self):
        with self.assertRaises(ValueError): within(self.root, self.root/'..'/'outside')
    def test_future_publication(self):
        save_json(self.run/'sources.json',[{'id':'s1','publication_date':'2026-10-07'}])
        self.assertTrue(check_run(self.run))
    def test_unread_source(self):
        save_json(self.run/'sources.json',[{'id':'s1','read':False}])
        save_json(self.run/'observations.json',[{'metric':'revenue','value':1,'source_id':'s1','location':'p1','status':'verified-reported'}])
        self.assertTrue(check_run(self.run))
    def test_null_not_zero(self):
        save_json(self.run/'observations.json',[{'metric':'revenue','value':0,'status':'not-found'}])
        self.assertTrue(check_run(self.run))
    def test_source_hash(self):
        file = self.run/'sources'/'source.txt'; file.write_text('original')
        save_json(self.run/'sources.json',[{'id':'s1','archived_file':'sources/source.txt','sha256':sha256(file)}])
        self.assertEqual(check_run(self.run), [])
        file.write_text('changed')
        self.assertTrue(check_run(self.run))
    def test_partial_cannot_publish(self):
        with self.assertRaises(ValueError): publish(self.run, root=self.root)
    def test_publish_and_update_preserve_old(self):
        r=read_json(self.run/'run.json'); r.update(status='complete',continuation='',checks={k:True for k in ['arithmetic','source_traceability','visual_review','workbook_recalculation','export_roundtrip']}); save_json(self.run/'run.json',r)
        for name in ['full-report.pdf','thesis.pdf','valuation.xlsx']: (self.run/'outputs'/name).write_bytes(b'test lifecycle fixture, not an artifact')
        publish(self.run,root=self.root)
        second=init_run('test-co','Test Co','TEST',as_of='2026-10-06',mode='update',predecessor=r['id'],root=self.root)
        self.assertEqual(verify_publication(self.run),[])
        self.assertEqual(read_json(second/'run.json')['predecessor'],r['id'])
        with self.assertRaises(ValueError): publish(self.run,root=self.root)
        (self.run/'outputs'/'thesis.pdf').write_bytes(b'tampered')
        self.assertTrue(verify_publication(self.run))
    def test_duplicate_sources(self):
        save_json(self.run/'sources.json',[{'id':'s1'},{'id':'s1'}])
        self.assertIn('Duplicate source ids',check_run(self.run))
    def test_required_review_blocks_publication(self):
        r=read_json(self.run/'run.json');r.update(status='complete',continuation='',stronger_review_required=True,stronger_review='pending',checks={k:True for k in ['arithmetic','source_traceability','visual_review','workbook_recalculation','export_roundtrip']});save_json(self.run/'run.json',r)
        for name in ['full-report.pdf','thesis.pdf','valuation.xlsx']:(self.run/'outputs'/name).write_bytes(b'lifecycle fixture')
        with self.assertRaisesRegex(ValueError,'stronger review'):publish(self.run,root=self.root)


if __name__=='__main__': unittest.main()
