"""Read-only checks of the supplied CSVs; write a reproducible JSON report."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import numpy as np
import pandas as pd

root=Path('/Users/honour/My Drive/Makale/Server Load')
paths={'output':root/'ExampleFiles/2/2026-06-29T10-55_export.csv',
       'slots':root/'ExampleFiles/timeslots_program_ready.csv',
       'raw':root/'HamVeriler/arasinavlar.xlsx'}
o=pd.read_csv(paths['output']); t=pd.read_csv(paths['slots'])
r=pd.read_excel(paths['raw'],sheet_name='Page 1')
g=r.groupby('DERS_KOD').OGR_SAY.sum()
m=o.set_index('exam_id').student_count.to_frame('output').join(g.rename('input'),how='outer')
loads=o.groupby('timeslot_id').student_count.sum()
j=o.merge(t,on='timeslot_id',how='left',suffixes=('_out','_slot'),validate='many_to_one',indicator=True)
start=pd.to_datetime(t.date+' '+t.start_time,format='%Y-%m-%d %H:%M')
end=pd.to_datetime(t.date+' '+t.end_time,format='%Y-%m-%d %H:%M')
durations=(end-start).dt.total_seconds()/60
limits=[]
for row in t.itertuples():
    n=int(loads.get(row.timeslot_id,0))
    limits.append({'timeslot_id':int(row.timeslot_id),'date':row.date,'start_time':row.start_time,'end_time':row.end_time,'students':n,
                   'cpu':n*.02,'ram':n*.05,'bandwidth':n*.2,
                   'provided_capacity_violation':bool(n>row.capacity or n>row.max_concurrent_students or n*.02>row.max_cpu or n*.05>row.max_ram or n*.2>row.max_bandwidth),
                   'default_capacity_violation':bool(n>5000 or n*.02>100 or n*.05>256 or n*.2>1000)})

def peak(starts,ends,counts):
    events=defaultdict(int)
    for s,e,n in zip(starts,ends,counts):events[s]+=int(n);events[e]-=int(n)
    active=highest=0;when=None
    for time,delta in sorted(events.items()):
        active+=delta
        if active>highest:highest=active;when=time
    assert active==0
    return {'peak':highest,'time':str(when)}

os=pd.to_datetime(o.date+' '+o.start_time,format='%Y-%m-%d %H:%M')
oe=pd.to_datetime(o.date+' '+o.end_time,format='%Y-%m-%d %H:%M')
rawstart=pd.to_datetime(r.TARIH+' '+r.SAAT,format='%d.%m.%Y %H:%M')
sensitivity=[]
for minutes in [30,60,120]:
    delta=pd.Timedelta(minutes=minutes)
    sensitivity.append({'assumed_minutes':minutes,'raw':peak(rawstart,rawstart+delta,r.OGR_SAY),'output':peak(os,os+delta,o.student_count),'interpretation':'Duration sensitivity only; actual exam duration unverified'})

rawdept=r.groupby('PROG_AD').OGR_SAY.sum()
outdept=o.groupby('department_id').student_count.sum()
dep=rawdept.to_frame('raw').join(outdept.rename('output'),how='outer').fillna(0)
dep['difference']=dep.output-dep.raw
deptdiff=[{'department':idx,**{k:int(v) for k,v in row.items()}} for idx,row in dep.loc[dep.difference.ne(0)].iterrows()]
coll=r.groupby('DERS_KOD').agg(departments=('PROG_AD','nunique'),dates=('TARIH','nunique'),times=('SAAT','nunique'),rows=('DERS_KOD','size'))
coll=coll[(coll.departments>1)|(coll.dates>1)|(coll.times>1)]
rawdate=pd.to_datetime(r.TARIH,format='%d.%m.%Y')
original_on_output_day=int(r.loc[rawdate.eq(pd.Timestamp('2023-04-10')),'OGR_SAY'].sum())
resource_errors={c:int((~np.isclose(o[c],o.student_count*k)).sum()) for c,k in [('cpu_usage',.02),('ram_usage',.05),('bandwidth_usage',.2)]}
report={
 'sources':{k:{'path':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in paths.items()},
 'raw_rows':len(r),'output_rows':len(o),'timeslot_rows':len(t),'enrollments':int(o.student_count.sum()),
 'duplicate_exam_ids':int(o.exam_id.duplicated().sum()),'duplicate_slot_ids':int(t.timeslot_id.duplicated().sum()),
 'missing_output_cells':int(o.isna().sum().sum()),'missing_slot_cells':int(t.isna().sum().sum()),
 'invalid_counts':int((~np.isfinite(o.student_count)|o.student_count.le(0)|o.student_count.mod(1).ne(0)).sum()),
 'identifier_or_count_mismatches':int((m.output.ne(m.input)|m.isna().any(axis=1)).sum()),
 'unmatched_slot_ids':int(j['_merge'].ne('both').sum()),
 'slot_field_mismatches':{c:int(j[c+'_out'].ne(j[c+'_slot']).sum()) for c in ['date','start_time','end_time']},
 'resource_formula_errors':resource_errors,'reported_slot_total_errors':int(o.timeslot_total_students.ne(o.timeslot_id.map(loads)).sum()),
 'invalid_intervals':int(end.le(start).sum()),'adjacent_overlap_count':int((start.iloc[1:].reset_index(drop=True)<end.iloc[:-1].reset_index(drop=True)).sum()),
 'duration_counts_minutes':{str(k):int(v) for k,v in durations.value_counts().sort_index().items()},
 'raw_unique_dates':int(rawdate.nunique()),'output_unique_dates':int(o.date.nunique()),'raw_date_range':[str(rawdate.min().date()),str(rawdate.max().date())],
 'original_enrollments_on_output_day':original_on_output_day,
 'slot_load_min':int(loads.min()),'slot_load_max':int(loads.max()),'slot_load_mean':float(loads.mean()),'slot_load_sample_variance':float(loads.var()),
 'provided_capacity_violation_slots':sum(x['provided_capacity_violation'] for x in limits),
 'default_capacity_violation_slots':sum(x['default_capacity_violation'] for x in limits),
 'peak_using_stated_end_times':peak(os,oe,o.student_count),'duration_sensitivity':sensitivity,
 'merged_conflicting_course_codes':len(coll),'department_total_differences':deptdiff,
 'slot_checks':limits,
 'common_course_examples':o[o.exam_id.isin(['TUR-270','ATA-260','ING-102','FRM-902','FRM-904','FRM-906'])][['exam_id','student_count','date','start_time','end_time']].to_dict('records'),
 'extra_index_column':{'name':'Unnamed: 0','unique':bool(o['Unnamed: 0'].is_unique),'min':int(o['Unnamed: 0'].min()),'max':int(o['Unnamed: 0'].max())},
}
dest=Path(__file__).parent/'csv_kontrol_sonuclari.json'
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['sources','department_total_differences','slot_checks']},ensure_ascii=False,indent=2))
print('Departments with changed totals:',len(deptdiff))
