"""One-shot public-source evidence capture for a bounded inspection, no monitoring."""
from pathlib import Path
import subprocess,json,hashlib,datetime,urllib.request,concurrent.futures
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'monitoring/studies/evidence/2026-10-10-netflix-expectations-gate-r001'
OUT.mkdir(exist_ok=False)
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
baseline={'checked_at':now(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'predecessors':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths]}
(ROOT/'validation/netflix-expectations-gate-baseline-2026-10-10-r001.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
sources={
 'event':'https://ir.netflix.net/investor-news-and-events/financial-releases/press-release-details/2026/Netflix-to-Announce-Third-Quarter-2026-Financial-Results/default.aspx',
 'split':'https://ir.netflix.net/investor-news-and-events/financial-releases/press-release-details/2025/Netflix-Announces-Ten-For-One-Stock-Split/default.aspx',
 'july-letter':'https://s22.q4cdn.com/959853165/files/doc_financials/2026/q2/FINAL-Q2-26-Shareholder-Letter.pdf',
 'annual-estimates':'https://stockanalysis.com/stocks/nflx/forecast/',
 'quarterly-estimates':'https://www.marketbeat.com/earnings/reports/2026-10-20-netflix-inc-stock/',
 'yahoo-analysis':'https://finance.yahoo.com/quote/NFLX/analysis/',
 'nasdaq-history':'https://www.nasdaq.com/market-activity/stocks/nflx/historical',
 'nasdaq-schedule':'https://www.nasdaq.com/market-activity/stock-market-holiday-schedule',
 'sec-submissions':'https://data.sec.gov/submissions/CIK0001065280.json'}
def fetch(item):
 key,url=item;record={'id':key,'url':url,'retrieved_at_utc':now(),'route':'direct unauthenticated urllib HTTPS; separate from web-tool reading'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'CompanyResearch2 personal research evidence inspection','Accept':'*/*'})
  with urllib.request.urlopen(req,timeout=25) as response:
   raw=response.read();record.update(status=response.status,content_type=response.headers.get('Content-Type'),last_modified=response.headers.get('Last-Modified'))
  sha=hashlib.sha256(raw).hexdigest();ext='pdf' if raw.startswith(b'%PDF') else 'json' if key=='sec-submissions' else 'html'
  path=OUT/f'{key}-{sha}.{ext}';path.write_bytes(raw)
  record.update(path=path.relative_to(ROOT).as_posix(),sha256=sha,bytes=len(raw),direct_archive=True)
 except Exception as exc:record.update(direct_archive=False,error=f'{type(exc).__name__}: {exc}')
 return record
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,sources.items()))
(OUT/'source-retrieval-register.json').write_text(json.dumps({'retrieved_at_utc':now(),'records':records,'note':'HTTP success alone does not establish substantive readable data or historical availability. Web-tool read projections are separately labelled.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'id':r['id'],'archived':r['direct_archive'],'bytes':r.get('bytes'),'error':r.get('error')} for r in records]))
