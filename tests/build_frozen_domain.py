"""Build signed seed=0 domain artifacts and later the 160-row TINA reconciliation."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'oracles/independent'))
from tina_raw_replay import classify_raw_record_detailed, replay

OUT = ROOT / 'contracts'
UNIVERSE = ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
SATURATION = ROOT / 'runs/domain_audit/fault_saturation_3840.csv'
APPENDIX = ROOT / 'reports/rulings/01_研究域_E3-05_主理论裁定附录.md'
TRACE = ROOT / 'reports/rulings/decision_trace.csv'


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

- `reports/rulings/01_研究域_E3-05_主理论裁定附录.md`, SHA-256 `{appendix_sha}`.
- `reports/rulings/decision_trace.csv`, SHA-256 `{trace_sha}`.
- `contracts/frozen_full_domain.json`, SHA-256 `{_sha(OUT / 'frozen_full_domain.json')}`.
- `contracts/domain_index.csv`, SHA-256 `{result['domain_index_sha256']}`.

This is a mathematical scope decision, not evidence that the 430,080 runs have
completed.  B is an auxiliary sensitivity view and does not replace A.
"""
    (OUT / 'domain_signed_decision.md').write_text(decision)
    return result


def _bounded_excerpt(stdout):
    lines = stdout.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == 'bounded' and any('REACHABILITY ANALYSIS' in previous
                                           for previous in lines[max(0, index - 6):index]):
            header = next(previous for previous in reversed(lines[max(0, index - 6):index])
                          if 'REACHABILITY ANALYSIS' in previous)
            return header.rstrip() + '\n' + line
    raise ValueError('bounded verdict line not found in reachability section')


def build_tina_reconciliation():
    scope = json.loads((ROOT / 'baseline_readonly/e2/scope/tina_retry_45127189704.json').read_text())
    with (ROOT / 'baseline_readonly/e2/runs/tina_cloud_45192651608/merged_candidate_verdicts.csv').open(newline='') as handle:
        strict = {row['candidate_id']: row for row in csv.DictReader(handle)}
    rows = []
    for retry_batch, group in enumerate(scope['batches'], 1):
        shard = ROOT / f'baseline_readonly/e2/runs/tina_cloud_45192651608/download/tina-retry-batch-{retry_batch}/tina_batch_{retry_batch}.jsonl.gz'
        with gzip.open(shard, 'rt', encoding='utf-8') as handle:
            for line_number, line in enumerate(handle, 1):
                raw = json.loads(line)
                verdict, annotations = classify_raw_record_detailed(raw)
                if raw['status'] != 'TIMEOUT' or verdict != 'BOUNDED':
                    continue
                if 'DECLARED_TIMEOUT_AFTER_REACHABILITY_VERDICT' not in annotations:
                    raise ValueError(f'missing recoverable annotation for {raw["candidate_id"]}')
                candidate = raw['candidate_id']
                rows.append(dict(
                    candidate_id=candidate,
                    query_scope='UNTIMED_P_T_REACHABILITY_ONLY',
                    declared_status=raw['status'],
                    strict_ledger_status=strict[candidate]['status'],
                    raw_verdict=verdict,
                    reconciled_status='BOUNDEDNESS_PROVED',
                    stdout_excerpt=_bounded_excerpt(raw['stdout']),
                    query_stage=('LIVENESS_PHASE_TIMEOUT' if 'LIVENESS ANALYSIS' in raw['stdout']
                                 else 'POST_REACHABILITY_TRUNCATED'),
                    run_id=45192651608,
                    retry_batch=retry_batch,
                    source_batch=group['source_batch'],
                    source_shard=str(shard.relative_to(ROOT)),
                    line_number=line_number,
                    raw_returncode='' if raw['returncode'] is None else raw['returncode'],
                    pnml_sha256=raw['pnml_sha256'],
                    stdout_sha256=hashlib.sha256(raw['stdout'].encode()).hexdigest(),
                    stderr_excerpt=raw['stderr'][:160],
                    parse_basis='DECLARED_TIMEOUT_AFTER_REACHABILITY_VERDICT; reachability answered boundedness before later-phase timeout',
                ))
    if len(rows) != 160:
        raise AssertionError(f'expected 160 recoverable rows, got {len(rows)}')
    rows.sort(key=lambda row: row['candidate_id'])
    path = ROOT / 'runs/domain_audit/tina_160_query_level_reconciliation.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    path.write_text(path.read_text().replace('\r\n', '\n'))
    verification = replay(ROOT / 'baseline_readonly/e2')
    assert verification['final']['recoverable_timeout_with_verdict'] == len(rows)
    assert verification['final']['raw_verdict_status_counts'] == {'BOUNDED': 104212, 'TIMEOUT': 3308}
    return dict(rows=len(rows), output=str(path.relative_to(ROOT)),
                declared_status_counts={'TIMEOUT': len(rows)},
                reconciled_status_counts={'BOUNDEDNESS_PROVED': len(rows)})


if __name__ == '__main__':
    print(json.dumps(build_domain(), indent=2, sort_keys=True))
    print(json.dumps(build_tina_reconciliation(), indent=2, sort_keys=True))
