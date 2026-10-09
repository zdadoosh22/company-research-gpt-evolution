"""Fictional contract tests, never research/strategy or phone validation."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from alert_contract import (AlertBook, AlertInstruction, ArtifactRef, Confirmation,
                            FreshnessPolicy, GateEvidence, GATES, OrderExposure,
                            PortfolioSnapshot, Quote, Security, VerifiedArtifact)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
        self.security = Security("LSE", "TEST", "ordinary", "GBX", "pence")
        self.research = self.ref("fictional-research", "a")
        self.dossier = self.ref("fictional-dossier", "b")
        self.decision = self.ref("fictional-decision", "c")
        self.policy = self.ref("fictional-policy", "d")
        self.quote = Quote(self.security, Decimal("100"), "ask", self.now, self.ref("fictional-quote", "e"))
        self.instruction = AlertInstruction("trial-1", 1, self.research, self.dossier, self.decision,
            self.policy, self.security, "buy", Decimal("10"), Decimal("11"), self.quote,
            self.now, self.now + timedelta(hours=1), ("A material contrary disclosure",), self.now,
            max_buy_price=Decimal("105"))
        self.portfolio = PortfolioSnapshot(Decimal("300"), ((self.security.key, Decimal("10")),), ())
        self.freshness = FreshnessPolicy(1800, 1800, 1800)
        self.book = AlertBook(); self.book.register(self.instruction)

    def ref(self, ident, letter):
        return ArtifactRef(ident, "v1", letter * 64)

    def evidence(self, portfolio=None, quote=None):
        portfolio = portfolio or self.portfolio; quote = quote or self.quote
        refs = {"research": self.research, "dossier": self.dossier, "decision":self.decision,
                "portfolio_policy": self.policy, "quote": quote.source}
        return tuple(GateEvidence(gate, refs.get(gate, self.ref("fictional-" + gate, "f")),
            self.now, self.now + timedelta(hours=1), "v1", "v1", portfolio.fingerprint,
            self.decision.sha256, self.dossier.sha256, self.book._current("trial-1").instruction.fingerprint,
            quote.fingerprint if gate in {"quote", "activation"} else None) for gate in sorted(GATES))

    def verifier(self, evidence):
        # This is expressly a fake test fixture, not a real artifact reader.
        return VerifiedArtifact(evidence.artifact, "fictional-validation", "fictional-reviewer",
            self.now, "accepted", evidence.decision_version, evidence.dossier_version,
            evidence.portfolio_fingerprint, evidence.decision_sha256, evidence.dossier_sha256, evidence.instruction_fingerprint,
            "satisfied" if evidence.gate == "activation" else "not-applicable", evidence.quote_fingerprint)

    def confirm(self, **overrides):
        values = dict(now=self.now, quote=self.quote, last_successful_monitoring=self.now,
            freshness=self.freshness, portfolio=self.portfolio, evidence=self.evidence(), verifier=self.verifier)
        values.update(overrides)
        return self.book.confirm("trial-1", **values)

    def test_confirmation_is_fifteen_minutes_and_bounded_by_instruction(self):
        confirmation = self.confirm()
        self.assertEqual(confirmation.expires_at, self.now + timedelta(minutes=15))
        book = AlertBook()
        book.register(replace(self.instruction, expires_at=self.now + timedelta(minutes=3)))
        evidence = tuple(replace(x, instruction_fingerprint=book._current("trial-1").instruction.fingerprint) for x in self.evidence())
        confirmation = book.confirm("trial-1", now=self.now, quote=self.quote,
            last_successful_monitoring=self.now, freshness=self.freshness,
            portfolio=self.portfolio, evidence=evidence, verifier=self.verifier)
        self.assertEqual(confirmation.expires_at, self.now + timedelta(minutes=3))

    def test_quote_monitor_and_gate_deadlines_shorten_confirmation(self):
        confirmation = self.confirm(freshness=FreshnessPolicy(90, 1800, 1800))
        self.assertEqual(confirmation.expires_at, self.now + timedelta(seconds=90))
        evidence = self.evidence()
        evidence = tuple(replace(x, valid_until=self.now + timedelta(seconds=60)) if x.gate == "phone" else x for x in evidence)
        self.assertEqual(self.confirm(evidence=evidence).expires_at, self.now + timedelta(seconds=60))

    def test_actual_review_expiry_bounds_confirmation(self):
        proof=lambda item:replace(self.verifier(item),valid_until=self.now+timedelta(seconds=30))
        self.assertEqual(self.confirm(verifier=proof).expires_at,self.now+timedelta(seconds=30))
        with self.assertRaises(ValueError):self.confirm(verifier=lambda item:replace(self.verifier(item),valid_until=self.now))

    def test_missing_or_boolean_gate_proofs_and_verifiers_rejected(self):
        for evidence in (tuple(True for _ in GATES), self.evidence()[:-1], self.evidence() + (self.evidence()[0],)):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError): self.confirm(evidence=evidence)
        with self.assertRaises(ValueError): self.confirm(verifier=lambda _: True)

    def test_verifier_hash_scope_and_check_freshness_rejected(self):
        for bad in (
            lambda x: replace(self.verifier(x), artifact=self.ref("wrong", "a")),
            lambda x: replace(self.verifier(x), decision_sha256="d" * 64),
            lambda x: replace(self.verifier(x), portfolio_fingerprint="a" * 64),
            lambda x: replace(self.verifier(x), verdict="draft"),
            lambda x: replace(self.verifier(x), checked_at=self.now - timedelta(hours=1)),
            lambda x: replace(self.verifier(x), checked_at=self.now + timedelta(seconds=1)),
        ):
            with self.subTest(verifier=bad), self.assertRaises(ValueError): self.confirm(verifier=bad)

    def test_gate_binding_rejects_same_version_different_decision_hash(self):
        evidence = tuple(replace(x, decision_sha256="a" * 64) for x in self.evidence())
        with self.assertRaises(ValueError): self.confirm(evidence=evidence)

    def test_buy_ask_ceiling_and_cost_aware_quantity(self):
        with self.assertRaises(ValueError): self.confirm(quote=replace(self.quote, price=Decimal("106")))
        with self.assertRaises(ValueError): self.confirm(quote=replace(self.quote, kind="last"))
        self.book = AlertBook(); self.book.register(replace(self.instruction, max_gbp_cost=Decimal("9")))
        with self.assertRaises(ValueError): self.confirm()

    def test_other_security_reservations_reduce_cash_and_unknown_orders_block(self):
        order = OrderExposure("pending-other", "LSE:OTHER:ordinary", "buy", "pending", Decimal("295"), Decimal("1"))
        portfolio = PortfolioSnapshot(Decimal("5"), self.portfolio.holdings, (order,))
        with self.assertRaises(ValueError): self.confirm(portfolio=portfolio, evidence=self.evidence(portfolio))
        portfolio = PortfolioSnapshot(Decimal("300"), self.portfolio.holdings, (replace(order, status="unknown"),))
        with self.assertRaises(ValueError): self.confirm(portfolio=portfolio, evidence=self.evidence(portfolio))

    def test_pending_same_security_blocks_duplicate_or_opposing_action(self):
        order = OrderExposure("pending", self.security.key, "sell", "pending", Decimal("0"), Decimal("1"))
        portfolio = PortfolioSnapshot(Decimal("300"), self.portfolio.holdings, (order,))
        with self.assertRaises(ValueError): self.confirm(portfolio=portfolio, evidence=self.evidence(portfolio))

    def test_acknowledgement_never_fills_and_duplicate_does_not_reset_state(self):
        fingerprint = self.portfolio.fingerprint
        self.book.acknowledge("trial-1", now=self.now)
        record = self.book.register(self.instruction)
        self.assertEqual(record.status, "acknowledged")
        self.assertEqual(self.portfolio.fingerprint, fingerprint)
        with self.assertRaises(ValueError): self.book.register(replace(self.instruction, quantity=Decimal("11")))

    def test_withdrawal_invalidation_and_revision_revoke_confirmations(self):
        confirmation = self.confirm()
        self.assertTrue(self.book.confirmation_current(confirmation, now=self.now, portfolio_fingerprint=self.portfolio.fingerprint))
        self.book.invalidate("trial-1", "New contrary disclosure")
        self.assertFalse(self.book.confirmation_current(confirmation, now=self.now, portfolio_fingerprint=self.portfolio.fingerprint))
        self.assertEqual(self.book.register(self.instruction).status, "withdrawn")
        self.book.register(replace(self.instruction, revision=2))
        self.assertEqual(self.book.records[("trial-1", 1)].status, "superseded")
        self.assertFalse(self.book.confirmation_current(confirmation, now=self.now, portfolio_fingerprint=self.portfolio.fingerprint))
        with self.assertRaises(ValueError): self.book.register(replace(self.instruction, revision=4))

    def test_expiry_changed_portfolio_and_forged_confirmation_not_current(self):
        confirmation = self.confirm()
        self.assertFalse(self.book.confirmation_current(confirmation, now=confirmation.expires_at, portfolio_fingerprint=self.portfolio.fingerprint))
        self.assertFalse(self.book.confirmation_current(confirmation, now=self.now, portfolio_fingerprint="a" * 64))
        self.assertFalse(self.book.confirmation_current(replace(confirmation, evidence_digest="a" * 64), now=self.now, portfolio_fingerprint=self.portfolio.fingerprint))

    def test_stale_future_or_regressed_prices_and_monitoring_rejected(self):
        with self.assertRaises(ValueError): self.confirm(now=self.now + timedelta(hours=1))
        with self.assertRaises(ValueError): self.confirm(quote=replace(self.quote, quoted_at=self.now + timedelta(seconds=1)))
        with self.assertRaises(ValueError): self.confirm(last_successful_monitoring=self.now - timedelta(seconds=1))

    def test_sell_requires_condition_attestation_and_owned_shares(self):
        sell_quote = replace(self.quote, kind="bid")
        self.book = AlertBook()
        self.book.register(replace(self.instruction, action="sell", quote=sell_quote,
            max_buy_price=None, sell_condition="Accepted thesis invalidation", max_gbp_cost=Decimal("1")))
        self.assertIsInstance(self.confirm(quote=sell_quote, evidence=self.evidence(quote=sell_quote)), Confirmation)
        with self.assertRaises(ValueError): self.confirm(quote=sell_quote, evidence=self.evidence(quote=sell_quote), verifier=lambda x: replace(self.verifier(x), condition_result="not-applicable"))
        portfolio = PortfolioSnapshot(Decimal("300"), ((self.security.key, Decimal("9")),), ())
        with self.assertRaises(ValueError): self.confirm(quote=sell_quote, portfolio=portfolio, evidence=self.evidence(portfolio))

    def test_identity_schema_and_exact_units_are_required(self):
        for kwargs in ({"schema_version": 2}, {"revision": True}, {"quantity": 1.1},
                       {"invalidation_conditions": []}, {"max_buy_price": None}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): replace(self.instruction, **kwargs)
        with self.assertRaises(ValueError): Security("LSE", "TEST", "ordinary", "GBX", "currency")
        with self.assertRaises(ValueError): replace(self.instruction, quote=replace(self.quote, security=Security("LSE", "TEST", "preferred", "GBX", "pence")))

    def test_instruction_acceptance_cannot_be_reused_for_changed_quantity(self):
        evidence = self.evidence()
        self.book = AlertBook()
        self.book.register(replace(self.instruction, quantity=Decimal("9")))
        with self.assertRaises(ValueError): self.confirm(evidence=evidence)

    def test_expired_acknowledgement_rejected(self):
        with self.assertRaises(ValueError):
            self.book.acknowledge("trial-1", now=self.now + timedelta(hours=1))

    def test_changed_quote_cannot_reuse_acceptance_for_same_artifact(self):
        with self.assertRaises(ValueError):
            self.confirm(quote=replace(self.quote, price=Decimal("99")))
        evidence = self.evidence(quote=replace(self.quote, price=Decimal("99")))
        self.assertIsInstance(self.confirm(quote=replace(self.quote, price=Decimal("99")), evidence=evidence), Confirmation)

    def test_external_quote_hash_and_asof_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.confirm(verifier=lambda x: replace(self.verifier(x), quote_fingerprint="a" * 64) if x.gate == "quote" else self.verifier(x))
        evidence = tuple(replace(x, as_of=self.now - timedelta(seconds=1)) if x.gate == "quote" else x for x in self.evidence())
        with self.assertRaises(ValueError): self.confirm(evidence=evidence)


if __name__ == "__main__": unittest.main()
