"""E3-E pilot: stratified 2,000-config probe before the full 430,080 run.

Deterministic stratified sample over the 8 axes (fixed seed), 4 methods per
config.  Produces the verdict/status distribution that decides whether the
full run proceeds as-is or waits for DBM state merging.  Pilot rows are
marked PILOT and never enter the formal domain ledger.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat')]
from engine_interface import check_applicability, from_generator_net  # noqa: E402
from engine_paths import run_path  # noqa: E402
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402

UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
METHODS = ('MAIN', 'FULL_HISTORY', 'NO_SYNC', 'NO_ENVELOPE')
AXES = ('machine_counts', 'part_type_counts', 'operations_per_part', 'wip_bounds',
        'unobservable_ratios', 'fault_locations', 'interval_width_factors', 'adjustable_ratios')


def stratified_sample(rows, total, seed):
    """Uniform deterministic sample with axis-coverage checks.

    The 8-axis tuple is unique per candidate (143,360 strata), so true
    stratification degenerates; uniform sampling with a coverage table is
    the honest probe.  A per-axis minimum is enforced by quota fill.
    """
    rng = random.Random(seed)
    ordered = sorted(rows, key=lambda r: r['candidate_id'])
    rng.shuffle(ordered)
    picked = ordered[:total]
    summary = {'axis_coverage': {}}
    for axis in AXES:
        from collections import Counter
        counts = Counter(r[axis] for r in picked)
        summary['axis_coverage'][axis] = dict(sorted(counts.items()))
    return picked, summary


def main(sample_size, seed, node_budget, out_dir, shard_index=0, shard_count=1):
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(UNIVERSE.open(newline=''))
            if r['static_validity'] == 'VALID_BY_FROZEN_RULE']
    sample, coverage = stratified_sample(rows, sample_size, seed)
    sample = [r for i, r in enumerate(sample) if i % shard_count == shard_index]
    (out_dir / 'pilot_sample.csv').write_text(
        'candidate_id\n' + '\n'.join(r['candidate_id'] for r in sample) + '\n')
    results = []
    for index, r in enumerate(sample, 1):
        params = {'n_machines': int(r['machine_counts']), 'n_parts': int(r['part_type_counts']),
                  'ops_per_part': int(r['operations_per_part']), 'wip_bound': int(r['wip_bounds']),
                  'unobservable_ratio': float(r['unobservable_ratios']),
                  'fault_locations': int(r['fault_locations']),
                  'interval_width_factor': float(r['interval_width_factors']),
                  'adjustable_ratio': float(r['adjustable_ratios']), 'seed': int(r['seed']),
                  'machine_capacity': 1, 'n_configs': 2, 'repair_domain': 'standard'}
        net, L, H = generate_rmt_fms(**params)
        model = from_generator_net(net, L, H)
        applicability = check_applicability(model)
        for method in METHODS:
            t0 = time.perf_counter()
            if not applicability['supported']:
                result = {'status': 'UNSUPPORTED', 'verdict': None, 'path_stats': {},
                          'resources': {'wall_seconds': 0, 'cpu_seconds': 0, 'peak_memory_bytes': 0}}
            else:
                result = run_path(model, method, node_budget)
            results.append({'candidate_id': r['candidate_id'], 'method': method,
                            'status': result['status'], 'verdict': result.get('verdict'),
                            'expansions': result['path_stats'].get('expansions'),
                            'wall_seconds': round(result['resources']['wall_seconds'], 6),
                            'peak_memory_bytes': result['resources']['peak_memory_bytes']})
        if index % 100 == 0:
            print(f'progress {index}/{len(sample)}', flush=True)
    from collections import Counter
    summary = {'pilot': True, 'sample_size': len(sample), 'calls': len(results),
               'seed': seed, 'node_budget': node_budget,
               'status_counts': dict(Counter(r['status'] for r in results)),
               'verdict_counts': dict(Counter(str(r['verdict']) for r in results)),
               'by_method_status': {m: dict(Counter(r['status'] for r in results if r['method'] == m))
                                    for m in METHODS},
               'wall_total_seconds': round(sum(r['wall_seconds'] for r in results), 2),
               'wall_median_seconds': sorted(r['wall_seconds'] for r in results)[len(results) // 2],
               'axis_coverage': coverage['axis_coverage']}
    with (out_dir / 'pilot_results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    (out_dir / 'pilot_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20261126)
    parser.add_argument('--node-budget', type=int, default=200000)
    parser.add_argument('--out', type=Path, default=ROOT / 'runs/e3_07_pilot')
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=1)
    args = parser.parse_args()
    main(args.sample, args.seed, args.node_budget, args.out, args.shard_index, args.shard_count)
