"""Local observation-only ledger. No broker or recommendation execution.

Integration tables use JSON text: events(id,created_at,kind,payload),
outbox(id,created_at,alert_id,payload,status,attempts,last_error), and
jobs(id,kind,payload,status,created_at,updated_at,attempts,last_error).
All Decimal amounts/quantities are text. Access ``Store.conn`` for integrations;
integrations must preserve these columns and use their own transactions.
"""
import json
import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def dec(value, positive=False):
    if isinstance(value, (float, bool)):
        raise ValueError('Use decimal strings, not floats or booleans')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid decimal') from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('Amount must be finite and nonnegative (positive if required)')
    return result


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def input_decimal(value, positive=False):
    """Bound external numeric representation; ledger arithmetic uses 80 digits.

    Eighteen integer and fractional digits cover broker money/share precision.
    Reject excess precision explicitly instead of silently rounding a fill.
    These are representation limits, not portfolio allocation policies.
    """
    result = dec(value, positive)
    if result.adjusted() >= 18 or result.as_tuple().exponent < -18:
        raise ValueError('Supported input precision is 18 integer and 18 fractional digits')
    return result


def identifier(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError('Identifiers must be explicit nonempty strings without surrounding whitespace')
    return value


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Store(path) as store:
        return store.status()


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS quotes(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fx_quotes(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,alert_id TEXT NOT NULL REFERENCES alerts(id),side TEXT NOT NULL,ticker TEXT NOT NULL,quantity TEXT NOT NULL,reserved_gbp TEXT NOT NULL,filled_quantity TEXT NOT NULL,spent_gbp TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fills(execution_id TEXT PRIMARY KEY,order_id TEXT NOT NULL REFERENCES orders(id),quantity TEXT NOT NULL,gbp_value TEXT NOT NULL,fees_gbp TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fill_exceptions(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,payload TEXT NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS holdings(ticker TEXT PRIMARY KEY,quantity TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cash_events(id TEXT PRIMARY KEY,kind TEXT NOT NULL,amount_gbp TEXT NOT NULL,ticker TEXT);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,alert_id TEXT,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT);
        INSERT OR IGNORE INTO meta VALUES('funded','0');
        INSERT OR IGNORE INTO meta VALUES('cash_gbp','0');
        INSERT OR IGNORE INTO meta VALUES('capital_gbp','0');
        ''')
        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.conn.close()

    def _atomic(self, action):
        nested = self.conn.in_transaction
        savepoint = 'core_' + uuid.uuid4().hex
        self.conn.execute('SAVEPOINT ' + savepoint if nested else 'BEGIN IMMEDIATE')
        try:
            with localcontext() as context:
                context.prec = 80
                result = action()
            if nested:
                self.conn.execute('RELEASE SAVEPOINT ' + savepoint)
            else:
                self.conn.commit()
            return result
        except Exception:
            if nested:
                self.conn.execute('ROLLBACK TO SAVEPOINT ' + savepoint)
                self.conn.execute('RELEASE SAVEPOINT ' + savepoint)
            else:
                self.conn.rollback()
            raise

    def _event(self, kind, payload):
        self.conn.execute('INSERT INTO events(created_at,kind,payload) VALUES(?,?,?)', (now(), kind, encoded(payload)))

    def _get(self, key):
        return self.conn.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()[0]

    def _set(self, key, value):
        self.conn.execute('UPDATE meta SET value=? WHERE key=?', (str(value), key))

    def _orders(self):
        return self.conn.execute("SELECT * FROM orders WHERE status='open'").fetchall()

    def _reserved(self):
        return sum((dec(r['reserved_gbp']) - dec(r['spent_gbp']) for r in self._orders() if r['side'] == 'buy'), Decimal(0))

    def status(self):
        # A single read snapshot prevents mixing cash before a fill with holdings
        # after it when a second connection commits during this read.
        own_transaction = not self.conn.in_transaction
        if own_transaction:
            self.conn.execute('BEGIN')
        try:
            with localcontext() as context:
                context.prec = 80
                result = self._status()
            if own_transaction:
                self.conn.commit()
            return result
        except Exception:
            if own_transaction:
                self.conn.rollback()
            raise

    def _status(self):
        cash, reserved = dec(self._get('cash_gbp')), self._reserved()
        holdings = {r['ticker']: r['quantity'] for r in self.conn.execute('SELECT * FROM holdings')}
        values, marks, unavailable = {}, {}, []
        latest = {}
        for row in self.conn.execute('SELECT payload FROM quotes ORDER BY id DESC'):
            quote = json.loads(row['payload'])
            latest.setdefault(quote['ticker'], quote)
        latest_fx={}
        for row in self.conn.execute('SELECT payload FROM fx_quotes ORDER BY id DESC'):
            fx=json.loads(row['payload']); latest_fx.setdefault(fx['currency'],fx)
        for ticker, quantity in holdings.items():
            if not dec(quantity):
                continue
            identity = ticker.split(':')
            if len(identity) not in (2, 3) or any(not part.strip() or part != part.strip() for part in identity):
                unavailable.append(ticker + ': security identifier must be exchange:ticker[:class] for valuation')
                continue
            quote = latest.get(ticker)
            if not quote:
                unavailable.append(ticker + ': missing quote')
                continue
            if not isinstance(quote['exchange'], str) or quote['exchange'].casefold() != identity[0].casefold():
                unavailable.append(ticker + ': quote exchange does not match qualified security identifier')
                continue
            timestamp = datetime.fromisoformat(quote['quote_timestamp'].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - timestamp).total_seconds() if timestamp.tzinfo else -1
            if timestamp.tzinfo is None or age < 0 or age > 1800 or dec(quote['delay_seconds']) > 1800:
                unavailable.append(ticker + ': stale/invalid quote time')
                continue
            if quote['currency'] == 'GBP' and quote['unit'] in ('major', 'GBP/share'):
                price = dec(quote['price'])
            elif quote['currency'] == 'GBX' and quote['unit'] in ('pence', 'GBX/share'):
                price = dec(quote['price']) / 100
            else:
                fx=latest_fx.get(quote['currency'])
                if not fx:
                    unavailable.append(ticker + ': GBP valuation unavailable; no inferred FX')
                    continue
                fx_time=datetime.fromisoformat(fx['quote_timestamp'].replace('Z','+00:00'))
                fx_age=(datetime.now(timezone.utc)-fx_time).total_seconds() if fx_time.tzinfo else -1
                if fx_age<0 or fx_age>1800 or dec(fx['delay_seconds'])>1800:
                    unavailable.append(ticker + ': stale/invalid FX time')
                    continue
                price=dec(quote['price'])*dec(fx['gbp_per_unit'])
            values[ticker] = dec(quantity) * price
            marks[ticker] = {'quantity': quantity, 'value_gbp': str(values[ticker]),
                             'price_gbp': str(price), 'quote_timestamp': quote['quote_timestamp'],
                             'source': quote['source'], 'quote_type': quote['quote_type'],
                             'description': 'Dated manually supplied quote snapshot; not a live valuation'}
            if quote['currency'] not in ('GBP','GBX'):
                marks[ticker]['fx']={'currency':fx['currency'],'gbp_per_unit':fx['gbp_per_unit'],
                    'quote_timestamp':fx['quote_timestamp'],'source':fx['source'],'quote_type':fx['quote_type']}
        exceptions=[dict(row) for row in self.conn.execute("SELECT * FROM fill_exceptions WHERE status='unresolved'")]
        for row in exceptions: row['payload']=json.loads(row['payload'])
        if exceptions: unavailable.append('Unreconciled reported fills: actual cash and exposure are uncertain')
        nav = None if unavailable else cash + sum(values.values(), Decimal(0))
        weights = None if nav is None or nav == 0 else dict(
            {'cash': str(cash / nav * 100)}, **{ticker: str(value / nav * 100) for ticker, value in values.items()})
        return {'mode': 'observation', 'actionable': False, 'planned_capital_gbp': '300',
                'funded': self._get('funded') == '1', 'capital_gbp': self._get('capital_gbp'),
                'cash_gbp': str(cash), 'reserved_gbp': str(reserved), 'available_gbp': str(cash-reserved),
                'holdings': holdings, 'net_asset_value_gbp': str(nav) if nav is not None else None,
                'reported_fill_exceptions':exceptions,'reconciliation_required':bool(exceptions),
                'weights': weights, 'valuations': marks, 'valuation_unavailable_reasons': unavailable,
                'valuation_basis': 'Manual dated security/FX snapshots only; no live data or inferred conversion. Gross marks exclude future liquidation costs.',
                'gates': ['portfolio_policy_unset', 'research_partial', 'observation_trial_pending', 'phone_delivery_unverified']}

    def confirm_funding(self, amount='300'):
        amount = input_decimal(amount, True)
        if amount > 300:
            raise ValueError('Initial sleeve cannot exceed £300')
        def action():
            if self._get('funded') == '1':
                if dec(self._get('capital_gbp')) != amount:
                    raise ValueError('Funding already recorded; cannot replace it')
                return self.status()
            self._set('funded', '1')
            self._set('cash_gbp', amount)
            self._set('capital_gbp', amount)
            self._event('funding_confirmed', {'amount_gbp': str(amount)})
            return self.status()
        return self._atomic(action)

    def quote(self, security):
        required = ('ticker', 'exchange', 'currency', 'unit', 'price', 'quote_type', 'source', 'quote_timestamp', 'delay_seconds')
        if any(security.get(k) is None or security.get(k) == '' for k in required):
            raise ValueError('Quote missing identity, currency/unit, source or freshness metadata')
        for key in ('ticker', 'exchange', 'currency', 'unit', 'quote_type', 'source', 'quote_timestamp'):
            identifier(security[key])
        input_decimal(security['price'], True)
        delay = input_decimal(security['delay_seconds'])
        if delay != delay.to_integral_value():
            raise ValueError('Delay must be integer seconds')
        currency, unit = security['currency'], security['unit']
        if currency not in ('GBP', 'GBX', 'USD', 'EUR', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SEK', 'NOK', 'DKK'):
            raise ValueError('Unsupported explicit currency')
        allowed_units = ('pence', 'GBX/share') if currency == 'GBX' else ('major', currency + '/share')
        if unit not in allowed_units:
            raise ValueError('Currency/unit mismatch')
        if security['quote_type'] not in ('bid', 'ask', 'last', 'manual-broker'):
            raise ValueError('Unknown quote type')
        timestamp = datetime.fromisoformat(security['quote_timestamp'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
            raise ValueError('Quote time must be aware and not in future')
        stale = (datetime.now(timezone.utc) - timestamp).total_seconds() > 1800 or delay > 1800
        record = dict(security, ingested_at=now(), actionable=False, freshness='stale' if stale else 'fresh')
        def action():
            cur = self.conn.execute('INSERT INTO quotes(created_at,payload) VALUES(?,?)', (now(), encoded(record)))
            self._event('quote_recorded', {'quote_id': cur.lastrowid})
            return dict(record, id=cur.lastrowid)
        return self._atomic(action)

    def fx_quote(self,payload):
        """Explicit GBP per ONE major currency unit. Never invert an unknown pair."""
        required=('currency','gbp_per_unit','quote_timestamp','delay_seconds','source','quote_type')
        if not isinstance(payload,dict) or any(payload.get(k) in (None,'') for k in required):
            raise ValueError('FX snapshot needs explicit direction, price, source and time')
        for field in ('currency','quote_timestamp','source','quote_type'): identifier(payload[field])
        allowed=set(required)|{'unit'}
        if set(payload)-allowed: raise ValueError('Unknown FX fields; use explicit GBP per major currency unit')
        if 'unit' in payload and payload['unit']!='GBP per one '+payload['currency']+' major unit':
            raise ValueError('FX unit contradicts explicit conversion direction')
        if payload['currency'] not in ('USD','EUR','CHF','JPY','CAD','AUD','HKD','SEK','NOK','DKK'):
            raise ValueError('FX input currency must be a supported foreign major unit')
        input_decimal(payload['gbp_per_unit'],True)
        delay=input_decimal(payload['delay_seconds'])
        if delay!=delay.to_integral_value(): raise ValueError('FX delay must be integer seconds')
        if payload['quote_type'] not in ('bid','ask','mid','manual-broker'):
            raise ValueError('Unsupported FX quote type')
        timestamp=datetime.fromisoformat(payload['quote_timestamp'].replace('Z','+00:00'))
        if timestamp.tzinfo is None or timestamp>datetime.now(timezone.utc):
            raise ValueError('FX timestamp must be aware and not future')
        record=dict(payload,unit='GBP per one '+payload['currency']+' major unit',ingested_at=now(),actionable=False)
        def action():
            row=self.conn.execute('INSERT INTO fx_quotes(created_at,payload) VALUES(?,?)',(now(),encoded(record)))
            self._event('fx_quote_recorded',{'fx_quote_id':row.lastrowid})
            return dict(record,id=row.lastrowid)
        return self._atomic(action)

    def _alert(self, alert_id):
        identifier(alert_id)
        row = self.conn.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown alert')
        return row

    def _notice(self, alert_id, payload):
        self.conn.execute('INSERT INTO outbox(id,created_at,alert_id,payload) VALUES(?,?,?,?)', (str(uuid.uuid4()), now(), alert_id, encoded(payload)))

    def create_trial_alert(self, payload):
        if payload.get('actionable') or payload.get('mode', 'observation') != 'observation':
            raise ValueError('Only nonactionable observation alerts are supported')
        alert_id = identifier(payload['id']) if 'id' in payload else str(uuid.uuid4())
        def action():
            existing = self.conn.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
            defaults = json.loads(existing['payload']) if existing else {}
            created = payload.get('created_at', defaults.get('created_at', now()))
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            expires = payload.get('expires_at', defaults.get('expires_at', (created_dt + timedelta(hours=24)).isoformat()))
            expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if created_dt.tzinfo is None or expires_dt.tzinfo is None or expires_dt <= created_dt:
                raise ValueError('Alert timestamps must be aware with expiry after creation')
            record = dict(payload, id=alert_id, mode='observation', actionable=False, gates=self.status()['gates'],
                          revision=payload.get('revision', 1), created_at=created, expires_at=expires,
                          last_source_check=payload.get('last_source_check'), confirmation_expires_at=None)
            if existing:
                if existing['payload'] != encoded(record):
                    raise ValueError('Alert ID conflict')
                return dict(record, status=existing['status'])
            self.conn.execute('INSERT INTO alerts VALUES(?,?,?,?)', (alert_id, created, 'active', encoded(record)))
            self._event('trial_alert_created', record)
            self._notice(alert_id, record)
            return dict(record, status='active')
        return self._atomic(action)

    def acknowledge(self, alert_id):
        self.expire_alerts()
        def action():
            row = self._alert(alert_id)
            if row['status'] in ('withdrawn', 'expired'):
                raise ValueError('Withdrawn/expired alert cannot be acknowledged')
            if row['status'] != 'acknowledged':
                self.conn.execute("UPDATE alerts SET status='acknowledged' WHERE id=?", (alert_id,))
                self._event('alert_acknowledged', {'id': alert_id})
            return {'id': alert_id, 'status': 'acknowledged', 'actionable': False}
        return self._atomic(action)

    def withdraw(self, alert_id, reason):
        if not str(reason).strip():
            raise ValueError('Withdrawal requires reason')
        def action():
            row = self._alert(alert_id)
            if row['status'] != 'withdrawn':
                self.conn.execute("UPDATE alerts SET status='withdrawn' WHERE id=?", (alert_id,))
                notice = {'id': alert_id, 'status': 'withdrawn', 'reason': reason, 'actionable': False,
                          'standing_orders': 'User must cancel broker orders separately'}
                self._event('alert_withdrawn', notice)
                self._notice(alert_id, notice)
            return {'id': alert_id, 'status': 'withdrawn', 'actionable': False}
        return self._atomic(action)

    def refresh_alert(self, alert_id):
        self.expire_alerts()
        row = self._alert(alert_id)
        return dict(json.loads(row['payload']), status=row['status'], actionable=False,
                    checked_at=now(), gates=self.status()['gates'])

    def expire_alerts(self):
        def action():
            expired = []
            for row in self.conn.execute("SELECT * FROM alerts WHERE status IN ('active','acknowledged')").fetchall():
                record = json.loads(row['payload'])
                expires = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
                if expires <= datetime.now(timezone.utc):
                    self.conn.execute("UPDATE alerts SET status='expired' WHERE id=?", (row['id'],))
                    notice = {'id': row['id'], 'status': 'expired', 'actionable': False, 'confirmation_expires_at': None}
                    self._event('alert_expired', notice)
                    self._notice(row['id'], notice)
                    expired.append(row['id'])
            return expired
        return self._atomic(action)

    def report_order(self, alert_id, side, ticker, quantity, reserved_gbp='0', order_id=None):
        quantity, reserve = input_decimal(quantity, True), input_decimal(reserved_gbp)
        if side not in ('buy', 'sell') or not isinstance(ticker, str) or not ticker.strip() or ticker != ticker.strip():
            raise ValueError('Explicit side and exact security identifier required')
        if side == 'buy' and reserve == 0 or side == 'sell' and reserve != 0:
            raise ValueError('Buys require GBP reservation; sells require zero cash reservation')
        order_id = identifier(order_id) if order_id is not None else str(uuid.uuid4())
        def action():
            self._alert(alert_id)
            existing = self.conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if existing:
                expected = (alert_id, side, ticker, quantity, reserve)
                actual = (existing['alert_id'], existing['side'], existing['ticker'], dec(existing['quantity']), dec(existing['reserved_gbp']))
                if actual != expected:
                    raise ValueError('Order ID conflict')
                return dict(existing)
            if self._get('funded') != '1':
                raise ValueError('Funding must be explicitly confirmed')
            if side == 'buy' and reserve > dec(self._get('cash_gbp')) - self._reserved():
                raise ValueError('Insufficient sleeve cash after reservations')
            if side == 'sell':
                held = self.conn.execute('SELECT quantity FROM holdings WHERE ticker=?', (ticker,)).fetchone()
                reserved = sum((dec(r['quantity']) - dec(r['filled_quantity']) for r in self._orders() if r['side'] == 'sell' and r['ticker'] == ticker), Decimal(0))
                if not held or quantity > dec(held[0]) - reserved:
                    raise ValueError('Cannot sell unrelated or already reserved sleeve shares')
            self.conn.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?)', (order_id, alert_id, side, ticker, str(quantity), str(reserve), '0', '0', 'open'))
            self._event('manual_order_reported', {'id': order_id, 'alert_id': alert_id, 'observation_only': True})
            return dict(self.conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())
        return self._atomic(action)

    def report_fill(self, order_id, execution_id, quantity, gbp_value, fees_gbp='0'):
        quantity, value, fees = input_decimal(quantity, True), input_decimal(gbp_value, True), input_decimal(fees_gbp)
        identifier(order_id)
        identifier(execution_id)
        def action():
            existing = self.conn.execute('SELECT * FROM fills WHERE execution_id=?', (execution_id,)).fetchone()
            if existing:
                if (existing['order_id'], dec(existing['quantity']), dec(existing['gbp_value']), dec(existing['fees_gbp'])) != (order_id, quantity, value, fees):
                    raise ValueError('Execution ID conflict')
                return dict(existing)
            row = self.conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if not row or row['status'] != 'open':
                raise ValueError('Unknown, cancelled or filled order; reconcile manually')
            filled = dec(row['filled_quantity']) + quantity
            if filled > dec(row['quantity']):
                raise ValueError('Fill exceeds reported order quantity')
            held = self.conn.execute('SELECT quantity FROM holdings WHERE ticker=?', (row['ticker'],)).fetchone()
            balance = dec(held[0]) if held else Decimal(0)
            cash = dec(self._get('cash_gbp'))
            spent = dec(row['spent_gbp'])
            if row['side'] == 'buy':
                cost = value + fees
                spent += cost
                if spent > dec(row['reserved_gbp']) or cost > cash:
                    raise ValueError('Fill exceeds reserved total cost; reconcile manually')
                balance += quantity
                cash -= cost
            else:
                if quantity > balance or fees - value > cash - self._reserved():
                    raise ValueError('Invalid sell proceeds or quantity')
                balance -= quantity
                cash += value - fees
            self._set('cash_gbp', cash)
            self.conn.execute('INSERT INTO holdings VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET quantity=excluded.quantity', (row['ticker'], str(balance)))
            self.conn.execute('UPDATE orders SET filled_quantity=?,spent_gbp=?,status=? WHERE id=?', (str(filled), str(spent), 'filled' if filled == dec(row['quantity']) else 'open', order_id))
            self.conn.execute('INSERT INTO fills VALUES(?,?,?,?,?)', (execution_id, order_id, str(quantity), str(value), str(fees)))
            record = {'execution_id': execution_id, 'order_id': order_id, 'quantity': str(quantity), 'gbp_value': str(value), 'fees_gbp': str(fees)}
            self._event('manual_fill_reported', record)
            return record
        return self._atomic(action)

    def capture_reported_fill(self,order_id,execution_id,quantity,gbp_value,fees_gbp='0'):
        """Retain a well-formed broker report even when normal accounting rejects it.

        This is unverified reported exposure, never an inferred fill or authority
        to charge unrelated ISA cash. Successful replay resolves only the exact
        report; conflicting variants remain visible for reconciliation.
        """
        identifier(order_id); identifier(execution_id)
        payload={'order_id':order_id,'execution_id':execution_id,
                 'quantity':str(input_decimal(quantity,True)),
                 'gbp_value':str(input_decimal(gbp_value,True)),
                 'fees_gbp':str(input_decimal(fees_gbp))}
        report_id=hashlib.sha256(encoded(payload).encode()).hexdigest()
        def action():
            try:
                result=self.report_fill(**payload)
            except ValueError as error:
                existing=self.conn.execute('SELECT * FROM fill_exceptions WHERE id=?',(report_id,)).fetchone()
                if not existing:
                    self.conn.execute('INSERT INTO fill_exceptions VALUES(?,?,?,?,?)',
                                      (report_id,now(),encoded(payload),str(error),'unresolved'))
                    self._event('reported_fill_requires_reconciliation',dict(payload,report_id=report_id,reason=str(error)))
                return dict(payload,report_id=report_id,status='reconciliation_required',
                            accounted=False,actionable=False,reason=str(error))
            changed=self.conn.execute("UPDATE fill_exceptions SET status='resolved_by_exact_replay' WHERE id=? AND status='unresolved'",(report_id,)).rowcount
            if changed: self._event('reported_fill_reconciled',{'report_id':report_id,'execution_id':execution_id})
            return dict(result,accounted=True,actionable=False)
        return self._atomic(action)

    def cancel_order(self, order_id):
        identifier(order_id)
        def action():
            row = self.conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if row is None:
                raise ValueError('Unknown order')
            if row['status'] == 'filled':
                raise ValueError('Cannot cancel filled order')
            if row['status'] != 'cancelled':
                self.conn.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
                self._event('manual_cancellation_confirmed', {'id': order_id})
            return {'id': order_id, 'status': 'cancelled'}
        return self._atomic(action)

    def record_cash_event(self, event_id, kind, amount_gbp, ticker=None):
        amount = input_decimal(amount_gbp, True)
        identifier(event_id)
        if kind not in ('dividend', 'fee'):
            raise ValueError('Unique cash event ID and dividend/fee kind required')
        def action():
            existing = self.conn.execute('SELECT * FROM cash_events WHERE id=?', (event_id,)).fetchone()
            if existing:
                if (existing['kind'], dec(existing['amount_gbp']), existing['ticker']) != (kind, amount, ticker):
                    raise ValueError('Cash event ID conflict')
                return dict(existing)
            if self._get('funded') != '1':
                raise ValueError('Funding must be explicitly confirmed')
            cash = dec(self._get('cash_gbp'))
            if kind == 'dividend':
                held = self.conn.execute('SELECT quantity FROM holdings WHERE ticker=?', (ticker,)).fetchone()
                if not held or dec(held[0]) == 0:
                    raise ValueError('Dividend requires an owned sleeve security; reconcile historical entitlements manually')
                cash += amount
            else:
                if amount > cash - self._reserved():
                    raise ValueError('Fee exceeds unreserved sleeve cash; reconcile manually')
                cash -= amount
            self._set('cash_gbp', cash)
            record = {'id': event_id, 'kind': kind, 'amount_gbp': str(amount), 'ticker': ticker}
            self.conn.execute('INSERT INTO cash_events VALUES(?,?,?,?)', (event_id, kind, str(amount), ticker))
            self._event('manual_cash_event', record)
            return record
        return self._atomic(action)
