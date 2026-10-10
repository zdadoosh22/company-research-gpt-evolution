"""Scoped author source/definition/calendar checks; not an independent review or event test."""
from pathlib import Path
import hashlib,json,re,datetime,urllib.robotparser
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from html import unescape
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'monitoring/studies/evidence/2026-10-10-netflix-protocol-r001'
ref=json.loads((F/'frozen-reference-r001.json').read_text())
reg=json.loads((F/'source-retrieval-register.json').read_text())
src={r['id']:r for r in reg['records']};checks=[]
def check(name,ok,evidence): checks.append({'name':name,'passed':bool(ok),'evidence':evidence})
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def raw(key): return (ROOT/src[key]['local_raw_path']).read_text(encoding='utf-8')
def text(key): return re.sub(r'\s+',' ',unescape(re.sub('<[^>]+>',' ',raw(key)))).strip()
def table(key,heading):
 s=raw(key).split(heading,1)[1];s=s[s.index('<table'):s.index('</table>')]
 return [[re.sub(r'\s+',' ',unescape(re.sub('<[^>]+>',' ',c))).strip() for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S)] for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',s,re.S)]
baseline=json.loads((ROOT/'validation/netflix-protocol-baseline-2026-10-10-r001.json').read_text())
check('All predecessor bytes preserved',all(sha(ROOT/r['path'])==r['sha256'] for r in baseline['predecessors']),len(baseline['predecessors']))
check('Ten captured source hashes match local bytes',len(src)==10 and all(sha(ROOT/r['local_raw_path'])==r['raw_sha256'] for r in src.values()),list(src))
old=json.loads((ROOT/'monitoring/studies/evidence/2026-10-10-netflix-expectations-gate-r001/source-retrieval-register.json').read_text())
oldsrc={r['id']:r for r in old['records']}
letter=ROOT/oldsrc['july-letter']['path'];pages=PdfReader(letter).pages
p1=re.sub(r'\s+',' ',pages[0].extract_text());p2=re.sub(r'\s+',' ',pages[1].extract_text());p12=re.sub(r'\s+',' ',pages[11].extract_text())
check('Management source identity and guidance provenance',sha(letter)==ref['management']['source_sha256'] and all(x in p1 for x in ['12,860','4,268','33.2%','$0.82']) and 'actual internal forecast' in p2,{'path':oldsrc['july-letter']['path'],'sha256':sha(letter)})
check('Issuer cash definition and unit conversion',all(x in p12 for x in ['1,743,812','218,644','1,525,168']) and D('1743.812')-D('218.644')==D('1525.168'),'CFO less property/equipment; source thousands converted USDm; not FCFE')
check('Guidance arithmetic uses compatible units',D('51000')*D('.315')==D('16065') and D('51400')*D('.315')==D('16191') and round(D('4268')/D('12860')*100,1)==D('33.2'),'Derived FY OI 16,065–16,191; Q3 rounded margin 33.2%')
check('Fresh Yahoo tables bound exactly',table('yahoo-analysis','Revenue Estimate')==ref['yahoo_reference']['revenue_table'] and table('yahoo-analysis','Earnings Estimate')==ref['yahoo_reference']['eps_table'],{'actual_estimate_update_time':ref['yahoo_reference']['actual_estimate_update_time']})
sel=raw('yahoo-analysis').split('Earnings Estimate',1)[1].split('<table',1)[0]
check('Yahoo GAAP actually selected; Normalized not assumed',bool(re.search(r'<input checked type="checkbox" value="gaap"',sel)) and not re.search(r'<input checked[^>]*value="normalized"',sel),'Publisher control only; no analyst reconciliation')
check('Annual estimates actual date and adjusted EPS qualification',all(x in text('annual-forecast') for x in ['Last updated: Oct 8, 2026','EPS and Forward PE are based on non-GAAP adjusted numbers.','16.12B','12.81B']),'Financial date differs from price and retrieval dates')
robot=urllib.robotparser.RobotFileParser();robot.parse(raw('robots').splitlines())
paths=[r['url'] for r in src.values() if r['url'].startswith('https://stockanalysis.com/')]
check('Explicit AI exception and actual robot paths',ref['permissions']['ai_exception_excerpt'] in text('terms') and all(robot.can_fetch(ref['permissions']['named_agent'],u) for u in paths),paths)
for sample in ref['price_feasibility_samples']:
 t=table(sample['id'],'Historical Data')
 check(sample['id']+' displayed OHLC and split statement',t[0]==sample['headers'] and t[1]==sample['sample_row'] and sample['split_statement'] in text(sample['id']),{'row':t[1],'scope':'source sample only; no returns'})
check('Data publisher timestamp/official-close claims present',all(x in text('data-sources').lower() for x in ['nasdaq','utp','15-minute','eastern']),'Publisher definitions do not independently certify any individual close')
event=datetime.datetime(2026,10,20,13,1,tzinfo=ZoneInfo('America/Los_Angeles'))
check('Event still prospective and original schedule present',datetime.datetime.fromisoformat(ref['frozen_at_utc'])<event and all(x in text('event') for x in ['October 20th, 2026','1:01 p.m. Pacific Time','1:45 p.m. Pacific Time']),{'scheduled_release_utc':event.astimezone(ZoneInfo('UTC')).isoformat()})
check('All new retrievals precede freeze and release',all(datetime.datetime.fromisoformat(r['retrieved_at_utc'])<=datetime.datetime.fromisoformat(ref['frozen_at_utc'])<event for r in src.values()),ref['frozen_at_utc'])
calpath=ROOT/oldsrc['nasdaq-schedule']['path'];cal=re.sub(r'\s+',' ',unescape(re.sub('<[^>]+>',' ',calpath.read_text(encoding='utf-8'))))
start=cal.index('2026 U.S. Stock Market Holiday Schedule');end=cal.index('Download Calendars',start);hol=cal[start:end]
check('Official calendar confirms no scheduled closures in observation envelope','November 26, 2026' in hol and not re.search(r'October \d+, 2026|November (?:[1-9]|1[0-7]), 2026',hol),{'url':oldsrc['nasdaq-schedule']['url'],'sha256':sha(calpath),'last_pre_window_holiday':'2026-09-07','next_holiday':'2026-11-26'})
sessions=[];day=datetime.date(2026,10,21)
while len(sessions)<20:
 if day.weekday()<5: sessions.append(day.isoformat())
 day+=datetime.timedelta(days=1)
expected={'reference':'2026-10-20',**{'D'+str(n):sessions[n-1] for n in (1,2,5,20)}}
check('Daily windows session counts and named zones',all(w['scheduled_session_date']==expected[w['label']] and datetime.datetime.fromisoformat(w['research_close_eastern']).astimezone(ZoneInfo('UTC')).isoformat()==w['utc'] and datetime.datetime.fromisoformat(w['research_close_eastern']).astimezone(ZoneInfo('Europe/London')).isoformat()==w['london'] for w in ref['predeclared_windows']),ref['predeclared_windows'])
check('No future observations in frozen windows',all(w['price_value'] is None for w in ref['predeclared_windows']),'No C0/D1/D2/D5/D20 event prices, returns or fills')
config=json.loads((ROOT/'monitoring/config.json').read_text())
check('Operational boundary unchanged',config['mode']=='observation-only' and config['quote_acquisition']=='manual-only','Config preserved by all-predecessor hash check; no phone/broker/monitor change')
output={'schema':'netflix-protocol-author-checks-v1','verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'passed':all(c['passed'] for c in checks),'scope':'Source binding, definitions, calendar/time arithmetic and predecessor preservation only. Not independent Astra review, model replay, engineering acceptance, event investigation or investment performance.'}
(ROOT/'validation/netflix-pre-event-protocol-verification-2026-10-10-r001.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':output['passed'],'checks':len(checks),'failed':[c['name'] for c in checks if not c['passed']]}))
raise SystemExit(0 if output['passed'] else 1)
