// Exercise exported workbooks in disposable memory; never alter delivered inputs.
import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, FileBlob } from '@oai/artifact-tool';
const run=path.resolve(process.argv[2]);
const m=JSON.parse(await fs.readFile(path.join(run,'model.json'),'utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(run,'outputs','valuation.xlsx')));
const sheet=n=>wb.worksheets.getItem(n);
const get=(n,a)=>sheet(n).getRange(a).values[0][0];
const set=(n,a,v)=>sheet(n).getRange(a).values=[[v]];
const records=[];
const actualCell=(metric,period)=>'C'+(m.source_actuals.findIndex(o=>o.metric===metric&&o.period===period)+4);
const actualBefore=sheet('Actuals').getUsedRange().values;
function assert(condition,label){if(!condition)throw Error(label);}
function mutation(name,n,a,value,verify){const before=get(n,a);set(n,a,value);wb.recalculate();try{verify();records.push(name);}catch(e){throw Error(name+': '+e.message+'; gate='+get(m.kind==='operating'?'Outputs':m.kind==='bank'?'Bank model':'Reconciliation',m.kind==='operating'?'B17':m.kind==='bank'?'B18':'B9')+(m.kind==='operating'?'; sensitivity='+JSON.stringify(sheet('Sensitivities').getRange('B6:F10').values):''));}finally{set(n,a,before);wb.recalculate();}}
if(m.kind==='operating'){
 const outputs=['B4','B5','B6','B7','B8','B10','B11','B13','B18','B19'];
 const withheld=()=>{for(const a of outputs)assert(get('Outputs',a)==='WITHHELD','Not withheld '+a);for(const row of sheet('Sensitivities').getRange('B6:F10').values)for(const v of row)assert(v==='WITHHELD','Sensitivity bypass');};
 const baseline=get('Outputs','B6');
 const refs=[...m.input_bindings.base_revenue,...m.input_bindings.diluted_shares,m.input_bindings.cash];
 for(const r of refs)mutation('missing actual '+r.metric+' '+r.period,'Actuals',actualCell(r.metric,r.period),null,withheld);
 for(const row of [15,16,...Array.from({length:65},(_,i)=>i+20)])mutation('missing active assumption E'+row,'Assumptions','E'+row,null,withheld);
 const invalid={E15:0,E16:-.01,E20:-1,E30:1.1,E35:-.1,E40:-.1,E45:-.1,E50:-1,E55:1000,E60:1.1,E65:-1,E70:-.01,E75:0,E80:-1};
 for(const [a,v]of Object.entries(invalid))mutation('invalid '+a,'Assumptions',a,v,withheld);
 mutation('negative borrowing blocked','Assumptions','E55',-100,withheld);
 mutation('missing valuation date','Assumptions','B11',null,withheld);
 mutation('missing price date','Assumptions','B17',null,withheld);
 mutation('future price date','Assumptions','B17',new Date('2026-10-07'),withheld);
 mutation('missing forecast date','Forecast','B4',null,withheld);
 mutation('forecast precedes as-of','Forecast','B4',new Date('2026-09-30'),withheld);
 mutation('unordered forecast date','Forecast','C4',new Date('2027-09-30'),withheld);
 mutation('unselected missing assumption does not block','Assumptions','C20',null,()=>assert(Math.abs(get('Outputs','B6')-baseline)<1e-7,'Unselected case blocked'));
 mutation('missing quote withholds returns only','Assumptions','B5',null,()=>{assert(get('Outputs','B10')==='WITHHELD','Missing quote return');assert(Math.abs(get('Outputs','B6')-baseline)<1e-7,'Missing quote changed value');});
 mutation('valid zero growth remains numeric','Assumptions','E20',0,()=>assert(typeof get('Outputs','B6')==='number','Valid zero rejected'));
 mutation('buybacks require ownership rerun','Assumptions','E65',100,()=>{assert(typeof get('Outputs','B6')==='number','Funded buyback blocked');assert(get('Sensitivities','B13')==='WITHHELD','Incorrect simple dilution scaling');});
 mutation('invalid repurchase price','Assumptions','E75',-1,withheld);
 mutation('sensitivity rejects its own terminal FCFE','Assumptions','E29',.013727353851481753,()=>{assert(get('Outputs','B17')==='PASS','Reproduction active case not valid');assert(get('Sensitivities','F8')==='WITHHELD','Negative sensitivity terminal FCFE accepted');});
 mutation('missing sensitivity growth axis','Sensitivities','D5',null,()=>assert(get('Sensitivities','D8')==='WITHHELD','Blank grid axis became zero'));
 mutation('missing sensitivity discount axis','Sensitivities','A8',null,()=>assert(get('Sensitivities','D8')==='WITHHELD','Blank grid discount became zero'));
 mutation('unfunded buyback','Assumptions','E65',1000000,()=>{assert(get('Outputs','B6')==='WITHHELD','Unfunded cash not blocked');for(const row of sheet('Sensitivities').getRange('B6:F10').values)for(const v of row)assert(v==='WITHHELD','Unfunded sensitivity');});
 assert(Math.abs(get('Sensitivities','D8')-baseline)<1e-7,'Sensitivity no longer matches');
}else if(m.kind==='bank'){
 const outputs=['B18','B24','B25'];const withheld=()=>{for(const a of outputs)assert(get('Bank model',a)==='WITHHELD','Bank support result bypass '+a);};
 for(const a of ['E13','E14','E15'])mutation('missing bank assumption '+a,'Bank model',a,null,withheld);
 mutation('missing tangible book source','Actuals',actualCell('Tangible book per share','2026-Q2'),null,withheld);
 mutation('invalid bank growth','Bank model','E15',.2,withheld);
 mutation('zero bank growth allowed','Bank model','E15',0,()=>assert(typeof get('Bank model','B18')==='number','Valid zero growth rejected'));
 for(const selector of [null,0,-1,5,1.5,'invalid'])mutation('invalid bank selector '+String(selector),'Bank model','B4',selector,withheld);
}else{
 for(const p of ['2025','2026-H1','2025-H1'])mutation('missing turnover '+p,'Actuals',actualCell('Turnover',p),null,()=>{assert(get('Reconciliation','B7')==='WITHHELD','TTM missing actual became zero');assert(get('Reconciliation','B9')==='MISSING TTM ACTUAL','TTM flag reassuring');});
 mutation('missing EBIT','Actuals',actualCell('Operating profit','2026-H1'),null,()=>assert(get('Reconciliation','B8')==='WITHHELD','Margin missing actual became zero'));
 mutation('zero denominator','Actuals',actualCell('Turnover','2026-H1'),0,()=>assert(get('Reconciliation','B8')==='WITHHELD','Zero denominator'));
 mutation('missing FX remains missing','Reconciliation','B12',4500,()=>assert(get('Reconciliation','B15')==='MISSING','Missing FX became zero'));
}
assert(JSON.stringify(sheet('Actuals').getUsedRange().values)===JSON.stringify(actualBefore),'Temporary edits changed actuals');
const result={passed:records.length,checks:records,restoredActuals:true,engine:'bundled artifact-tool imported XLSX',nativeExcelVerified:false};
await fs.writeFile(path.join(run,'work','audit-input-validation.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify({passed:records.length,kind:m.kind}));
