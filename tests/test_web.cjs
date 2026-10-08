const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=require('../web/app.js');
const report=JSON.parse(fs.readFileSync('web/data/benchmark.json','utf8'));
test('rejects malformed and legacy reports',()=>{for(const x of [null,{}, {...report,schema_version:1}])assert.throws(()=>app.validateReport(x));});
test('empty convergence is not a zero result',()=>assert.match(app.lineSVG([{points:[]}],{title:'empty'}),/bulunamadı/));
test('chart labels are escaped',()=>{assert.equal(app.esc('<script>'),'&lt;script&gt;');assert.ok(!app.barSVG([],'mean_peak','<script>','').includes('<script>'));});
test('report contains only the paper and mathematical models',()=>{
 app.validateReport(report);
 assert.deepEqual(Object.keys(report.algorithms),['cp_gd','mip','ilp','goal']);
 for(const e of report.experiments){assert.equal(e.summary.length,4);assert.equal(e.runs.length,12);assert.match(app.comparisonCSV(e),/mean_gap_pct/);for(const s of e.summary)assert.ok(Object.hasOwn(report.algorithms,s.algorithm));}
});
test('advantages and losses follow measured data',()=>{
 const c=app.comparePaper({summary:[{algorithm:'cp_gd',mean_peak:100,success_rate:100,mean_runtime:2},{algorithm:'mip',mean_peak:120,success_rate:50,mean_runtime:3},{algorithm:'ilp',mean_peak:90,success_rate:100,mean_runtime:1}]});
 assert.deepEqual(c.reliability,['mip']);assert.deepEqual(c.lowerPeak,['mip']);assert.deepEqual(c.higherPeak,['ilp']);assert.deepEqual(c.faster,['mip']);
 assert.equal(c.verdict,'mixed');
});
test('a favorable verdict requires lower peaks than every baseline',()=>{
 const row=(algorithm,peak)=>({algorithm,mean_peak:peak,success_rate:100,mean_runtime:2});
 assert.equal(app.comparePaper({summary:[row('cp_gd',100),row('mip',110),row('ilp',120)]}).verdict,'better_peak');
 assert.equal(app.comparePaper({summary:[row('cp_gd',150),row('mip',110),row('ilp',120)]}).verdict,'worse_peak');
 assert.equal(app.comparePaper({summary:[row('cp_gd',100),row('mip',100)]}).verdict,'tie');
});
test('no solution does not imply a peak advantage',()=>{
 const c=app.comparePaper({summary:[{algorithm:'cp_gd',mean_peak:null,success_rate:0,mean_runtime:2},{algorithm:'mip',mean_peak:3,success_rate:100,mean_runtime:1}]});assert.deepEqual(c.lowerPeak,[]);assert.deepEqual(c.higherPeak,[]);
});
test('combined convergence contains only selected mathematical methods',()=>{
 const series=app.allConvergence(report.experiments[0],42);assert.equal(series.length,4);assert.ok(series.find(s=>s.id==='cp_gd').points.length>0);assert.equal(app.allConvergence(report.experiments[0],999).flatMap(s=>s.points).length,0);
});
test('English includes gap and pairwise comparison explanations',()=>{
 app.languageChange('en');assert.match(app.matrixHTML(report),/Scenario 1/);assert.match(app.scatterSVG(report.experiments[0].summary),/Mean runtime/);assert.match(app.paperComparisonHTML(report.experiments[0]),/Shared certified lower bound/);assert.match(app.lineSVG([{points:[]}],{title:'empty'}),/No feasible/);assert.throws(()=>app.validateReport({}),/Invalid report/);app.languageChange('tr');
});
