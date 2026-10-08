'use strict';
const langAPI=typeof module!=='undefined'?require('./i18n.js'):I18N;
const {UI,L}=langAPI;
let language='tr';
function setLanguage(value){language=value==='en'?'en':'tr';langAPI.setLanguage(language);}
const SHORT={...UI.tr.short};
const number=(n,d=0)=>n==null?'—':n.toLocaleString(language==='en'?'en-US':'tr-TR',{maximumFractionDigits:d,minimumFractionDigits:d});
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function validateReport(r){
 const fail=()=>{throw new Error(L('Geçersiz rapor. benchmark.json seçin.','Invalid report. Select benchmark.json.'));};
 const finite=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
 if(!r||r.schema_version!==2||!r.dataset||!r.settings||!r.algorithms||!Array.isArray(r.experiments)||!r.experiments.length||!Array.isArray(r.timeline)||r.timeline.length<2||!Array.isArray(r.exams)||!Array.isArray(r.starts)||!r.starts.length)fail();
 if(!finite(r.dataset.exams)||!finite(r.dataset.enrollments)||!finite(r.dataset.duration_minutes)||!Array.isArray(r.settings.seeds))fail();
 if(r.timeline.some((t,i)=>!Number.isFinite(Date.parse(t))||(i&&Date.parse(t)<=Date.parse(r.timeline[i-1]))))fail();
 const metrics=m=>m&&finite(m.peak)&&typeof m.feasible==='boolean'&&finite(m.minutes_above_capacity)&&Array.isArray(m.loads)&&m.loads.length===r.timeline.length-1&&m.loads.every(finite);
 for(const e of r.experiments){
  if(!e||!finite(e.capacity)||!e.capacity||!metrics(e.reference)||!Array.isArray(e.runs)||!e.runs.length||!Array.isArray(e.summary))fail();
  for(const run of e.runs){
   if(!Object.hasOwn(SHORT,run.algorithm)||!finite(run.seed)||!finite(run.runtime_seconds)||!finite(run.evaluations)||!Array.isArray(run.history))fail();
   if(run.metrics!==null&&!metrics(run.metrics))fail();
   if(run.metrics&&(!Array.isArray(run.assignment)||run.assignment.length!==r.exams.length||run.assignment.some(t=>!Number.isInteger(t)||t<0||t>=r.starts.length)))fail();
   if(run.history.some(h=>!finite(h.seconds)||!finite(h.peak)||typeof h.feasible!=='boolean'))fail();
  }
  if(e.summary.some(s=>!Object.hasOwn(SHORT,s.algorithm)||!finite(s.success_rate)||s.success_rate>100||!finite(s.mean_runtime)||!finite(s.runs)||!finite(s.feasible_runs)||[s.mean_peak,s.std_peak,s.best_peak].some(v=>v!==null&&!finite(v))))fail();
 }
 return r;
}
function csvCell(value){const s=String(value??'');return '"'+(/^[=+@-]/.test(s)?"'":'')+s.replace(/"/g,'""')+'"';}
function comparisonCSV(e){return [['algorithm','feasible_runs','runs','success_rate_pct','mean_peak','std_peak','best_peak','mean_runtime_seconds','mean_gap_pct'],...e.summary.map(s=>[s.algorithm,s.feasible_runs,s.runs,s.success_rate,s.mean_peak,s.std_peak,s.best_peak,s.mean_runtime,s.mean_gap_pct])].map(row=>row.map(csvCell).join(',')).join('\r\n');}
function barSVG(rows,field,title,unit,errors=false){
 const w=520,h=210,left=115,right=70,top=12,step=40,max=Math.max(1,...rows.map(r=>(r[field]??0)+(errors?(r.std_peak??0):0)))*1.12,scale=v=>v/max*(w-left-right);
 let content='';
 for(let i=0;i<4;i++){let v=max*i/3,x=left+scale(v);content+=`<line x1="${x}" y1="3" x2="${x}" y2="${h-20}" stroke="#edf0f2"/><text x="${x}" y="${h-3}" text-anchor="middle">${number(v,unit==='s'?1:0)}</text>`;}
 rows.forEach((r,i)=>{const y=top+i*step,v=r[field],color=COLORS[r.algorithm];content+=`<text x="${left-12}" y="${y+13}" text-anchor="end">${esc(SHORT[r.algorithm])}</text>`;
 if(v==null){content+=`<text x="${left+4}" y="${y+13}">${L('Olurlu çözüm yok','No feasible result')}</text>`;return;}
 content+=`<rect x="${left}" y="${y}" width="${scale(v)}" height="19" rx="3" fill="${color}"><title>${esc(SHORT[r.algorithm])}: ${number(v,1)} ${esc(unit)}</title></rect><text x="${left+scale(v)+8}" y="${y+13}">${number(v,unit==='s'?2:0)}${esc(unit)}</text>`;
 if(errors&&r.std_peak){const a=left+scale(Math.max(0,v-r.std_peak)),b=left+scale(v+r.std_peak);content+=`<path d="M${a},${y+5}V${y+15}M${a},${y+10}H${b}M${b},${y+5}V${y+15}" stroke="#294c58" fill="none"/>`;}});
 return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${content}</svg>`;
}
function lineSVG(series,{title,capacity=null,time=false,width=1080,height=270}={}){
 const points=series.flatMap(s=>s.points);if(!points.length)return '<p class="subtle">'+L('Olurlu çözüm bulunamadı.','No feasible solution found.')+'</p>';
 const left=55,top=20,right=20,bottom=42,xmin=Math.min(...points.map(p=>p[0])),xmax=Math.max(xmin+1,...points.map(p=>p[0])),ymax=Math.max(1,capacity??0,...points.map(p=>p[1]))*1.15;
 const x=v=>left+(v-xmin)/(xmax-xmin)*(width-left-right),y=v=>height-bottom-v/ymax*(height-top-bottom);
 let content='';for(let i=0;i<=4;i++){const v=ymax*i/4;content+=`<line x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}" stroke="#e9eef1"/><text x="${left-10}" y="${y(v)+4}" text-anchor="end">${number(v)}</text>`;}
 for(let i=0;i<=4;i++){const v=xmin+(xmax-xmin)*i/4,label=time?new Date(v).toLocaleString(language==='en'?'en-GB':'tr-TR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'UTC'}):number(v,2)+' s';content+=`<text x="${x(v)}" y="${height-15}" text-anchor="${i===0?'start':i===4?'end':'middle'}">${esc(label)}</text>`;}
 if(capacity!=null)content+=`<path d="M${left},${y(capacity)}H${width-right}" stroke="#d78264" stroke-width="1.5" stroke-dasharray="6 5"/>`;
 series.forEach(s=>{if(!s.points.length)return;let path=`M${x(s.points[0][0])},${y(s.points[0][1])}`;for(const p of s.points.slice(1))path+=`H${x(p[0])}V${y(p[1])}`;content+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.id==='cp_gd'?3.5:1.8}"/><circle cx="${x(s.points[0][0])}" cy="${y(s.points[0][1])}" r="2.5" fill="${s.color}"/>`;});
 return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${content}</svg>`;
}
const COLORS={cp_gd:'#126b70',mip:'#d28a22',ilp:'#597bc3',goal:'#a6579c'};
function scenarioName(e){return e.scenario==='paper'?L('Makale deneyi','Paper experiment')+' · '+number(e.capacity):L('Senaryo ','Scenario ')+(e.scenario.match(/\d+/)?.[0]??e.scenario)+' · '+number(e.capacity);}
function comparePaper(e){
 const p=e.summary.find(s=>s.algorithm==='cp_gd');if(!p)return null;
 const others=e.summary.filter(s=>s.algorithm!=='cp_gd');
 const comparable=others.filter(s=>s.mean_peak!=null);
 const verdict=p.mean_peak==null?'no_feasible':!others.length?'insufficient':
   comparable.length<others.length?'incomplete':
   others.every(s=>p.success_rate>=s.success_rate&&p.mean_peak<s.mean_peak)?'better_peak':
   others.every(s=>p.success_rate===s.success_rate&&p.mean_peak===s.mean_peak)?'tie':
   others.every(s=>p.success_rate<=s.success_rate&&p.mean_peak>=s.mean_peak)&&others.some(s=>p.mean_peak>s.mean_peak)?'worse_peak':'mixed';
 return {paper:p,verdict,reliability:others.filter(s=>p.success_rate>s.success_rate).map(s=>s.algorithm),
 lowerPeak:others.filter(s=>p.mean_peak!=null&&s.mean_peak!=null&&p.mean_peak<s.mean_peak).map(s=>s.algorithm),
 higherPeak:others.filter(s=>p.mean_peak!=null&&s.mean_peak!=null&&p.mean_peak>s.mean_peak).map(s=>s.algorithm),
 faster:others.filter(s=>p.mean_runtime<s.mean_runtime).map(s=>s.algorithm)};
}
function allConvergence(e,seed){return Object.keys(SHORT).map(id=>{const r=e.runs.find(r=>r.algorithm===id&&r.seed===seed);const points=(r?.history??[]).filter(h=>h.feasible).map(h=>[h.seconds,h.peak]);if(points.length)points.push([r.runtime_seconds,points.at(-1)[1]]);return {id,color:COLORS[id],points};});}
function scatterSVG(rows){
 const valid=rows.filter(r=>r.mean_peak!=null),w=1080,h=340,left=70,right=80,top=20,bottom=55;
 if(!valid.length)return '<p>'+L('Olurlu sonuç yok.','No feasible results.')+'</p>';
 const xmax=Math.max(.001,...valid.map(r=>r.mean_runtime))*1.2,ymax=Math.max(1,...valid.map(r=>r.mean_peak))*1.15;
 const x=v=>left+v/xmax*(w-left-right),y=v=>h-bottom-v/ymax*(h-top-bottom);
 let out='';for(let i=0;i<=4;i++){const xx=x(xmax*i/4),yy=y(ymax*i/4);out+=`<path d="M${left},${yy}H${w-right}M${xx},${top}V${h-bottom}" stroke="#e9eef1" fill="none"/><text x="${left-10}" y="${yy+4}" text-anchor="end">${number(ymax*i/4)}</text><text x="${xx}" y="${h-bottom+20}" text-anchor="middle">${number(xmax*i/4,2)}</text>`;}
 valid.forEach((r,i)=>{const xx=x(r.mean_runtime),yy=y(r.mean_peak);out+=`<circle cx="${xx}" cy="${yy}" r="${r.algorithm==='cp_gd'?8:5}" fill="${COLORS[r.algorithm]}" stroke="white" stroke-width="1.5"><title>${esc(SHORT[r.algorithm])}: ${number(r.mean_runtime,3)} s / ${number(r.mean_peak,1)}; ${number(r.success_rate)}%</title></circle><text x="${xx+10}" y="${yy+(i%2?15:-8)}" style="fill:${COLORS[r.algorithm]}">${esc(SHORT[r.algorithm])}</text>`;});
 out+=`<text x="${w/2}" y="${h-5}" text-anchor="middle">${L('Ortalama süre (s)','Mean runtime (s)')}</text><text x="15" y="${h/2}" transform="rotate(-90 15 ${h/2})" text-anchor="middle">${L('Ortalama tepe','Mean peak')}</text>`;
 return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${L('Süre ve tepe yük karşılaştırması','Runtime and peak comparison')}">${out}</svg>`;
}
function matrixHTML(report){
 let html='<table><thead><tr><th>'+L('Algoritma','Algorithm')+'</th>'+report.experiments.map(e=>`<th>${esc(scenarioName(e))}</th>`).join('')+'</tr></thead><tbody>';
 for(const id of Object.keys(SHORT)){html+=`<tr class="${id==='cp_gd'?'proposed':''}"><td>${esc(SHORT[id])}</td>`;
 for(const e of report.experiments){const s=e.summary.find(s=>s.algorithm===id),best=Math.min(...e.summary.filter(s=>s.mean_peak!=null).map(s=>s.mean_peak));html+=`<td class="${s?.mean_peak!=null&&s.mean_peak===best?'best-cell':''}">${s?number(s.mean_peak,1)+' / '+number(s.success_rate)+'%':'—'}</td>`;}html+='</tr>';}
 return html+'</tbody></table>';
}
function paperComparisonHTML(e){
 const paper=e.summary.find(s=>s.algorithm==='cp_gd');if(!paper)return '';
 const peers=e.summary.filter(s=>s.algorithm!=='cp_gd');
 const rows=peers.map(s=>{const paired=e.runs.filter(r=>r.algorithm==='cp_gd'&&r.metrics?.feasible).map(p=>[p,e.runs.find(r=>r.algorithm===s.algorithm&&r.seed===p.seed)]).filter(([p,q])=>q?.metrics?.feasible);
 const wins=paired.filter(([p,q])=>p.metrics.peak<q.metrics.peak).length, ties=paired.filter(([p,q])=>p.metrics.peak===q.metrics.peak).length;
 const change=paper.mean_peak!=null&&s.mean_peak>0?100*(s.mean_peak-paper.mean_peak)/s.mean_peak:null;
 return '<tr><td>'+esc(SHORT[s.algorithm])+'</td><td>'+number(change,1)+(change==null?'':'%')+'</td><td>'+wins+' / '+ties+' / '+(paired.length-wins-ties)+'</td><td>'+number(paper.mean_runtime,3)+' / '+number(s.mean_runtime,3)+' s</td></tr>';}).join('');
 return '<table><thead><tr><th>'+L('Karşı model','Baseline')+'</th><th>'+L('Tepe avantajı (+ iyi)','Peak advantage (+ better)')+'</th><th>'+L('İyi / eşit / kötü*','Wins / ties / losses*')+'</th><th>'+L('Süre: makale / model','Runtime: paper / model')+'</th></tr></thead><tbody>'+rows+'</tbody></table><p class="subtle">'+L('*Aynı tohumdaki iki olurlu koşu. Tepe avantajı olurlu ortalamalardan hesaplanır.','*Pairs of feasible runs with the same seed. Peak advantage uses feasible-run means.')+'</p><p class="subtle">'+L('Ortak kanıtlanmış alt sınır: ','Shared certified lower bound: ')+number(e.certified_lower_bound)+'. '+L('Tablodaki açıklık: (tepe − alt sınır) / tepe; düşük daha iyi.','Table gap: (peak − lower bound) / peak; lower is better.')+'</p>';
}
function languageChange(value){setLanguage(value);Object.assign(SHORT,UI[language].short);}
if(typeof module!=='undefined')module.exports={validateReport,comparisonCSV,barSVG,lineSVG,esc,comparePaper,allConvergence,scatterSVG,matrixHTML,languageChange,paperComparisonHTML};
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id);let report;
 const selected=()=>report.experiments[Number($('scenario').value)];
 const run=()=>selected().runs.find(r=>r.algorithm===$('algorithm').value&&String(r.seed)===$('seed').value);
 const text=(id,value)=>{$(id).textContent=value;};
 function options(id,rows){const old=$(id).value;$(id).replaceChildren(...rows.map(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;}));if([...$(id).options].some(o=>o.value===old))$(id).value=old;}
 function selects(){options('scenario',report.experiments.map((e,i)=>[i,scenarioName(e)]));options('algorithm',Object.entries(UI[language].names).filter(([id])=>selected().runs.some(r=>r.algorithm===id)));setSeeds();}
 function setSeeds(){options('seed',selected().runs.filter(r=>r.algorithm===$('algorithm').value).map(r=>[r.seed,L('Tohum ','Seed ')+r.seed]));}
 function evidence(){
  $('evidence').replaceChildren();
  const names=ids=>ids.map(id=>SHORT[id]).join(', ');
  for(const e of report.experiments){const c=comparePaper(e);if(!c)continue;
   const card=document.createElement('article'),title=document.createElement('h4');title.textContent=scenarioName(e);card.append(title);
   const conclusions={
    better_peak:L('Bu deneyde bütün karşı modellere göre daha düşük ortalama tepe.','Lower mean peak than every baseline in this experiment.'),
    worse_peak:L('Bu deneyde tepe yük açısından karşı modellerin önüne geçmedi.','Did not outperform the baselines on peak load in this experiment.'),
    tie:L('Tepe yük ve başarı oranı eşit.','Peak load and success rate are tied.'),
    mixed:L('Sonuç karma; avantaj karşı modele ve ölçüte bağlı.','Mixed result; advantages depend on the baseline and metric.'),
    no_feasible:L('Makale yöntemi bu bütçede olurlu çözüm bulamadı.','The paper method found no feasible solution within this budget.'),
    incomplete:L('Bazı modeller çözüm bulamadı; tam tepe kıyaslaması yapılamıyor.','Some models found no feasible result; peak comparison is incomplete.'),
    insufficient:L('Karşı model sonucu yok.','No baseline results available.')};
   const lines=[conclusions[c.verdict],L('Olurlu koşular: ','Feasible runs: ')+`${c.paper.feasible_runs}/${c.paper.runs}`];
   if(c.reliability.length)lines.push(L('Daha yüksek başarı oranı: ','Higher success rate than: ')+names(c.reliability));
   if(c.lowerPeak.length)lines.push(L('Daha düşük ortalama tepe: ','Lower mean peak than: ')+names(c.lowerPeak));
   if(c.higherPeak.length)lines.push(L('Daha düşük tepe üretenler: ','Methods with lower peaks: ')+names(c.higherPeak));
   if(c.faster.length)lines.push(L('Daha kısa ortalama süre: ','Lower mean runtime than: ')+names(c.faster));
   if(!c.reliability.length&&!c.lowerPeak.length)lines.push(L('Başarı veya tepe yükte üstünlük gözlenmedi.','No advantage observed in success rate or peak load.'));
   for(const line of lines){const p=document.createElement('p');p.textContent=line;card.append(p);}$('evidence').append(card);
  }
 }
 function render(){
  const e=selected(),r=run(),m=r?.metrics,d=report.dataset;
  text('dataset-note',`${d.source_name} · ${number(d.exams)} ${L('sınav','exams')} · ${number(d.enrollments)} ${L('katılım','enrollments')} · ${d.slots} ${L('başlangıç','starts')} · ${d.duration_minutes} min`);
  text('data-badge',d.synthetic?L('SENTETİK ÖRNEK','SYNTHETIC SAMPLE'):L('YÜKLENEN DENEY','LOADED EXPERIMENT'));
  text('before-peak',number(e.reference.peak));text('after-peak',number(m?.peak));
  const reduction=m&&e.reference.peak?100*(e.reference.peak-m.peak)/e.reference.peak:null;
  text('reduction',reduction==null?'—':`${number(Math.abs(reduction),1)}% ${reduction>=0?L('azalma','reduction'):L('artış','increase')}`);
  text('feasibility',m?(m.feasible?L('Olurlu','Feasible'):L('Aşım','Exceeded')):L('Sonuç yok','No result'));
  text('overload',m?`${number(m.minutes_above_capacity)} min ${L('kapasite aşımı','over capacity')}`:`CP-SAT: ${r?.cp_status??'—'}`);
  text('runtime',`${number(r?.runtime_seconds,2)} s`);text('evals',`${number(r?.evaluations)} ${L('değerlendirme','evaluations')}`);
  text('run-note',r?.initial_peak!=null?`CP-SAT: ${number(r.initial_peak)} → GD: ${number(m.peak)}`:L('Seçilen tek koşu.','Selected single run.'));
  const times=report.timeline.map(t=>Date.parse(t+'Z')),curve=loads=>[...loads.map((v,i)=>[times[i],v]),[times.at(-1),0]];
  $('timeline-chart').innerHTML=lineSVG([{color:'#b1bec6',points:curve(e.reference.loads)},...(m?[{color:'#167d85',points:curve(m.loads)}]:[])],{title:L('Eşzamanlı katılım','Concurrent enrollments'),capacity:e.capacity,time:true});
  $('peak-chart').innerHTML=barSVG(e.summary,'mean_peak',L('Ortalama tepe','Mean peak'),'',true);
  $('runtime-chart').innerHTML=barSVG(e.summary,'mean_runtime',L('Ortalama süre','Mean runtime'),'s');
  $('success-chart').innerHTML=barSVG(e.summary,'success_rate',L('Başarı oranı','Success rate'),'%');
  $('tradeoff-chart').innerHTML=scatterSVG(e.summary);
  const convergence=allConvergence(e,Number($('seed').value));
  $('convergence-chart').innerHTML=lineSVG(convergence,{title:L('Tüm algoritmaların yakınsaması','All-algorithm convergence'),width:700,height:350});
  $('all-legend').innerHTML=Object.keys(SHORT).map(id=>`<span><i style="background:${COLORS[id]}"></i>${esc(SHORT[id])}${convergence.find(s=>s.id===id)?.points.length?'':L(' (olurlu geçmiş yok)',' (no feasible history)')}</span>`).join('');
  $('scenario-matrix').innerHTML=matrixHTML(report);$('paper-comparison').innerHTML=paperComparisonHTML(e);evidence();
  const sorted=[...e.summary].sort((a,b)=>b.success_rate-a.success_rate||(a.mean_peak??Infinity)-(b.mean_peak??Infinity));
  text('ranking-note',L('Sıralama: başarı oranı ↓, ortalama tepe ↑','Order: success rate ↓, mean peak ↑'));
  $('results-body').replaceChildren(...sorted.map(s=>{const tr=document.createElement('tr');if(s.algorithm==='cp_gd')tr.className='proposed';[UI[language].names[s.algorithm],`${s.feasible_runs} / ${s.runs}`,number(s.mean_peak,1),number(s.std_peak,1),number(s.best_peak),number(s.mean_runtime,3)+' s',number(s.mean_gap_pct,1)+'%'].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});return tr;}));
  text('settings-note',`${L('Tohumlar','Seeds')}: ${report.settings.seeds.join(', ')} · ${report.settings.seconds_per_run} s · ${report.settings.gd_max_evaluations} ${L('GD değerlendirme sınırı','GD evaluation limit')} · OR-Tools ${report.settings.ortools}`);
  $('schedule-download').disabled=!r?.assignment;
 }
 function translate(value){languageChange(value);document.documentElement.lang=language;$('language').value=language;document.querySelectorAll('[data-tr][data-en]').forEach(el=>{el.textContent=el.dataset[language];});try{localStorage.setItem('exam-balance-language',language);}catch{}if(report){selects();render();}if(!$('error').hidden)text('error',L('Rapor yüklenemedi. Geçerli bir JSON raporu seçin.','Report could not be loaded. Select a valid JSON report.'));}
 function accept(data){const checked=validateReport(data);report=checked;selects();const preferred=report.experiments.findIndex(e=>e.scenario==='paper');if(preferred>=0)$('scenario').value=preferred;selects();render();$('dashboard').hidden=false;$('loading').hidden=true;$('error').hidden=true;$('export').disabled=false;}
 function error(e){text('error',e.message);$('error').hidden=false;$('loading').hidden=true;}
 function download(content,name,type){const a=document.createElement('a'),url=URL.createObjectURL(new Blob(['\ufeff',content],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 $('language').addEventListener('change',()=>translate($('language').value));
 $('scenario').addEventListener('change',()=>{selects();render();});$('algorithm').addEventListener('change',()=>{setSeeds();render();});$('seed').addEventListener('change',render);
 $('report-file').addEventListener('change',async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>50*1024*1024)throw new Error(L('Rapor en fazla 50 MB olabilir.','Report size must not exceed 50 MB.'));accept(JSON.parse(await f.text()));}catch{error(new Error(L('Geçersiz rapor. benchmark.json seçin.','Invalid report. Select benchmark.json.')));}finally{e.target.value='';}});
 document.querySelector('label[for="report-file"]').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('report-file').click();}});
 $('export').addEventListener('click',()=>download(comparisonCSV(selected()),'algorithm_comparison.csv','text/csv;charset=utf-8'));
 $('schedule-download').addEventListener('click',()=>{const r=run();if(!r?.assignment)return;const rows=[['exam_id','student_count','reference_start','optimized_start'],...report.exams.map((e,i)=>[e.exam_id,e.student_count,report.starts[e.reference_slot],report.starts[r.assignment[i]]])];download(rows.map(row=>row.map(csvCell).join(',')).join('\r\n'),`schedule_${r.algorithm}_${r.seed}.csv`,'text/csv;charset=utf-8');});
 let initial='tr';try{initial=localStorage.getItem('exam-balance-language')||'tr';}catch{}translate(initial);
 fetch('data/benchmark.json').then(r=>{if(!r.ok)throw new Error();return r.json();}).then(accept).catch(()=>error(new Error(L('Örnek rapor yüklenemedi. JSON raporu seçebilirsiniz.','Sample report unavailable. You can load a JSON report.'))));
}
