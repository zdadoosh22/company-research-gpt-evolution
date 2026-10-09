// A single active model with separately preserved reported scenarios.
// Rebuild snapshots only after an approved report/model update.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile, FileBlob } from '@oai/artifact-tool';
const run=path.resolve(process.argv[2]);
const companyRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','companies');
if(path.relative(companyRoot,run).startsWith('..'))throw Error('Run must be inside this company archive');
try{await fs.access(path.join(run,'publication.json'));throw Error('Published run is immutable; create an update');}catch(e){if(e.code!=='ENOENT')throw e;}
const model=JSON.parse(await fs.readFile(path.join(run,'model.json'),'utf8'));
const runRecord=JSON.parse(await fs.readFile(path.join(run,'run.json'),'utf8'));
const sources=JSON.parse(await fs.readFile(path.join(run,'sources.json'),'utf8'));
const results=JSON.parse(await fs.readFile(path.join(run,'reviewed-results.json'),'utf8').catch(()=> '{}'));
const wb=Workbook.create();
const names=model.kind==='operating'?['Start','Actuals','Assumptions','Forecast','Outputs','Sensitivities','Sources']:model.kind==='bank'?['Start','Actuals','Bank model','Sources']:['Start','Actuals','Reconciliation','Sources'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
function v(s,a,value){s.getRange(a).values=[[value]];}
function f(s,a,formula){s.getRange(a).formulas=[[formula]];}
function heading(s,label,end='G'){s.getRange(`A1:${end}1`).merge();v(s,'A1',label);s.getRange(`A1:${end}1`).format.fill='#173348';s.getRange(`A1:${end}1`).format.font={name:'Calibri',size:17,bold:true,color:'#FFFFFF'};s.getRange('A1').format.rowHeight=34;}
function band(s,a){s.getRange(a).format.fill='#DCE7EB';s.getRange(a).format.font.bold=true;}
function edit(s,a){s.getRange(a).format.fill='#FFF1D6';s.getRange(a).format.font.color='#1764AB';}
for(const s of Object.values(sheets)){s.showGridLines=false;s.getRange('A1:H100').format.font={name:'Calibri',size:11,color:'#202B33'};s.getRange('A1:H100').format.rowHeight=22;s.getRange('A:A').format.columnWidth=37;s.getRange('B:F').format.columnWidth=18;s.getRange('G:H').format.columnWidth=26;s.freezePanes.freezeRows(3);}
const start=sheets.Start;heading(start,model.title);start.getRange('A3:G3').merge();v(start,'A3','Research date: '+model.as_of+' | Methodology '+runRecord.methodology_version+' | Review: '+runRecord.stronger_review);
let sr=5;for(const text of ['Blue text on pale yellow = editable input. Black = reported inputs/formulas. Every sheet is visible.','The PDF is a dated assessment; changing this workbook does not update its narrative.',...(model.kind==='operating'?['Select 1 Bear / 2 Base / 3 Bull / 4 What-if in Assumptions B4. Edit only What-if E15:E84 to preserve reported inputs.','One forecast is active. Reported scenario comparison is an explicitly dated snapshot; rebuild after an approved model update.','Values USD million, ownership million shares, per-share outputs USD. Returns gross before personal taxes and costs.']:[]),...model.limitations,'Recalculated and export/import tested with the bundled engine. Native Microsoft Excel has not been independently opened/tested.']){start.getRange(`A${sr}:G${sr}`).merge();v(start,`A${sr}`,text);start.getRange(`A${sr}`).format.wrapText=true;start.getRange(`A${sr}`).format.rowHeight=42;sr++;}
const actual=sheets.Actuals;heading(actual,'Sourced historical inputs', 'H');actual.getRange('A3:H3').values=[['Metric','Period','Reported value','Unit','Scope','Source','Location','Status']];band(actual,'A3:H3');
actual.getRange('A4:H'+(model.source_actuals.length+3)).values=model.source_actuals.map(o=>[o.metric,o.period,o.value,o.unit,o.scope,o.source_id,o.location,o.status]);actual.getRange('C4:C100').setNumberFormat('#,##0.000;(#,##0.000);"-"');actual.getRange('E4:H100').format.wrapText=true;actual.getRange('E4:H100').format.rowHeight=65;actual.getRange('E:E').format.columnWidth=40;actual.getRange('F:F').format.columnWidth=12;actual.getRange('G:G').format.columnWidth=52;
function actualCell(metric,period){const i=model.source_actuals.findIndex(o=>o.metric===metric&&o.period===period);if(i<0)throw Error('Missing '+metric+' '+period);return `'Actuals'!C${i+4}`;}
function boundCell(ref){const hits=model.source_actuals.map((o,i)=>({o,i})).filter(({o})=>o.metric===ref.metric&&o.period===ref.period&&o.source_id===ref.source_id);if(hits.length!==1||typeof hits[0].o.value!=='number')throw Error('Ambiguous or missing explicit actual binding');return `'Actuals'!C${hits[0].i+4}`;}
function boundSum(parts){return parts.map(ref=>`${ref.coefficient}*${boundCell(ref)}`).join('+');}
const src=sheets.Sources;heading(src,'Read sources and preservation','F');src.getRange('A3:F3').values=[['ID / title','Published','Type','URL','Preservation','Locations']];band(src,'A3:F3');src.getRange('A4:F'+(sources.length+3)).values=sources.map(s=>[s.id+' | '+s.title,s.publication_date||'Unverified / undated',s.type,s.url,s.preservation||s.archived_file||s.access_error||'Link only',(s.locations||[]).join('; ')]);src.getRange('A4:F100').format.wrapText=true;src.getRange('A4:F100').format.rowHeight=75;src.getRange('A:A').format.columnWidth=37;src.getRange('D:D').format.columnWidth=66;src.getRange('E:F').format.columnWidth=45;
let outputs,baseline,change;
if(model.kind==='operating'){
 if(model.forecast_dates.length!==5||!model.input_bindings)throw Error('This validated workbook pattern requires five explicitly dated periods and input_bindings; build/validate an extended or different sector model separately.');
 const s=sheets.Assumptions; heading(s,'Case inputs | one active forecast','F');
 if(typeof model.operating_cash_reserve!=='number'||typeof model.other_equity_assets!=='number')throw Error('Explicit operating reserve and other-equity-asset valuation required');
 const meta=[['Active selector (1-4)',4],['Dated market price',model.price],['TTM continuing revenue',null],['Opening ownership proxy',null],['Opening excess cash',null],['Operating liquidity reserve',model.operating_cash_reserve],['Other equity assets',model.other_equity_assets],['Research valuation date',new Date(model.as_of)],['Active equity discount rate',null],['Active terminal growth',null]];
 s.getRange('A4:B13').values=meta;edit(s,'B4:B5');edit(s,'B9:B10');s.getRange('B11').setNumberFormat('yyyy-mm-dd');
 s.getRange('B4').dataValidation={rule:{type:'whole',operator:'between',formula1:1,formula2:4}};
 f(s,'B6',`=${boundSum(model.input_bindings.base_revenue)}`);
 f(s,'B7',`=${boundSum(model.input_bindings.diluted_shares)}`);
 f(s,'B8',`=${boundCell(model.input_bindings.cash)}-B9`);
 const requiredRefs=[...model.input_bindings.base_revenue,...model.input_bindings.diluted_shares,model.input_bindings.cash].map(boundCell);
 f(s,'F18',`=IF(AND(COUNT(${requiredRefs.join(',')})=${requiredRefs.length},COUNT(B9:B10)=2),"PASS","MISSING INPUT")`);
 v(s,'A18','Required source / policy inputs');
 s.getRange('A14:F14').values=[['Driver','Bear','Base','Bull','What-if','Active']];band(s,'A14:F14');
 v(s,'A17','Price cash-flow observation date');v(s,'B17',new Date(model.price_date||model.as_of));s.getRange('B17').setNumberFormat('yyyy-mm-dd');
 const cases=['Bear','Base','Bull','What-if'];
 s.getRange('A15:E16').values=[['Cost of equity',...cases.map(c=>model.scenarios[c].cost_of_equity)],['Terminal growth',...cases.map(c=>model.scenarios[c].terminal_growth)]];
 const keys=['growth','operating_margin','tax_rate','da_ratio','capex_ratio','working_capital_ratio','interest','net_borrowing','dividend_payout','buybacks','gross_dilution','repurchase_price','cash_yield'];
 const labels=['Revenue growth','EBIT margin after SBC','Tax rate','Cash DA / revenue','Capex / revenue','Incremental WC / revenue','Annual interest','Annual net borrowing','Dividend payout','Period buybacks','Separate gross dilution','Buyback price per share','Excess cash yield'];
 for(let k=0;k<keys.length;k++){const row=20+k*5;s.getRange(`A${row}:E${row+4}`).values=Array.from({length:5},(_,i)=>[labels[k]+' | Y'+(i+1),...cases.map(c=>model.scenarios[c][keys[k]][i])]);for(let i=0;i<5;i++){f(s,`F${row+i}`,`=CHOOSE($B$4,B${row+i},C${row+i},D${row+i},E${row+i})`);}s.getRange(`B${row}:F${row+4}`).setNumberFormat([6,7,9,11].includes(k)?'#,##0.00;(#,##0.00);"-"':'0.0%');}
 for(const row of [15,16])f(s,`F${row}`,`=CHOOSE($B$4,B${row},C${row},D${row},E${row})`);
 f(s,'B12','=F15');f(s,'B13','=F16');s.getRange('B12:F16').setNumberFormat('0.0%');edit(s,'E15:E16');edit(s,'E20:E84');
 const p=sheets.Forecast;heading(p,'Active operating / ownership forecast','F');
 const rowLabels={4:'Forecast date',5:'Period fraction (actual / 365)',6:'Years from valuation date',8:'Opening annual revenue',9:'Closing annual revenue',10:'EBIT margin after economic SBC',11:'EBIT for period',12:'Tax rate',13:'Interest for period',14:'After-tax levered profit',15:'Cash DA add-back',16:'Capital expenditure',17:'Incremental working capital',18:'Net borrowing for period',19:'FCFE after financing',21:'Opening diluted ownership',22:'Dividend payout fraction',23:'Total dividends',24:'Dividend per opening share',25:'Buyback cash',26:'Buyback execution price',27:'Separate gross dilution',28:'Closing diluted ownership',30:'Opening excess cash',31:'Treasury cash yield',32:'Closing excess cash',34:'Holder receipt incl. exit at Y5',35:'PV of receipt at equity cost'};
 for(const [row,label]of Object.entries(rowLabels))v(p,'A'+row,label);
 for(let i=0;i<5;i++){const c=String.fromCharCode(66+i),prev=String.fromCharCode(65+i);v(p,c+'4',new Date(model.forecast_dates[i]));p.getRange(c+'4').setNumberFormat('yyyy-mm-dd');
 const refs={5:`=(${c}4-${i?prev+'4':"'Assumptions'!B11"})/365`,6:`=(${c}4-'Assumptions'!B11)/365`,8:i?`=${prev}9`:"='Assumptions'!B6",9:`=${c}8*(1+'Assumptions'!F${20+i})^${c}5`,10:`='Assumptions'!F${25+i}`,11:`=${c}9*${c}10*${c}5`,12:`='Assumptions'!F${30+i}`,13:`='Assumptions'!F${50+i}*${c}5`,14:`=(${c}11-${c}13)*(1-${c}12)`,15:`=${c}9*'Assumptions'!F${35+i}*${c}5`,16:`=${c}9*'Assumptions'!F${40+i}*${c}5`,17:`=(${c}9-${c}8)*'Assumptions'!F${45+i}`,18:`='Assumptions'!F${55+i}*${c}5`,19:`=${c}14+${c}15-${c}16-${c}17+${c}18`,21:i?`=${prev}28`:"='Assumptions'!B7",22:`='Assumptions'!F${60+i}`,23:`=MAX(${c}19,0)*${c}22`,24:`=${c}23/${c}21`,25:`='Assumptions'!F${65+i}`,26:`='Assumptions'!F${75+i}`,27:`='Assumptions'!F${70+i}`,28:`=${c}21*(1+${c}27)^${c}5-${c}25/${c}26`,30:i?`=${prev}32`:"='Assumptions'!B8",31:`='Assumptions'!F${80+i}`,32:`=${c}30*(1+${c}31)^${c}5+${c}19-${c}23-${c}25`,34:i===4?`=${c}24+'Outputs'!B7`:`=${c}24`,35:`=${c}34/(1+'Assumptions'!B12)^${c}6`};
 refs[34]=i===4?`=IF(ISNUMBER('Outputs'!B7),${c}24+'Outputs'!B7,"WITHHELD")`:`=${c}24`;
 refs[35]=`=IF(ISNUMBER(${c}34),${c}34/(1+'Assumptions'!B12)^${c}6,"WITHHELD")`;
 for(const[row,formula]of Object.entries(refs))f(p,c+row,formula);
 }
 p.getRange('B5:F35').setNumberFormat('#,##0.00;(#,##0.00);"-"');for(const row of [10,12,22,27,31])p.getRange('B'+row+':F'+row).setNumberFormat('0.0%');for(const row of [19,28,32,34,35])band(p,'A'+row+':F'+row);
 const o=sheets.Outputs;heading(o,'Four separate outputs | conditional','G');
const outputLabels={4:'Terminal annual revenue',5:'First terminal year FCFE',6:'Illustrative PV / proxy share',7:'Illustrative horizon / proxy share',8:'Terminal continuing equity value',10:'Illustrative annualised total return',11:'Annualised price appreciation',12:'Reverse-growth illustration snapshot',13:'PV / horizon bridge residual',15:'Report comparison remains a snapshot',17:'Arithmetic input gate',18:'Terminal cash before interest',19:'Constant interest claim value'};for(const[row,label]of Object.entries(outputLabels))v(o,'A'+row,label);
 o.getRange('A3:G3').merge();v(o,'A3','Illustrations only. Intrinsic value, investment judgement and actionable entry levels remain withheld.');o.getRange('A3').format.wrapText=true;o.getRange('A3').format.rowHeight=34;
 v(s,'A19','Active input / date domain');
 f(s,'F19',"=IF(ISNUMBER(B4),IF(AND(B4=INT(B4),B4>=1,B4<=4),IF(AND(F18=\"PASS\",CHOOSE(B4,COUNT(B20:B84),COUNT(C20:C84),COUNT(D20:D84),COUNT(E20:E84))=65,CHOOSE(B4,COUNT(B15:B16),COUNT(C15:C16),COUNT(D15:D16),COUNT(E15:E16))=2,COUNT(B11,B17)=2,COUNT('Forecast'!B4:F4)=5,MIN('Forecast'!B5:F5)>0,B17<=B11,B6>0,B7>0,B8>=0,B9>=0,B12>B13,B12>0,B13>=0,MIN(F20:F24)>-1,MIN(F30:F34)>=0,MAX(F30:F34)<=1,MIN(F35:F54)>=0,MIN(F55:F59)=0,MAX(F55:F59)=0,MIN(F60:F64)>=0,MAX(F60:F64)<=1,MIN(F65:F74)>=0,MIN(F75:F79)>0,MIN(F80:F84)>-1),\"PASS\",\"WITHHELD\"),\"WITHHELD\"),\"WITHHELD\")");
 f(o,'B4',"=IF('Assumptions'!F19=\"PASS\",'Forecast'!F9*(1+'Assumptions'!B13),\"WITHHELD\")");
 f(o,'B5',"=IF('Assumptions'!F19=\"PASS\",(B4*'Forecast'!F10-'Assumptions'!F54)*(1-'Forecast'!F12)+B4*('Assumptions'!F39-'Assumptions'!F44)-(B4-'Forecast'!F9)*'Assumptions'!F49,\"WITHHELD\")");
 f(o,'B18',"=IF('Assumptions'!F19=\"PASS\",B4*'Forecast'!F10*(1-'Forecast'!F12)+B4*('Assumptions'!F39-'Assumptions'!F44)-(B4-'Forecast'!F9)*'Assumptions'!F49,\"WITHHELD\")");
 f(o,'B19',"=IF('Assumptions'!F19=\"PASS\",'Assumptions'!F54*(1-'Forecast'!F12)/'Assumptions'!B12,\"WITHHELD\")");
 f(o,'B8',"=IF('Assumptions'!F19=\"PASS\",B18/('Assumptions'!B12-'Assumptions'!B13)-B19,\"WITHHELD\")");
 f(o,'B17',"=IF('Assumptions'!F19=\"PASS\",IF(AND(B5>0,MIN('Forecast'!B32:F32)>=0,MIN('Forecast'!B28:F28)>0),\"PASS\",\"WITHHELD\"),\"WITHHELD\")");
 f(o,'B7',"=IF(B17=\"PASS\",(B8+'Forecast'!F32+'Assumptions'!B10)/'Forecast'!F28,\"WITHHELD\")");
 f(o,'B6','=IF(B17="PASS",SUM(\'Forecast\'!B35:F35),"WITHHELD")');
 o.getRange('A22:C22').values=[['Explicit cash-flow date','Per-share cash flow','Years from valuation']];band(o,'A22:C22');
 f(o,'A23',"='Assumptions'!B17");f(o,'B23',"=IF(AND(ISNUMBER('Assumptions'!B5),'Assumptions'!B5>0),-'Assumptions'!B5,\"WITHHELD\")");v(o,'C23',0);
 for(let i=0;i<5;i++){const c=String.fromCharCode(66+i);f(o,'A'+(24+i),`='Forecast'!${c}4`);f(o,'B'+(24+i),`='Forecast'!${c}34`);f(o,'C'+(24+i),`='Forecast'!${c}6`);}
 o.getRange('A23:A28').setNumberFormat('yyyy-mm-dd');
 f(o,'B10','=IF(AND(B17="PASS",ISNUMBER(B23)),XIRR(B23:B28,A23:A28),"WITHHELD")');
 f(o,'B11',"=IF(AND(B17=\"PASS\",ISNUMBER(B23)),(B7/'Assumptions'!B5)^(365/('Forecast'!F4-'Assumptions'!B17))-1,\"WITHHELD\")");
 v(o,'B12',model.reverse_growth??'WITHHELD');v(o,'C12','Unvalidated Base inputs fixed; dated arithmetic snapshot, not accepted market expectations.');o.getRange('C12:G12').merge();o.getRange('C12').format.wrapText=true;o.getRange('C12').format.rowHeight=44;
 f(o,'B13',"=IF(B17=\"PASS\",B6-SUMPRODUCT('Forecast'!B24:F24,1/(1+'Assumptions'!B12)^'Forecast'!B6:F6)-B7/(1+'Assumptions'!B12)^'Forecast'!F6,\"WITHHELD\")");
 o.getRange('A31:D31').values=[['Reported illustration snapshot','PV illustration','Horizon illustration','Illustrative annualised return']];band(o,'A31:D31');o.getRange('A31:D31').format.wrapText=true;o.getRange('A31:D31').format.rowHeight=36;
 o.getRange('A32:D34').values=['Bear','Base','Bull'].map(c=>[c,results[c].current_value,results[c].horizon_value,results[c].annualised_return??'WITHHELD']);
 v(o,'A37','Entry illustration | intact forecast');o.getRange('B37:E37').values=[[.08,.10,.12,.15]];o.getRange('B37:E37').setNumberFormat('0%');
 for(let i=0;i<4;i++){const c=String.fromCharCode(66+i);f(o,c+'38',`=IF($B$17="PASS",SUMPRODUCT($B$24:$B$28,1/(1+${c}37)^$C$24:$C$28),"WITHHELD")`);}
 o.getRange('B4:E38').setNumberFormat('#,##0.00;(#,##0.00);"-"');o.getRange('B10:B12').setNumberFormat('0.0%');o.getRange('D32:D34').setNumberFormat('0.0%');o.getRange('B37:E37').setNumberFormat('0%');
 const sen=sheets.Sensitivities;heading(sen,'Active forecast sensitivity | equity cost / terminal growth','F');v(sen,'A3','Forecast held fixed; rebuild terminal working capital for each g.');sen.getRange('B5:F5').values=[[.01,.02,.03,.035,.04]];sen.getRange('A6:A10').values=[[.09],[.10],[.11],[.12],[.13]];
 for(let r=6;r<=10;r++)for(let c=66;c<=70;c++){
  const col=String.fromCharCode(c),k=`$A${r}`,g=`${col}$5`;
  const rev=`('Forecast'!F9*(1+${g}))`;
  const pre=`(${rev}*'Forecast'!F10*(1-'Forecast'!F12)+${rev}*('Assumptions'!F39-'Assumptions'!F44)-'Forecast'!F9*${g}*'Assumptions'!F49)`;
  const terminal=`(${pre}/(${k}-${g})-'Assumptions'!F54*(1-'Forecast'!F12)/${k})`;
  const exit=`((${terminal}+'Forecast'!F32+'Assumptions'!B10)/'Forecast'!F28)`;
  f(sen,col+r,`=IF('Outputs'!B17="PASS",IF(COUNT(${k},${g})=2,IF(AND(${k}>${g},${k}>0,${g}>=0,${pre}-'Assumptions'!F54*(1-'Forecast'!F12)>0),SUMPRODUCT('Forecast'!B24:F24,1/(1+${k})^'Forecast'!B6:F6)+${exit}/(1+${k})^'Forecast'!F6,"WITHHELD"),"WITHHELD"),"WITHHELD")`);
 }
 sen.getRange('A6:A10').setNumberFormat('0.0%');sen.getRange('B5:F5').setNumberFormat('0.0%');sen.getRange('B6:F10').setNumberFormat('0.0');v(sen,'A13','Ownership +5% | zero buybacks only');f(sen,'B13',"=IF(AND('Outputs'!B17=\"PASS\",SUM('Forecast'!B25:F25)=0),'Outputs'!B6/1.05,\"WITHHELD\")");sen.getRange('B13').setNumberFormat('0.0');v(sen,'A15','Arithmetic illustrations; no approved maturity or probabilities.');
 wb.recalculate();outputs=o.getRange('B6:B13').values;baseline=o.getRange('B6').values[0][0];
 // Verify each published case against independently calculated expected results.
 const casesChecked=[];
 for(let i=0;i<4;i++){v(s,'B4',i+1);wb.recalculate();const actualValues=[o.getRange('B6').values[0][0],o.getRange('B7').values[0][0],o.getRange('B10').values[0][0]];const ex=results[cases[i]];[ex.current_value,ex.horizon_value,ex.annualised_return].forEach((expected,j)=>{if(expected===null){if(actualValues[j]!=='WITHHELD')throw Error('Missing return not withheld');return;}if(typeof actualValues[j]!=='number'||!Number.isFinite(actualValues[j])||Math.abs(actualValues[j]-expected)>1e-7*Math.max(1,Math.abs(expected)))throw Error('Case mismatch '+cases[i]+' '+j+' '+actualValues[j]+' vs '+expected);});casesChecked.push(cases[i]);}
 v(s,'B4',4);const original=s.getRange('E20').values[0][0];v(s,'E20',original+.05);wb.recalculate();change=o.getRange('B6').values[0][0];if(!(change>baseline))throw Error('What-if change did not flow to value');if(actual.getRange('C4').values[0][0]!==model.source_actuals[0].value)throw Error('Actuals changed');v(s,'E20',null);wb.recalculate();if(o.getRange('B6').values[0][0]!=='WITHHELD')throw Error('Missing forecast input silently became zero');v(s,'E20',original);wb.recalculate();if(typeof sen.getRange('D8').values[0][0]!=='number'||Math.abs(sen.getRange('D8').values[0][0]-baseline)>1e-7)throw Error('Sensitivity base combination does not match active valuation');
 await fs.writeFile(path.join(run,'work','case-validation.json'),JSON.stringify({casesChecked,baseline,changed:change,missingInputWithheld:true,actualsUnchanged:true,bridgeResidual:o.getRange('B13').values[0][0]},null,2));
}else if(model.kind==='bank'){
 const b=sheets['Bank model'];heading(b,'Tangible equity / excess return substitution','F');b.getRange('A4:B9').values=[['Active case 1-4',4],['Tangible book / share',null],['Long-run ROTCE',null],['Equity cost',null],['Sustainable book growth',null],['Optional verified market price',null]];edit(b,'B4');edit(b,'B9');f(b,'B5',`=${actualCell('Tangible book per share','2026-Q2')}`);
 b.getRange('A12:E12').values=[['Driver','Bear','Base','Bull','What-if']];band(b,'A12:E12');const keys=['roe','k','g'];b.getRange('A13:E15').values=keys.map(k=>[k,...Object.values(model.cases).map(c=>c[k])]);edit(b,'E13:E15');b.getRange('B13:E15').setNumberFormat('0.0%');
 b.getRange('B4').dataValidation={rule:{type:'whole',operator:'between',formula1:1,formula2:4}};
 for(let i=0;i<3;i++){const row=13+i;f(b,'B'+(6+i),`=IF(ISNUMBER(B4),IF(AND(B4=INT(B4),B4>=1,B4<=4),IF(CHOOSE(B4,COUNT(B${row}),COUNT(C${row}),COUNT(D${row}),COUNT(E${row}))=1,CHOOSE(B4,B${row},C${row},D${row},E${row}),"WITHHELD"),"WITHHELD"),"WITHHELD")`);}
 v(b,'A18','Steady-state value illustration');f(b,'B18','=IF(COUNT(B6:B8)=3,IF(AND(B5>0,B8>=0,B6>B8,B7>B8),B5*(B6-B8)/(B7-B8),"WITHHELD"),"WITHHELD")');v(b,'A20','Price-dependent returns / entry');v(b,'B20','WITHHELD');v(b,'A21','No capital-constrained distribution path verified.');b.getRange('A21:F21').merge();
 v(b,'A24','Required reinvestment fraction');f(b,'B24','=IF(ISNUMBER(B18),B8/B6,"WITHHELD")');v(b,'A25','Illustrative distributable earnings');f(b,'B25','=IF(ISNUMBER(B18),B5*(B6-B8),"WITHHELD")');v(b,'A27','Do not add deposits or deduct bank debt again.');b.getRange('A27:F27').merge();
 b.getRange('B6:B8').setNumberFormat('0.0%');b.getRange('B18').setNumberFormat('0.00');b.getRange('B24').setNumberFormat('0.0%');
 wb.recalculate();baseline=b.getRange('B18').values[0][0];if(Math.abs(baseline-results.Base)>1e-8)throw Error('Bank independently calculated result mismatch');v(b,'E13',.19);wb.recalculate();change=b.getRange('B18').values[0][0];if(change<=baseline)throw Error('Bank what-if failed');v(b,'E13',.18);outputs=b.getRange('B18').values;
}else{
 const s=sheets.Reconciliation;heading(s,'Period / scope / currency safeguards','F');s.getRange('A4:B9').values=[['FY2025 continuing turnover',null],['H1 2026 continuing turnover',null],['H1 2025 re-presented turnover',null],['Valid TTM continuing turnover',null],['H1 2026 IFRS operating margin',null],['TTM validity',null]];
 const revenueRefs=[actualCell('Turnover','2025'),actualCell('Turnover','2026-H1'),actualCell('Turnover','2025-H1')];
 const scopeRows=model.source_actuals.filter(o=>o.metric==='Turnover'&&['2025','2026-H1','2025-H1'].includes(o.period));
 if(scopeRows.length!==3||new Set(scopeRows.map(o=>o.unit)).size!==1||new Set(scopeRows.map(o=>o.scope_key||o.scope)).size!==1)throw Error('Incompatible continuing-scope TTM actuals');
 f(s,'B4',`=${revenueRefs[0]}`);f(s,'B5',`=${revenueRefs[1]}`);f(s,'B6',`=${revenueRefs[2]}`);f(s,'B7',`=IF(AND(COUNT(${revenueRefs.join(',')})=3,MIN(B4:B6)>=0),B4+B5-B6,"WITHHELD")`);f(s,'B8',`=IF(AND(COUNT(${actualCell('Operating profit','2026-H1')},${revenueRefs[1]})=2,B5>0),${actualCell('Operating profit','2026-H1')}/B5,"WITHHELD")`);f(s,'B9','=IF(ISNUMBER(B7),"Continuing / EUR / H1 inputs present","MISSING TTM ACTUAL")');s.getRange('B8').setNumberFormat('0.0%');
 s.getRange('A12:B16').values=[['London share price in GBp',null],['Dated EUR per GBP spot',null],['Share price in GBP',null],['Equivalent price in EUR',null],['Security valuation / shareholder return','WITHHELD']];edit(s,'B12:B13');f(s,'B14','=IF(AND(ISNUMBER(B12),B12>0),B12/100,"MISSING")');f(s,'B15','=IF(AND(ISNUMBER(B14),ISNUMBER(B13),B13>0),B14*B13,"MISSING")');
 s.getRange('A19:F19').merge();v(s,'A19','FX is a dated input, never an invented currency forecast.');s.getRange('A21:F21').merge();v(s,'A21','2025 share consolidation requires rebased per-share history.');
 wb.recalculate();baseline=s.getRange('B7').values[0][0];if(baseline!==50620)throw Error('Global TTM mismatch');v(s,'B12',4500);v(s,'B13',1.2);wb.recalculate();if(s.getRange('B15').values[0][0]!==54)throw Error('GBp / GBP / EUR conversion failed');v(s,'B12',null);v(s,'B13',null);outputs=s.getRange('B7:B9').values;
}
wb.recalculate();
const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NUM!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:30},maxChars:2500});
const target=path.join(run,'outputs','valuation.xlsx');await (await SpreadsheetFile.exportXlsx(wb)).save(target);
const reopened=await SpreadsheetFile.importXlsx(await FileBlob.load(target));reopened.recalculate();
const outSheet=model.kind==='operating'?'Outputs':model.kind==='bank'?'Bank model':'Reconciliation';const cell=model.kind==='operating'?'B6':model.kind==='bank'?'B18':'B7';const roundtrip=reopened.worksheets.getItem(outSheet).getRange(cell).values[0][0];if(Math.abs(roundtrip-baseline)>1e-7*Math.max(1,Math.abs(baseline)))throw Error('Export/import recalculation mismatch');
for(const name of names){const ranges={Start:'A1:G18',Actuals:'A1:H12',Assumptions:'A1:F24',Forecast:'A1:F35',Outputs:'A1:G38',Sensitivities:'A1:F16',Sources:'A1:F8','Bank model':'A1:F28',Reconciliation:'A1:F22'};const preview=await wb.render({sheetName:name,range:ranges[name],scale:1.4,format:'png'});await fs.writeFile(path.join(run,'work','sheet-'+name.replaceAll(' ','-')+'.png'),new Uint8Array(await preview.arrayBuffer()));}
await fs.writeFile(path.join(run,'work','workbook-validation.json'),JSON.stringify({baseline,change,roundtrip,formulaScan:scan.ndjson,outputs,nativeExcelVerified:false},null,2));
console.log(JSON.stringify({title:model.title,baseline,change,roundtrip,file:target}));
