const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {validateReport,comparisonCSV,lineSVG,barSVG,esc}=require('../web/app.js');
test('rejects malformed reports',()=>{for(const x of [null,{}, {schema_version:1}])assert.throws(()=>validateReport(x));});
test('empty convergence does not fabricate a zero',()=>{assert.match(lineSVG([{points:[]}],{title:'empty'}),/bulunamadı/);});
test('escapes chart content',()=>{assert.equal(esc('<script>'),'&lt;script&gt;');assert.ok(!barSVG([],'mean_peak','<script>','').includes('<script>'));});
test('bundled report and exports are consistent',()=>{
 const report=validateReport(JSON.parse(fs.readFileSync('web/data/benchmark.json','utf8')));
 assert.equal(report.experiments.length,4);
 for(const e of report.experiments){assert.equal(e.summary.length,9);assert.equal(e.runs.length,27);assert.match(comparisonCSV(e),/cp_gd/);}
});

const app=require('../web/app.js');
const report=JSON.parse(fs.readFileSync('web/data/benchmark.json','utf8'));
test('paper advantages reflect measured tradeoffs rather than universal superiority',()=>{
 const narrow=app.comparePaper(report.experiments[0]);
 assert.deepEqual(narrow.reliability,['pso','hs','ann']);
 assert.ok(narrow.lowerPeak.includes('ga'));
 assert.ok(narrow.higherPeak.includes('heuristic'));
 const wide=app.comparePaper(report.experiments[2]);
 assert.equal(wide.reliability.length,0);
 assert.ok(wide.higherPeak.includes('ga'));
});
test('missing feasible runs are not described as worse peak measurements',()=>{
 const r=app.comparePaper({summary:[{algorithm:'cp_gd',mean_peak:null,success_rate:0,mean_runtime:2},{algorithm:'ga',mean_peak:3,success_rate:100,mean_runtime:1}]});
 assert.deepEqual(r.lowerPeak,[]);assert.deepEqual(r.higherPeak,[]);
});
test('combined convergence includes nine methods and only feasible histories',()=>{
 const series=app.allConvergence(report.experiments[0],42);
 assert.equal(series.length,9);
 assert.equal(series.find(s=>s.id==='pso').points.length,0);
 assert.ok(series.find(s=>s.id==='cp_gd').points.length>0);
 assert.equal(app.allConvergence(report.experiments[0],999).flatMap(s=>s.points).length,0);
});
test('English applies to charts, errors, matrix and empty states',()=>{
 app.languageChange('en');
 assert.match(app.matrixHTML(report),/Scenario 1/);
 assert.match(app.matrixHTML(report),/Heuristic/);
 assert.match(app.scatterSVG(report.experiments[0].summary),/Mean runtime/);
 assert.match(app.lineSVG([{points:[]}],{title:'empty'}),/No feasible/);
 assert.throws(()=>app.validateReport({}),/Invalid report/);
 app.languageChange('tr');
 assert.match(app.matrixHTML(report),/Senaryo 1/);
});
