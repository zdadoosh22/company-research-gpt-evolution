"""Separate durable paper decision/instruction lane. No delivery or broker calls.

Acceptance callbacks must check actual reviewed artifacts and reconciliation.
They return typed dated scope proofs, never booleans. This lane checks binding
and atomic capital controls; it does not substitute for analytical verification.
Canonical artifact hashing uses json.dumps(sort_keys=True, default=str).
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sqlite3

from alert_contract import AlertBook, AlertInstruction, ArtifactRef, PortfolioSnapshot, OrderExposure, Quote, Security, amount, name, stamp


def canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


def artifact_hash(payload):
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


@dataclass(frozen=True)
class ArtifactAcceptance:
    artifact: ArtifactRef
    validation_id: str
    reviewer: str
    checked_at: datetime
    valid_until: datetime
    scope: dict
    verdict: str


@dataclass(frozen=True)
class PortfolioAcceptance:
    fingerprint: str
    validation_id: str
    reviewer: str
    checked_at: datetime
    valid_until: datetime


@dataclass(frozen=True)
class AllocationAcceptance:
    """Trusted reviewer supplies current marked holdings plus order commitments.

    Group identities and prices must come from read, hash-bound evidence. The
    lane neither guesses cross-listing relationships nor uses entry cost as NAV.
    exposure_gbp contains issuer:<id> and catalyst:<id> totals before this buy.
    """
    instruction_fingerprint: str
    portfolio_fingerprint: str
    issuer_id: str
    catalyst_groups: tuple[str, ...]
    exposure_gbp: tuple[tuple[str, Decimal], ...]
    evidence_refs: tuple[ArtifactRef, ...]
    validation_id: str
    reviewer: str
    checked_at: datetime
    valid_until: datetime


@dataclass(frozen=True)
class LanePolicy:
    capital_cap_gbp: Decimal
    per_idea_cap_gbp: Decimal
    max_new_unreported: int
    verification_seconds: int
    snapshot_seconds: int

    def __post_init__(self):
        cap=amount(self.capital_cap_gbp,positive=True); idea=amount(self.per_idea_cap_gbp,positive=True)
        if cap>300 or idea>cap or type(self.max_new_unreported) is not int or self.max_new_unreported!=1:
            raise ValueError('Explicit contribution cap <=£300, per-idea cap and one-unreported policy required')
        if any(type(v) is not int or v<=0 for v in (self.verification_seconds,self.snapshot_seconds)):
            raise ValueError('Explicit positive freshness policy required')


def _instruction(payload):
    value=json.loads(payload)
    for key in ('research','dossier','decision','portfolio_policy'): value[key]=ArtifactRef(**value[key])
    value['security']=Security(**value['security'])
    quote=value['quote'];quote['security']=Security(**quote['security']);quote['source']=ArtifactRef(**quote['source'])
    value['quote']=Quote(**quote)
    value['invalidation_conditions']=tuple(value['invalidation_conditions'])
    return AlertInstruction(**value)


class DecisionLane:
    def __init__(self,path,policy,clock=None):
        if not isinstance(policy,LanePolicy): raise ValueError('Typed explicit experimental policy required')
        self.policy=policy;self.clock=clock or (lambda:datetime.now(timezone.utc))
        path=Path(path)
        if path.name.casefold()=='operations.sqlite3': raise ValueError('Live operations database prohibited')
        path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(str(path),timeout=30);self.conn.row_factory=sqlite3.Row
        existing={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if existing and 'lane_meta' not in existing:
            self.conn.close();raise ValueError('Existing database belongs to another system')
        self.conn.execute('PRAGMA journal_mode=WAL');self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS lane_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT,version TEXT,kind TEXT,sha256 TEXT,payload TEXT,scope TEXT,PRIMARY KEY(id,version));
        CREATE TABLE IF NOT EXISTS artifact_scopes(id TEXT,version TEXT,scope_hash TEXT,scope TEXT,PRIMARY KEY(id,version,scope_hash));
        CREATE TABLE IF NOT EXISTS instructions(key TEXT PRIMARY KEY,alert_id TEXT,revision INTEGER,security TEXT,payload TEXT,fingerprint TEXT,state TEXT,cash_remaining TEXT,quantity_remaining TEXT,filled_quantity TEXT,spent TEXT,order_id TEXT UNIQUE,pre_portfolio TEXT,reason TEXT,UNIQUE(alert_id,revision));
        CREATE TABLE IF NOT EXISTS fills(id TEXT PRIMARY KEY,key TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS fill_reports(id TEXT PRIMARY KEY,execution_id TEXT,key TEXT,payload TEXT,received_at TEXT);
        CREATE TABLE IF NOT EXISTS fill_suspense(report_id TEXT PRIMARY KEY,reason TEXT);
        CREATE TABLE IF NOT EXISTS report_resolutions(report_id TEXT PRIMARY KEY,resolution TEXT,resolved_at TEXT);
        CREATE TABLE IF NOT EXISTS fill_adjustments(id INTEGER PRIMARY KEY,execution_id TEXT,report_id TEXT UNIQUE,key TEXT,payload TEXT,reconciliation_id TEXT);
        CREATE TABLE IF NOT EXISTS lane_confirmations(receipt_id TEXT PRIMARY KEY,key TEXT,instruction_fingerprint TEXT,payload TEXT,at TEXT);
        CREATE TABLE IF NOT EXISTS holdings(security TEXT PRIMARY KEY,quantity TEXT);
        CREATE TABLE IF NOT EXISTS external_orders(id TEXT PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS reconciliation(id TEXT PRIMARY KEY,key TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT,kind TEXT,payload TEXT);
        ''')
        if 'raw_payload' not in {row[1] for row in self.conn.execute('PRAGMA table_info(artifacts)')}:
            self.conn.execute('ALTER TABLE artifacts ADD COLUMN raw_payload BLOB')
        existing_policy=self.conn.execute("SELECT value FROM lane_meta WHERE key='policy'").fetchone()
        frozen=canonical(asdict(policy))
        if existing_policy and existing_policy[0]!=frozen:
            self.conn.close();raise ValueError('Policy amendment requires a separate new decision cohort/database')
        self.conn.execute("INSERT OR IGNORE INTO lane_meta VALUES('policy',?)",(frozen,));self.conn.commit()

    def __enter__(self): return self
    def __exit__(self,*args): self.conn.close()
    def _now(self): return stamp(self.clock())

    def _atomic(self,action):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            with localcontext() as ctx:
                ctx.prec=80;result=action()
            self.conn.commit();return result
        except Exception:
            self.conn.rollback();raise

    def _audit(self,kind,payload):
        self.conn.execute('INSERT INTO audit(at,kind,payload) VALUES(?,?,?)',(self._now().isoformat(),kind,canonical(payload)))

    def _assert_no_suspense(self):
        if self.conn.execute('SELECT 1 FROM fill_reports f LEFT JOIN report_resolutions r ON r.report_id=f.id WHERE r.report_id IS NULL').fetchone():
            raise ValueError('Unresolved execution reports: portfolio/NAV unknown; reconcile before commitments')

    def execution_reports(self):
        return [dict(row) for row in self.conn.execute('SELECT f.*,s.reason,r.resolution FROM fill_reports f LEFT JOIN fill_suspense s ON s.report_id=f.id LEFT JOIN report_resolutions r ON r.report_id=f.id ORDER BY f.received_at,f.id')]

    def _allocation_proof(self,instruction,portfolio,verifier):
        if not callable(verifier): raise ValueError('Current marked issuer/catalyst allocation verifier required')
        proof=verifier(instruction,portfolio,self._now())
        if not isinstance(proof,AllocationAcceptance) or proof.instruction_fingerprint!=instruction.fingerprint or proof.portfolio_fingerprint!=portfolio.fingerprint:
            raise ValueError('Exact typed current allocation proof required')
        self._proof_time(proof,self.policy.verification_seconds)
        name(proof.issuer_id)
        if not isinstance(proof.catalyst_groups,tuple) or not proof.catalyst_groups or len(set(proof.catalyst_groups))!=len(proof.catalyst_groups):
            raise ValueError('Explicit unique catalyst groups required')
        for group in proof.catalyst_groups:name(group)
        if not isinstance(proof.evidence_refs,tuple) or not proof.evidence_refs or any(not isinstance(ref,ArtifactRef) for ref in proof.evidence_refs):
            raise ValueError('Hash-bound mark and group-mapping evidence required')
        required={'issuer:'+proof.issuer_id}|{'catalyst:'+g for g in proof.catalyst_groups}
        if not isinstance(proof.exposure_gbp,tuple) or len(proof.exposure_gbp)!=len(required):raise ValueError('Complete current group exposures required')
        values=dict(proof.exposure_gbp)
        if set(values)!=required:raise ValueError('Exact issuer/catalyst exposure groups required')
        for exposure in values.values():
            if not isinstance(exposure,Decimal):raise ValueError('Current marked GBP exposure must be exact decimal')
            if amount(exposure)+instruction.max_gbp_cost>amount(self.policy.per_idea_cap_gbp):
                raise ValueError('Aggregate issuer/shared-catalyst paper budget exceeded')
        self._audit('allocation_verified',asdict(proof))
        return proof

    def _proof_time(self,proof,seconds):
        name(proof.validation_id);name(proof.reviewer)
        checked=stamp(proof.checked_at);until=stamp(proof.valid_until);now=self._now()
        if checked>now or now>=until or now>=checked+timedelta(seconds=seconds): raise ValueError('Acceptance proof is stale/future')

    def _artifact_proof(self,ref,kind,scope,verifier):
        if not callable(verifier): raise ValueError('Actual artifact verifier callback required')
        proof=verifier(ref,kind,scope,self._now())
        if not isinstance(proof,ArtifactAcceptance) or proof.artifact!=ref or proof.scope!=scope or proof.verdict!='accepted':
            raise ValueError('Exact typed artifact acceptance required; flags are insufficient')
        self._proof_time(proof,self.policy.verification_seconds)
        return proof

    def register_artifact(self,ref,kind,payload,scope,verifier,raw_bytes=None):
        if not isinstance(ref,ArtifactRef) or kind not in ('research','review','dossier','decision','portfolio_policy','reconciliation'):
            raise ValueError('Typed versioned artifact and explicit kind required')
        raw=canonical(payload).encode() if raw_bytes is None else raw_bytes
        if not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=ref.sha256:
            raise ValueError('Artifact byte hash mismatch')
        if json.loads(raw.decode('utf-8-sig'))!=payload: raise ValueError('Artifact bytes and parsed content differ')
        def action():
            self._artifact_proof(ref,kind,scope,verifier)
            row=self.conn.execute('SELECT * FROM artifacts WHERE id=? AND version=?',(ref.artifact_id,ref.version)).fetchone()
            record=(kind,ref.sha256,canonical(payload),canonical(scope))
            if row:
                if tuple(row[k] for k in ('kind','sha256','payload'))!=record[:3]: raise ValueError('Immutable artifact version conflict')
                self.conn.execute('INSERT OR IGNORE INTO artifact_scopes VALUES(?,?,?,?)',(ref.artifact_id,ref.version,artifact_hash(scope),canonical(scope)))
                return dict(row)
            self.conn.execute('INSERT INTO artifacts(id,version,kind,sha256,payload,scope,raw_payload) VALUES(?,?,?,?,?,?,?)',(ref.artifact_id,ref.version,*record,raw))
            self.conn.execute('INSERT INTO artifact_scopes VALUES(?,?,?,?)',(ref.artifact_id,ref.version,artifact_hash(scope),canonical(scope)))
            self._audit('artifact_accepted',{'id':ref.artifact_id,'version':ref.version,'kind':kind})
            return {'id':ref.artifact_id,'version':ref.version,'sha256':ref.sha256}
        return self._atomic(action)

    @staticmethod
    def scope(instruction,portfolio):
        return {'security_key':instruction.security.key,'instruction_fingerprint':instruction.fingerprint,
                'decision_sha256':instruction.decision.sha256,'dossier_sha256':instruction.dossier.sha256,
                'decision_version':instruction.decision.version,'dossier_version':instruction.dossier.version,
                'portfolio_fingerprint':portfolio.fingerprint}

    def _verify_instruction(self,instruction,scope,verifier):
        if self._now()<instruction.created_at or self._now()>=instruction.expires_at: raise ValueError('Instruction inactive by chronology')
        for kind in ('research','dossier','decision','portfolio_policy'):
            ref=getattr(instruction,kind)
            row=self.conn.execute('SELECT * FROM artifacts WHERE id=? AND version=?',(ref.artifact_id,ref.version)).fetchone()
            scoped=self.conn.execute('SELECT scope FROM artifact_scopes WHERE id=? AND version=? AND scope_hash=?',(ref.artifact_id,ref.version,artifact_hash(scope))).fetchone()
            raw=row['raw_payload'] if row and row['raw_payload'] is not None else canonical(json.loads(row['payload'])).encode() if row else b''
            if not row or row['kind']!=kind or row['sha256']!=ref.sha256 or hashlib.sha256(raw).hexdigest()!=ref.sha256 or json.loads(raw.decode('utf-8-sig'))!=json.loads(row['payload']) or not scoped or json.loads(scoped[0])!=scope:
                raise ValueError('Missing immutable artifact with exact instruction scope')
            self._artifact_proof(ref,kind,scope,verifier)

    def _snapshot_proof(self,portfolio,reconciled_at,verifier):
        if not isinstance(portfolio,PortfolioSnapshot) or not callable(verifier): raise ValueError('Reconciled typed portfolio and verifier required')
        date=stamp(reconciled_at)
        if date>self._now() or self._now()>=date+timedelta(seconds=self.policy.snapshot_seconds): raise ValueError('Reconciliation timestamp stale/future')
        proof=verifier(portfolio,date,self._now())
        if not isinstance(proof,PortfolioAcceptance) or proof.fingerprint!=portfolio.fingerprint: raise ValueError('Verified exact portfolio fingerprint required')
        self._proof_time(proof,self.policy.snapshot_seconds)

    def initialize_portfolio(self,portfolio,reconciled_at,verifier):
        def action():
            self._snapshot_proof(portfolio,reconciled_at,verifier)
            original=self.conn.execute("SELECT value FROM lane_meta WHERE key='initial_portfolio'").fetchone()
            if original:
                if original[0]!=portfolio.fingerprint: raise ValueError('Portfolio cannot reset cash/holdings; explicit reconciliation needed')
                return self._portfolio()
            # Initial available cash is already net of external buy reservations.
            cash=portfolio.available_gbp+sum((o.reserved_gbp for o in portfolio.orders if o.side=='buy' and o.status in ('pending','unknown')),Decimal(0))
            if cash>amount(self.policy.capital_cap_gbp): raise ValueError('Initial reconciled cash exceeds supplied contribution cap')
            self.conn.executemany('INSERT INTO lane_meta VALUES(?,?)',[('initial_portfolio',portfolio.fingerprint),('cash',str(cash))])
            for security,qty in portfolio.holdings:self.conn.execute('INSERT INTO holdings VALUES(?,?)',(security,str(qty)))
            for order in portfolio.orders:self.conn.execute('INSERT INTO external_orders VALUES(?,?)',(order.order_id,canonical(asdict(order))))
            self._audit('portfolio_initialized',{'fingerprint':portfolio.fingerprint})
            return self._portfolio()
        return self._atomic(action)

    def _portfolio(self,exclude=None):
        cash=self.conn.execute("SELECT value FROM lane_meta WHERE key='cash'").fetchone()
        if not cash: raise ValueError('No explicitly reconciled funded portfolio')
        orders=[];reserved=Decimal(0)
        for row in self.conn.execute('SELECT payload FROM external_orders'):
            order=OrderExposure(**json.loads(row[0]));orders.append(order)
            if order.side=='buy' and order.status in ('pending','unknown'):reserved+=order.reserved_gbp
        for row in self.conn.execute("SELECT * FROM instructions WHERE state NOT IN ('planned','filled','cancelled-confirmed')"):
            if row['key']==exclude:continue
            instruction=_instruction(row['payload']);side='buy' if instruction.action=='buy' else 'sell'
            status='pending' if row['order_id'] else 'unknown'
            order=OrderExposure(row['order_id'] or 'lane:'+row['key'],row['security'],side,status,Decimal(row['cash_remaining']),Decimal(row['quantity_remaining']))
            orders.append(order)
            if side=='buy':reserved+=order.reserved_gbp
        holdings=tuple((r['security'],Decimal(r['quantity'])) for r in self.conn.execute('SELECT * FROM holdings ORDER BY security'))
        return PortfolioSnapshot(Decimal(cash[0])-reserved,holdings,tuple(orders))

    def portfolio(self):
        def action():
            self._assert_no_suspense();return self._portfolio()
        return self._atomic(action)
    def get(self,key):
        row=self.conn.execute('SELECT * FROM instructions WHERE key=?',(name(key),)).fetchone()
        if not row:raise ValueError('Unknown instruction')
        return dict(row)

    def plan(self,instruction):
        if not isinstance(instruction,AlertInstruction):raise ValueError('Typed instruction required')
        key=instruction.alert_id+':'+str(instruction.revision)
        def action():
            row=self.conn.execute('SELECT * FROM instructions WHERE key=?',(key,)).fetchone()
            if row:
                if row['fingerprint']!=instruction.fingerprint:raise ValueError('Immutable instruction revision conflict')
                return dict(row)
            previous=self.conn.execute('SELECT * FROM instructions WHERE alert_id=? ORDER BY revision DESC LIMIT 1',(instruction.alert_id,)).fetchone()
            if instruction.revision!=(previous['revision']+1 if previous else 1):raise ValueError('Sequential revisions required')
            if previous and previous['state'] not in ('planned','filled','cancelled-confirmed'):raise ValueError('Prior revision has unresolved exposure; reconcile before superseding')
            if previous and previous['state']=='planned':self.conn.execute("UPDATE instructions SET state='cancelled-confirmed',reason='Superseded before reservation' WHERE key=?",(previous['key'],))
            self.conn.execute('INSERT INTO instructions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,instruction.alert_id,instruction.revision,instruction.security.key,canonical(asdict(instruction)),instruction.fingerprint,'planned','0',str(instruction.quantity),'0','0',None,None,None))
            self._audit('instruction_planned',{'key':key})
            return self.get(key)
        return self._atomic(action)

    def reserve(self,key,portfolio,reconciled_at,snapshot_verifier,artifact_verifier,allocation_verifier=None):
        def action():
            self._assert_no_suspense()
            row=self.get(key);instruction=_instruction(row['payload'])
            if row['state']!='planned':
                if row['state']=='reserved':return row
                raise ValueError('Instruction is not planned')
            self._snapshot_proof(portfolio,reconciled_at,snapshot_verifier)
            current=self._portfolio()
            if current.fingerprint!=portfolio.fingerprint:raise ValueError('Stale snapshot cannot overwrite current capital')
            scope=self.scope(instruction,portfolio);self._verify_instruction(instruction,scope,artifact_verifier)
            if any(o.status=='unknown' or o.security_key==instruction.security.key and o.status=='pending' for o in portfolio.orders):raise ValueError('Unknown/conflicting broker or instruction exposure requires reconciliation')
            outstanding=self.conn.execute("SELECT COUNT(*) FROM instructions WHERE state IN ('reserved','issued','acknowledged')").fetchone()[0]
            if outstanding>=self.policy.max_new_unreported:raise ValueError('Global unreported-instruction limit reached')
            if self.conn.execute("SELECT 1 FROM instructions WHERE security=? AND state NOT IN ('planned','filled','cancelled-confirmed')",(instruction.security.key,)).fetchone():raise ValueError('One outstanding instruction per security')
            if instruction.max_gbp_cost>amount(self.policy.per_idea_cap_gbp):raise ValueError('Supplied per-idea budget cap exceeded')
            if instruction.action=='buy':
                self._allocation_proof(instruction,portfolio,allocation_verifier)
                if instruction.max_gbp_cost>portfolio.available_gbp:raise ValueError('Insufficient unreserved cash')
                reserve=instruction.max_gbp_cost
            else:
                held=dict(portfolio.holdings).get(instruction.security.key,Decimal(0))
                held-=sum((o.remaining_quantity for o in portfolio.orders if o.security_key==instruction.security.key and o.side=='sell' and o.status in ('pending','unknown')),Decimal(0))
                if instruction.quantity>held:raise ValueError('Insufficient unreserved sleeve shares')
                reserve=Decimal(0)
            self.conn.execute("UPDATE instructions SET state='reserved',cash_remaining=?,pre_portfolio=? WHERE key=?",(str(reserve),canonical(scope),key))
            self._audit('instruction_reserved',{'key':key,'portfolio_fingerprint':portfolio.fingerprint})
            return self.get(key)
        return self._atomic(action)

    def issue(self,key,artifact_verifier,*,book=None,confirmation=None,allocation_verifier=None):
        def action():
            self._assert_no_suspense()
            row=self.get(key)
            if row['state'] not in ('reserved','issued','acknowledged'):raise ValueError('Must reserve before issuance')
            scope=json.loads(row['pre_portfolio'])
            if self._portfolio(exclude=key).fingerprint!=scope['portfolio_fingerprint']:raise ValueError('Portfolio changed since reviewed reservation')
            if not isinstance(book,AlertBook) or not book.confirmation_current(confirmation,now=self._now(),
                    portfolio_fingerprint=scope['portfolio_fingerprint'],instruction_fingerprint=row['fingerprint']):
                raise ValueError('Current complete-gate confirmation required before issuance')
            self._verify_instruction(_instruction(row['payload']),scope,artifact_verifier)
            instruction=_instruction(row['payload'])
            if instruction.action=='buy':self._allocation_proof(instruction,self._portfolio(exclude=key),allocation_verifier)
            receipt=canonical(asdict(confirmation))
            self.conn.execute('INSERT OR IGNORE INTO lane_confirmations VALUES(?,?,?,?,?)',(hashlib.sha256(receipt.encode()).hexdigest(),key,row['fingerprint'],receipt,self._now().isoformat()))
            if row['state'] in ('issued','acknowledged'):return row
            self.conn.execute("UPDATE instructions SET state='issued' WHERE key=?",(key,));self._audit('paper_instruction_issued',{'key':key,'delivery':False})
            return self.get(key)
        return self._atomic(action)

    def acknowledge(self,key):
        def action():
            row=self.get(key)
            if row['state']=='acknowledged':return row
            if row['state']!='issued' or self._now()>=_instruction(row['payload']).expires_at:raise ValueError('Cannot acknowledge inactive instruction')
            self.conn.execute("UPDATE instructions SET state='acknowledged' WHERE key=?",(key,));self._audit('acknowledged',{'key':key});return self.get(key)
        return self._atomic(action)

    def report_order(self,key,broker_order_id):
        name(broker_order_id)
        def action():
            row=self.get(key)
            if row['order_id']:
                if row['order_id']!=broker_order_id:raise ValueError('Conflicting broker order report')
                return row
            if row['state'] not in ('issued','acknowledged','withdrawn-awaiting-reconciliation'):raise ValueError('No issued instruction to report')
            state='withdrawn-awaiting-reconciliation' if row['state'].startswith('withdrawn') else 'order_reported'
            self.conn.execute('UPDATE instructions SET state=?,order_id=? WHERE key=?',(state,broker_order_id,key));self._audit('manual_order_reported',{'key':key,'broker_order_id':broker_order_id});return self.get(key)
        return self._atomic(action)

    def report_fill(self,key,execution_id,quantity,gross_gbp,fees_gbp):
        name(key);name(execution_id);quantity=amount(quantity,positive=True);gross=amount(gross_gbp,positive=True);fees=amount(fees_gbp)
        payload={'key':key,'quantity':str(quantity),'gross_gbp':str(gross),'fees_gbp':str(fees)}
        report_id=artifact_hash({'execution_id':execution_id,'payload':payload})
        def retain():
            self.conn.execute('INSERT OR IGNORE INTO fill_reports VALUES(?,?,?,?,?)',(report_id,execution_id,key,canonical(payload),self._now().isoformat()))
        self._atomic(retain)
        def action():
            old=self.conn.execute('SELECT * FROM fills WHERE id=?',(execution_id,)).fetchone()
            if old:
                latest=self.conn.execute('SELECT payload,key FROM fill_adjustments WHERE execution_id=? ORDER BY id DESC LIMIT 1',(execution_id,)).fetchone()
                if old['payload']!=canonical(payload) and (not latest or latest['payload']!=canonical(payload) or latest['key']!=key):raise ValueError('Conflicting execution replay')
                self.conn.execute('INSERT OR IGNORE INTO report_resolutions VALUES(?,?,?)',(report_id,'exact-successful-replay',self._now().isoformat()))
                return self.get(key)
            resolved=self.conn.execute('SELECT resolution FROM report_resolutions WHERE report_id=?',(report_id,)).fetchone()
            if resolved:raise ValueError('Previously reconciled report cannot be reapplied as a new execution')
            row=self.get(key);instruction=_instruction(row['payload'])
            if not row['order_id'] or row['state'] not in ('order_reported','partial_fill','withdrawn-awaiting-reconciliation'):raise ValueError('Unresolved/absent broker order; reconcile before fill')
            remaining=Decimal(row['quantity_remaining'])-quantity
            if remaining<0:raise ValueError('Fill exceeds remaining instruction shares')
            cash=Decimal(self.conn.execute("SELECT value FROM lane_meta WHERE key='cash'").fetchone()[0]);holding=self.conn.execute('SELECT quantity FROM holdings WHERE security=?',(row['security'],)).fetchone();held=Decimal(holding[0]) if holding else Decimal(0)
            reserve=Decimal(row['cash_remaining']);spent=Decimal(row['spent'])
            if instruction.action=='buy':
                cost=gross+fees
                if cost>reserve:raise ValueError('Actual fill exceeds reserved total; reconciliation exception required')
                cash-=cost;held+=quantity;reserve-=cost;spent+=cost
            else:
                if quantity>held or fees-gross>self._portfolio().available_gbp:raise ValueError('Sell exceeds shares/free fee cash')
                cash+=gross-fees;held-=quantity
            state='filled' if not remaining else 'withdrawn-awaiting-reconciliation' if row['state'].startswith('withdrawn') else 'partial_fill'
            if not remaining:reserve=Decimal(0)
            self.conn.execute("UPDATE lane_meta SET value=? WHERE key='cash'",(str(cash),))
            self.conn.execute('INSERT INTO holdings VALUES(?,?) ON CONFLICT(security) DO UPDATE SET quantity=excluded.quantity',(row['security'],str(held)))
            self.conn.execute('UPDATE instructions SET state=?,cash_remaining=?,quantity_remaining=?,filled_quantity=?,spent=? WHERE key=?',(state,str(reserve),str(remaining),str(Decimal(row['filled_quantity'])+quantity),str(spent),key))
            self.conn.execute('INSERT INTO fills VALUES(?,?,?)',(execution_id,key,canonical(payload)))
            self.conn.execute('INSERT OR IGNORE INTO report_resolutions VALUES(?,?,?)',(report_id,'execution-recorded',self._now().isoformat()))
            self._audit('manual_fill_reported',payload);return self.get(key)
        try:return self._atomic(action)
        except ValueError as error:
            def suspend():
                self.conn.execute('INSERT OR IGNORE INTO fill_suspense VALUES(?,?)',(report_id,str(error)))
                self._audit('execution_report_suspended',{'report_id':report_id,'reason':str(error)})
            self._atomic(suspend)
            raise

    def reconcile_execution(self,report_id,reconciliation_id,ref,payload,verifier):
        """Evidence-bound exception resolution; never invent an ISA contribution.

        execution-confirmed applies the retained report exactly, despite an
        instruction ceiling/cancellation breach. rejected-report-confirmed keeps
        the raw report and records evidence that it was not a sleeve execution.
        execution-correction-confirmed applies a verified delta to an already
        accounted execution; the original fill is never overwritten.
        The caller must provide exact pre-adjustment ledger hash and broker ID.
        """
        name(report_id);name(reconciliation_id)
        def action():
            report=self.conn.execute('SELECT * FROM fill_reports WHERE id=?',(report_id,)).fetchone()
            if not report or not self.conn.execute('SELECT 1 FROM fill_suspense WHERE report_id=?',(report_id,)).fetchone():raise ValueError('Known suspended execution report required')
            old=self.conn.execute('SELECT * FROM reconciliation WHERE id=?',(reconciliation_id,)).fetchone()
            if old:
                if old['key']!=report_id or old['payload']!=canonical(payload):raise ValueError('Reconciliation replay conflict')
                return {'report_id':report_id,'resolved':True}
            if self.conn.execute('SELECT 1 FROM report_resolutions WHERE report_id=?',(report_id,)).fetchone():raise ValueError('Report already resolved')
            before=self._portfolio()
            outcome=payload.get('outcome')
            if outcome not in ('execution-confirmed','execution-correction-confirmed','rejected-report-confirmed') or payload.get('report_id')!=report_id or payload.get('before_portfolio_fingerprint')!=before.fingerprint:
                raise ValueError('Exact report and pre-adjustment portfolio required')
            if not isinstance(ref,ArtifactRef) or artifact_hash(payload)!=ref.sha256:raise ValueError('Exact reconciliation evidence hash required')
            name(payload.get('reason'))
            evidence=payload.get('evidence_refs')
            if not isinstance(evidence,list) or not evidence:raise ValueError('Broker evidence references required')
            for source in evidence:ArtifactRef(**source)
            scope={'report_id':report_id,'execution_id':report['execution_id'],'before_portfolio_fingerprint':before.fingerprint,'reconciliation_id':reconciliation_id}
            self._artifact_proof(ref,'reconciliation',scope,verifier)
            if outcome in ('execution-confirmed','execution-correction-confirmed'):
                row=self.get(payload.get('instruction_key',report['key']));instruction=_instruction(row['payload'])
                if payload.get('broker_order_id')!=row['order_id'] or not row['order_id']:raise ValueError('Exact known broker order required')
                recorded=self.conn.execute('SELECT * FROM fills WHERE id=?',(report['execution_id'],)).fetchone()
                old_quantity=old_gross=old_fees=Decimal(0)
                if outcome=='execution-correction-confirmed':
                    if not recorded or recorded['key']!=row['key']:raise ValueError('Correction must bind an accounted execution in the same instruction')
                    latest=self.conn.execute('SELECT payload FROM fill_adjustments WHERE execution_id=? ORDER BY id DESC LIMIT 1',(report['execution_id'],)).fetchone()
                    prior=json.loads(latest[0] if latest else recorded['payload'])
                    if payload.get('prior_execution_sha256')!=artifact_hash(prior):raise ValueError('Correction must bind latest accounted execution content')
                    old_quantity=amount(prior['quantity'],positive=True);old_gross=amount(prior['gross_gbp'],positive=True);old_fees=amount(prior['fees_gbp'])
                elif recorded:raise ValueError('Already-accounted execution conflict requires explicit correction')
                actual=json.loads(report['payload']);qty=amount(actual['quantity'],positive=True);gross=amount(actual['gross_gbp'],positive=True);fees=amount(actual['fees_gbp'])
                cash=Decimal(self.conn.execute("SELECT value FROM lane_meta WHERE key='cash'").fetchone()[0])
                held=dict(before.holdings).get(row['security'],Decimal(0));quantity_delta=qty-old_quantity
                remaining=max(Decimal(0),Decimal(row['quantity_remaining'])-quantity_delta)
                reserve=Decimal(row['cash_remaining']);spent=Decimal(row['spent'])
                if instruction.action=='buy':
                    cost_delta=gross+fees-old_gross-old_fees
                    cash-=cost_delta;held+=quantity_delta;spent+=cost_delta
                    reserve=max(Decimal(0),reserve-cost_delta) if remaining else Decimal(0)
                else:cash+=gross-fees-old_gross+old_fees;held-=quantity_delta
                if cash<0 or held<0:raise ValueError('Actual execution breaches isolated sleeve resources; retain suspense, no unrelated ISA attribution')
                # Other commitments may now exceed remaining sleeve resources.
                other_reservations=sum((o.reserved_gbp for o in self._portfolio(exclude=row['key']).orders if o.side=='buy' and o.status in ('pending','unknown')),Decimal(0))
                if cash<other_reservations+reserve:raise ValueError('Actual execution conflicts with other sleeve commitments; reconcile those first')
                if not remaining:reserve=Decimal(0)
                self.conn.execute("UPDATE lane_meta SET value=? WHERE key='cash'",(str(cash),))
                self.conn.execute('INSERT INTO holdings VALUES(?,?) ON CONFLICT(security) DO UPDATE SET quantity=excluded.quantity',(row['security'],str(held)))
                self.conn.execute('UPDATE instructions SET state=?,cash_remaining=?,quantity_remaining=?,filled_quantity=?,spent=? WHERE key=?',('filled' if not remaining else 'withdrawn-awaiting-reconciliation',str(reserve),str(remaining),str(Decimal(row['filled_quantity'])+quantity_delta),str(spent),row['key']))
                if outcome=='execution-correction-confirmed':
                    self.conn.execute('INSERT INTO fill_adjustments(execution_id,report_id,key,payload,reconciliation_id) VALUES(?,?,?,?,?)',(report['execution_id'],report_id,row['key'],report['payload'],reconciliation_id))
                else:self.conn.execute('INSERT INTO fills VALUES(?,?,?)',(report['execution_id'],row['key'],report['payload']))
            after=self._portfolio()
            self.conn.execute('INSERT INTO reconciliation VALUES(?,?,?)',(reconciliation_id,report_id,canonical(payload)))
            self.conn.execute('INSERT INTO report_resolutions VALUES(?,?,?)',(report_id,reconciliation_id,self._now().isoformat()))
            self._audit('exception_reconciled',{'report_id':report_id,'outcome':outcome,'before':asdict(before),'after':asdict(after)})
            return {'report_id':report_id,'resolved':True,'portfolio_fingerprint':after.fingerprint}
        return self._atomic(action)

    def withdraw(self,key,reason):
        name(reason)
        def action():
            row=self.get(key)
            if row['state'] in ('filled','cancelled-confirmed'):return row
            if row['state']=='planned':
                self.conn.execute("UPDATE instructions SET state='cancelled-confirmed',reason=? WHERE key=?",(reason,key));self._audit('unissued_plan_cancelled',{'key':key,'reason':reason});return self.get(key)
            self.conn.execute("UPDATE instructions SET state='withdrawn-awaiting-reconciliation',reason=? WHERE key=?",(reason,key));self._audit('withdrawn_no_release',{'key':key,'reason':reason});return self.get(key)
        return self._atomic(action)

    def expire(self):
        def action():
            keys=[]
            for row in self.conn.execute("SELECT * FROM instructions WHERE state IN ('reserved','issued','acknowledged','order_reported','partial_fill')").fetchall():
                if self._now()>=_instruction(row['payload']).expires_at:
                    self.conn.execute("UPDATE instructions SET state='withdrawn-awaiting-reconciliation',reason='Expired; execution unknown' WHERE key=?",(row['key'],));keys.append(row['key']);self._audit('expired_no_release',{'key':row['key']})
            return keys
        return self._atomic(action)

    def reconcile_cancel(self,key,reconciliation_id,ref,payload,verifier):
        name(reconciliation_id)
        def action():
            old=self.conn.execute('SELECT * FROM reconciliation WHERE id=?',(reconciliation_id,)).fetchone()
            if old:
                if old['key']!=key or old['payload']!=canonical(payload):raise ValueError('Reconciliation replay conflict')
                return self.get(key)
            row=self.get(key)
            if row['state'] in ('filled','cancelled-confirmed'):raise ValueError('No unresolved remainder')
            if payload.get('outcome') not in ('cancelled-confirmed','nonexecution-confirmed') or payload.get('broker_order_id')!=row['order_id'] or payload.get('filled_quantity')!=row['filled_quantity']:
                raise ValueError('Cancellation must reconcile exact broker order and recorded executions')
            scope={'instruction_fingerprint':row['fingerprint'],'broker_order_id':row['order_id'],'filled_quantity':row['filled_quantity'],'reconciliation_id':reconciliation_id}
            if not isinstance(ref,ArtifactRef) or artifact_hash(payload)!=ref.sha256:raise ValueError('Exact reconciliation evidence hash required')
            self._artifact_proof(ref,'reconciliation',scope,verifier)
            self.conn.execute("UPDATE instructions SET state='cancelled-confirmed',cash_remaining='0',quantity_remaining='0' WHERE key=?",(key,))
            self.conn.execute('INSERT INTO reconciliation VALUES(?,?,?)',(reconciliation_id,key,canonical(payload)));self._audit('reconciled_reservation_released',{'key':key,'id':reconciliation_id});return self.get(key)
        return self._atomic(action)
