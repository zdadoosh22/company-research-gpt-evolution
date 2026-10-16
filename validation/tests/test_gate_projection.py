"""Read-only projection of the existing verifier, with fictional evidence."""
import unittest
from datetime import timedelta
import test_decision_readiness as fixtures
from decision_readiness import project_gates


class GateProjectionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReadinessTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_exact_current_verification_and_tamper_regression(self):
        f=self.f;ref=f.add();e=f.evidence(ref);v=f.verifier()
        first=project_gates([e],verifier=v,now=f.now)
        self.assertEqual(len(first['gates']),10)
        self.assertEqual(next(g for g in first['gates'] if g['gate']=='dossier')['status'],'satisfied')
        self.assertFalse(first['live_recommendations_enabled'])
        f.save(f.entries[0]['path'],'tampered')
        second=project_gates([e],verifier=v,now=f.now)
        self.assertEqual(next(g for g in second['gates'] if g['gate']=='dossier')['status'],'invalidated')

    def test_duplicate_and_missing_actual_validator_fail_closed(self):
        f=self.f;ref=f.add();e=f.evidence(ref)
        p=project_gates([e,e],verifier=f.verifier(),now=f.now)
        self.assertEqual(next(g for g in p['gates'] if g['gate']=='dossier')['status'],'invalidated')
        ref=f.add('monitoring','monitoring');e=f.evidence(ref,'monitoring')
        p=project_gates([e],verifier=f.verifier(),now=f.now)
        self.assertEqual(next(g for g in p['gates'] if g['gate']=='monitoring')['status'],'invalidated')

    def test_stale_verifier_or_user_checkbox_is_not_acceptance(self):
        f=self.f
        with self.assertRaises(ValueError):project_gates([],verifier=f.verifier(),now=f.now+timedelta(seconds=1))
        with self.assertRaises(ValueError):project_gates([{'gate':'research','satisfied':True}],verifier=f.verifier(),now=f.now)
