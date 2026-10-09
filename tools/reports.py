"""Render reviewed prose and model results; this utility never chooses a thesis."""
import argparse,re,json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

STYLES=getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='BodyResearch',fontName='Helvetica',fontSize=10.5,leading=15,spaceAfter=8))
STYLES.add(ParagraphStyle(name='CellResearch',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=0))
STYLES.add(ParagraphStyle(name='SourceResearch',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=6))
STYLES['Title'].fontSize=24;STYLES['Title'].leading=29;STYLES['Title'].textColor=colors.HexColor('#173348')
STYLES['Heading1'].fontSize=16;STYLES['Heading1'].leading=20;STYLES['Heading1'].textColor=colors.HexColor('#173348')
STYLES['Heading2'].fontSize=12;STYLES['Heading2'].leading=16

def safe(text):
 return escape(str(text).replace('\u2011','-').replace('\u2014',' - ').replace('\u2013','-'))

def linked(text,sources):
 result=safe(text)
 for source in sources:
  if source.get('read'):
   sid=source['id'];href=escape(source['url'],{'"':'&quot;'})
   result=re.sub(r'(?<![A-Za-z0-9])'+re.escape(sid)+r'(?![A-Za-z0-9])',lambda match:'<link href="'+href+'" color="#1764AB">'+match.group()+'</link>',result)
 return result

def table(rows,width=475):
 cells=[[Paragraph(safe(x),STYLES['CellResearch']) for x in row] for row in rows]
 colwidth=[width/len(rows[0])]*len(rows[0]); t=Table(cells,colWidths=colwidth,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE7EB')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#173348')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F7F8')])]))
 return t

def blocks(sections,sources):
 result=[]
 for s in sections:
  if s.get('page_break'):result.append(PageBreak())
  if s.get('title'):result.append(Paragraph(safe(s['title']),STYLES['Heading1']))
  for b in s.get('blocks',[]):
   if 'heading' in b:result.append(Paragraph(safe(b['heading']),STYLES['Heading2']))
   if 'text' in b:result.append(Paragraph(linked(b['text'],sources),STYLES['BodyResearch']))
   if 'table' in b:result.extend([table(b['table']),Spacer(1,10)])
 return result

def render(run):
 run=Path(run).resolve()
 if not run.is_relative_to(Path(__file__).resolve().parents[1]/'companies'):raise ValueError('Report run must be in this company archive')
 if (run/'publication.json').exists():raise ValueError('Published run is immutable; create an update')
 r=json.loads((run/'run.json').read_text(encoding='utf-8'));spec=json.loads((run/'report.json').read_text(encoding='utf-8'));sources=json.loads((run/'sources.json').read_text(encoding='utf-8'))
 def footer(canvas,doc):
  canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#667882'));canvas.drawString(48,30,r['legal_name']+' | '+r['as_of']+' | Method '+r['methodology_version']);canvas.drawRightString(A4[0]-48,30,str(doc.page))
 def build(filename,body):
  p=run/'outputs'/filename
  SimpleDocTemplate(str(p),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=43,bottomMargin=47,title=spec['title'],author='Company research 2').build(body,onFirstPage=footer,onLaterPages=footer)
  return len(PdfReader(p).pages)
 def title():return [Paragraph(safe(spec['title']),STYLES['Title']),Paragraph('Dated '+r['as_of']+' | '+safe(spec.get('status','Pilot - review pending')),STYLES['BodyResearch']),Spacer(1,10)]
 appendix=[Spacer(1,14) if r['mode']=='full' else PageBreak(),Paragraph('Evidence appendix',STYLES['Heading1'])]
 for s in sources:
  if s.get('read'):
   link='<link href="'+escape(s['url'],{'"':'&quot;'})+'" color="#1764AB">'+safe(s['id']+' | '+s['title'])+'</link>'
   text=link+'<br/>'+safe('Published: '+str(s.get('publication_date') or 'not verified / undated')+' | '+s['type']+' | locations: '+'; '.join(s.get('locations',[])))+'<br/>'+safe('Preservation: '+str(s.get('preservation') or s.get('archived_file') or 'link only'))
   appendix.append(Paragraph(text,STYLES['SourceResearch']))
 if r['mode']=='full':
  short=title()+blocks(spec['standalone'],sources);count=build('thesis.pdf',short)
  if count>5:raise ValueError(f'Short thesis has {count} pages; revise content, do not shrink readability')
  fullcount=build('full-report.pdf',title()+blocks(spec['standalone'],sources)+[PageBreak()]+blocks(spec['supporting'],sources)+appendix)
  print(json.dumps(dict(short_pages=count,full_pages=fullcount)))
 else:print(json.dumps(dict(pilot_pages=build('pilot.pdf',title()+blocks(spec['sections'],sources)+appendix))))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');render(p.parse_args().run)
