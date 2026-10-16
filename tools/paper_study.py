"""Isolated prospective paper records, not a broker simulator or trading signal.

Inputs supply rules, quotes, costs and FX evidence. No market data, model calls,
automatic fills or live ledger writes. Each exit arm is a separate constrained
copy of the same portfolio. Missing observations remain missing.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from decimal import Decimal, localcontext
from pathlib import Path


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Explicit nonempty text required')
    return value


def number(value, positive=False):
    if isinstance(value, (bool, float)):
        raise ValueError('Use exact decimal strings')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or positive and result == 0:
        raise ValueError('Invalid nonnegative number')
    if result.adjusted() >= 18 or result.as_tuple().exponent < -18:
        raise ValueError('Maximum input precision: 18 integer and fractional digits')
    return result


def stamp(value):
    result = datetime.fromisoformat(text(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    return result.astimezone(timezone.utc)


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


class PaperStudy:
    def __init__(self, path, clock=None):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.conn = sqlite3.connect(str(path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        existing={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if existing and 'paper_meta' not in existing:
            self.conn.close()
            raise ValueError('Use a separate paper-study database; existing database belongs to another system')
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS paper_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT OR IGNORE INTO paper_meta VALUES('format','prospective-paper-v1');
        CREATE TABLE IF NOT EXISTS cohorts(id TEXT PRIMARY KEY,created TEXT NOT NULL,protocol TEXT NOT NULL,hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS arms(cohort TEXT REFERENCES cohorts(id),name TEXT,cash TEXT NOT NULL,PRIMARY KEY(cohort,name));
        CREATE TABLE IF NOT EXISTS ideas(id TEXT PRIMARY KEY,cohort TEXT REFERENCES cohorts(id),registered TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,quantity TEXT NOT NULL,budget TEXT NOT NULL,filled TEXT NOT NULL,spent TEXT NOT NULL,entry_open INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,received TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS positions(idea TEXT REFERENCES ideas(id),arm TEXT,quantity TEXT NOT NULL,exit_cash TEXT NOT NULL,PRIMARY KEY(idea,arm));
        CREATE TABLE IF NOT EXISTS exits(id TEXT PRIMARY KEY,idea TEXT REFERENCES ideas(id),arm TEXT,requested TEXT NOT NULL,payload TEXT NOT NULL,quantity TEXT NOT NULL,filled TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS executions(id TEXT PRIMARY KEY,kind TEXT NOT NULL,known TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,cohort TEXT REFERENCES cohorts(id),asof TEXT NOT NULL,payload TEXT NOT NULL);
        ''')
        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.conn.close()

    def _now(self):
        return stamp(self.clock().isoformat())

    def _write(self, action):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            with localcontext() as ctx:
                ctx.prec = 80
                result = action()
            self.conn.commit()
            return result
        except Exception:
            self.conn.rollback()
            raise

    def _audit(self, kind, payload):
        self.conn.execute('INSERT INTO audit(at,kind,payload) VALUES(?,?,?)', (self._now().isoformat(), kind, dump(payload)))

    def _row(self, table, id):
        row = self.conn.execute('SELECT * FROM '+table+' WHERE id=?', (text(id),)).fetchone()
        if row is None:
            raise ValueError('Unknown '+table+' record')
        return row

    def _protocol(self, cohort):
        row = self._row('cohorts', cohort)
        if hashlib.sha256(row['protocol'].encode()).hexdigest() != row['hash']:
            raise ValueError('Frozen protocol integrity failure')
        return json.loads(row['protocol'])

    def _replay(self, table, id, payload):
        row = self.conn.execute('SELECT * FROM '+table+' WHERE id=?', (text(id),)).fetchone()
        if row:
            if row['payload'] != dump(payload):
                raise ValueError('Conflicting record ID')
            return dict(row)
        return None

    def create_cohort(self, id, protocol):
        protocol = json.loads(dump(protocol))
        capital = number(protocol['capital_gbp'], True)
        if capital > 300:
            raise ValueError('Paper contribution exceeds £300')
        for field in ('quote_max_age_seconds', 'response_delay_seconds'):
            if type(protocol[field]) is not int or protocol[field] < 0:
                raise ValueError('Explicit nonnegative integer timing parameters required')
        if not isinstance(protocol['arms'], dict) or len(protocol['arms']) < 2:
            raise ValueError('At least two named exit arms required')
        for arm, rule in protocol['arms'].items():
            text(arm)
            if not isinstance(rule, dict) or not rule:
                raise ValueError('Each arm needs an explicit frozen rule record')
        if not protocol.get('benchmark') or not protocol.get('cash_reference'):
            raise ValueError('Preselected benchmark and cash reference assumptions required')
        payload = dump(protocol)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        def action():
            existing = self.conn.execute('SELECT * FROM cohorts WHERE id=?', (text(id),)).fetchone()
            if existing:
                if existing['protocol'] != payload:
                    raise ValueError('Amendments require a new cohort ID and protocol hash')
                return dict(existing)
            self.conn.execute('INSERT INTO cohorts VALUES(?,?,?,?)', (id, self._now().isoformat(), payload, digest))
            for arm in protocol['arms']:
                self.conn.execute('INSERT INTO arms VALUES(?,?,?)', (id, arm, str(capital)))
            self._audit('cohort_registered', {'id': id, 'protocol_hash': digest})
            return dict(self._row('cohorts', id))
        return self._write(action)

    def _available(self, cohort, arm, asof=None):
        cash = Decimal(self.conn.execute('SELECT cash FROM arms WHERE cohort=? AND name=?', (cohort, arm)).fetchone()[0])
        reserved = sum((Decimal(r['budget'])-Decimal(r['spent']) for r in self.conn.execute('SELECT * FROM ideas WHERE cohort=? AND entry_open=1', (cohort,))), Decimal(0))
        locked = Decimal(0)
        for row in self.conn.execute('SELECT p.exit_cash,i.payload FROM positions p JOIN ideas i ON p.idea=i.id WHERE i.cohort=? AND p.arm=?', (cohort, arm)):
            if stamp(json.loads(row['payload'])['deadline']) > (asof or self._now()):
                locked += Decimal(row['exit_cash'])
        return cash-reserved-locked

    def register_opportunity(self, cohort, id, payload):
        payload = json.loads(dump(payload))
        if payload['status'] not in ('accepted', 'rejected', 'missed'):
            raise ValueError('Record accepted, rejected or missed status')
        text(payload['reason']); text(payload['security'])
        if len(payload['security'].split(':')) not in (2,3) or any(not x.strip() for x in payload['security'].split(':')):
            raise ValueError('Exact exchange:ticker[:class] security required')
        if stamp(payload['evidence_asof']) > self._now() or not payload.get('evidence'):
            raise ValueError('Contemporaneous evidence and its actual date required')
        quantity = number(payload['entry_quantity'], True) if payload['status']=='accepted' else Decimal(0)
        budget = number(payload['entry_budget_gbp'], True) if payload['status']=='accepted' else Decimal(0)
        def action():
            self._protocol(cohort)
            existing = self._replay('ideas', id, payload)
            if existing:
                if existing['cohort'] != cohort:
                    raise ValueError('Opportunity ID belongs to another cohort')
                return existing
            if payload['status']=='accepted':
                # Older same-ID records replay above with their frozen terms.
                if budget > Decimal('100'):
                    raise ValueError('Accepted paper idea exceeds the £100 per-idea experimental ceiling')
                if stamp(payload['deadline']) <= self._now():
                    raise ValueError('Prospective deadline must be in the future')
                for arm in self._protocol(cohort)['arms']:
                    if budget > self._available(cohort, arm):
                        raise ValueError('Insufficient common capital after commitments and locked exit proceeds')
            self.conn.execute('INSERT INTO ideas VALUES(?,?,?,?,?,?,?,?,?,?)', (id,cohort,self._now().isoformat(),dump(payload),payload['status'],str(quantity),str(budget),'0','0',int(payload['status']=='accepted')))
            if payload['status']=='accepted':
                for arm in self._protocol(cohort)['arms']:
                    self.conn.execute('INSERT INTO positions VALUES(?,?,?,?)', (id,arm,'0','0'))
            self._audit('opportunity_registered', {'id':id,'cohort':cohort,'status':payload['status']})
            return dict(self._row('ideas',id))
        return self._write(action)

    def record_quote(self, id, payload):
        payload = json.loads(dump(payload))
        for key in ('security','source','currency','unit','quote_type'):
            text(payload[key])
        if payload['quote_type'] not in ('bid','ask','last','manual-executable'):
            raise ValueError('Explicit quote type required')
        number(payload['native_price'],True); rate=number(payload['gbp_per_unit'],True)
        currency=payload['currency']
        if currency=='GBP' and (payload['unit']!='major' or rate!=1):
            raise ValueError('GBP major unit requires conversion factor one')
        if currency=='GBX' and (payload['unit']!='pence' or rate!=Decimal('0.01')):
            raise ValueError('GBX pence requires GBP factor 0.01')
        if currency not in ('GBP','GBX'):
            if payload['unit']!='major' or not payload.get('fx_source') or stamp(payload['fx_asof']) > stamp(payload['asof']):
                raise ValueError('Explicit dated FX evidence required; no inferred conversion')
        if type(payload['delay_seconds']) is not int or payload['delay_seconds']<0 or stamp(payload['asof'])>self._now():
            raise ValueError('Quote must have nonnegative delay and actual nonfuture timestamp')
        def action():
            existing=self._replay('quotes',id,payload)
            if existing: return existing
            self.conn.execute('INSERT INTO quotes VALUES(?,?,?)',(id,self._now().isoformat(),dump(payload)))
            self._audit('manual_quote_recorded',{'id':id})
            return dict(self._row('quotes',id))
        return self._write(action)

    def _quote(self, quote_id, idea, earliest, execution=True, asof=None):
        record=self._row('quotes',quote_id); quote=json.loads(record['payload'])
        when=stamp(quote['asof']); cutoff=asof or self._now()
        protocol=self._protocol(idea['cohort'])
        if quote['security']!=json.loads(idea['payload'])['security'] or when<earliest or when>cutoff or stamp(record['received'])>cutoff:
            raise ValueError('Quote identity/date fails prospective cutoff')
        if (cutoff-when).total_seconds()>protocol['quote_max_age_seconds'] or quote['delay_seconds']>protocol['quote_max_age_seconds']:
            raise ValueError('Missing fresh quote; paper execution withheld')
        if quote['currency'] not in ('GBP','GBX') and (cutoff-stamp(quote['fx_asof'])).total_seconds()>protocol['quote_max_age_seconds']:
            raise ValueError('FX conversion evidence is stale')
        if execution and quote['quote_type'] not in ('bid','ask','manual-executable'):
            raise ValueError('Last price is not evidence of executable fill')
        return quote, number(quote['native_price'],True)*number(quote['gbp_per_unit'],True)

    def entry_fill(self, idea_id, execution_id, quantity, quote_id, fees_gbp):
        quantity=number(quantity,True); fees=number(fees_gbp)
        payload={'idea':idea_id,'quantity':str(quantity),'quote_id':quote_id,'fees_gbp':str(fees)}
        def action():
            existing=self._replay('executions',execution_id,payload)
            if existing: return existing
            idea=self._row('ideas',idea_id)
            if not idea['entry_open'] or idea['status']!='accepted': raise ValueError('Entry is closed/not accepted')
            if self._now()>=stamp(json.loads(idea['payload'])['deadline']): raise ValueError('Entry deadline has passed')
            earliest=stamp(idea['registered'])+timedelta(seconds=self._protocol(idea['cohort'])['response_delay_seconds'])
            quote,price=self._quote(quote_id,idea,earliest)
            if quote['quote_type']=='bid': raise ValueError('Buy requires ask or explicitly executable quote')
            filled=Decimal(idea['filled'])+quantity; cost=quantity*price+fees; spent=Decimal(idea['spent'])+cost
            if filled>Decimal(idea['quantity']) or spent>Decimal(idea['budget']): raise ValueError('Entry quantity/cost exceeds frozen commitment')
            for arm in self._protocol(idea['cohort'])['arms']:
                cash=Decimal(self.conn.execute('SELECT cash FROM arms WHERE cohort=? AND name=?',(idea['cohort'],arm)).fetchone()[0])
                self.conn.execute('UPDATE arms SET cash=? WHERE cohort=? AND name=?',(str(cash-cost),idea['cohort'],arm))
                self.conn.execute('UPDATE positions SET quantity=? WHERE idea=? AND arm=?',(str(filled),idea_id,arm))
            self.conn.execute('UPDATE ideas SET filled=?,spent=?,entry_open=? WHERE id=?',(str(filled),str(spent),int(filled<Decimal(idea['quantity'])),idea_id))
            self.conn.execute('INSERT INTO executions VALUES(?,?,?,?)',(execution_id,'entry',self._now().isoformat(),dump(payload)))
            self._audit('paired_entry_fill',payload)
            return payload
        return self._write(action)

    def cancel_entry(self, idea_id):
        def action():
            if self._row('ideas',idea_id)['entry_open']:
                self.conn.execute('UPDATE ideas SET entry_open=0 WHERE id=?',(idea_id,))
                self._audit('entry_remainder_cancelled',{'idea':idea_id})
        return self._write(action)

    def cancel_exit(self, request_id):
        def action():
            request=self._row('exits',request_id)
            if request['status']=='filled': raise ValueError('Filled exit cannot be cancelled')
            if request['status']!='cancelled':
                self.conn.execute("UPDATE exits SET status='cancelled' WHERE id=?",(request_id,))
                self._audit('exit_remainder_cancelled',{'request':request_id})
        return self._write(action)

    def request_exit(self, idea_id, arm, id, payload):
        payload=json.loads(dump(payload)); quantity=number(payload['quantity'],True)
        text(payload['reason'])
        if not payload.get('evidence') or stamp(payload['evidence_asof'])>self._now(): raise ValueError('Contemporaneous exit evidence required')
        def action():
            existing=self._replay('exits',id,payload)
            if existing:
                if existing['idea']!=idea_id or existing['arm']!=arm: raise ValueError('Exit ID conflict')
                return existing
            idea=self._row('ideas',idea_id)
            held=self.conn.execute('SELECT quantity FROM positions WHERE idea=? AND arm=?',(idea_id,arm)).fetchone()
            reserved=sum((Decimal(r['quantity'])-Decimal(r['filled']) for r in self.conn.execute("SELECT * FROM exits WHERE idea=? AND arm=? AND status='open'",(idea_id,arm))),Decimal(0))
            if not held or quantity>Decimal(held[0])-reserved: raise ValueError('Exit exceeds unreserved paper shares')
            self.conn.execute('UPDATE ideas SET entry_open=0 WHERE id=?',(idea_id,))
            self.conn.execute('INSERT INTO exits VALUES(?,?,?,?,?,?,?,?)',(id,idea_id,arm,self._now().isoformat(),dump(payload),str(quantity),'0','open'))
            self._audit('exit_requested',{'id':id,'idea':idea_id,'arm':arm})
            return dict(self._row('exits',id))
        return self._write(action)

    def exit_fill(self, request_id, execution_id, quantity, quote_id, fees_gbp):
        quantity=number(quantity,True); fees=number(fees_gbp)
        payload={'request':request_id,'quantity':str(quantity),'quote_id':quote_id,'fees_gbp':str(fees)}
        def action():
            existing=self._replay('executions',execution_id,payload)
            if existing: return existing
            request=self._row('exits',request_id); idea=self._row('ideas',request['idea']); protocol=self._protocol(idea['cohort'])
            earliest=stamp(request['requested'])+timedelta(seconds=protocol['response_delay_seconds'])
            quote,price=self._quote(quote_id,idea,earliest)
            if quote['quote_type']=='ask': raise ValueError('Sell requires bid or explicitly executable quote')
            filled=Decimal(request['filled'])+quantity
            if request['status']!='open' or filled>Decimal(request['quantity']): raise ValueError('Exit fill exceeds requested quantity')
            position=self.conn.execute('SELECT * FROM positions WHERE idea=? AND arm=?',(idea['id'],request['arm'])).fetchone()
            cash=Decimal(self.conn.execute('SELECT cash FROM arms WHERE cohort=? AND name=?',(idea['cohort'],request['arm'])).fetchone()[0])
            proceeds=quantity*price-fees
            if proceeds<0 and -proceeds>self._available(idea['cohort'],request['arm']): raise ValueError('Exit fees exceed free cash')
            self.conn.execute('UPDATE arms SET cash=? WHERE cohort=? AND name=?',(str(cash+proceeds),idea['cohort'],request['arm']))
            self.conn.execute('UPDATE positions SET quantity=?,exit_cash=? WHERE idea=? AND arm=?',(str(Decimal(position['quantity'])-quantity),str(Decimal(position['exit_cash'])+max(proceeds,Decimal(0))),idea['id'],request['arm']))
            self.conn.execute('UPDATE exits SET filled=?,status=? WHERE id=?',(str(filled),'filled' if filled==Decimal(request['quantity']) else 'open',request_id))
            self.conn.execute('INSERT INTO executions VALUES(?,?,?,?)',(execution_id,'exit',self._now().isoformat(),dump(payload)))
            self._audit('manual_exit_fill',payload)
            return payload
        return self._write(action)

    def snapshot(self, cohort, asof, marks, benchmark=None, cash_reference=None):
        cutoff=stamp(asof)
        if cutoff>self._now(): raise ValueError('Snapshot cannot use future date')
        def action():
            protocol=self._protocol(cohort)
            if cutoff<stamp(self._row('cohorts',cohort)['created']): raise ValueError('Snapshot predates cohort')
            latest_audit=self.conn.execute('SELECT at FROM audit ORDER BY id DESC LIMIT 1').fetchone()
            if latest_audit and stamp(latest_audit['at'])>cutoff: raise ValueError('Snapshot predates latest known record; historical reconstruction unsupported')
            # Historical accounting reconstruction is not claimed by this engine.
            for row in self.conn.execute('SELECT known,payload FROM executions'):
                execution=json.loads(row['payload'])
                idea=self._row('ideas',execution['idea']) if 'idea' in execution else self._row('ideas',self._row('exits',execution['request'])['idea'])
                if idea['cohort']==cohort and stamp(row['known'])>cutoff: raise ValueError('Snapshot predates known accounting; retrospective reconstruction unsupported')
            outcomes={}
            for arm in protocol['arms']:
                cash=Decimal(self.conn.execute('SELECT cash FROM arms WHERE cohort=? AND name=?',(cohort,arm)).fetchone()[0]); value=Decimal(0); missing=[]; valuations=[]
                for row in self.conn.execute('SELECT p.*,i.id AS idea_id FROM positions p JOIN ideas i ON p.idea=i.id WHERE i.cohort=? AND p.arm=?',(cohort,arm)):
                    if Decimal(row['quantity'])==0: continue
                    idea=self._row('ideas',row['idea_id']); security=json.loads(idea['payload'])['security']
                    try:
                        quote,price=self._quote(marks[security],idea,stamp(idea['registered']),False,cutoff)
                        marked=Decimal(row['quantity'])*price; value+=marked
                        valuations.append({'security':security,'quantity':row['quantity'],'value_gbp':str(marked),'quote_asof':quote['asof'],'quote_type':quote['quote_type']})
                    except (KeyError,ValueError) as exc: missing.append({'security':security,'reason':str(exc)})
                nav=None if missing else cash+value
                outcomes[arm]={'cash_gbp':str(cash),'available_gbp':str(self._available(cohort,arm,cutoff)), 'marked_nav_gbp':str(nav) if nav is not None else None,'gain_loss_gbp':str(nav-number(protocol['capital_gbp'])) if nav is not None else None,'open_marks':valuations,'missing':missing,'future_liquidation_costs_excluded':bool(valuations)}
            references={}
            for name,record in (('benchmark',benchmark),('cash_reference',cash_reference)):
                if record is None: references[name]={'status':'missing'}; continue
                if stamp(record['asof'])!=cutoff or number(record['capital_gbp'])!=number(protocol['capital_gbp']) or not record.get('source'): raise ValueError('Reference must use identical capital/asof and explicit source')
                number(record['net_value_gbp']); references[name]=dict(record,status='supplied')
            result={'cohort':cohort,'protocol_hash':self._row('cohorts',cohort)['hash'],'asof':asof,'arms':outcomes,'references':references,'actionable':False,'exit_rule_conformance':'manual evidence supplied; not automatically adjudicated','kind':'prospective paper records; not broker fills or profitability validation'}
            self.conn.execute('INSERT INTO snapshots(cohort,asof,payload) VALUES(?,?,?)',(cohort,asof,dump(result)))
            return result
        return self._write(action)


Store=PaperStudy
