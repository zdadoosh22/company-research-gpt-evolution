"""Inspect exported formulas, cached results, PDFs and context reload independently."""
import json,sys,re
from pathlib import Path
from math import isclose
import openpyxl
from pypdf import PdfReader
from research import ROOT,read_json,sha256,check_run,save_json
from finance import shareholder_path,bank_excess_return

def validate(run, *, workbook_only=False):
 run=Path(run);m=read_json(run/'model.json');errors=[]
 errors.extend(check_run(run))
 formulas=openpyxl.load_workbook(run/'outputs/valuation.xlsx',data_only=False)
 cached=openpyxl.load_workbook(run/'outputs/valuation.xlsx',data_only=True)
 counts={s.title:sum(c.data_type=='f' for row in s for c in row) for s in formulas}
 required={'operating':['Assumptions','Forecast','Outputs','Sensitivities'],'bank':['Bank model'],'reconciliation':['Reconciliation']}[m['kind']]
 if any(counts.get(s,0)==0 for s in required):errors.append('Required formulas missing after export')
 if any(s.sheet_state!='visible' for s in formulas):errors.append('Hidden workbook logic')
 errors_codes={'#REF!','#DIV/0!','#VALUE!','#NUM!','#NAME?','#N/A','#SPILL!'}
 for s in cached:
  for row in s:
   for c in row:
    if isinstance(c.value,str) and c.value in errors_codes:errors.append(f'{s.title}!{c.coordinate}: {c.value}')
 if m['kind']=='operating':
  expected=shareholder_path(m,m['scenarios']['What-if']);observed=cached['Outputs']['B6'].value
  if not isinstance(observed,(int,float)) or not isclose(observed,expected['current_value'],rel_tol=1e-9):errors.append('Exported current value not independently reproduced')
  if not isclose(cached['Outputs']['B7'].value,expected['horizon_value'],rel_tol=1e-9):errors.append('Exported horizon value mismatch')
  observed_return=cached['Outputs']['B10'].value
  if expected['annualised_return'] is None:
   if observed_return!='WITHHELD':errors.append('Missing price did not withhold return')
  elif not isinstance(observed_return,(int,float)) or not isclose(observed_return,expected['annualised_return'],abs_tol=1e-9):errors.append('Exported dated shareholder return mismatch')
  if abs(cached['Outputs']['B13'].value)>1e-7:errors.append('Bridge residual')
  for i,o in enumerate(m['source_actuals'],4):
   if cached['Actuals'].cell(i,3).value!=o['value']:errors.append('Actuals changed during workbook construction')
  if not workbook_only:
   short=PdfReader(run/'outputs/thesis.pdf');full=PdfReader(run/'outputs/full-report.pdf')
   if len(short.pages)>5:errors.append('Standalone exceeds 5 pages')
   if [p.extract_text() for p in short.pages]!=[p.extract_text() for p in full.pages[:len(short.pages)]]:errors.append('Full report does not begin with same standalone thesis')
 elif m['kind']=='bank':
  c=m['cases']['What-if'];expected=bank_excess_return(m['tbv'],c['roe'],c['k'],c['g'])
  if not isclose(cached['Bank model']['B18'].value,expected,rel_tol=1e-9):errors.append('Bank export mismatch')
 else:
  if cached['Reconciliation']['B7'].value!=50620:errors.append('Scope-compatible TTM mismatch')
  if cached['Reconciliation']['B15'].value!='MISSING':errors.append('Missing FX converted to value')
 for p in (run/'outputs').glob('*.pdf'):
  pdf=PdfReader(p)
  for i,page in enumerate(pdf.pages):
   text=page.extract_text()
   if '\ufffd' in text or '\u25a0' in text:errors.append(f'{p.name} p{i+1}: replacement glyph')
  if not any(page.get('/Annots') for page in pdf.pages):errors.append(f'{p.name}: no linked citations')
 # Simulate context loading from only files; no history or session memory.
 r=read_json(run/'run.json');pointer=read_json(ROOT/'methodology/current.json')
 method=ROOT/r.get('methodology_file',pointer['file'])
 if sha256(method)!=r['methodology_sha256']:errors.append('Methodology version/hash unavailable on reload')
 if not r.get('continuation') and r['status']!='complete':errors.append('Incomplete run lacks continuation point')
 return dict(errors=errors,scope='workbook-only fixture' if workbook_only else 'workbook and reports',formula_counts=counts,pdf_pages={p.name:len(PdfReader(p).pages) for p in (run/'outputs').glob('*.pdf')},native_excel_verified=False,context_reload='files sufficient for dates, method, security, request, gaps and continuation')

if __name__=='__main__':
 result=validate(sys.argv[1]);save_json(Path(sys.argv[1])/'work/artifact-validation.json',result);print(json.dumps(result));sys.exit(bool(result['errors']))
