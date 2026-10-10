"""Targeted evidence/definition checks. No model replay, strategy test or execution."""
from pathlib import Path
import hashlib,json,re,datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from html import unescape
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'monitoring/studies/evidence/2026-10-10-netflix-expectations-gate-r001'
records=json.loads((F/'source-retrieval-register.json').read_text(encoding='utf-8'))['records']
src={r['id']:r for r in records};results=[]
def check(name,condition,detail):
 results.append({'name':name,'passed':bool(condition),'detail':detail})
def text(key):return re.sub(r'\s+',' ',(F/(key+'.derived.txt')).read_text(encoding='utf-8'))
def raw(key):return (ROOT/src[key]['path']).read_text(encoding='utf-8')
baseline=json.loads((ROOT/'validation/netflix-expectations-gate-baseline-2026-10-10-r001.json').read_text())
check('505 original tracked files preserved',all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in baseline['predecessors']),len(baseline['predecessors']))
check('Nine new raw archives match retrieval hashes',all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in records),len(records))
check('July PDF identical to reviewed predecessor',src['july-letter']['sha256']=='8441bb4517a6c37a25495bbf189a8d3f6ca1958b4764bb64bdf646e29b9e9241',src['july-letter']['sha256'])
pages=PdfReader(ROOT/src['july-letter']['path']).pages
page1=re.sub(r'\s+',' ',pages[0].extract_text());page2=re.sub(r'\s+',' ',pages[1].extract_text());page12=re.sub(r'\s+',' ',pages[11].extract_text())
check('July guide table and management provenance actually present',all(v in page1 for v in ['12,860','4,268','33.2%','$0.82']) and 'actual internal forecast' in page2,'Q3 USDm; GAAP diluted EPS, guidance not consensus')
check('Issuer FCF bridge source and arithmetic',all(v in page12 for v in ['1,743,812','218,644','1,525,168']) and D('1743.812')-D('218.644')==D('1525.168'),'Printed p12 figures thousands; record converts to USDm')
def table(key,heading):
 content=raw(key);start=content.index(heading);fragment=content[start:];fragment=fragment[fragment.index('<table'):fragment.index('</table>')]
 output=[]
 for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',fragment,re.S):
  row=[re.sub(r'\s+',' ',unescape(re.sub('<[^>]+>',' ',c))).strip() for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S)]
  output.append(row)
 return output
rev=table('yahoo-analysis','Revenue Estimate');eps=table('yahoo-analysis','Earnings Estimate')
revdict={r[0]:r[1:] for r in rev[1:]};epsdict={r[0]:r[1:] for r in eps[1:]}
check('Yahoo quarter revenue table headers and facts',rev[0][1]=='Current Qtr. (Sep 2026)' and revdict['Avg. Estimate'][0]=='12.88B' and revdict['No. of Analysts'][0]=='38',rev)
check('Yahoo GAAP selection and quarterly EPS facts',bool(re.search(r'<input checked type="checkbox" value="gaap"',raw('yahoo-analysis').split('Earnings Estimate',1)[1].split('<table',1)[0])) and epsdict['Avg. Estimate'][0]=='0.82' and epsdict['No. of Analysts'][0]=='35',eps)
check('Annual estimates date and adjusted EPS qualification',all(v in text('annual-estimates') for v in ['Last updated: Oct 8, 2026','EPS and Forward PE are based on non-GAAP adjusted numbers.','16.12B','12.81B']),'Explicit Oct8 forecast date; price dates separate')
check('MarketBeat split-basis defect observable',all(v in text('quarterly-estimates') for v in ['Prior-Year EPS $5.87','-86.0%']) and 'November 17, 2025' in text('split') and '$0.59' in page1,'5.87/10=0.587 versus rounded July Q3 2025 0.59; no vendor definition repair')
check('Guide/provider scale arithmetic',D('51000')*D('.315')==D('16065') and D('51400')*D('.315')==D('16191') and D('16065')<=D('16120')<=D('16191'),'FY OI interval contains provider; does not certify adjustment basis')
times=[]
for hour,minute in [(13,1),(13,45)]:
 event=datetime.datetime(2026,10,20,hour,minute,tzinfo=ZoneInfo('America/Los_Angeles'))
 times.append({'pacific':event.isoformat(),'utc':event.astimezone(ZoneInfo('UTC')).isoformat(),'london':event.astimezone(ZoneInfo('Europe/London')).isoformat()})
check('Primary event schedule and named-zone conversion','October 20th, 2026' in text('event') and '1:01 p.m. Pacific Time' in text('event') and '1:45 p.m. Pacific Time' in text('event') and times[0]['london']=='2026-10-20T21:01:00+01:00',times)
check('Nasdaq source establishes hours but not historical prices','9:30 am Eastern' in text('nasdaq-schedule') and 'Closes: 4:00 pm Eastern' in text('nasdaq-schedule') and 'Historical Data is currently not available' in text('nasdaq-history'),'Public shell is not working data feed')
sub=json.loads(raw('sec-submissions'));q=sub['filings']['recent'];i=q['form'].index('10-Q')
check('Latest quarterly metadata, not substantive capital reconciliation',q['reportDate'][i]=='2026-06-30' and q['filingDate'][i]=='2026-07-17',{'accession':q['accessionNumber'][i],'reportDate':q['reportDate'][i],'filingDate':q['filingDate'][i]})
config=json.loads((ROOT/'monitoring/config.json').read_text(encoding='utf-8'))
parent=json.loads((ROOT/'monitoring/decisions/2026-10-10-netflix-feasibility-disposition-r001.json').read_text())
check('Research/portfolio/execution boundary retained',config['mode']=='observation-only' and config['quote_acquisition']=='manual-only' and not parent['actionable'] and parent['current_intrinsic_value'] is None and parent['portfolio_decision'] is None and parent['execution_instruction'] is None,'No live acceptance or model revision')
observations={'schema':'bounded-expectations-inspection-v1','as_of':'2026-10-10','source_retrieval_register':(F/'source-retrieval-register.json').relative_to(ROOT).as_posix(),'decision':'viable_for_separately_authorised_limited_dossier','dossier_launched':False,'goal_created':False,'model_changed':False,'actionable':False,'yahoo_revenue':rev,'yahoo_gaap_selected_eps':eps,'financial_timestamp':'Yahoo estimate update time not established; direct October10 retrieval only','event':times,'calculated_revenue_context':{'yahoo_minus_guide_usdm':'20','percent':str((D('12880')/D('12860')-1)*100)},'unavailable':['matched external quarterly OI consensus','matched future recurring owner-cash consensus','verified intraday response-price dataset','executable broker quotes and costs'],'visual_check':'Issuer July PDF printed p1 rendered and inspected by parent; Q3 column and blank future cash/share cells confirmed'}
(ROOT/'validation/netflix-expectations-gate-observations-2026-10-10-r001.json').write_text(json.dumps(observations,indent=2)+'\n',encoding='utf-8')
report={'schema':'targeted-evidence-gate-checks-v1','verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Source preservation, definitions, time zones and bounded comparison arithmetic; no model audit, engineering suite, response study, fills or investment performance','passed':sum(r['passed'] for r in results),'failed':sum(not r['passed'] for r in results),'checks':results}
(ROOT/'validation/netflix-expectations-gate-verification-2026-10-10-r001.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'failed':report['failed'],'scope':report['scope']}));assert report['failed']==0
