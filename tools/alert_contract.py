"""Dormant v1 instruction contract. Pure functions only: no trading or delivery.

This module checks structure, communication validity and externally supplied
evidence identity. It cannot establish research truth, suitability, broker state,
phone delivery or profitability. A verifier must read/hash/check the real accepted
artifacts and their scope. Tests use fictional proofs and certify no investments.
Strategy validation means a defensible experimental case, costs and failure
controls; it does not require or claim statistically proven future profitability.
The live observation coordinator does not enable this contract.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Callable

SCHEMA_VERSION = 1
GATES = frozenset({"research", "dossier", "decision", "portfolio_policy", "quote", "phone",
                   "monitoring", "operational_trial", "strategy_validation", "activation"})


def stamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def amount(value, *, positive=False):
    if isinstance(value, (bool, float)) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Exact decimal input required")
    try:
        result = Decimal(value)
    except Exception:
        raise ValueError("Invalid decimal") from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError("Finite nonnegative amount required")
    return result


def name(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("Nonempty identifier required")
    return value


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    version: str
    sha256: str

    def __post_init__(self):
        name(self.artifact_id); name(self.version)
        if not isinstance(self.sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("Artifact SHA256 required")


@dataclass(frozen=True)
class Security:
    exchange: str
    ticker: str
    share_class: str
    currency: str
    unit: str

    def __post_init__(self):
        for field in (self.exchange, self.ticker, self.share_class): name(field)
        if self.currency not in {"GBP", "GBX", "USD", "EUR", "JPY", "CHF", "CAD", "AUD", "HKD"}:
            raise ValueError("Unsupported explicit trading currency")
        if self.unit != ("pence" if self.currency == "GBX" else "currency"):
            raise ValueError("Currency/unit mismatch")

    @property
    def key(self):
        return self.exchange + ":" + self.ticker + ":" + self.share_class


@dataclass(frozen=True)
class Quote:
    security: Security
    price: Decimal
    kind: str
    quoted_at: datetime
    source: ArtifactRef

    def __post_init__(self):
        if not isinstance(self.security, Security) or not isinstance(self.source, ArtifactRef):
            raise ValueError("Typed exact security and quote artifact required")
        object.__setattr__(self, "price", amount(self.price, positive=True))
        object.__setattr__(self, "quoted_at", stamp(self.quoted_at))
        if self.kind not in {"bid", "ask", "last"}: raise ValueError("Quote kind required")

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class FreshnessPolicy:
    quote_seconds: int
    monitoring_seconds: int
    verification_seconds: int

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in
               (self.quote_seconds, self.monitoring_seconds, self.verification_seconds)):
            raise ValueError("Explicit positive freshness limits required")


@dataclass(frozen=True)
class AlertInstruction:
    alert_id: str
    revision: int
    research: ArtifactRef
    dossier: ArtifactRef
    decision: ArtifactRef
    portfolio_policy: ArtifactRef
    security: Security
    action: str
    quantity: Decimal
    max_gbp_cost: Decimal
    quote: Quote
    created_at: datetime
    expires_at: datetime
    invalidation_conditions: tuple[str, ...]
    last_successful_monitoring: datetime
    max_buy_price: Decimal | None = None
    sell_condition: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        name(self.alert_id)
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported alert schema")
        if type(self.revision) is not int or self.revision < 1: raise ValueError("Positive revision required")
        if any(not isinstance(x, ArtifactRef) for x in
               (self.research, self.dossier, self.decision, self.portfolio_policy)):
            raise ValueError("Versioned research, dossier, decision and policy artifacts required")
        if not isinstance(self.security, Security) or not isinstance(self.quote, Quote) or self.quote.security != self.security:
            raise ValueError("Exact quote security must match instruction")
        if self.action not in {"buy", "sell", "trim"}: raise ValueError("Unsupported action")
        object.__setattr__(self, "quantity", amount(self.quantity, positive=True))
        object.__setattr__(self, "max_gbp_cost", amount(self.max_gbp_cost, positive=self.action == "buy"))
        for field in ("created_at", "expires_at", "last_successful_monitoring"):
            object.__setattr__(self, field, stamp(getattr(self, field)))
        if self.expires_at <= self.created_at or self.quote.quoted_at > self.created_at or self.last_successful_monitoring > self.created_at:
            raise ValueError("Invalid instruction chronology")
        if not isinstance(self.invalidation_conditions, tuple) or not self.invalidation_conditions:
            raise ValueError("Explicit immutable invalidation conditions required")
        for condition in self.invalidation_conditions: name(condition)
        if self.action == "buy":
            object.__setattr__(self, "max_buy_price", amount(self.max_buy_price, positive=True))
            if self.sell_condition is not None: raise ValueError("Buy cannot have a sell condition")
        else:
            name(self.sell_condition)
            if self.max_buy_price is not None: raise ValueError("Sell cannot have a buy ceiling")

    @property
    def fingerprint(self):
        """Bind evidence acceptance to the complete immutable instruction envelope."""
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class OrderExposure:
    order_id: str
    security_key: str
    side: str
    status: str
    reserved_gbp: Decimal
    remaining_quantity: Decimal

    def __post_init__(self):
        name(self.order_id); name(self.security_key)
        if self.side not in {"buy", "sell"} or self.status not in {"pending", "unknown", "filled", "cancelled"}:
            raise ValueError("Explicit order side/status required")
        object.__setattr__(self, "reserved_gbp", amount(self.reserved_gbp))
        object.__setattr__(self, "remaining_quantity", amount(self.remaining_quantity))


@dataclass(frozen=True)
class PortfolioSnapshot:
    available_gbp: Decimal
    holdings: tuple[tuple[str, Decimal], ...]
    orders: tuple[OrderExposure, ...]

    def __post_init__(self):
        object.__setattr__(self, "available_gbp", amount(self.available_gbp))
        if not isinstance(self.holdings, tuple) or not isinstance(self.orders, tuple):
            raise ValueError("Immutable portfolio snapshot required")
        keys = set()
        for key, value in self.holdings:
            name(key)
            if key in keys or not isinstance(value, Decimal): raise ValueError("Unique exact holdings required")
            amount(value); keys.add(key)
        if any(not isinstance(x, OrderExposure) for x in self.orders) or len({x.order_id for x in self.orders}) != len(self.orders):
            raise ValueError("Unique typed order exposures required")

    @property
    def fingerprint(self):
        body = {"available_gbp": str(self.available_gbp),
                "holdings": sorted((key, str(qty)) for key, qty in self.holdings),
                "orders": sorted((x.order_id, x.security_key, x.side, x.status,
                                   str(x.reserved_gbp), str(x.remaining_quantity)) for x in self.orders)}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class GateEvidence:
    gate: str
    artifact: ArtifactRef
    as_of: datetime
    valid_until: datetime
    decision_version: str
    dossier_version: str
    portfolio_fingerprint: str
    decision_sha256: str
    dossier_sha256: str
    instruction_fingerprint: str
    quote_fingerprint: str | None = None

    def __post_init__(self):
        if self.gate not in GATES or not isinstance(self.artifact, ArtifactRef): raise ValueError("Named artifact gate required")
        object.__setattr__(self, "as_of", stamp(self.as_of))
        object.__setattr__(self, "valid_until", stamp(self.valid_until))
        if self.valid_until <= self.as_of: raise ValueError("Evidence validity window required")
        name(self.decision_version); name(self.dossier_version)
        if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
               for value in (self.portfolio_fingerprint, self.decision_sha256, self.dossier_sha256, self.instruction_fingerprint)):
            raise ValueError("Exact portfolio/decision/dossier hash binding required")
        if self.quote_fingerprint is not None and not re.fullmatch(r"[0-9a-f]{64}", self.quote_fingerprint):
            raise ValueError("Invalid quote context hash")


@dataclass(frozen=True)
class VerifiedArtifact:
    """Returned by external real-artifact verifier, never minted by this module."""
    artifact: ArtifactRef
    validation_id: str
    reviewer: str
    checked_at: datetime
    verdict: str
    decision_version: str
    dossier_version: str
    portfolio_fingerprint: str
    decision_sha256: str
    dossier_sha256: str
    instruction_fingerprint: str
    condition_result: str = "not-applicable"
    quote_fingerprint: str | None = None
    valid_until: datetime | None = None


@dataclass(frozen=True)
class Confirmation:
    alert_id: str
    revision: int
    decision: ArtifactRef
    checked_at: datetime
    expires_at: datetime
    portfolio_fingerprint: str
    evidence_digest: str


@dataclass(frozen=True)
class AlertRecord:
    instruction: AlertInstruction
    status: str = "active"
    reason: str | None = None


class AlertBook:
    """Pure in-memory lifecycle; caller persists records atomically when integrating."""
    def __init__(self):
        self.records = {}
        self.latest = {}
        self._confirmations = set()

    def register(self, instruction):
        if not isinstance(instruction, AlertInstruction): raise ValueError("Typed instruction required")
        key = (instruction.alert_id, instruction.revision)
        if key in self.records:
            if self.records[key].instruction != instruction: raise ValueError("Alert/revision identity conflict")
            return self.records[key]
        previous = self.latest.get(instruction.alert_id)
        if instruction.revision != (previous + 1 if previous is not None else 1):
            raise ValueError("Revisions must start at one and increase sequentially")
        if previous is not None:
            old = (instruction.alert_id, previous)
            self.records[old] = replace(self.records[old], status="superseded", reason="New reviewed revision")
        record = AlertRecord(instruction)
        self.records[key] = record
        self.latest[instruction.alert_id] = instruction.revision
        return record

    def _current(self, alert_id):
        return self.records[(alert_id, self.latest[alert_id])]

    def acknowledge(self, alert_id, *, now):
        self.expire(now)
        record = self._current(alert_id)
        if record.status not in {"active", "acknowledged"}: raise ValueError("Inactive alert cannot be acknowledged")
        self.records[(alert_id, record.instruction.revision)] = replace(record, status="acknowledged")
        return self._current(alert_id)  # Never changes holdings or creates a fill.

    def withdraw(self, alert_id, reason):
        name(reason)
        record = self._current(alert_id)
        if record.status == "withdrawn": return record
        self.records[(alert_id, record.instruction.revision)] = replace(record, status="withdrawn", reason=reason)
        return self._current(alert_id)

    def invalidate(self, alert_id, reason):
        return self.withdraw(alert_id, reason)

    def expire(self, now):
        now = stamp(now)
        for key, record in list(self.records.items()):
            if record.status in {"active", "acknowledged"} and now >= record.instruction.expires_at:
                self.records[key] = replace(record, status="expired", reason="Instruction expired")

    def confirm(self, alert_id, *, now, quote, last_successful_monitoring, freshness,
                portfolio, evidence, verifier: Callable[[GateEvidence], VerifiedArtifact]):
        """No bare gate flags. External verifier owns actual evidence acceptance.

        available_gbp is net of existing reservations. Its fingerprint must be
        attested by the external portfolio verifier against the actual ledger.
        """
        now = stamp(now); self.expire(now)
        record = self._current(alert_id); instruction = record.instruction
        if record.status not in {"active", "acknowledged"}: raise ValueError("Alert inactive")
        if not isinstance(quote, Quote) or quote.security != instruction.security or not isinstance(freshness, FreshnessPolicy):
            raise ValueError("Matching typed current quote/freshness required")
        monitor = stamp(last_successful_monitoring)
        if quote.quoted_at > now or monitor > now or now < instruction.created_at:
            raise ValueError("Future freshness timestamps rejected")
        if quote.quoted_at < instruction.quote.quoted_at or monitor < instruction.last_successful_monitoring:
            raise ValueError("Freshness history cannot regress")
        if now >= quote.quoted_at + timedelta(seconds=freshness.quote_seconds) or now >= monitor + timedelta(seconds=freshness.monitoring_seconds):
            raise ValueError("Quote or monitoring stale")
        if not isinstance(portfolio, PortfolioSnapshot): raise ValueError("Current typed portfolio required")
        if any(x.status == "unknown" for x in portfolio.orders): raise ValueError("Ambiguous outstanding order requires reconciliation")
        if any(x.security_key == instruction.security.key and x.status == "pending" for x in portfolio.orders):
            raise ValueError("Outstanding order blocks conflicting or duplicate instruction")
        if instruction.action == "buy":
            if quote.kind != "ask" or quote.price > instruction.max_buy_price: raise ValueError("Executable ask exceeds buy condition")
            if instruction.max_gbp_cost > portfolio.available_gbp: raise ValueError("Insufficient cash after existing reservations")
            if instruction.security.currency in {"GBP", "GBX"}:
                minimum_cost = quote.price * instruction.quantity / (100 if instruction.security.currency == "GBX" else 1)
                if minimum_cost > instruction.max_gbp_cost: raise ValueError("Quantity exceeds total GBP cost ceiling before fees")
        elif quote.kind != "bid" or instruction.quantity > dict(portfolio.holdings).get(instruction.security.key, Decimal(0)):
            raise ValueError("Sell requires current bid and sufficient sleeve-owned shares")
        if not isinstance(evidence, tuple) or any(not isinstance(x, GateEvidence) for x in evidence):
            raise ValueError("Typed artifact evidence required, not gate booleans")
        if len(evidence) != len(GATES) or {x.gate for x in evidence} != GATES:
            raise ValueError("One proof for every required gate required")
        bound_refs = {"research": instruction.research, "dossier": instruction.dossier, "decision": instruction.decision,
                      "portfolio_policy": instruction.portfolio_policy, "quote": quote.source}
        expiry = min(now + timedelta(minutes=15), instruction.expires_at,
                     quote.quoted_at + timedelta(seconds=freshness.quote_seconds),
                     monitor + timedelta(seconds=freshness.monitoring_seconds))
        verified = []
        for item in evidence:
            if (item.decision_version != instruction.decision.version or item.dossier_version != instruction.dossier.version
                    or item.decision_sha256 != instruction.decision.sha256 or item.dossier_sha256 != instruction.dossier.sha256
                    or item.portfolio_fingerprint != portfolio.fingerprint or item.instruction_fingerprint != instruction.fingerprint):
                raise ValueError("Gate proof belongs to another decision/dossier/portfolio")
            if item.gate in bound_refs and item.artifact != bound_refs[item.gate]: raise ValueError("Gate artifact identity mismatch")
            if item.gate in {"quote", "activation"} and item.quote_fingerprint != quote.fingerprint:
                raise ValueError("Exact current quote values must be externally attested")
            if item.as_of > now or item.valid_until <= now: raise ValueError("Gate evidence expired or future-dated")
            if item.gate == "monitoring" and item.as_of != monitor: raise ValueError("Monitoring evidence timestamp mismatch")
            if item.gate == "quote" and item.as_of != quote.quoted_at: raise ValueError("Quote evidence timestamp mismatch")
            proof = verifier(item)
            if not isinstance(proof, VerifiedArtifact) or proof.artifact != item.artifact or proof.verdict != "accepted":
                raise ValueError("External verified artifact acceptance required")
            name(proof.validation_id); name(proof.reviewer)
            checked = stamp(proof.checked_at)
            if proof.valid_until is not None:
                verified_until=stamp(proof.valid_until)
                if verified_until<=now: raise ValueError('Verified artifact acceptance expired')
                expiry=min(expiry,verified_until)
            if checked > now or now >= checked + timedelta(seconds=freshness.verification_seconds): raise ValueError("Artifact verification stale")
            if (proof.decision_version, proof.dossier_version, proof.portfolio_fingerprint, proof.decision_sha256, proof.dossier_sha256, proof.instruction_fingerprint) != (item.decision_version, item.dossier_version, item.portfolio_fingerprint, item.decision_sha256, item.dossier_sha256, item.instruction_fingerprint):
                raise ValueError("Verifier acceptance scope mismatch")
            if proof.quote_fingerprint != item.quote_fingerprint: raise ValueError("Verifier quote scope mismatch")
            if item.gate == "activation" and proof.condition_result != "satisfied":
                raise ValueError("External current instruction-condition attestation required")
            expiry = min(expiry, item.valid_until, checked + timedelta(seconds=freshness.verification_seconds))
            verified.append((item.gate, item.artifact.artifact_id, item.artifact.sha256, proof.validation_id))
        digest = hashlib.sha256(json.dumps(sorted(verified)).encode()).hexdigest()
        confirmation = Confirmation(alert_id, instruction.revision, instruction.decision, now, expiry, portfolio.fingerprint, digest)
        self._confirmations.add(confirmation)
        return confirmation

    def confirmation_current(self, confirmation, *, now, portfolio_fingerprint, instruction_fingerprint=None):
        now = stamp(now); self.expire(now)
        if not isinstance(confirmation, Confirmation) or confirmation not in self._confirmations: return False
        record = self._current(confirmation.alert_id)
        return (record.status in {"active", "acknowledged"} and record.instruction.revision == confirmation.revision
                and (instruction_fingerprint is None or record.instruction.fingerprint==instruction_fingerprint)
                and record.instruction.decision == confirmation.decision
                and confirmation.checked_at <= now < confirmation.expires_at
                and portfolio_fingerprint == confirmation.portfolio_fingerprint)
