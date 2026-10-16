"""Descriptive publication tables derived only from recorded runs."""
import numpy as np


def comparison_tables(experiment):
    baseline = experiment['reference']
    capacity = experiment['capacity']
    impact = [{'model': 'reference', 'n': 1, 'peak': baseline['peak'], 'reduction_pct': 0,
               'utilization_pct': 100 * baseline['peak'] / capacity,
               'overload_minutes': baseline['minutes_above_capacity'],
               'excess_minutes': baseline['excess_participant_minutes'],
               'variance': baseline['load_variance']}]
    stability, quality = [], []
    for summary in experiment['summary']:
        model = summary['algorithm']
        runs = [r for r in experiment['runs'] if r['algorithm'] == model]
        feasible = [r for r in runs if r.get('metrics') and r['metrics']['feasible']]
        peaks = [r['metrics']['peak'] for r in feasible]
        mean = lambda values: float(np.mean(values)) if values else None
        avg = mean(peaks)
        metric = lambda key: mean([r['metrics'][key] for r in feasible])
        impact.append({'model': model, 'n': len(feasible), 'peak': avg,
                       'reduction_pct': 100 * (baseline['peak'] - avg) / baseline['peak'] if avg is not None and baseline['peak'] else None,
                       'utilization_pct': 100 * avg / capacity if avg is not None else None,
                       'overload_minutes': metric('minutes_above_capacity'),
                       'excess_minutes': metric('excess_participant_minutes'), 'variance': metric('load_variance')})
        stability.append({'model': model, 'total': len(runs), 'feasible': len(feasible),
                          'min': min(peaks) if peaks else None, 'median': float(np.median(peaks)) if peaks else None,
                          'max': max(peaks) if peaks else None,
                          'std': float(np.std(peaks, ddof=1)) if len(peaks) > 1 else None,
                          'runtime': mean([r['runtime_seconds'] for r in runs])})
        bound = experiment['certified_lower_bound']
        quality.append({'model': model, 'bound': bound, 'best': min(peaks) if peaks else None,
                        'gap': 100 * (min(peaks) - bound) / min(peaks) if peaks and min(peaks) else None,
                        'certified': sum(p == bound for p in peaks), 'total': len(runs)})
    return {'impact': impact, 'stability': stability, 'quality': quality}


TABLE_LABELS = {'impact': ('Başlangıca göre iyileşme ve kapasite', 'Improvement and capacity', {'model': ('Model', 'Model'), 'n': ('Olurlu koşu', 'Feasible runs'), 'peak': ('Ort. tepe', 'Mean peak'), 'reduction_pct': ('Tepe azalması (%)', 'Peak reduction (%)'), 'utilization_pct': ('Tepe / kapasite (%)', 'Peak / capacity (%)')}), 'stability': ('Tekrarlar arası tutarlılık', 'Consistency across runs', {'model': ('Model', 'Model'), 'feasible': ('Olurlu koşu', 'Feasible runs'), 'min': ('En düşük tepe', 'Minimum peak'), 'max': ('En yüksek tepe', 'Maximum peak'), 'runtime': ('Ort. süre (sn)', 'Mean runtime (s)')}), 'quality': ('Alt sınır ve optimum kanıtı', 'Lower bound and optimality evidence', {'model': ('Model', 'Model'), 'bound': ('Ortak alt sınır', 'Shared lower bound'), 'best': ('En iyi tepe', 'Best peak'), 'gap': ('En iyi açıklık (%)', 'Best gap (%)')})}


def advantage_rows(report):
    rows = []
    for e in report['experiments']:
        proposed = next(s for s in e['summary'] if s['algorithm'] == 'cp_gd')
        for peer in e['summary']:
            delta = None
            if proposed['mean_peak'] is not None and peer['mean_peak']:
                delta = 100 * (peer['mean_peak'] - proposed['mean_peak']) / peer['mean_peak']
            rows.append({'scenario': e['scenario'], 'capacity': e['capacity'], 'baseline': peer['algorithm'],
                         'advantage_pct': delta, 'proposed_peak': proposed['mean_peak'], 'baseline_peak': peer['mean_peak'],
                         'proposed_success': proposed['success_rate'], 'baseline_success': peer['success_rate']})
    return rows
