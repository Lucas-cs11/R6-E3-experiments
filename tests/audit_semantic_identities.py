"""E3-05 fact audit: three-layer identities for all 107,520 valid configs.

config_sha256      full parameter row + seed + generator identity
semantic_net_sha256 canonical places/initial marking/transitions (label,
                   fault/adjustable flags, intervals, admissible sets,
                   authorized ranges)/arcs — excludes non-semantic metadata
spec_sha256        L, H, repair domain

Identical semantic hashes mean identical canonical content, NOT proven
behavioral equivalence. V0 rows are never modified.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'baseline_readonly/e2/implementations/generator_compat'))
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402

UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
OUT_DIR = ROOT / 'runs/domain_audit'
GENERATOR_FILES = ('src/benchmarks/rmt_fms_generator.py', 'src/model/tpn.py')
AXES = ('machine_counts', 'part_type_counts', 'operations_per_part', 'wip_bounds',
        'unobservable_ratios', 'fault_locations', 'interval_width_factors',
        'adjustable_ratios', 'seed')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon_fraction(value) -> str:
    return f'{value.numerator}/{value.denominator}' if hasattr(value, 'numerator') else str(value)


def semantic_payload(net) -> dict:
    transitions = {}
    for name in sorted(net.transitions):
        t = net.transitions[name]
        transitions[name] = {
            'label': t.label, 'is_fault': t.is_fault, 'is_adjustable': t.is_adjustable,
            'interval': [canon_fraction(t.interval.earliest), canon_fraction(t.interval.latest)],
            'admissible_intervals': [[canon_fraction(i.earliest), canon_fraction(i.latest)]
                                     for i in t.admissible_intervals],
            'authorized_range': None if t.authorized_range is None else {
                'l_min': canon_fraction(t.authorized_range.l_min),
                'l_max': canon_fraction(t.authorized_range.l_max),
                'u_min': canon_fraction(t.authorized_range.u_min),
                'u_max': canon_fraction(t.authorized_range.u_max),
                'resolution': canon_fraction(t.authorized_range.resolution)},
        }
    return {
        'places': sorted(net.places),
        'initial_marking': {k: net.initial_marking[k] for k in sorted(net.initial_marking)},
        'transitions': transitions,
        'arcs': sorted((a.from_node, a.to_node) for a in net.arcs),
        'completion_markings': sorted(tuple(sorted(m.items())) for m in net.completion_markings),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generator_id = sha(b''.join(
        (ROOT / 'baseline_readonly/e2/implementations/generator_compat' / f).read_bytes()
        for f in GENERATOR_FILES))
    rows = [r for r in csv.DictReader(UNIVERSE.open(newline='', encoding='utf-8'))
            if r['static_validity'] == 'VALID_BY_FROZEN_RULE']
    out_path = OUT_DIR / 'semantic_identities_107520.csv'
    semantic_groups = defaultdict(list)
    distinct_config_hashes = set()
    with out_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            'candidate_id', 'config_sha256', 'semantic_net_sha256', 'spec_sha256',
            'places', 'transitions', 'arcs', 'L', 'H'])
        writer.writeheader()
        for index, r in enumerate(rows, 1):
            config = {k: r[k] for k in AXES}
            config.update({'machine_capacity': r['machine_capacity'], 'n_configs': r['n_configs'],
                           'repair_domain': r['repair_domain'], 'generator_sha256': generator_id})
            config_hash = sha(json.dumps(config, sort_keys=True).encode())
            params = {'n_machines': int(r['machine_counts']), 'n_parts': int(r['part_type_counts']),
                      'ops_per_part': int(r['operations_per_part']), 'wip_bound': int(r['wip_bounds']),
                      'unobservable_ratio': float(r['unobservable_ratios']),
                      'fault_locations': int(r['fault_locations']),
                      'interval_width_factor': float(r['interval_width_factors']),
                      'adjustable_ratio': float(r['adjustable_ratios']),
                      'seed': int(r['seed']), 'machine_capacity': 1, 'n_configs': 2,
                      'repair_domain': 'standard'}
            net, L, H = generate_rmt_fms(**params)
            semantic_hash = sha(json.dumps(semantic_payload(net), sort_keys=True).encode())
            spec_hash = sha(json.dumps({'L': canon_fraction(L), 'H': canon_fraction(H),
                                        'repair_domain': r['repair_domain']}, sort_keys=True).encode())
            distinct_config_hashes.add(config_hash)
            writer.writerow({'candidate_id': r['candidate_id'], 'config_sha256': config_hash,
                             'semantic_net_sha256': semantic_hash, 'spec_sha256': spec_hash,
                             'places': len(net.places), 'transitions': len(net.transitions),
                             'arcs': len(net.arcs), 'L': L, 'H': H})
            semantic_groups[semantic_hash].append((r['candidate_id'], config))
            if index % 10752 == 0:
                print(f'progress {index}/{len(rows)}', flush=True)
    group_sizes = Counter({h: len(v) for h, v in semantic_groups.items()})
    axis_no_effect = {}
    for axis in AXES:
        unchanged = 0
        comparable = 0
        by_axis_value = defaultdict(set)
        for h, members in semantic_groups.items():
            for candidate_id, config in members:
                key = tuple((a, config[a]) for a in AXES if a != axis)
                by_axis_value[key].add((config[axis], h))
        for key, values in by_axis_value.items():
            if len(values) < 2:
                continue
            comparable += 1
            hashes = {h for _, h in values}
            if len(hashes) == 1:
                unchanged += 1
        axis_no_effect[axis] = {'axis_value_pairs_sharing_config_context': comparable,
                                'pairs_with_identical_semantic_net': unchanged}
    summary = {
        'status': 'PASS',
        'scope': 'FACT_AUDIT_CANONICAL_CONTENT_NOT_BEHAVIORAL_EQUIVALENCE',
        'valid_configs': len(rows),
        'distinct_semantic_net_sha256': len(semantic_groups),
        'distinct_config_sha256': len(distinct_config_hashes),
        'largest_groups': group_sizes.most_common(10),
        'group_size_histogram': dict(Counter(group_sizes.values())),
        'axis_no_effect': axis_no_effect,
        'generator_sha256': generator_id,
        'csv': str(out_path.relative_to(ROOT)),
    }
    (OUT_DIR / 'semantic_identities_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'largest_groups'}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
