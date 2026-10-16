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
 app.languageChange('en');assert.match(app.matrixHTML(report),/Scenario 3/);assert.match(app.scatterSVG(report.experiments[0].summary),/Mean runtime/);assert.match(app.paperComparisonHTML(report.experiments[0]),/Shared certified lower bound/);assert.match(app.lineSVG([{points:[]}],{title:'empty'}),/No feasible/);assert.throws(()=>app.validateReport({}),/Invalid report/);app.languageChange('tr');
});

test('scenario 3 uses 5000 without a duplicate paper experiment',()=>{
 assert.equal(report.scenarios.scenario_3,5000);
 assert.equal(report.experiments.find(e=>e.scenario==='scenario_3').capacity,5000);
 assert.equal(report.experiments.some(e=>e.scenario==='paper'),false);
 const html=fs.readFileSync('web/index.html','utf8');
 assert.ok(!html.includes('<code>'));
 assert.ok(!html.includes('6,000'));
});
test('publication tables preserve failed runs and compute sample statistics',()=>{
 const metric=peak=>({peak,feasible:true,minutes_above_capacity:0,excess_participant_minutes:0,load_variance:4});
 const e={capacity:100,certified_lower_bound:40,reference:metric(200),summary:[{algorithm:'a'},{algorithm:'b'}],runs:[{algorithm:'a',metrics:metric(40),runtime_seconds:1},{algorithm:'a',metrics:metric(60),runtime_seconds:3},{algorithm:'a',metrics:null,runtime_seconds:8},{algorithm:'b',metrics:null,runtime_seconds:2}]};
 const t=app.publicationTables(e);
 assert.equal(t.impact[1].reduction_pct,75);assert.equal(t.impact[2].overload_minutes,null);
 assert.equal(t.stability[0].median,50);assert.equal(t.stability[0].runtime,4);
 assert.equal(t.stability[0].std,Math.sqrt(200));assert.equal(t.quality[0].certified,1);
});
test('publication site exposes research data and Excel without method section',()=>{
 const html=fs.readFileSync('web/index.html','utf8');
 assert.match(html,/ExamFlow: A Capacity-Constrained Exam Timetabling System/);
 assert.match(html,/Anonymized_Example_data.xlsx/);
 assert.match(html,/id="schedule-excel"/);
 assert.ok(!html.includes('id="method"'));
 assert.ok(fs.existsSync('web/data/Anonymized_Example_data.xlsx'));
});
