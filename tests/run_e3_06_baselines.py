"""E3-06 baseline comparison: TINA projection tier (SHARED_PROJECTION_ONLY)."""
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/e3_06'
AXES = ('machine_counts', 'part_type_counts', 'operations_per_part', 'wip_bounds',
        'unobservable_ratios', 'fault_locations', 'interval_width_factors', 'adjustable_ratios')


def sample_configs(n, seed):
    rows = [r for r in csv.DictReader((ROOT / 'contracts/domain_index.csv').open(newline=''))
            if r['static_validity'] == 'VALID_BY_FROZEN_RULE']
    rng = random.Random(seed)
    ordered = sorted(rows, key=lambda r: r['candidate_id'])
    rng.shuffle(ordered)
    picked = ordered[:n]
    coverage = {a: {} for a in AXES}
    for r in picked:
        for a in AXES:
            coverage[a][r[a]] = coverage[a].get(r[a], 0) + 1
    return picked, coverage


def load_legacy():
    """Per-config TINA verdicts from the RAW parse (9,138 rows).

    NOTE: tina_all_merged.csv is the RETRACTED artifact (all rows marked
    unbounded); it must never be used as comparison data.  Aggregate corrected
    counts (104,212 bounded / 3,308 undetermined) come from the independent
    raw replay summary and are reported as context only.
    """
    path = ROOT / 'baseline_readonly/e2/results/tina_all_107520.csv'
    rows = {}
    with path.open(newline='') as handle:
        for r in csv.DictReader(handle):
            rows[r['candidate_id']] = r
    return rows


def load_replay_aggregate():
    path = ROOT / 'runs/math_p0/tina_raw_replay/replay.stdout.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return data.get('final', {})


def load_engine_rows(shard_dir):
    """Collect MAIN-method rows already executed in the release shards (if present)."""
    executed = {}
    for f in sorted(Path(shard_dir).glob('shard_*.csv')):
        with f.open(newline='') as handle:
            for r in csv.DictReader(handle):
                if r['method_id'] != 'MAIN':
                    continue
                if r['result_status'] in ('NOT_EXECUTED',):
                    continue
                executed[r['candidate_id']] = r
    return executed


def main(n=200, seed=20261128, shard_dir=None, out_dir=None):
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    picked, coverage = sample_configs(n, seed)
    legacy = load_legacy()
    engine = load_engine_rows(shard_dir) if shard_dir else {}
    rows = []
    for r in picked:
        cid = r['candidate_id']
        old = legacy.get(cid)
        eng = engine.get(cid)
        if old is None:
            rows.append({'candidate_id': cid, 'tina_status': 'NOT_IN_LEGACY_LEDGER',
                         'tina_bounded': '', 'engine_status': (eng or {}).get('result_status', 'NOT_YET'),
                         'engine_verdict': (eng or {}).get('v_L', ''),
                         'comparison': 'MISSING'})
            continue
        bounded = old['tina_bounded']
        if eng is None:
            rows.append({'candidate_id': cid, 'tina_status': 'BOUNDED' if bounded == 'True' else 'TIMEOUT',
                         'tina_bounded': bounded, 'engine_status': 'NOT_YET',
                         'engine_verdict': '', 'comparison': 'ENGINE_PENDING'})
            continue
        rows.append({'candidate_id': cid, 'tina_status': 'BOUNDED' if bounded == 'True' else 'TIMEOUT',
                     'tina_bounded': bounded, 'engine_status': eng['result_status'],
                     'engine_verdict': eng.get('v_L', ''),
                     'comparison': 'BOTH_PRESENT'})
    with (out_dir / 'b2_tina_comparison.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {'sample': len(rows), 'in_legacy': sum(r['tina_status'] != 'NOT_IN_LEGACY_LEDGER' for r in rows),
               'legacy_source': 'tina_all_107520.csv (raw parse; merged file retracted and excluded)',
               'replay_aggregate': load_replay_aggregate(),
               'tina_bounded': sum(r['tina_status'] == 'BOUNDED' for r in rows),
               'tina_timeout': sum(r['tina_status'] == 'TIMEOUT' for r in rows),
               'engine_executed': sum(r['comparison'] == 'BOTH_PRESENT' for r in rows),
               'missing': sum(r['comparison'] == 'MISSING' for r in rows),
               'coverage': coverage, 'tier': 'SHARED_PROJECTION_ONLY'}
    (out_dir / 'b2_tina_comparison_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=200)
    parser.add_argument('--seed', type=int, default=20261128)
    parser.add_argument('--shard-dir', default=None)
    args = parser.parse_args()
    main(args.sample, args.seed, args.shard_dir)
