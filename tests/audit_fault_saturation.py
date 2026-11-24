"""E3-05 fact audit: recompute actual fault counts for saturated candidates.

For every VALID candidate whose requested fault_locations exceeds the number
of machines that can host operations, generate the real PN and count actual
distinct fault machines and fault transitions. The generator saturates at
min(requested, used_machines); this audit measures, never edits, V0.
"""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'baseline_readonly/e2/implementations/generator_compat'))
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402

UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
OUT_DIR = ROOT / 'runs/domain_audit'


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(UNIVERSE.open(newline='', encoding='utf-8')))
    saturated = [r for r in rows
                 if r['static_validity'] == 'VALID_BY_FROZEN_RULE'
                 and int(r['fault_locations']) > min(int(r['machine_counts']),
                                                     int(r['part_type_counts']) * int(r['operations_per_part']))]
    results = []
    mismatches = []
    for index, r in enumerate(saturated, 1):
        params = {'n_machines': int(r['machine_counts']), 'n_parts': int(r['part_type_counts']),
                  'ops_per_part': int(r['operations_per_part']), 'wip_bound': int(r['wip_bounds']),
                  'unobservable_ratio': float(r['unobservable_ratios']),
                  'fault_locations': int(r['fault_locations']),
                  'interval_width_factor': float(r['interval_width_factors']),
                  'adjustable_ratio': float(r['adjustable_ratios']),
                  'seed': int(r['seed']), 'machine_capacity': 1, 'n_configs': 2,
                  'repair_domain': 'standard'}
        net, L, H = generate_rmt_fms(**params)
        fault_transitions = [t for t in net.transitions.values() if t.is_fault]
        fault_machines = {t.name.split('_m')[-1].split('_cfg')[0] for t in fault_transitions}
        used_machines = min(params['n_machines'], params['n_parts'] * params['ops_per_part'])
        expected_fault_machines = min(params['fault_locations'], used_machines)
        row = {'candidate_id': r['candidate_id'],
               'requested_fault_locations': params['fault_locations'],
               'used_machine_count': used_machines,
               'actual_distinct_fault_machine_count': len(fault_machines),
               'actual_fault_transition_count': len(fault_transitions),
               'n_configs': params['n_configs'],
               'expected_fault_machine_count': expected_fault_machines,
               'expected_fault_transition_count': expected_fault_machines * params['n_parts'] * params['ops_per_part'] // used_machines * params['n_configs'],
               'L': str(L), 'H': str(H)}
        results.append(row)
        if (row['actual_distinct_fault_machine_count'] != expected_fault_machines
                or row['actual_fault_transition_count'] % params['n_configs'] != 0):
            mismatches.append(row)
        if index % 480 == 0:
            print(f'progress {index}/{len(saturated)}', flush=True)
    out_csv = OUT_DIR / 'fault_saturation_3840.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    summary = {'status': 'PASS' if not mismatches else 'FAIL',
               'scope': 'FACT_AUDIT_ONLY_V0_UNMODIFIED',
               'saturated_valid_candidates': len(results),
               'formula_mismatches': len(mismatches),
               'requested_range': [min(r['requested_fault_locations'] for r in results),
                                   max(r['requested_fault_locations'] for r in results)],
               'actual_fault_machine_range': [min(r['actual_distinct_fault_machine_count'] for r in results),
                                              max(r['actual_distinct_fault_machine_count'] for r in results)],
               'actual_fault_transition_range': [min(r['actual_fault_transition_count'] for r in results),
                                                 max(r['actual_fault_transition_count'] for r in results)],
               'semantics': 'requested fault_locations saturates at used_machine_count; '
                            'actual fault transitions = ops on sampled fault machines x n_configs',
               'csv': str(out_csv.relative_to(ROOT))}
    (OUT_DIR / 'fault_saturation_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return int(bool(mismatches))


if __name__ == '__main__':
    sys.exit(main())
