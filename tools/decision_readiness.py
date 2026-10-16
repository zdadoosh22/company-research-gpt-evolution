"""Offline, fail-closed acceptance verifier for the dormant alert contract.

Registry schema 1: entries contain artifact_id/version/sha256/path and
review_path/review_sha256/gates. Every JSON artifact identifies artifact_id,
version and kind. A review contains id, reviewer, status='accepted', accepted_at,
valid_until, scope, findings, evidence_refs and check_records. References are
{id,path,sha256}; check records are {id,method,outcome='accepted',evidence_ids}.
Scope exactly binds decision/dossier versions and hashes, instruction and
portfolio fingerprints, and (where applicable) quote_fingerprint. Registry
digest is provided by the trusted caller, not read from the registry itself.

Hash integrity and substantive review records are necessary, not proof of truth.
The named reviewer remains responsible for analytical and operational findings.
Current quote/monitoring/activation and portfolio-state facts require a trusted
caller validator returning CurrentAcceptance; absent validation fails closed.
Nothing here enables delivery, broker access, trading or live activation.
"""
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
from pathlib import Path

try:
    from .alert_contract import ArtifactRef, GateEvidence, VerifiedArtifact, stamp, name
except ImportError:
    from alert_contract import ArtifactRef, GateEvidence, VerifiedArtifact, stamp, name

SCOPE_FIELDS = ('decision_version', 'dossier_version', 'decision_sha256',
                'dossier_sha256', 'instruction_fingerprint', 'portfolio_fingerprint',
                'quote_fingerprint')
SCOPED_COVERAGE = frozenset({'security_identity', 'event_window', 'financial_resilience',
    'business_drivers', 'ownership_financing_claims', 'source_facts', 'model_assumptions',
    'material_limitations', 'contrary_evidence'})
CURRENT_GATES = frozenset({'quote', 'monitoring', 'activation', 'portfolio_policy', 'phone', 'operational_trial'})
PHONE_CASES = frozenset({'locked_delivery', 'delayed_reading', 'status_refresh', 'withdrawal', 'acknowledgement'})
TRIAL_CASES = frozenset({'sleep_restart', 'internet_loss', 'quota_exhaustion', 'expired_auth',
    'delayed_reading', 'withdrawal', 'duplicate_delivery', 'partial_fills', 'currency_units', 'unrelated_holdings'})


@dataclass(frozen=True)
class CurrentAcceptance:
    validation_id: str
    checked_at: object
    scope: dict
    condition_result: str = 'not-applicable'


class ArtifactVerifier:
    """Callable usable as AlertBook.confirm(verifier=...). Reads on every call.

    expected_scope is independently supplied from the current instruction and
    reconciled portfolio, not copied from untrusted evidence. max_review_age is
    explicit policy; this module invents no monitoring or review frequency.
    validators[gate](artifact, review, evidence) must attest actual current facts.
    Tests can inject fictional validators; they never certify the real project.
    """
    def __init__(self, root, registry_path, registry_sha256, *, now,
                 expected_scope, max_review_age, validators=None):
        self.root = Path(root).resolve()
        self.registry_path = registry_path
        self.registry_sha256 = ArtifactRef('registry', '1', registry_sha256).sha256
        self.now = stamp(now)
        if not isinstance(max_review_age, timedelta) or max_review_age.total_seconds() <= 0:
            raise ValueError('Positive explicit review age required')
        self.max_review_age = max_review_age
        self.expected_scope = dict(expected_scope)
        if set(self.expected_scope) != set(SCOPE_FIELDS):
            raise ValueError('Complete independent scope required')
        self.validators = dict(validators or {})

    def _path(self, value, *, base=None):
        if not isinstance(value, str) or not value or '\\' in value or ':' in value:
            raise ValueError('Workspace-relative forward-slash path required')
        rel = Path(value)
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Escaping path rejected')
        target = ((base or self.root) / rel).resolve()
        if not target.is_relative_to(self.root) or target.relative_to(self.root).parts[0] not in {'monitoring', 'validation', 'companies', 'methodology'}:
            raise ValueError('Path outside evidence allowlist')
        if any(part.startswith('.') for part in target.relative_to(self.root).parts) or target.suffix.lower() in {'.dpapi', '.env', '.sqlite', '.db'}:
            raise ValueError('Credential or operational state path rejected')
        if not target.is_file(): raise ValueError('Evidence file missing')
        return target

    def _bytes(self, path, digest=None):
        data = path.read_bytes()
        if digest is not None and hashlib.sha256(data).hexdigest() != ArtifactRef('digest', '1', digest).sha256:
            raise ValueError('Evidence hash mismatch')
        return data

    def _json(self, path, digest=None):
        return json.loads(self._bytes(path, digest).decode('utf-8-sig'))

    def _dated(self, record):
        accepted, expiry = stamp(record['accepted_at']), stamp(record['valid_until'])
        if accepted > self.now or expiry <= self.now or expiry <= accepted or self.now - accepted >= self.max_review_age:
            raise ValueError('Review future, stale or expired')

    def _refs(self, refs):
        if not isinstance(refs, list) or not refs: raise ValueError('Substantive evidence references required')
        identities = set()
        for ref in refs:
            rid = name(ref['id'])
            if rid in identities: raise ValueError('Duplicate evidence identity')
            identities.add(rid)
            self._bytes(self._path(ref['path']), ref['sha256'])
        return identities

    def _checks(self, review):
        identities = self._refs(review['evidence_refs'])
        checks = review.get('check_records')
        if not isinstance(checks, list) or not checks: raise ValueError('Review check records required')
        seen = set()
        for check in checks:
            cid = name(check['id']); name(check['method'])
            if cid in seen or check.get('outcome') != 'accepted': raise ValueError('Check record not accepted')
            seen.add(cid)
            refs = check.get('evidence_ids')
            if not isinstance(refs, list) or not refs or not set(refs).issubset(identities):
                raise ValueError('Check has no matching outcome evidence')
        findings = review.get('findings')
        if not isinstance(findings, list): raise ValueError('Explicit findings required')
        for finding in findings:
            name(finding['id']); name(finding['assessment'])
            if not isinstance(finding.get('material'), bool) or finding.get('status') not in {'resolved', 'accepted-limitation'}:
                raise ValueError('Explicit typed finding severity and disposition required')
            if finding.get('material') and finding.get('status') != 'resolved':
                raise ValueError('Unfinished material finding blocks decision')

    def _load(self, ref, gate, entries, *, scope=None):
        rows = [x for x in entries if x.get('artifact_id') == ref.artifact_id and x.get('version') == ref.version]
        if len(rows) != 1: raise ValueError('Unique allowlisted artifact required')
        entry = rows[0]
        if entry.get('sha256') != ref.sha256 or gate not in entry.get('gates', []):
            raise ValueError('Artifact identity or gate mismatch')
        artifact = self._json(self._path(entry['path']), ref.sha256)
        if (artifact.get('artifact_id'), artifact.get('version')) != (ref.artifact_id, ref.version):
            raise ValueError('Artifact embedded identity mismatch')
        review = self._json(self._path(entry['review_path']), entry['review_sha256'])
        if review.get('status') != 'accepted': raise ValueError('Artifact lacks accepted review')
        if review.get('artifact') != {'artifact_id': ref.artifact_id, 'version': ref.version, 'sha256': ref.sha256}:
            raise ValueError('Review does not bind artifact')
        name(review['id']); name(review['reviewer']); self._dated(review); self._checks(review)
        if review.get('scope') != (scope if scope is not None else self.expected_scope): raise ValueError('Review scope mismatch')
        if artifact.get('simulated') is True or artifact.get('origin') in {'fixture', 'simulation'}:
            raise ValueError('Simulated artifact cannot establish readiness')
        return artifact, review

    def _method(self):
        current = self._json(self._path('methodology/current.json'))
        self._bytes(self._path(current['file']), current['sha256'])
        return current

    def _research(self, artifact, entries, scope):
        current = self._method()
        if artifact.get('methodology_sha256') != current['sha256']:
            raise ValueError('Approved methodology not pinned')
        if artifact.get('kind') == 'scoped-company-review':
            add = artifact.get('extension_methodology', {})
            addendum, _ = self._load(ArtifactRef(**add), 'extension_methodology', entries, scope=scope)
            if addendum.get('kind') != 'extension-methodology' or addendum.get('base_methodology_sha256') != current['sha256']:
                raise ValueError('Accepted explicit methodology addendum required')
            if not SCOPED_COVERAGE.issubset(set(addendum.get('required_coverage', []))) or not SCOPED_COVERAGE.issubset(set(artifact.get('coverage', {}))):
                raise ValueError('Decision-sufficient company scope missing')
            for key in SCOPED_COVERAGE: name(artifact['coverage'][key])
            if not artifact.get('label') or artifact.get('status') != 'accepted-scoped':
                raise ValueError('Scoped review must be separately labelled')
            window = artifact['window']
            if stamp(window['reviewed_at']) > self.now or stamp(window['expires_at']) <= self.now or stamp(window['expires_at']) <= stamp(window['reviewed_at']):
                raise ValueError('Scoped window stale or future')
            self._checks(artifact)
            self._refs(artifact['source_facts'])
            for source in artifact['source_facts']:
                if stamp(source['read_at']) > stamp(window['reviewed_at']) or stamp(source['publication_at']) > stamp(source['read_at']) or not source.get('locations'):
                    raise ValueError('Source facts lack dated actual reading locations')
            return
        if artifact.get('kind') != 'published-company-research':
            raise ValueError('Accepted published or explicitly scoped company review required')
        indexpath = self._path(artifact['company_index'])
        index = self._json(indexpath, artifact['company_index_sha256'])
        runpath = self._path(artifact['run_record']); runroot = runpath.parent
        run = self._json(runpath, artifact['run_record_sha256'])
        if runroot.parent.name != 'runs' or runroot.parents[1] != indexpath.parent:
            raise ValueError('Run belongs to another company index')
        if runpath.name != 'run.json' or index.get('latest') != run['id'] or not any(x.get('id') == run['id'] and x.get('status') == 'complete' for x in index.get('runs', [])):
            raise ValueError('Company index has no matching approved publication')
        if index.get('latest_active'):
            raise ValueError('Unfinished successor requires explicit scoped reassessment')
        if run.get('mode') != 'full' or run.get('status') != 'complete' or run.get('continuation'):
            raise ValueError('Partial/pilot/unfinished run cannot establish readiness')
        if run['as_of'] > self.now.date().isoformat(): raise ValueError('Future research as-of')
        if (run.get('methodology_sha256'), run.get('methodology_version')) != (current['sha256'], current['version']):
            raise ValueError('Run methodology identity mismatch')
        if run.get('stronger_review_required') and run.get('stronger_review') != 'passed':
            raise ValueError('Required stronger review unfinished')
        if any(x.get('material') and not x.get('resolved') for x in run.get('review_findings', [])):
            raise ValueError('Material unresolved limitation blocks trading use')
        publication = self._json(self._path('publication.json', base=runroot), artifact['publication_sha256'])
        if stamp(publication['published']) > self.now: raise ValueError('Future publication')
        files = publication['files']
        required = {'run.json', 'sources.json', 'observations.json', 'outputs/full-report.pdf', 'outputs/thesis.pdf', 'outputs/valuation.xlsx'}
        if not required.issubset(files): raise ValueError('Published full analytical package incomplete')
        for path, digest in files.items(): self._bytes(self._path(path, base=runroot), digest)
        sources = self._json(self._path('sources.json', base=runroot))
        observations = self._json(self._path('observations.json', base=runroot))
        sourceids = [s['id'] for s in sources]
        if not sources or len(set(sourceids)) != len(sourceids): raise ValueError('Source register empty or duplicated')
        for source in sources:
            if source.get('publication_date', '') > run['as_of']: raise ValueError('Future research source')
            if source.get('archived_file'):
                path = source['archived_file']
                if files.get(path) != source.get('sha256'): raise ValueError('Source not bound into publication')
                self._bytes(self._path(path, base=runroot), source['sha256'])
        for observation in observations:
            if observation.get('status') == 'verified-reported':
                source = next((s for s in sources if s['id'] == observation.get('source_id')), None)
                if observation.get('value') is None or not source or not source.get('read') or not observation.get('location'):
                    raise ValueError('Unverified reported observation')
            if observation.get('status') in {'not-found', 'inaccessible', 'not-applicable'} and observation.get('value') is not None:
                raise ValueError('Missing source value converted to number')

    def _operational(self, artifact, gate):
        """Executed records supplement reviewer acceptance; never truth by flag."""
        expected = 'actual-device-test' if gate == 'phone' else 'actual-operation-trial'
        if artifact.get('kind') != expected or artifact.get('execution_mode') != 'actual':
            raise ValueError('Actual device/trial evidence required')
        self._refs(artifact['observations'])
        if gate == 'phone':
            if artifact.get('device') != 'iPhone': raise ValueError('Actual iPhone delivery evidence required')
            required = PHONE_CASES
            start, end = stamp(artifact['started_at']), stamp(artifact['ended_at'])
        else:
            start, end = stamp(artifact['started_at']), stamp(artifact['ended_at'])
            if end > self.now or end - start < timedelta(days=14): raise ValueError('Fourteen actual elapsed days required')
            required = TRIAL_CASES
            coverage = artifact['coverage_evaluation']
            name(coverage['assessment']); name(coverage['reviewer'])
            if not isinstance(coverage.get('gaps'), list): raise ValueError('Explicit coverage gaps assessment required')
            for gap in coverage['gaps']:
                name(gap['id']); name(gap['assessment'])
                if gap.get('disposition') != 'accepted-limitation': raise ValueError('Unadmitted operational coverage gap')
            self._refs(coverage['evidence_refs'])
        if start > end or end > self.now: raise ValueError('Future or inverted executed test period')
        records = artifact['executed_cases']
        if not isinstance(records, list) or {x.get('case') for x in records} != required or len(records) != len(required):
            raise ValueError('Required executed operational cases incomplete')
        ids = set()
        for record in records:
            rid = name(record['id']); name(record['method']); name(record['observed_outcome']); name(record['control_response'])
            if rid in ids: raise ValueError('Duplicate executed case identity')
            ids.add(rid)
            if record.get('execution_mode') not in {'actual', 'fault-injection'} or (gate == 'phone' and record.get('execution_mode') != 'actual'):
                raise ValueError('Phone cases must be actual; operational faults must be labelled')
            if not start <= stamp(record['executed_at']) <= end: raise ValueError('Case outside actual test period')
            self._refs(record['evidence_refs'])
            if gate == 'phone':
                name(record['recipient_receipt_id'])
                if stamp(record['received_at']) < stamp(record['executed_at']) or stamp(record['received_at']) > end:
                    raise ValueError('Dated actual device receipt required')

    def __call__(self, evidence):
        if not isinstance(evidence, GateEvidence): raise ValueError('Typed gate evidence required')
        scope = {field: getattr(evidence, field) for field in SCOPE_FIELDS}
        expected = dict(self.expected_scope)
        if evidence.gate not in {'quote', 'activation'}: expected['quote_fingerprint'] = None
        else: ArtifactRef('current-quote', '1', expected['quote_fingerprint'])
        if scope != expected: raise ValueError('Evidence scope mismatch')
        if evidence.as_of > self.now or evidence.valid_until <= self.now:
            raise ValueError('Evidence future or expired')
        registry = self._json(self._path(self.registry_path), self.registry_sha256)
        if registry.get('schema_version') != 1: raise ValueError('Unsupported registry schema')
        artifact, review = self._load(evidence.artifact, evidence.gate, registry['entries'], scope=expected)
        if evidence.gate == 'research': self._research(artifact, registry['entries'], expected)
        if evidence.gate in {'phone', 'operational_trial'}:
            self._operational(artifact, evidence.gate)
        condition = 'not-applicable'; validation_id = review['id']
        if evidence.gate in CURRENT_GATES:
            validator = self.validators.get(evidence.gate)
            if not callable(validator): raise ValueError('Trusted current-state validator required')
            result = validator(artifact, review, evidence)
            if not isinstance(result, CurrentAcceptance): raise ValueError('Typed actual current-state acceptance required')
            name(result.validation_id)
            if result.scope != expected or stamp(result.checked_at) != self.now:
                raise ValueError('Current-state attestation scope/time mismatch')
            condition = result.condition_result
            if evidence.gate == 'activation' and condition != 'satisfied': raise ValueError('Current activation conditions not satisfied')
            validation_id += '/' + result.validation_id
        return VerifiedArtifact(evidence.artifact, validation_id, review['reviewer'], self.now,
            'accepted', evidence.decision_version, evidence.dossier_version,
            evidence.portfolio_fingerprint, evidence.decision_sha256, evidence.dossier_sha256,
            evidence.instruction_fingerprint, condition, evidence.quote_fingerprint, stamp(review['valid_until']))


def project_gates(evidence, *, verifier, now):
    """Read-only view of the existing verifier; never adds registry entries.

    The caller supplies the independent current instruction scope, registry
    digest and actual validators when constructing ArtifactVerifier. A missing
    current validator remains a failure. Engine research records alone cannot
    enter this interface because they are not accepted gate artifacts.
    """
    try:
        from .alert_contract import GATES
    except ImportError:
        from alert_contract import GATES
    now=stamp(now)
    if not isinstance(verifier,ArtifactVerifier) or verifier.now!=now:
        raise ValueError('Current existing artifact verifier required')
    if not isinstance(evidence,(list,tuple)) or any(not isinstance(e,GateEvidence) for e in evidence):
        raise ValueError('Typed gate evidence list required')
    gates=[]
    for gate in sorted(GATES):
        rows=[e for e in evidence if e.gate==gate]
        row=dict(gate=gate,status='evidence incomplete',evidence=[],reason='No version-bound acceptance evidence',valid_until=None)
        if len(rows)>1:row.update(status='invalidated',reason='Conflicting duplicate gate evidence')
        elif rows:
            e=rows[0]
            try:
                verified=verifier(e)
                if verified.artifact!=e.artifact or verified.checked_at!=now or verified.verdict!='accepted':
                    raise ValueError('Verifier outcome inconsistent')
                expiry=min(e.valid_until,verified.valid_until)
                row.update(status='satisfied',evidence=[dict(artifact_id=e.artifact.artifact_id,version=e.artifact.version,sha256=e.artifact.sha256)],
                    reason='Existing current artifact verifier accepted this exact scope',valid_until=expiry.isoformat())
            except (ValueError,KeyError,TypeError,OSError):row.update(status='invalidated',reason='Acceptance evidence changed, expired or lacks current verification')
        gates.append(row)
    return dict(authoritative=False,assessed_at=now.isoformat(),gates=gates,activation='disabled',
        live_recommendations_enabled=False,limitation='Read-only acceptance view; capability activation is a separate operation.')
