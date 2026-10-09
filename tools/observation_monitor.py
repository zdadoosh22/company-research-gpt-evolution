"""Primary-document change detection. Baselines are observations, never approval."""
import hashlib
import html
import json
import re
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

MAX_BYTES = 8_000_000
PRIMARY_HOSTS = {'data.sec.gov','www.sec.gov','www.unilever.com'}

def approved_url(url):
    parsed=urlparse(url)
    return (parsed.scheme=='https' and parsed.hostname in PRIMARY_HOSTS
            and parsed.username is None and parsed.password is None
            and parsed.port in (None,443))

class PrimaryRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        # Validate before contacting the redirected destination.
        if not approved_url(newurl): raise ValueError('Unapproved primary-source redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def init_monitor(conn):
    statements='''
    CREATE TABLE IF NOT EXISTS monitor_state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS source_documents(id TEXT PRIMARY KEY,company TEXT NOT NULL,
      url TEXT NOT NULL,publication_date TEXT, fetched_at TEXT NOT NULL, sha256 TEXT NOT NULL,
      archive_path TEXT NOT NULL, baseline INTEGER NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS monitor_jobs(id TEXT PRIMARY KEY,company TEXT NOT NULL,
      status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,payload TEXT NOT NULL,
      result TEXT,attempts INTEGER NOT NULL DEFAULT 0,next_attempt TEXT);
    CREATE TABLE IF NOT EXISTS monitor_failures(source TEXT PRIMARY KEY,reason TEXT NOT NULL,
      first_seen TEXT NOT NULL,last_seen TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS monitor_checks(id TEXT PRIMARY KEY,source TEXT NOT NULL,
      checked_at TEXT NOT NULL,outcome TEXT NOT NULL,documents_seen INTEGER NOT NULL,
      changes_detected INTEGER NOT NULL,duration_ms INTEGER NOT NULL,reason TEXT);
    '''
    # Individual statements preserve a surrounding Telegram command transaction.
    for statement in statements.split(';'):
        if statement.strip(): conn.execute(statement)

def get_state(conn,key,default=None):
    row=conn.execute('SELECT value FROM monitor_state WHERE key=?',(key,)).fetchone()
    return row[0] if row else default

def set_state(conn,key,value):
    conn.execute('INSERT INTO monitor_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))

def due_slot(config, now=None):
    local=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(config['timezone']))
    due=[t for t in config['check_times'] if t <= local.strftime('%H:%M')]
    # Before today's first slot, catch up yesterday's last slot after restart.
    if not due:
        from datetime import timedelta
        return (local.date()-timedelta(days=1)).isoformat()+'T'+max(config['check_times'])
    return local.date().isoformat()+'T'+max(due)

def fetch(url,user_agent):
    if not approved_url(url):
        raise ValueError('Unapproved primary-source host')
    req=Request(url,headers={'User-Agent':user_agent,'Accept':'application/json,text/html'})
    with build_opener(PrimaryRedirects()).open(req,timeout=30) as response:
        if not approved_url(response.url):
            raise ValueError('Unapproved redirect')
        body=response.read(MAX_BYTES+1)
    if len(body)>MAX_BYTES: raise ValueError('Source size limit exceeded')
    return body

def filings(body, item):
    data=json.loads(body)
    if int(data['cik'])!=int(item['cik']) or item['expected_name'].upper() not in data['name'].upper():
        raise ValueError('Issuer identity mismatch')
    recent=data['filings']['recent']
    fields=('accessionNumber','filingDate','form','primaryDocument')
    if len({len(recent[k]) for k in fields})!=1: raise ValueError('Inconsistent submission arrays')
    result=[]
    for accession,day,form,document in zip(*(recent[k] for k in fields)):
        if form not in {'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','20-F','20-F/A','6-K','DEF 14A'}: continue
        if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or '/' in document or '..' in document:
            raise ValueError('Invalid SEC filing identity')
        datetime.strptime(day,'%Y-%m-%d')
        result.append({'id':item['cik']+':'+accession,'publication_date':day,'form':form,
          'url':f"https://www.sec.gov/Archives/edgar/data/{int(item['cik'])}/{accession.replace('-','')}/{document}"})
    return result

def normalized_page(body):
    text=body.decode('utf-8',errors='replace')
    text=re.sub(r'<(script|style|nav|footer)\b[^>]*>.*?</\1>',' ',text,flags=re.S|re.I)
    main=re.search(r'<main\b[^>]*>(.*?)</main>',text,re.S|re.I)
    text=main.group(1) if main else text
    # A new report can keep its visible label while its document link changes.
    links=sorted({html.unescape(match[1]).strip() for match in
        re.findall(r'href\s*=\s*([\"\'])(.*?)\1',text,re.S|re.I)
        if match[1].strip() and not match[1].strip().lower().startswith(('#','javascript:','mailto:'))})
    text=html.unescape(re.sub(r'<[^>]+>',' ',text))
    text=' '.join(text.split())
    if len(text)<100: raise ValueError('Insufficient source text; possible access challenge')
    if any(s in text.lower() for s in ('verify you are human','access denied','captcha')):
        raise ValueError('Source access challenge')
    return text+'\nDOCUMENT LINKS\n'+'\n'.join(links)

def queue_job(conn,company,changes):
    existing=conn.execute("SELECT id,payload FROM monitor_jobs WHERE company=? AND status='queued'",(company,)).fetchone()
    now=utcnow()
    if existing:
        payload=json.loads(existing['payload'])
        known={x['id'] for x in payload['changes']}
        payload['changes'].extend(c for c in changes if c['id'] not in known)
        conn.execute('UPDATE monitor_jobs SET payload=?,updated_at=? WHERE id=?',(json.dumps(payload),now,existing['id']))
        return existing['id']
    ident=hashlib.sha256((company+now).encode()).hexdigest()[:24]
    payload={'job_id':ident,'company':company,'changes':changes,'question':
      'Read the newly detected primary sources. Determine what changed, evidence gaps, materiality, and whether focused update or full reassessment is needed. No investment recommendation. Preserve partial pilot boundaries.'}
    conn.execute('INSERT INTO monitor_jobs(id,company,status,created_at,updated_at,payload) VALUES(?,?,?,?,?,?)',
                 (ident,company,'queued',now,now,json.dumps(payload)))
    return ident

def check_sources(conn,config,state_root,fetcher=fetch):
    if conn.in_transaction: raise RuntimeError('Source monitoring requires no pending transaction')
    init_monitor(conn)
    archive=Path(state_root)/'sources'; archive.mkdir(parents=True,exist_ok=True)
    changes=[]; failures=[]; checked=[]
    sources=[dict(x,id='sec-'+x['cik'],url='https://data.sec.gov/submissions/CIK'+x['cik']+'.json',kind='sec') for x in config['watchlist']]
    sources.extend(dict(x,kind='page') for x in config.get('pages',[]))
    for item in sources:
        started=time.monotonic()
        now=utcnow()
        conn.execute('SAVEPOINT source_pass')
        try:
            body=fetcher(item['url'],config['sec_user_agent'])
            digest=hashlib.sha256(body).hexdigest()
            name=digest+('.json' if item['kind']=='sec' else '.html')
            path=archive/name
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                    raise ValueError('Existing immutable source archive fails integrity')
            else:
                temporary=archive/(name+'.'+uuid.uuid4().hex+'.tmp')
                try:
                    temporary.write_bytes(body)
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
            prior=get_state(conn,'baseline:'+item['id'])
            if item['kind']=='sec': documents=filings(body,item)
            else:
                fingerprint=hashlib.sha256(normalized_page(body).encode()).hexdigest()
                previous=get_state(conn,'fingerprint:'+item['id'])
                if previous is None and prior is not None:
                    latest=conn.execute('SELECT payload FROM source_documents WHERE id LIKE ? ORDER BY fetched_at DESC LIMIT 1',(item['id']+':%',)).fetchone()
                    if latest: previous=json.loads(latest[0])['id'].split(':')[-1]
                documents=[] if fingerprint==previous else [{'id':item['id']+':'+uuid.uuid4().hex,
                  'url':item['url'],'publication_date':None,'form':'page-change-unclassified',
                  'fingerprint':fingerprint,'previous_fingerprint':previous}]
                set_state(conn,'fingerprint:'+item['id'],fingerprint)
            detected=[]
            for document in documents:
                if document['publication_date'] and document['publication_date']>now[:10]: continue
                seen=conn.execute('SELECT 1 FROM source_documents WHERE id=?',(document['id'],)).fetchone()
                if seen: continue
                document.update({'company':item['company'],'retrieved_at':now,'source_index_url':item['url'],
                  'archive_path':str(path),'sha256':digest,'source_read':False})
                conn.execute('INSERT INTO source_documents VALUES(?,?,?,?,?,?,?,?,?)',
                  (document['id'],item['company'],document['url'],document['publication_date'],now,digest,str(path),int(prior is None),json.dumps(document)))
                if prior is not None: detected.append(document)
            if detected:
                queue_job(conn,item['company'],detected); changes.extend(detected)
            set_state(conn,'baseline:'+item['id'],now)
            set_state(conn,'checked:'+item['id'],now)
            conn.execute('DELETE FROM monitor_failures WHERE source=?',(item['id'],))
            checked.append(item['id'])
            conn.execute('INSERT INTO monitor_checks VALUES(?,?,?,?,?,?,?,?)',
              (uuid.uuid4().hex,item['id'],now,'baseline' if prior is None else ('changed' if detected else 'unchanged'),
               len(documents),len(detected),int((time.monotonic()-started)*1000),None))
            conn.execute('RELEASE SAVEPOINT source_pass')
        except Exception as exc:
            conn.execute('ROLLBACK TO SAVEPOINT source_pass')
            conn.execute('RELEASE SAVEPOINT source_pass')
            # Source IDs and exception classes suffice; never dump response content or credentials.
            reason=type(exc).__name__+(f' HTTP {exc.code}' if isinstance(exc,HTTPError) else '')+': source retrieval/validation failed'
            conn.execute('INSERT INTO monitor_failures VALUES(?,?,?,?) ON CONFLICT(source) DO UPDATE SET reason=excluded.reason,last_seen=excluded.last_seen',
                        (item['id'],reason,now,now))
            failures.append({'source':item['id'],'reason':reason})
            conn.execute('INSERT INTO monitor_checks VALUES(?,?,?,?,?,?,?,?)',
              (uuid.uuid4().hex,item['id'],now,'failed',0,0,int((time.monotonic()-started)*1000),reason))
            # Release the failure write before a later source's potentially slow
            # HTTP request, so manual fills/cancellations can be recorded promptly.
            conn.commit()
    set_state(conn,'last_source_check',utcnow())
    if not failures: set_state(conn,'last_successful_source_check',utcnow())
    conn.commit()
    return {'changed':changes,'failures':failures,'checked':checked,'coverage':'configured primary sources only; not exhaustive news coverage'}

def recover_jobs(conn):
    now=utcnow()
    conn.execute("UPDATE monitor_jobs SET status='interrupted',updated_at=?,result=? WHERE status='running'",(now,json.dumps({'reason':'service restarted; preserve work and reconcile before retry'})))
    set_state(conn,'restart_at',now)
    conn.commit()
