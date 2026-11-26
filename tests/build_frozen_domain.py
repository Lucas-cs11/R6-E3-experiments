"""Build signed seed=0 domain artifacts and later the 160-row TINA reconciliation."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'contracts'
UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
SATURATION = ROOT / 'runs/domain_audit/fault_saturation_3840.csv'
APPENDIX = ROOT / 'reports/01_研究域_E3-05_主理论裁定附录.md'
TRACE = ROOT / 'reports/decision_trace.csv'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def build_domain():
    OUT.mkdir(parents=True, exist_ok=True)
    universe = _rows(UNIVERSE)
    saturation = {row['candidate_id']: row for row in _rows(SATURATION)}
    valid = [row for row in universe if row['static_validity'] == 'VALID_BY_FROZEN_RULE']
    invalid = [row for row in universe if row['static_validity'] != 'VALID_BY_FROZEN_RULE']
    assert len(universe) == 143360 and len(valid) == 107520 and len(invalid) == 35840
    fields = ['candidate_id', 'machine_counts', 'part_type_counts', 'operations_per_part',
              'wip_bounds', 'unobservable_ratios', 'fault_locations', 'interval_width_factors',
              'adjustable_ratios', 'seed', 'fault_locations_requested', 'used_machine_count',
              'actual_distinct_fault_machine_count', 'actual_fault_transition_count',
              'n_configs', 'machine_capacity', 'repair_domain', 'static_validity', 'saturated']
    index_path = OUT / 'domain_index.csv'
    saturated_count = 0
    with index_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in valid:
            candidate = row['candidate_id']
            used = min(int(row['machine_counts']),
                       int(row['part_type_counts']) * int(row['operations_per_part']))
            requested = int(row['fault_locations'])
            is_saturated = requested > used
            saturated_count += is_saturated
            if is_saturated:
                actual = saturation[candidate]
                actual_machines = int(actual['actual_distinct_fault_machine_count'])
                actual_transitions = int(actual['actual_fault_transition_count'])
                assert used == int(actual['used_machine_count'])
            else:
                actual_machines = requested
                actual_transitions = requested * int(row['n_configs'])
            writer.writerow({
                'candidate_id': candidate,
                'machine_counts': row['machine_counts'],
                'part_type_counts': row['part_type_counts'],
                'operations_per_part': row['operations_per_part'],
                'wip_bounds': row['wip_bounds'],
                'unobservable_ratios': row['unobservable_ratios'],
                'fault_locations': row['fault_locations'],
                'interval_width_factors': row['interval_width_factors'],
                'adjustable_ratios': row['adjustable_ratios'],
                'seed': row['seed'],
                'fault_locations_requested': requested,
                'used_machine_count': used,
                'actual_distinct_fault_machine_count': actual_machines,
                'actual_fault_transition_count': actual_transitions,
                'n_configs': row['n_configs'],
                'machine_capacity': row['machine_capacity'],
                'repair_domain': row['repair_domain'],
                'static_validity': row['static_validity'],
                'saturated': int(is_saturated),
            })
    assert saturated_count == 3840
    appendix_sha = _sha(APPENDIX)
    trace_sha = _sha(TRACE)
    result = {
        'status': 'MATH_SIGNED_SCOPE',
        'seed': 0,
        'ruling': 'APPROVED_A_WITH_LIMITATIONS',
        'candidates': len(universe),
        'valid_configs': len(valid),
        'invalid_configs': len(invalid),
        'minimum_task_records': len(valid) * 4,
        'method_count': 4,
        'saturated_configurations': saturated_count,
        'distinct_semantic_net_contents': 85024,
        'fault_locations_semantics': 'requested upper bound saturated at used_machine_count',
        'declared_ledger': {'BOUNDED': 104052, 'TIMEOUT': 3468},
        'query_reconciled': {'boundedness_proved': 104212, 'boundedness_undetermined': 3308},
        'sensitivity_B': {
            'valid_configs': len(valid) - saturated_count,
            'declared_ledger': {'BOUNDED': 100212, 'TIMEOUT': 3468},
            'query_reconciled': {'boundedness_proved': 100372, 'boundedness_undetermined': 3308},
        },
        'provenance_unresolved': ['15 seeds', 'param_slice:3', 'historical 36,450 instances'],
        'ruling_reference': str(APPENDIX.relative_to(ROOT)),
        'ruling_reference_sha256': appendix_sha,
        'decision_trace': str(TRACE.relative_to(ROOT)),
        'decision_trace_sha256': trace_sha,
        'source_universe_sha256': _sha(UNIVERSE),
        'saturation_audit_sha256': _sha(SATURATION),
        'domain_index_sha256': _sha(index_path),
    }
    assert result['minimum_task_records'] == 430080
    (OUT / 'frozen_full_domain.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    decision = f"""# Signed research-domain decision

Ruling: `MATH_SIGNED_SCOPE`, A scheme approved with limitations, seed=0 only.

- Candidates: 143,360; valid 107,520; invalid 35,840.
- Minimum task records: 430,080 = 107,520 × 4 methods.
- `fault_locations` is an upper bound saturated by used machines, not an exact fault count.
- Saturated configurations retained in A: 3,840.
- Canonical semantic network contents: 85,024, hashes are not behavioral equivalence classes.
- Declared ledger A: 104,052 BOUNDED + 3,468 TIMEOUT.
- Query-reconciled A: 104,212 boundedness-proved + 3,308 boundedness-undetermined.
- Auxiliary B: 103,680 configurations; declared 100,212 + 3,468; query-reconciled 100,372 + 3,308.
- Historical 15 seeds / param_slice:3 / 36,450 remain PROVENANCE_UNRESOLVED.

References:

- `reports/01_研究域_E3-05_主理论裁定附录.md`, SHA-256 `{appendix_sha}`.
- `reports/decision_trace.csv`, SHA-256 `{trace_sha}`.
- `contracts/frozen_full_domain.json`, SHA-256 `{_sha(OUT / 'frozen_full_domain.json')}`.
- `contracts/domain_index.csv`, SHA-256 `{result['domain_index_sha256']}`.

This is a mathematical scope decision, not evidence that the 430,080 runs have
completed.  B is an auxiliary sensitivity view and does not replace A.
"""
    (OUT / 'domain_signed_decision.md').write_text(decision)
    return result


if __name__ == '__main__':
    print(json.dumps(build_domain(), indent=2, sort_keys=True))
