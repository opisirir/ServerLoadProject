from pathlib import Path
import hashlib
import json
import tempfile

import altair as alt
import pandas as pd
import streamlit as st

from examlab.benchmark import run
from examlab.comparison import comparison_tables, TABLE_LABELS, advantage_rows
from examlab.data import load_problem
from examlab.export import schedule_xlsx
from examlab.model import SCENARIOS

ROOT = Path(__file__).parent
MODELS = ['cp_gd', 'mip', 'ilp', 'goal']
NAMES = {'cp_gd': 'CP-SAT → Great Deluge', 'mip': 'MIP · CBC', 'ilp': 'ILP · CP-SAT', 'goal': 'Goal · CBC'}
COLORS = ['#2563eb', '#f97316', '#60a5fa', '#a78bfa']

st.set_page_config(page_title='ExamFlow: A Capacity-Constrained Exam Timetabling System', page_icon='📊', layout='wide')
st.markdown('''<style>
.block-container {max-width:1320px;padding-top:2rem;}
[data-testid="stMetric"] {background:#f1f5f9;border:1px solid #e2e8f0;border-radius:12px;padding:16px;}
[data-testid="stSidebar"] {background:#eff6ff;}
[data-testid="stDownloadButton"] button, [data-testid="stButton"] button {border:1px solid #93c5fd;background:#eff6ff;color:#1e40af;border-radius:10px;font-weight:600;}
[data-testid="stDownloadButton"] button:hover, [data-testid="stButton"] button:hover {background:#dbeafe;border-color:#2563eb;color:#1e3a8a;}
button[kind="primary"], [data-testid="stFormSubmitButton"] button {background:#2563eb;color:white;border:1px solid #2563eb;border-radius:10px;}
button[kind="primary"]:hover {background:#c2410c;border-color:#c2410c;}
h1,h2,h3 {color:#172554;}
h1 {letter-spacing:-.04em;} h3 {font-size:1.15rem;}
</style>''', unsafe_allow_html=True)
lang = st.sidebar.radio('Dil / Language', ['Türkçe', 'English'])
def t(tr, en):
    return tr if lang == 'Türkçe' else en


def validate_report(report):
    if not isinstance(report, dict):
        raise ValueError('Expected a JSON report object.')
    if report.get('schema_version') != 2 or set(report.get('algorithms', {})) != set(MODELS):
        raise ValueError('Expected schema_version 2 and cp_gd, mip, ilp, goal.')
    if not report.get('experiments'):
        raise ValueError('No experiments.')
    for e in report['experiments']:
        if set(s['algorithm'] for s in e['summary']) != set(MODELS):
            raise ValueError('Incomplete model summary.')
        if any(r['algorithm'] not in MODELS for r in e['runs']):
            raise ValueError('Unknown model.')
    return report


def model_color():
    return alt.Color('model:N', title=t('Model', 'Model'), scale=alt.Scale(domain=list(NAMES.values()), range=COLORS))


def chart(data, x, y, kind='bar'):
    base = alt.Chart(data)
    if kind == 'point':
        base = base.mark_circle(size=160)
    else:
        base = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    return base.encode(x=x, y=y, color=model_color(), tooltip=list(data.columns)).properties(height=300)


st.title('ExamFlow: A Capacity-Constrained Exam Timetabling System')
st.caption('Research companion · Algorithmic Exam Timetabling to Prevent Server Crash in Cloud-Based Learning Management Systems')
st.caption(t('Sınav çizelgeleme · Matematiksel model karşılaştırması', 'Exam timetabling · Mathematical model comparison'))
source = st.sidebar.selectbox(t('Veri kaynağı', 'Data source'), ['demo', 'report', 'compute'], format_func=lambda v: {'demo': t('Örnek veri sonuçları', 'Example dataset results'), 'report': t('JSON raporu yükle', 'Upload JSON report'), 'compute': t('Yeni karşılaştırma', 'New comparison')}[v])
st.sidebar.download_button(t('Örnek veriyi indir (Excel)', 'Download example data (Excel)'), (ROOT / 'web/data/Anonymized_Example_data.xlsx').read_bytes(), 'Anonymized_Example_data.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
with st.expander(t('Araştırma kullanımı ve sorumluluk bildirimi', 'Research use and disclaimer')):
    st.write(t('Bu uygulama bir akademik araştırma prototipidir ve her sınav programına uygun olmayabilir. Öğrenci çakışmaları ve kuruma özgü tüm kısıtlar modellenmez. Sonuçlar uygulamaya alınmadan önce kullanıcı tarafından doğrulanmalıdır. Hizmet sürekliliği, sunucu çökmesinin önlenmesi veya belirli bir sonuca ilişkin garanti verilmez. Yürürlükteki hukukun izin verdiği ölçüde, geliştiriciler ve araştırmacılar kullanım kaynaklı zararlardan sorumluluk kabul etmez. Bu bildirim kanunen dışlanamayan sorumlulukları sınırlamaz.', 'This application is an academic research prototype and may not suit every examination timetable. Student conflicts and all institution-specific constraints are not modeled. Users must validate results before operational use. No warranty is provided for service continuity, prevention of server crashes, or any particular outcome. To the extent permitted by applicable law, developers and researchers disclaim liability for damages arising from use. This notice does not exclude liability that cannot legally be excluded.'))
report = None
if source == 'demo':
    report = json.loads((ROOT / 'web/data/benchmark.json').read_text(encoding='utf-8'))
    st.info(t('Anonymized_Example_data: makale çalışmasına ait anonimleştirilmiş örnek veri. Gösterilen sonuçlar bu dosyayla yeniden hesaplanmıştır; makalede raporlanan koşulardan farklı olabilir.', 'Anonymized_Example_data: anonymized example data associated with the paper. Displayed results were recomputed from this file and may differ from the runs reported in the manuscript.'))
elif source == 'report':
    upload = st.sidebar.file_uploader(t('Sonuç raporu', 'Result report'), type=['json'])
    if upload:
        try:
            report = validate_report(json.loads(upload.getvalue()))
        except (ValueError, KeyError, TypeError) as exc:
            st.error(t('Geçersiz rapor: ', 'Invalid report: ') + str(exc))
else:
    st.subheader(t('Yeni karşılaştırma', 'New comparison'))
    st.caption(t('Kolonlar: exam_id, student_count, date, start_time. Türkçe karşılıkları desteklenir.', 'Columns: exam_id, student_count, date, start_time. Turkish aliases are supported.'))
    upload = st.file_uploader(t('Sınav verisi', 'Exam data'), type=['csv', 'xlsx', 'json'])
    with st.form('compute'):
        c1, c2, c3, c4 = st.columns(4)
        scenario = c1.selectbox(t('Senaryo', 'Scenario'), list(SCENARIOS), index=2, format_func=lambda s: (t('Senaryo ', 'Scenario ') + s[-1]) + f' · {SCENARIOS[s]:,}')
        seconds = c2.number_input(t('Model / koşu süresi (sn)', 'Seconds per model / run'), 1, 60, 15)
        repeats = c3.number_input(t('Tekrar', 'Repeats'), 1, 5, 3)
        minutes = c4.number_input(t('Sınav süresi (dk)', 'Exam duration (min)'), 1, 240, 60)
        submitted = st.form_submit_button(t('Karşılaştırmayı çalıştır', 'Run comparison'), type='primary')
    st.caption(t('Dört model sırayla çalışır. Toplam süre yaklaşık 4 × tekrar × süre.', 'Four models run sequentially. Total time is approximately 4 × repeats × seconds.'))
    if submitted:
        if upload is None:
            st.warning(t('Önce veri dosyasını seçin.', 'Select a data file first.'))
        else:
            try:
                with st.spinner(t('Modeller çalışıyor…', 'Running models…')):
                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory) / ('input' + Path(upload.name).suffix.lower())
                        path.write_bytes(upload.getvalue())
                        p, metadata = load_problem(path, int(minutes))
                    metadata['source_name'] = upload.name
                    metadata['sha256'] = hashlib.sha256(upload.getvalue()).hexdigest()
                    capacity = SCENARIOS[scenario]
                    st.session_state['computed_report'] = run(p, metadata, {scenario: capacity}, list(range(42, 42 + int(repeats))), float(seconds), 1000000)
            except (ValueError, RuntimeError, OSError) as exc:
                st.error(str(exc))
    report = st.session_state.get('computed_report')

if report is None:
    st.stop()
try:
    validate_report(report)
    experiments = report['experiments']
    options = list(range(len(experiments)))
    default = next((i for i, e in enumerate(experiments) if e['scenario'] == 'scenario_3'), 0)
    def scenario_label(i):
        e = experiments[i]
        name = t('Makale', 'Paper') if e['scenario'] == 'paper' else t('Senaryo ', 'Scenario ') + e['scenario'][-1]
        return f"{name} · {e['capacity']:,}"
    index = st.sidebar.selectbox(t('Rapor senaryosu · maks. kullanıcı', 'Report scenario · max. users'), options, index=default, format_func=scenario_label)
    e = experiments[index]
    df = pd.DataFrame(e['summary'])
    df['model'] = df['algorithm'].map(NAMES)
    dataset = report['dataset']
    columns = st.columns(4)
    for col, label, value in zip(columns, [t('Sınav', 'Exams'), t('Katılım', 'Enrollments'), t('Maks. eşzamanlı kullanıcı', 'Max. concurrent users'), t('Süre', 'Time')], [dataset['exams'], dataset['enrollments'], e['capacity'], str(report['settings']['seconds_per_run']) + ' s']):
        col.metric(label, f'{value:,}' if isinstance(value, int) else value)
    st.caption(f"{dataset.get('source_name', '')} · {dataset['duration_minutes']} min · {len(report['settings']['seeds'])} " + t('tekrar', 'repeats'))
    comparison, load_tab = st.tabs([t('Karşılaştırma', 'Comparison'), t('Yük ve çizelge', 'Load and schedule')])
    with comparison:
        paper = next(s for s in e['summary'] if s['algorithm'] == 'cp_gd')
        peers = [s for s in e['summary'] if s['algorithm'] != 'cp_gd']
        complete = paper['feasible_runs'] == paper['runs'] and all(s['feasible_runs'] == s['runs'] for s in peers)
        better = complete and all(paper['mean_peak'] < s['mean_peak'] for s in peers)
        worse = complete and all(paper['mean_peak'] > s['mean_peak'] for s in peers)
        tied = complete and all(paper['mean_peak'] == s['mean_peak'] for s in peers)
        verdict = t('Makale yöntemi bu deneyde daha düşük ortalama tepe yük buldu.', 'The paper method found a lower mean peak in this experiment.') if better else t('Makale yöntemi bu deneyde daha yüksek ortalama tepe yük buldu.', 'The paper method found a higher mean peak in this experiment.') if worse else t('Ortalama tepe yükleri eşit.', 'Mean peaks are equal.') if tied else t('Sonuç karma veya olurlu koşular eksik; genel üstünlük gösterilmedi.', 'Results are mixed or feasible runs are missing; overall superiority is not established.')
        if better:
            st.success(verdict)
        else:
            st.info(verdict)
        st.subheader(t('Önerilen yöntemin karşı modellere göre tepe yük avantajı', 'Proposed method: peak-load advantage over baselines'))
        advantage = pd.DataFrame(advantage_rows(report))
        advantage['baseline'] = advantage['baseline'].map(NAMES)
        advantage['scenario'] = advantage.apply(lambda r: f"{r['scenario'].split('_')[-1]} · {r['capacity']:,}", axis=1)
        comparison_load = df.dropna(subset=['mean_peak']).copy()
        comparison_load['display'] = comparison_load.apply(lambda r: r['model'] + (t(' · Makale yöntemi', ' · Proposed method') if r['algorithm'] == 'cp_gd' else ''), axis=1)
        max_peak = max(1, comparison_load['mean_peak'].max()) if len(comparison_load) else 1
        bars = alt.Chart(comparison_load).mark_bar(cornerRadius=5, size=30).encode(
            y=alt.Y('display:N', title=None, sort=alt.SortField(field='mean_peak', order='ascending'), axis=alt.Axis(labelLimit=340)),
            x=alt.X('mean_peak:Q', title=t('Ortalama tepe yük · Daha düşük daha iyi', 'Mean peak load · Lower is better'), scale=alt.Scale(domain=[0, max_peak * 1.18])),
            color=alt.condition(alt.datum.algorithm == 'cp_gd', alt.value('#2563eb'), alt.value('#f97316')),
            tooltip=[alt.Tooltip('model:N', title='Model'), alt.Tooltip('mean_peak:Q', format='.2f'), alt.Tooltip('success_rate:Q')])
        labels_adv = bars.mark_text(align='left', dx=7, fontSize=14, fontWeight='bold').encode(text=alt.Text('mean_peak:Q', format=',.2f'), color=alt.value('#172554'))
        st.altair_chart((bars + labels_adv).properties(height=240), use_container_width=True)
        st.caption(t('Daha kısa çubuk, daha düşük sunucu tepe yükü demektir. Mavi: makale yöntemi; turuncu: karşı modeller. Tüm çubuklar sıfırdan başlar ve aynı ölçektedir. Ortalamalar olurlu sonuçlara aittir.', 'A shorter bar means a lower server peak load. Blue: proposed method; orange: baselines. All bars start at zero and share the same scale. Means cover feasible results.'))
        for peer in peers:
            if paper['mean_peak'] is not None and peer['mean_peak']:
                reduction = 100 * (peer['mean_peak'] - paper['mean_peak']) / peer['mean_peak']
                direction = t('daha düşük', 'lower') if reduction > 0 else t('daha yüksek', 'higher') if reduction < 0 else t('eşit', 'equal')
                st.markdown(f"**{NAMES[peer['algorithm']]}:** " + t('Makale yönteminin ortalama tepe yükü ', 'The proposed method’s mean peak load is ') + (f"**%{abs(reduction):.2f} {direction}**" if reduction else f"**{direction}**"))
        st.download_button(t('Avantaj tablosunu indir', 'Download advantage table'), advantage.to_csv(index=False).encode('utf-8-sig'), 'peak_advantages.csv', 'text/csv')
        stages = [{'seed': str(r['seed']), 'stage': label, 'peak': peak} for r in e['runs'] if r['algorithm'] == 'cp_gd' and r.get('initial_peak') is not None and r.get('metrics') and r['metrics']['feasible'] for label, peak in [(t('CP-SAT başlangıç', 'CP-SAT initial'), r['initial_peak']), (t('GD sonrası', 'After GD'), r['metrics']['peak'])]]
        if stages:
            st.subheader(t('Great Deluge aşamasının gözlenen katkısı', 'Observed contribution of the Great Deluge stage'))
            stages_chart = alt.Chart(pd.DataFrame(stages)).mark_bar().encode(x=alt.X('seed:N', title=t('Koşu tohumu', 'Run seed')), xOffset='stage:N', y=alt.Y('peak:Q', title=t('Tepe yük', 'Peak load'), scale=alt.Scale(zero=True)), color=alt.Color('stage:N', title=t('Aşama', 'Stage')), tooltip=['seed', 'stage', 'peak'])
            st.altair_chart(stages_chart, use_container_width=True)
            st.caption(t('Aynı koşudaki ilk olurlu CP-SAT çözümü ile GD sonrasını karşılaştırır. Eşit süreli bağımsız CP-SAT optimizasyonuna karşı üstünlük testi değildir.', 'Compares the first feasible CP-SAT solution with the result after GD in the same run. This is not a superiority test against standalone CP-SAT optimization with equal time.'))
        c1, c2 = st.columns(2)
        c1.subheader(t('Ortalama tepe yük ↓', 'Mean peak load ↓'))
        c1.altair_chart(chart(df.dropna(subset=['mean_peak'])[['model', 'mean_peak', 'std_peak']], alt.X('model:N', title=None, sort=list(NAMES.values()), axis=alt.Axis(labelAngle=0)), alt.Y('mean_peak:Q', title=t('Eşzamanlı katılım', 'Concurrent enrollments'))), use_container_width=True)
        c2.subheader(t('Süre ve çözüm kalitesi', 'Runtime and solution quality'))
        c2.altair_chart(chart(df.dropna(subset=['mean_peak'])[['model', 'mean_runtime', 'mean_peak']], alt.X('mean_runtime:Q', title=t('Ortalama süre (sn) ↓', 'Mean runtime (s) ↓'), scale=alt.Scale(zero=True)), alt.Y('mean_peak:Q', title=t('Ortalama tepe ↓', 'Mean peak ↓')), 'point'), use_container_width=True)
        labels = {'model': t('Model', 'Model'), 'mean_peak': t('Ort. tepe', 'Mean peak'), 'mean_runtime': t('Süre (sn)', 'Runtime (s)'), 'success_rate': t('Olurlu koşu (%)', 'Feasible runs (%)'), 'mean_gap_pct': t('Açıklık (%)', 'Gap (%)')}
        table = df[list(labels)].rename(columns=labels)
        st.dataframe(table, hide_index=True, width='stretch')
        rows = []
        for peer in peers:
            delta = None if paper['mean_peak'] is None or not peer['mean_peak'] else 100 * (peer['mean_peak'] - paper['mean_peak']) / peer['mean_peak']
            paired = []
            for r in e['runs']:
                if r['algorithm'] != 'cp_gd' or not r['metrics'] or not r['metrics']['feasible']:
                    continue
                other = next((o for o in e['runs'] if o['algorithm'] == peer['algorithm'] and o['seed'] == r['seed'] and o['metrics'] and o['metrics']['feasible']), None)
                if other:
                    paired.append(r['metrics']['peak'] - other['metrics']['peak'])
            rows.append({t('Karşı model', 'Baseline'): NAMES[peer['algorithm']], t('Tepe azalması (%)', 'Peak reduction (%)'): delta, t('Kazanma / eşit / kaybetme', 'Wins / ties / losses'): f"{sum(x < 0 for x in paired)} / {sum(x == 0 for x in paired)} / {sum(x > 0 for x in paired)}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
        st.caption(t('Pozitif azalma makale yöntemi lehinedir. Yalnız iki modelin de olurlu olduğu eşleşmiş koşular sayılır.', 'Positive reduction favors the paper method. Paired counts include only runs where both models are feasible.'))
        st.subheader(t('Yakınsama', 'Convergence'))
        seed = st.selectbox(t('Koşu tohumu', 'Run seed'), report['settings']['seeds'])
        history = [{'model': NAMES[r['algorithm']], 'seconds': h['seconds'], 'peak': h['peak']} for r in e['runs'] if r['seed'] == seed for h in r.get('history', []) if h.get('feasible')]
        if history:
            base = alt.Chart(pd.DataFrame(history)).encode(x=alt.X('seconds:Q', title=t('Süre (sn)', 'Time (s)')), y=alt.Y('peak:Q', title=t('Tepe yük', 'Peak load')), color=model_color(), tooltip=['model', 'seconds', 'peak'])
            st.altair_chart(base.mark_line(interpolate='step-after', point=True).properties(height=300), use_container_width=True)
        st.caption(t('CBC yalnız son noktayı bildirir. Eksik çözüm sıfır olarak gösterilmez.', 'CBC reports only its final point. Missing solutions are not plotted as zero.'))
        st.caption(t('Ortak kanıtlanmış alt sınır: ', 'Shared certified lower bound: ') + str(e['certified_lower_bound']) + '. ' + t('Pozitif açıklık kesin optimum farkı değildir. Az sayıda tekrar genel üstünlüğü kanıtlamaz.', 'A positive gap is not the exact distance to optimum. Few repeats do not establish general superiority.'))
        st.download_button(t('Karşılaştırma CSV', 'Comparison CSV'), table.to_csv(index=False).encode('utf-8-sig'), 'comparison.csv', 'text/csv')
        st.subheader(t('Makale için karşılaştırma tabloları', 'Comparison tables for the paper'))
        st.caption(t('Seçili senaryo ve aynı deney bütçesi. Referans tek çizelgedir; model yük ölçüleri yalnız olurlu koşuların ortalamasıdır. Çözüm bulunamaması sıfır aşım anlamına gelmez.', 'Selected scenario and shared experiment budget. The reference is one schedule; model load metrics average feasible runs only. A missing solution does not mean zero overload.'))
        for key, rows in comparison_tables(e).items():
            title_tr, title_en, labels = TABLE_LABELS[key]
            with st.expander(t(title_tr, title_en), expanded=True):
                frame = pd.DataFrame(rows)[list(labels)]
                frame['model'] = frame['model'].map({**NAMES, 'reference': t('Başlangıç çizelgesi', 'Reference schedule')})
                frame = frame.rename(columns={k: t(*v) for k, v in labels.items()})
                st.dataframe(frame, hide_index=True, width='stretch')
                st.download_button(t('Tabloyu CSV indir', 'Download table CSV'), frame.to_csv(index=False).encode('utf-8-sig'), f'{e["scenario"]}_{key}.csv', 'text/csv', key=f'table_{key}')
        st.caption(t('Açıklık = (en iyi tepe − ortak alt sınır) / en iyi tepe. Pozitif açıklık gerçek optimum farkı değildir.', 'Gap = (best peak − shared lower bound) / best peak. A positive gap is not the exact distance to optimum.'))
    with load_tab:
        seed_load = st.selectbox(t('Yük grafiği tohumu', 'Load chart seed'), report['settings']['seeds'])
        load_rows = []
        selected = [r for r in e['runs'] if r['seed'] == seed_load and r['metrics']]
        for name, metrics in [(t('Referans', 'Reference'), e['reference'])] + [(NAMES[r['algorithm']], r['metrics']) for r in selected]:
            load_rows.extend({'time': stamp, 'load': value, 'model': name} for stamp, value in zip(report['timeline'][:-1], metrics['loads']))
            load_rows.append({'time': report['timeline'][-1], 'load': 0, 'model': name})
        load_chart = alt.Chart(pd.DataFrame(load_rows)).mark_line(interpolate='step-after').encode(x=alt.X('time:T', title=t('Zaman', 'Time')), y=alt.Y('load:Q', title=t('Eşzamanlı katılım', 'Concurrent enrollments')), color=alt.Color('model:N', title='Model'), tooltip=['time:T', 'model', 'load'])
        limit = alt.Chart(pd.DataFrame({'capacity': [e['capacity']]})).mark_rule(color='#ef4444', strokeDash=[5, 4]).encode(y='capacity:Q')
        st.altair_chart((load_chart + limit).properties(height=380), use_container_width=True)
        st.caption(t('Kırmızı çizgi: kapasite. Aralıklar [başlangıç, bitiş).', 'Red line: capacity. Intervals are [start, end).'))
        if selected:
            chosen = st.selectbox(t('Çizelge modeli', 'Schedule model'), [r['algorithm'] for r in selected], format_func=NAMES.get)
            result = next(r for r in selected if r['algorithm'] == chosen)
            schedule = pd.DataFrame([{'exam_id': exam['exam_id'], 'student_count': exam['student_count'], 'start': report['starts'][slot]} for exam, slot in zip(report['exams'], result['assignment'])])
            st.dataframe(schedule, hide_index=True, width='stretch')
            st.download_button(t('Optimize edilmiş çizelgeyi indir (Excel)', 'Download optimized schedule (Excel)'), schedule_xlsx(report, e, result), f'ExamFlow_{chosen}_{seed_load}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            st.download_button(t('Çizelge CSV', 'Schedule CSV'), schedule.to_csv(index=False).encode('utf-8-sig'), 'schedule.csv', 'text/csv')
    st.sidebar.download_button(t('JSON raporu indir', 'Download JSON report'), json.dumps(report, ensure_ascii=False, allow_nan=False), 'benchmark.json', 'application/json')
except (KeyError, TypeError, ValueError, IndexError) as exc:
    st.error(t('Rapor okunamadı: ', 'Could not read report: ') + str(exc))
