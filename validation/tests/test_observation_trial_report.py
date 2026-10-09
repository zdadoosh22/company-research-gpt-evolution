import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from observation_trial_report import summarize


class TrialEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript("CREATE TABLE monitor_state(key TEXT,value TEXT); CREATE TABLE monitor_checks(id TEXT,source TEXT,checked_at TEXT,outcome TEXT,changes_detected INTEGER); INSERT INTO monitor_state VALUES('trial_started_at','2026-10-01T00:00:00+00:00');")
        self.now = datetime(2026,10,16,tzinfo=timezone.utc)

    def test_elapsed_time_and_successes_do_not_certify_acceptance_or_uptime(self):
        self.db.executemany('INSERT INTO monitor_checks VALUES(?,?,?,?,?)',[
            ('a','sec','2026-10-01T08:00:00+00:00','baseline',0),
            ('b','sec','2026-10-03T08:00:00+00:00','unchanged',0),
            ('c','uk','2026-10-01T08:00:00+00:00','failed',0)])
        report = summarize(self.db,self.now)
        self.assertEqual(report['elapsed_wall_days'],15)
        self.assertIsNone(report['uptime_fraction'])
        self.assertFalse(report['actionable'])
        self.assertEqual(report['sources']['sec']['largest_gap_between_checks_seconds'],172800)
        self.assertEqual(report['sources']['sec']['successful_checks'],2)
        self.assertIsNone(report['sources']['uk']['last_success'])
        self.assertEqual(report['acceptance'],'pending-independent-operational-evaluation')

    def test_future_or_ambiguous_evidence_cannot_be_accepted(self):
        for timestamp in ('2026-10-17T00:00:00+00:00','2026-10-01T08:00:00'):
            self.db.execute('DELETE FROM monitor_checks')
            self.db.execute('INSERT INTO monitor_checks VALUES(?,?,?,?,?)',('a','sec',timestamp,'baseline',0))
            with self.assertRaises(ValueError): summarize(self.db,self.now)
