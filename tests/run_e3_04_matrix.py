"""E3-04 52x4 run matrix: four engine paths on the inherited model set.

36 generated cases run for real; 16 micro cases have no original bytes and
are recorded NOT_RUNNABLE_PROVENANCE rather than fabricated.  All resource
metrics are measured at run time.
"""
import csv
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat')]
from engine_interface import check_applicability, from_generator_net  # noqa: E402
from engine_paths import run_path  # noqa: E402
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402

LEDGER = ROOT / 'reports/e3_06/r6_12_logic_52x4_ledger.csv'
METHODS = ('MAIN', 'FULL_HISTORY', 'NO_SYNC', 'NO_ENVELOPE')
OUT = ROOT / 'runs/e3_04'


def generate_from_params(params):
    return generate_rmt_fms(n_machines=params['n_machines'], n_parts=params['n_parts'],
                            ops_per_part=params['ops_per_part'], wip_bound=params['wip_bound'],
                            unobservable_ratio=params['unobservable_ratio'],
                            fault_locations=params['fault_locations'],
                            interval_width_factor=params['interval_width_factor'],
                            adjustable_ratio=params['adjustable_ratio'],
                            seed=params.get('seed', 0), machine_capacity=1, n_configs=2,
                            repair_domain='standard')


def main(node_budget=200000):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(LEDGER.open()))
    results = []
    cases = sorted({r['case_id'] for r in rows})
    for case in cases:
        case_rows = [r for r in rows if r['case_id'] == case]
        family = case_rows[0]['family']
        if family == 'micro':
            for r in case_rows:
                results.append({'case_id': case, 'family': family, 'method': r['method'],
                                'status': 'NOT_RUNNABLE_PROVENANCE',
                                'note': 'original micro model bytes absent; no fabricated run'})
            continue
        params = json.loads(case_rows[0]['params'])
        net, L, H = generate_from_params(params)
        model = from_generator_net(net, L, H)
        applicability = check_applicability(model)
        for method in METHODS:
            if not applicability['supported']:
                results.append({'case_id': case, 'family': family, 'method': method,
                                'status': 'UNSUPPORTED',
                                'reasons': json.dumps(applicability['reasons'])})
                continue
            result = run_path(model, method, node_budget)
            stats = result.get('path_stats', {})
            resources = result.get('resources', {})
            results.append({'case_id': case, 'family': family, 'method': method,
                            'status': result['status'], 'verdict': result.get('verdict'),
                            'expansions': stats.get('expansions'),
                            'state_classes': stats.get('state_classes'),
                            'sync_pairs': stats.get('sync_pairs'),
                            'lp_calls': stats.get('lp_calls'),
                            'envelope_splits': stats.get('envelope_splits'),
                            'wall_seconds': round(resources.get('wall_seconds', 0), 6),
                            'cpu_seconds': round(resources.get('cpu_seconds', 0), 6),
                            'peak_memory_bytes': resources.get('peak_memory_bytes'),
                            'certificate': json.dumps(result.get('certificate'), sort_keys=True)})
        print(f'{case}: done', flush=True)
    out_csv = OUT / 'matrix_52x4.csv'
    fields = ['case_id', 'family', 'method', 'status', 'verdict', 'expansions', 'state_classes',
              'sync_pairs', 'lp_calls', 'envelope_splits', 'wall_seconds', 'cpu_seconds',
              'peak_memory_bytes', 'certificate', 'reasons', 'note']
    with out_csv.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    summary = {'rows': len(results),
               'runnable_cases': sum(1 for c in cases if next(r for r in rows if r['case_id'] == c)['family'] != 'micro'),
               'not_runnable_micro': sum(1 for r in results if r['status'] == 'NOT_RUNNABLE_PROVENANCE'),
               'method_calls': sum(1 for r in results if r['method'] in METHODS and r['status'] not in ('NOT_RUNNABLE_PROVENANCE',)),
               'status_counts': {s: sum(1 for r in results if r['status'] == s)
                                 for s in sorted({r['status'] for r in results})},
               'csv': str(out_csv.relative_to(ROOT))}
    (OUT / 'matrix_52x4_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main(node_budget=int(sys.argv[1]) if len(sys.argv) > 1 else 200000)
