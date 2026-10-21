"""Observation service and manual-record CLI. Never places orders or approves trades."""
import argparse
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import sys
import time
import uuid
from decimal import Decimal
from contextlib import closing, contextmanager

from observation_core import Store, initialize
from observation_monitor import (check_sources, due_slot, get_state, init_monitor,
                                 recover_jobs, set_state, utcnow)
from observation_transport import (configure_credentials, load_credentials, init_transport,
                                   enqueue_send, enqueue_edit, dispatch_outbox, ingest_updates)

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'state'/'observation'
DB=STATE/'operations.sqlite3'

@contextmanager
def engine_lock(state_root=STATE, wait_seconds=0):
    """One service pass/daemon per Windows user; ledger commands use SQLite locks."""
    import msvcrt
    Path(state_root).mkdir(parents=True,exist_ok=True)
    lock=open(Path(state_root)/'service.lock','a+b')
    if lock.seek(0,2)==0: lock.write(b'0'); lock.flush()
    lock.seek(0)
    deadline=time.monotonic()+wait_seconds
    while True:
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            break
        except OSError:
            if time.monotonic()>=deadline:
                lock.close()
                raise ValueError('Observation service is already running; use status or stop the task before a manual tick') from None
            time.sleep(0.25)
    try: yield
    finally:
        lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1); lock.close()

def read_config(root=ROOT):
    config=json.loads((root/'monitoring'/'config.json').read_text(encoding='utf-8-sig'))
    if config.get('mode') not in ('observation-only', 'model-portfolio'):
        raise ValueError('Supported config modes: observation-only, model-portfolio')
    return config

def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,default=str),encoding='utf-8'); tmp.replace(path)

def full_status(store):
    init_monitor(store.conn); init_transport(store.conn)
    result=store.status()
    reconciliation_note=get_state(store.conn,'reconciliation_required')
    if reconciliation_note:
        result['reconciliation_required']=True
        result['net_asset_value_gbp']=None; result['weights']=None
        result['valuation_unavailable_reasons'].append('Outstanding operational reconciliation: '+str(reconciliation_note))
    nav=result.get('net_asset_value_gbp')
    result['gain_loss_gbp']=str(Decimal(nav)-Decimal(result['capital_gbp'])) if nav is not None and result['funded'] else None
    result['performance_basis']='Recorded sleeve cash flows and available manual marks; unrelated ISA activity excluded'
    trial_started=get_state(store.conn,'trial_started_at')
    last_tick=get_state(store.conn,'last_service_tick')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(last_tick)).total_seconds() if last_tick else None
    result.update({'snapshot_created_at':utcnow(),
      'service_liveness':'recent recorded tick' if age is not None and 0<=age<=120 else 'tick missing or stale; inspect task',
      'service_liveness_scope':'Tick freshness only; does not verify sources, phone delivery or investment readiness',
      'funding_basis':get_state(store.conn,'funding_basis','manual ledger declaration; broker cash not independently verified'),
      'latest_ledger_backup':get_state(store.conn,'latest_ledger_backup'),
      'last_source_check':get_state(store.conn,'last_source_check'),
      'last_successful_source_check':get_state(store.conn,'last_successful_source_check'),
      'last_successful_source_check_scope':'Most recent pass where every configured source succeeded; individual source results follow',
      'last_service_tick':get_state(store.conn,'last_service_tick'),
      'source_failures':[dict(r) for r in store.conn.execute('SELECT * FROM monitor_failures')],
      'source_check_history':{'first_recorded_check':store.conn.execute('SELECT min(checked_at) FROM monitor_checks').fetchone()[0],
          'counts':[dict(r) for r in store.conn.execute('SELECT source,outcome,count(*) AS checks,sum(changes_detected) AS changes FROM monitor_checks GROUP BY source,outcome')],
          'per_source':[dict(r) for r in store.conn.execute("SELECT source,max(checked_at) AS last_attempt,max(CASE WHEN outcome IN ('baseline','changed','unchanged') THEN checked_at END) AS last_success,max(CASE WHEN outcome='failed' THEN checked_at END) AS last_failure FROM monitor_checks GROUP BY source ORDER BY source")],
          'scope':'History begins at refinement; earlier checks are not reconstructed. Counts do not establish materiality or document reading.'},
      'research_jobs':[dict(r) for r in store.conn.execute('SELECT id,company,status,attempts FROM monitor_jobs ORDER BY created_at DESC LIMIT 20')],
      'notifications':[dict(r) for r in store.conn.execute('SELECT id,state,error_code FROM transport_outbox ORDER BY created DESC LIMIT 20')],
      'telegram_configured':(STATE/'telegram.dpapi').exists(),
      'trial_started_at':trial_started,
      'trial_elapsed_days':((datetime.now(timezone.utc)-datetime.fromisoformat(trial_started)).days if trial_started else 0),
      'trial_acceptance':'pending; elapsed time does not approve research or recommendations',
      'reconciliation_required':bool(result['reconciliation_required']),
      'operational_reconciliation_note':reconciliation_note,
      'real_recommendations':'disabled; no activation command in this version',
      'coverage':'configured primary disclosures only; automatic price feed disabled',
      'setup':([] if result['funded'] else ['confirm £300 allocation funding'])+['define portfolio policy','verify research/model acceptance',
               'configure Telegram and test iPhone','complete 14-day observation trial','verify quote source']})
    return result

def render_status(store):
    status=full_status(store)
    write_json(STATE/'status.json',status)
    content=html.escape(json.dumps(status,indent=2,default=str))
    funding='£300 allocation declared by you; broker cash remains unverified.' if status['funded'] else '£300 is planned until the allocation is explicitly recorded.'
    def escaped(value): return html.escape(str(value))
    money=lambda value: 'Unavailable' if value is None else '£'+format(Decimal(value),'.2f')
    failures=''.join('<li><strong>'+escaped(x['source'])+'</strong>: '+escaped(x['reason'])+'</li>' for x in status['source_failures']) or '<li>No recorded retrieval failure. Coverage is still limited to configured sources.</li>'
    jobs=''.join('<li>'+escaped(x['company'])+' — '+escaped(x['status'])+'</li>' for x in status['research_jobs']) or '<li>No queued disclosure research.</li>'
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>£300 research observation</title><style>
    body{font:17px system-ui;max-width:1040px;margin:3rem auto;padding:0 1.5rem;background:#f4f6f8;color:#17212e;line-height:1.55}
    h1{font-size:2.2rem;line-height:1.15}h2{font-size:1.25rem}.notice{padding:1rem;background:#fff0cb;border-radius:12px}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin:1.5rem 0}.card,section,details{background:white;border:1px solid #dce2e9;border-radius:12px;padding:1.2rem}
    .card span{display:block;color:#586775}.card strong{display:block;font-size:1.7rem;margin-top:.3rem}section{margin-top:1rem}
    .small{font-size:.9rem;color:#586775}.stale{color:#9c351d;font-weight:700}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px monospace}summary{cursor:pointer}li{margin:.4rem 0}
    </style><h1>£300 research &amp; growth sleeve</h1>
    <p>Aggressive growth over days to a few months · manual Trading 212 orders</p>
    <p class="notice"><strong>Observation only — no current buy or sell instruction.</strong><br>'''+escaped(funding)+'''</p>
    <div class="cards"><div class="card"><span>Recorded cash</span><strong>'''+money(status['cash_gbp'])+'''</strong></div>
    <div class="card"><span>Cash available after orders</span><strong>'''+money(status['available_gbp'])+'''</strong></div>
    <div class="card"><span>Recorded gain / loss</span><strong>'''+money(status['gain_loss_gbp'])+'''</strong></div></div>
    <p class="small">Ledger values exclude unrelated ISA holdings. Investment marks are manual dated snapshots; these figures do not verify your broker balance.</p>
    <section><h2>Operating status</h2><p id="tick" data-tick="'''+escaped(status['last_service_tick'] or '')+'''">'''+escaped(status['service_liveness'])+'''</p>
    <p>Last recorded service tick: '''+escaped(status['last_service_tick'] or 'None')+'''<br>Last source check: '''+escaped(status['last_source_check'] or 'None')+'''</p>
    <p>Phone: '''+('credentials present; actual iPhone delivery still requires verification' if status['telegram_configured'] else 'awaiting private Telegram setup')+'''<br>Prices: manual input; independent price detection unavailable<br>Research acceptance: pilots remain partial</p>
    <p class="small">This is a snapshot generated at '''+escaped(status['snapshot_created_at'])+'''. Reopen or refresh it to load new records. A recent tick establishes neither complete source coverage nor trading readiness.</p></section>
    <section><h2>Source coverage gaps</h2><ul>'''+failures+'''</ul><p class="small">Coverage is limited to configured primary disclosure feeds. Metadata discovery does not establish that a full filing was read. Unilever UK coverage remains incomplete.</p></section>
    <section><h2>Research queue</h2><ul>'''+jobs+'''</ul><p>New drafts require evidence review and cannot approve a portfolio decision.</p></section>
    <section><h2>Next development</h2><p>Complete research foundations, validate the short-term opportunity and exit comparison, verify quotes and phone delivery, then finish the observation trial. See monitoring/IMPROVEMENT-ROADMAP.md.</p></section>
    <details><summary>Detailed audit snapshot</summary><pre>'''+content+'''</pre></details>
    <script>function tickAge(){const e=document.getElementById('tick');const t=Date.parse(e.dataset.tick);const a=(Date.now()-t)/1000;
    if(!Number.isFinite(a)||a<0||a>120){e.textContent='Snapshot tick is stale or unavailable — check the running service and reload this file.';e.className='stale';}
    else{e.textContent='Recent recorded tick ('+Math.floor(a)+' seconds before now).';e.className='';}}tickAge();setInterval(tickAge,5000);</script></html>'''
    page_path=STATE/'status.html'
    temp_page=page_path.with_name(page_path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp_page.write_text(page,encoding='utf-8'); temp_page.replace(page_path)
    return status

def bridge_notices(conn):
    init_transport(conn)
    for row in conn.execute("SELECT * FROM outbox WHERE status='pending'").fetchall():
        payload=json.loads(row['payload'])
        is_signal=payload.get('actionable') or payload.get('mode')=='model-signal'
        header='MODEL PORTFOLIO SIGNAL (£300 SLEEVE — MANUAL T212 EXECUTION)\n' if is_signal else 'OBSERVATION ONLY — DO NOT TRADE\n'
        body=payload.get('formatted_text') if isinstance(payload.get('formatted_text'),str) else json.dumps(payload,indent=2,ensure_ascii=False)
        text=(header+body)[:3900]
        if payload.get('status') in ('withdrawn','expired'):
            # Edit delivered original, then send separate historical withdrawal notice.
            original=conn.execute("SELECT t.message_id FROM outbox o JOIN transport_outbox t ON t.dedup_key='core:'||o.id WHERE o.alert_id=? AND t.message_id IS NOT NULL AND t.operation='send' ORDER BY o.created_at LIMIT 1",(row['alert_id'],)).fetchone()
            if original: enqueue_edit(conn,original[0],text,'core-edit:'+row['id'])
            # An undelivered original must not arrive as active after withdrawal.
            conn.execute("UPDATE transport_outbox SET state='superseded' WHERE state='pending' AND dedup_key IN (SELECT 'core:'||id FROM outbox WHERE alert_id=? AND id<>?)",(row['alert_id'],row['id']))
        enqueue_send(conn,text,'core:'+row['id'],{'inline_keyboard':[[{'text':'Check current status','callback_data':'status:'+str(row['alert_id'])}]]})
        conn.execute("UPDATE outbox SET status='staged' WHERE id=?",(row['id'],))
    conn.commit()

def telegram_handler(conn,update):
    store=Store.__new__(Store); store.conn=conn
    uid=str(update['update_id'])
    callback=update.get('callback_query')
    text=('/status '+callback.get('data','').split(':',1)[1]) if callback and callback.get('data','').startswith('status:') else update.get('message',{}).get('text','')
    try:
        args=shlex.split(text); command=args[0].split('@')[0] if args else ''
        if command in ('/start','/help'):
            result={'message':'Observation only. /status [alert-id]; /ack alert-id; /order alert-id buy|sell ticker quantity GBP-reserve order-id; /fill order-id execution-id quantity GBP-value GBP-fees; /cancel order-id. Fill reports count only after confirmation here. No order is placed by this bot.'}
        elif command=='/status': result=store.refresh_alert(args[1]) if len(args)==2 else full_status(store)
        elif command=='/ack' and len(args)==2: result=store.acknowledge(args[1])
        elif command=='/order' and len(args)==7: result=store.report_order(args[1],args[2],args[3],args[4],args[5],order_id=args[6])
        elif command=='/fill' and len(args)==6: result=store.capture_reported_fill(args[1],args[2],args[3],args[4],args[5])
        elif command=='/cancel' and len(args)==2: result=store.cancel_order(args[1])
        else: result={'error':'Unknown command or missing fields. Use /help.'}
    except (ValueError,IndexError) as exc: result={'error':str(exc)}
    # No credentials, model work or broker side effects in command transactions.
    enqueue_send(conn,('OBSERVATION ONLY — NO CURRENT TRADE APPROVAL\n'+json.dumps(result,indent=2,default=str))[:3900],'reply:'+uid)

def notification_preflight(conn,item):
    """Reject stale active core notices while holding the dispatch write lock.

    A delivered preview is still historical; this does not make it a trade approval.
    """
    if item['operation']!='send' or not item['dedup_key'].startswith('core:'): return True
    row=conn.execute('SELECT alert_id,payload FROM outbox WHERE id=?',(item['dedup_key'][5:],)).fetchone()
    if not row or not row['alert_id']: return False
    notice=json.loads(row['payload'])
    if notice.get('status') in ('withdrawn','expired'): return True
    current=conn.execute('SELECT status,payload FROM alerts WHERE id=?',(row['alert_id'],)).fetchone()
    if not current or current['status'] in ('withdrawn','expired'): return False
    expiry=json.loads(current['payload']).get('expires_at')
    return not expiry or datetime.fromisoformat(expiry)>datetime.now(timezone.utc)

def backup(conn,state_root=STATE):
    if conn.in_transaction: raise RuntimeError('Backup requires no pending transaction')
    day=datetime.now(timezone.utc).date().isoformat()
    path=Path(state_root)/'backups'/('operations-'+day+'.sqlite3')
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        with closing(sqlite3.connect(temp)) as destination: conn.backup(destination)
        temp.replace(path)
    # Preserve the daily opening snapshot and also refresh the ledger recovery
    # copy when substantive manual records change. Credentials remain separate.
    event=conn.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
    latest=path.parent/'latest-ledger.sqlite3'
    saved_event=None
    if latest.exists():
        try:
            # Inspect the snapshot itself: a process can die between filesystem
            # replacement and metadata commit, so metadata alone is insufficient.
            with closing(sqlite3.connect(latest.resolve().as_uri()+'?mode=ro',uri=True)) as saved:
                saved_event=saved.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
        except sqlite3.DatabaseError:
            saved_event=None  # Replace a broken latest copy from primary state.
    if saved_event is None or saved_event<event:
        temp=latest.with_name(latest.name+'.'+uuid.uuid4().hex+'.tmp')
        with closing(sqlite3.connect(temp)) as destination: conn.backup(destination)
        temp.replace(latest)
        set_state(conn,'backup_ledger_event',event)
        set_state(conn,'latest_ledger_backup',utcnow()); conn.commit()
    return path

def run_one_job(store,config):
    from observation_research import run_research,validate_observation
    row=store.conn.execute("SELECT * FROM monitor_jobs WHERE status='queued' AND (next_attempt IS NULL OR next_attempt<=?) ORDER BY created_at LIMIT 1",(utcnow(),)).fetchone()
    if not row or not config.get('research_enabled'): return None
    # Claim first; a restart marks this interrupted rather than pretending completion.
    claimed=store.conn.execute("UPDATE monitor_jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=? AND status='queued'",(utcnow(),row['id'])).rowcount; store.conn.commit()
    if not claimed: return None
    company=row['company']
    try:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',company):
            raise ValueError('Invalid company identity')
        job=json.loads(row['payload'])
        job['context_paths']=['AGENTS.md','README.md','methodology/current.json','methodology/company-research-v1.0.0.md',
          'methodology/principles.md','workflows/research.md','workflows/evidence.md','workflows/model-review.md',
          'lessons/confirmed.md','validation/status.json','validation/continuation.md']
        index_path=ROOT/f'companies/{company}/index.json'
        if index_path.is_file():
            job['context_paths'].append(f'companies/{company}/index.json')
            index=json.loads(index_path.read_text())
            if index.get('latest_active'): job['context_paths'].append(f"companies/{company}/runs/{index['latest_active']}/run.json")
        else:
            candidates=[item for item in config.get('watchlist',[]) if item.get('company')==company]
            contexts=candidates[0].get('research_context_paths') if len(candidates)==1 else None
            if not isinstance(contexts,list) or not contexts:
                raise FileNotFoundError('Missing company run or explicit discovery context')
            for context in contexts:
                if not isinstance(context,str): raise ValueError('Invalid discovery context')
                path=(ROOT/context).resolve()
                if not path.is_relative_to((ROOT/'monitoring/studies').resolve()) or path.suffix not in ('.json','.md') or not path.is_file():
                    raise ValueError('Discovery context must be a saved study within monitoring/studies')
                job['context_paths'].append(str(path.relative_to(ROOT.resolve())).replace('\\','/'))
            job['research_context_kind']='discovery-screen-only; no approved company run or investment selection'
        job['sources']=job.pop('changes',[])
        result=run_research(ROOT,job,state_root=STATE)
    except Exception as exc: result={'status':'failed','reason':type(exc).__name__,'continuation_required':True}
    success=result.get('status')=='needs-review' and not result.get('continuation_required',True)
    excerpt=''
    if success:
        try:
            draft_path=Path(result['result_path']).resolve()
            if not draft_path.is_relative_to(STATE.resolve()) or not draft_path.is_file():
                raise ValueError('Missing or uncontained draft')
            draft=validate_observation(json.loads(draft_path.read_text(encoding='utf-8')),ROOT)
            links=sorted({s['uri'] for o in draft.get('observations',[]) for s in o.get('sources',[]) if s.get('uri','').startswith('https://')})
            excerpt='\nDRAFT — AWAITS EVIDENCE REVIEW\n'+draft.get('summary','')[:1800]+'\n'+'\n'.join(links[:4])
        except (ValueError,OSError,TypeError,KeyError):
            success=False
            result={'status':'failed','reason':'saved draft unavailable or invalid; inspect checkpoint','continuation_required':True,'analytical_approval':False}
    status='awaiting-review' if success else ('deferred' if row['attempts']>=4 else 'queued')
    next_attempt=None if success else (datetime.now(timezone.utc)+timedelta(hours=6)).isoformat()
    store.conn.execute('UPDATE monitor_jobs SET status=?,result=?,updated_at=?,next_attempt=? WHERE id=?',
       (status,json.dumps(result),utcnow(),next_attempt,row['id']))
    enqueue_send(store.conn,('RESEARCH UPDATE — OBSERVATION ONLY\n'+company+excerpt+'\n'+json.dumps(result,default=str))[:3900],'job:'+row['id']+':'+str(row['attempts']+1))
    store.conn.commit()
    return result

def tick(store,config,*,force=False,models=True,network=True):
    init_monitor(store.conn); init_transport(store.conn); store.conn.commit()
    current=utcnow(); previous=get_state(store.conn,'last_service_tick')
    if not get_state(store.conn,'trial_started_at'): set_state(store.conn,'trial_started_at',current)
    if previous and datetime.fromisoformat(current)-datetime.fromisoformat(previous)>timedelta(hours=24):
        set_state(store.conn,'reconciliation_required','extended downtime; resend unconfirmed fills and reconcile broker orders')
    set_state(store.conn,'last_service_tick',current); store.conn.commit()
    if hasattr(store,'expire_alerts'): store.expire_alerts()
    slot=due_slot(config)
    if network and (force or get_state(store.conn,'last_due_slot')!=slot):
        result=check_sources(store.conn,config,STATE)
        set_state(store.conn,'last_due_slot',slot)
        fingerprint=hashlib.sha256(json.dumps(result['failures'],sort_keys=True).encode()).hexdigest()
        if result['failures'] and fingerprint!=get_state(store.conn,'failure_notice'):
            enqueue_send(store.conn,'MONITORING GAP — OBSERVATION ONLY\n'+json.dumps(result['failures']),'failure:'+slot+':'+fingerprint)
        if not result['failures'] and get_state(store.conn,'had_source_failures')=='True':
            enqueue_send(store.conn,'MONITORING RECOVERY — configured sources retrieved successfully; coverage remains limited and no trading instruction is active.','recovery:'+slot)
        set_state(store.conn,'had_source_failures',bool(result['failures']))
        set_state(store.conn,'failure_notice',fingerprint)
        store.conn.commit()
    iso=datetime.now(timezone.utc).isocalendar(); week=f'{iso.year}-W{iso.week}'
    if get_state(store.conn,'digest_week')!=week:
        enqueue_send(store.conn,'WEEKLY OBSERVATION STATUS\n'+json.dumps(full_status(store),default=str)[:3500],'digest:'+week)
        set_state(store.conn,'digest_week',week); store.conn.commit()
    bridge_notices(store.conn)
    secret=STATE/'telegram.dpapi'
    if network and secret.exists():
        try:
            client=load_credentials(secret)
            ingest_updates(store.conn,client,telegram_handler)
            bridge_notices(store.conn)
            dispatch_outbox(store.conn,client,preflight=notification_preflight)
            set_state(store.conn,'transport_error','')
            set_state(store.conn,'last_transport_attempt',utcnow()); store.conn.commit()
        except Exception as exc:
            set_state(store.conn,'transport_error',type(exc).__name__+'; credentials/network/setup need attention'); store.conn.commit()
    if network and models: run_job_safely(store,config)
    backup(store.conn)
    return render_status(store)

def run_job_safely(store,config):
    """A failed finalisation must not strand a claimed job until Windows restarts."""
    try: return run_one_job(store,config)
    except Exception as exc:
        store.conn.rollback()
        reason={'status':'interrupted','reason':type(exc).__name__+' during worker finalisation; inspect saved draft before retry',
                'continuation_required':True,'analytical_approval':False}
        store.conn.execute("UPDATE monitor_jobs SET status='interrupted',result=?,updated_at=? WHERE status='running'",
                           (json.dumps(reason),utcnow()))
        store.conn.commit()
        return reason

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    for name in ('init','status','daemon','backup'): sub.add_parser(name)
    t=sub.add_parser('tick'); t.add_argument('--force',action='store_true'); t.add_argument('--no-models',action='store_true'); t.add_argument('--offline',action='store_true')
    f=sub.add_parser('fund'); f.add_argument('--amount',default='300')
    for name in ('quote','fx-quote'): sub.add_parser(name).add_argument('json_file')
    ta=sub.add_parser('trial-alert'); ta.add_argument('json_file'); ta.add_argument('--force',action='store_true'); ta.add_argument('--model-signal',action='store_true')
    ss=sub.add_parser('send-signal'); ss.add_argument('--json',dest='json_file'); ss.add_argument('--text'); ss.add_argument('--id',dest='alert_id'); ss.add_argument('--ticker'); ss.add_argument('--verdict',default='ACTIONABLE_BUY_SIGNAL')
    sub.add_parser('ack').add_argument('alert_id')
    w=sub.add_parser('withdraw'); w.add_argument('alert_id'); w.add_argument('reason')
    o=sub.add_parser('order'); o.add_argument('alert_id'); o.add_argument('side',choices=['buy','sell']); o.add_argument('ticker'); o.add_argument('quantity'); o.add_argument('--reserve-gbp',default='0'); o.add_argument('--order-id',required=True)
    f=sub.add_parser('fill'); f.add_argument('order_id'); f.add_argument('execution_id'); f.add_argument('quantity'); f.add_argument('gbp_value'); f.add_argument('--fees-gbp',default='0')
    sub.add_parser('cancel').add_argument('order_id')
    c=sub.add_parser('cash-event'); c.add_argument('event_id'); c.add_argument('kind',choices=['dividend','fee']); c.add_argument('amount_gbp'); c.add_argument('--ticker')
    sub.add_parser('configure-telegram')
    sub.add_parser('retry-job').add_argument('job_id')
    sub.add_parser('reconcile').add_argument('note')
    args=p.parse_args(); STATE.mkdir(parents=True,exist_ok=True); config=read_config()
    if args.command=='configure-telegram':
        token=getpass.getpass('Telegram bot token (hidden): '); chat=input('Allowed private chat ID: ').strip()
        configure_credentials(STATE/'telegram.dpapi',token,chat)
        print('Credentials protected locally. No messages sent; run tick to test transport.'); return
    with Store(DB) as store:
        init_monitor(store.conn); init_transport(store.conn); store.conn.commit()
        if args.command=='daemon':
            from concurrent.futures import ThreadPoolExecutor
            with engine_lock(wait_seconds=10):
                recover_jobs(store.conn)
                executor=ThreadPoolExecutor(max_workers=1)
                research_future=None
                def worker():
                    with Store(DB) as worker_store:
                        return run_job_safely(worker_store,config)
                while True:
                    try:
                        tick(store,config,models=False)
                        if research_future is None or research_future.done():
                            if research_future is not None:
                                try: research_future.result()
                                except Exception as exc:
                                    write_json(STATE/'research-worker-error.json',{'time':utcnow(),'error':type(exc).__name__})
                            research_future=executor.submit(worker)
                    except Exception as exc:
                        store.conn.rollback()
                        write_json(STATE/'service-error.json',{'time':utcnow(),'error':type(exc).__name__,'actionable':False})
                    time.sleep(config['service_interval_seconds'])
        elif args.command=='tick':
            with engine_lock(wait_seconds=10): result=tick(store,config,force=args.force,models=not args.no_models,network=not args.offline)
        elif args.command in ('init','status'): result=render_status(store)
        elif args.command=='backup': result={'backup':str(backup(store.conn))}
        elif args.command=='fund': result=store.confirm_funding(args.amount)
        elif args.command in ('quote','fx-quote'):
            payload=json.loads(Path(args.json_file).read_text(encoding='utf-8-sig'))
            handlers={'quote':store.quote,'fx-quote':store.fx_quote}
            result=handlers[args.command](payload)
        elif args.command=='trial-alert':
            payload=json.loads(Path(args.json_file).read_text(encoding='utf-8-sig'))
            force_signal=bool(getattr(args,'force',False) or getattr(args,'model_signal',False))
            result=store.create_trial_alert(payload,force=force_signal)
            bridge_notices(store.conn)
            secret=STATE/'telegram.dpapi'
            if force_signal and secret.exists():
                client=load_credentials(secret)
                dispatch_outbox(store.conn,client,preflight=notification_preflight)
        elif args.command=='send-signal':
            if args.json_file:
                payload=json.loads(Path(args.json_file).read_text(encoding='utf-8-sig'))
            elif args.text:
                payload={'formatted_text':args.text,'verdict':args.verdict}
                if args.ticker: payload['ticker']=args.ticker
            else:
                raise ValueError('send-signal requires either --json <file> or --text "<message>"')
            if args.alert_id: payload['id']=args.alert_id
            payload['mode']='model-signal'
            payload['actionable']=True
            result=store.create_signal_alert(payload)
            bridge_notices(store.conn)
            secret=STATE/'telegram.dpapi'
            if secret.exists():
                client=load_credentials(secret)
                sent=dispatch_outbox(store.conn,client,preflight=notification_preflight)
                result['telegram_dispatch']=sent
            else:
                result['telegram_dispatch']='staged_in_outbox (run configure-telegram to enable live delivery)'
        elif args.command=='ack': result=store.acknowledge(args.alert_id)
        elif args.command=='withdraw': result=store.withdraw(args.alert_id,args.reason)
        elif args.command=='order': result=store.report_order(args.alert_id,args.side,args.ticker,args.quantity,args.reserve_gbp,order_id=args.order_id)
        elif args.command=='fill': result=store.capture_reported_fill(args.order_id,args.execution_id,args.quantity,args.gbp_value,args.fees_gbp)
        elif args.command=='cancel': result=store.cancel_order(args.order_id)
        elif args.command=='cash-event': result=store.record_cash_event(args.event_id,args.kind,args.amount_gbp,args.ticker)
        elif args.command=='retry-job':
            count=store.conn.execute("UPDATE monitor_jobs SET status='queued',next_attempt=NULL,updated_at=? WHERE id=? AND status IN ('interrupted','deferred')",(utcnow(),args.job_id)).rowcount
            store.conn.commit()
            if not count: raise ValueError('Only interrupted or deferred jobs can be requeued')
            result={'requeued':args.job_id,'actionable':False}
        elif args.command=='reconcile':
            if not args.note.strip(): raise ValueError('A reconciliation note is required')
            set_state(store.conn,'reconciliation_required',''); set_state(store.conn,'last_reconciliation',utcnow())
            store._event('manual_reconciliation',{'note':args.note}); store.conn.commit()
            result={'recorded':True,'actionable':False}
        if args.command in ('fund','quote','fx-quote','trial-alert','send-signal','ack','withdraw','order','fill','cancel','cash-event','reconcile'):
            backup(store.conn)
        if args.command not in ('status','init','tick'): render_status(store)
        print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':
    try: main()
    except (ValueError, OSError) as exc:
        if sys.stderr is not None: print(json.dumps({'error':str(exc),'actionable':False}),file=sys.stderr)
        else: write_json(STATE/'startup-error.json',{'time':utcnow(),'error':type(exc).__name__,'actionable':False})
        sys.exit(1)
    except Exception as exc:
        write_json(STATE/'startup-error.json',{'time':utcnow(),'error':type(exc).__name__,'actionable':False})
        if sys.stderr is not None: raise
        sys.exit(1)
