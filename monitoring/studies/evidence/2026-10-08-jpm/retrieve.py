from pathlib import Path
from datetime import datetime, timezone
import urllib.request, urllib.error, hashlib, json, re, html
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).parent
SOURCES={
 'event':'https://jpmorganchaseco.gcs-web.com/news-releases/news-release-details/jpmorganchase-host-third-quarter-2026-earnings-call/',
 'q2-10q':'https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm',
 'capital-note21':'https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/R29.htm',
 'q2-release':'https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfexhibit991narrative.htm',
 'q2-supplement':'https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfex992supplement.htm',
 'q2-presentation':'https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/quarterly-earnings/2026/2nd-quarter/9e8f3cef-bd2a-4140-b50f-83c4fba3f23c.pdf',
 'q2-transcript':'https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/quarterly-earnings/2026/2nd-quarter/2Q26-earnings-transcript.pdf',
 'dividend':'https://www.jpmorganchase.com/ir/news/2026/jpmc-declares-increased-common-stock-dividend-9-15',
 'price-history':'https://stockanalysis.com/stocks/jpm/history/',
 'sec-submissions':'https://data.sec.gov/submissions/CIK0000019617.json',
}
def fetch(item):
 key,url=item
 rec={'id':key,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
 try:
  r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CompanyResearch2 personal research monitoring'}),timeout=45)
  content=r.read()
  rec.update(http_status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url)
  if r.status!=200:
   rec['status']='failed';return rec
  ext='.pdf' if content.startswith(b'%PDF') else '.json' if key=='sec-submissions' else '.html'
  path=ROOT/(key+ext);path.write_bytes(content)
  rec.update(status='archived',file=path.name,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content))
  if ext=='.pdf':
   return rec
  elif ext=='.html':
   txt=content.decode('utf-8',errors='replace')
   txt=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',txt,flags=re.S|re.I)
   txt=html.unescape(re.sub('<[^>]+>',' ',txt))
   txt=re.sub(r'\s+',' ',txt)
   # Keep full content, wrapped only to make local locations readable.
   import textwrap
   txt='\n'.join(textwrap.wrap(txt,150,break_long_words=False))
  else:txt=content.decode('utf-8')
  (ROOT/(key+'.txt')).write_text(txt,encoding='utf-8')
 except Exception as exc:rec.update(status='failed',error=str(exc),http_status=getattr(exc,'code',None))
 return rec
records=list(ThreadPoolExecutor(max_workers=4).map(fetch,SOURCES.items()))
(ROOT/'retrieval-register.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(records,indent=2))
