"""E3-07 full-logic batch infrastructure: pre-registration and resumable runs.

Contract item 1: every expected config×spec×method task ID is written first
with status NOT_EXECUTED; real runs then update rows in place.  The candidate
V0 domain (seed=0, 107,520 valid configs × 4 methods) is used only as the
pre-registration population; if the signed domain differs, regenerate.
Nothing here executes the full domain before signoff.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat')]
from engine_interface import check_applicability, from_generator_net  # noqa: E402
from engine_paths import run_path  # noqa: E402
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402

UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
OUT = ROOT / 'runs/e3_07'
METHODS = ('MAIN', 'FULL_HISTORY', 'NO_SYNC', 'NO_ENVELOPE')
TERMINAL_STATUSES = {'EXHAUSTED_FOR_MODEL', 'UNRESOLVED', 'UNSUPPORTED', 'FAILED',
                     'NOT_RUNNABLE_PROVENANCE'}
FIELDS = ['task_id', 'candidate_id', 'spec_id', 'method_id', 'result_status', 'v_L',
          'witness_path', 'completeness_certificate', 'timed_trace', 'symbolic_state_count',
          'synchronized_pair_count', 'LP_count', 'elapsed_wall', 'cpu_seconds',
          'peak_python_alloc_bytes', 'exit_code', 'attempts', 'failure_reason',
          'model_sha256', 'updated_at']


def preregister(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(UNIVERSE.open(newline='')) if r['static_validity'] == 'VALID_BY_FROZEN_RULE']
    path = out_dir / 'preregistered_tasks.csv'
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            for method in METHODS:
                writer.writerow({'task_id': f"{r['candidate_id']}|L{''}|H{''}|{method}",
                                 'candidate_id': r['candidate_id'], 'spec_id': 'L,H:default',
                                 'method_id': method, 'result_status': 'NOT_EXECUTED',
                                 'attempts': 0})
    summary = {'tasks': len(rows) * len(METHODS), 'configs': len(rows), 'methods': len(METHODS),
               'domain': 'CANDIDATE_V0_107520_seed0_UNTIL_SIGNOFF', 'path': str(path)}
    (out_dir / 'preregister_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def execute_shard(out_dir, shard_index, shard_count, node_budget, limit=None):
    """Resumable: only NOT_EXECUTED rows in this shard are attempted."""
    path = out_dir / 'preregistered_tasks.csv'
    rows = list(csv.DictReader(path.open()))
    shard_rows = [r for i, r in enumerate(rows) if i % shard_count == shard_index]
    pending = [r for r in shard_rows if r['result_status'] == 'NOT_EXECUTED']
    if limit:
        pending = pending[:limit]
    log_dir = out_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    done = 0
    for row in pending:
        candidate = next(r for r in csv.DictReader(UNIVERSE.open(newline=''))
                         if r['candidate_id'] == row['candidate_id'])
        params = {'n_machines': int(candidate['machine_counts']), 'n_parts': int(candidate['part_type_counts']),
                  'ops_per_part': int(candidate['operations_per_part']), 'wip_bound': int(candidate['wip_bounds']),
                  'unobservable_ratio': float(candidate['unobservable_ratios']),
                  'fault_locations': int(candidate['fault_locations']),
                  'interval_width_factor': float(candidate['interval_width_factors']),
                  'adjustable_ratio': float(candidate['adjustable_ratios']), 'seed': int(candidate['seed']),
                  'machine_capacity': 1, 'n_configs': 2, 'repair_domain': 'standard'}
        log = {'task_id': row['task_id'], 'started': time.time()}
        try:
            net, L, H = generate_rmt_fms(**params)
            model = from_generator_net(net, L, H)
            applicability = check_applicability(model)
            if not applicability['supported']:
                row.update(result_status='UNSUPPORTED', failure_reason=json.dumps(applicability['reasons']),
                           exit_code=0, updated_at=str(time.time()))
            else:
                result = run_path(model, row['method_id'], node_budget)
                stats, resources = result['path_stats'], result['resources']
                row.update(result_status=result['status'], v_L=result.get('verdict'),
                           witness_path=json.dumps(result.get('trace'))[:2000],
                           completeness_certificate=json.dumps(result.get('certificate'), sort_keys=True),
                           symbolic_state_count=stats.get('state_classes'),
                           synchronized_pair_count=stats.get('sync_pairs'),
                           LP_count=stats.get('lp_calls'),
                           elapsed_wall=resources.get('wall_seconds'),
                           cpu_seconds=resources.get('cpu_seconds'),
                           peak_python_alloc_bytes=resources.get('peak_memory_bytes'),
                           exit_code=0, updated_at=str(time.time()))
            log['result_status'] = row['result_status']
        except Exception as exc:  # real failure: keep row NOT_EXECUTED? no — mark FAILED, keep log
            row.update(result_status='FAILED', failure_reason=f'{type(exc).__name__}: {exc}',
                       exit_code=1, updated_at=str(time.time()))
            log.update(result_status='FAILED', error=str(exc))
        row['attempts'] = int(row['attempts']) + 1
        (log_dir / f"{_sha(row['task_id'])[:16]}.json").write_text(json.dumps(log, indent=2) + '\n')
        done += 1
        if done % 100 == 0:
            _write_back(path, rows)
            print(f'shard {shard_index}: {done}/{len(pending)}', flush=True)
    _write_back(path, rows)
    summary = {'shard': shard_index, 'attempted': done, 'remaining_not_executed':
               sum(1 for r in rows if r['result_status'] == 'NOT_EXECUTED')}
    print(json.dumps(summary, indent=2))


def _write_back(path, rows):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preregister', 'execute'])
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=1)
    parser.add_argument('--node-budget', type=int, default=200000)
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()
    if args.mode == 'preregister':
        preregister(args.out)
    else:
        execute_shard(args.out, args.shard_index, args.shard_count, args.node_budget, args.limit)
