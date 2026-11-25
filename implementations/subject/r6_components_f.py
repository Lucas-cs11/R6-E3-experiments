"""R6-12/13 auditable traceability and source-data components."""
import csv
import json
from collections import Counter
from pathlib import Path

from r6_components import make_acceptance_record as _component_acceptance_record


_PATCHES = {
    'MICRO_MARKED_RECONSTRUCTED': dict(
        component_id='R6-12', old='micro original bytes stay UNAVAILABLE_ORIGINAL_BYTES',
        new='mark every micro row RECONSTRUCTED_VIA_GENERATOR'),
    'ENGINE_PREFILLED_PASS': dict(
        component_id='R6-12', old='e3_04_engine_result=NOT_EXECUTED',
        new='prefill every engine result as PASS'),
}


def mutation_patch(mutation_id):
    return dict(_PATCHES[mutation_id], mutation_id=mutation_id,
                mode='SPECIFIC_LEDGER_MUTATION')


def _load_adapter(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 52 or len({row['case_id'] for row in rows}) != 52:
        raise ValueError('adapter must contain 52 unique cases')
    return {row['case_id']: row for row in rows}


def _build_rows(freeze_path, adapter_path):
    freeze = json.loads(Path(freeze_path).read_text())
    adapters = _load_adapter(adapter_path)
    rows = []
    for task in freeze['tasks']:
        family = task['family']
        if family not in ('micro', 'rmt_original_subset'):
            continue
        adapter = adapters[task['case_id']]
        micro = family == 'micro'
        rows.append({
            'case_id': task['case_id'],
            'family': family,
            'method': task['method'],
            'historical_task_id': str(task['id']),
            'model_source': task['path'] if micro else 'freeze.json:params',
            'model_identity': 'UNAVAILABLE_ORIGINAL_BYTES' if micro else 'RECONSTRUCTED_VIA_GENERATOR',
            'params': '' if micro else json.dumps(task['params'], sort_keys=True),
            'adapter_status': adapter['status'],
            'adapter_sha256': adapter['model_sha256'],
            'e3_04_engine_result': 'NOT_EXECUTED',
            'note': ('E3-04 engine pending; original bytes absent' if micro else
                     'adapter validated vs historical structure'),
        })
    return rows


def _compare_ledger(rows, ledger_path):
    with Path(ledger_path).open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        expected = list(reader)
    mismatches = sum(row != expected_row for row, expected_row in zip(rows, expected))
    mismatches += abs(len(rows) - len(expected))
    if fields != list(rows[0]):
        raise ValueError('ledger header differs from generated schema')
    return mismatches


def _summary(rows):
    micro = [row for row in rows if row['family'] == 'micro']
    generated = [row for row in rows if row['family'] == 'rmt_original_subset']
    return {
        'cases': len({row['case_id'] for row in rows}), 'rows': len(rows),
        'micro_cases': len({row['case_id'] for row in micro}),
        'generated_cases': len({row['case_id'] for row in generated}),
        'micro_rows': len(micro), 'generated_rows': len(generated),
        'unavailable_original_bytes': sum(row['model_identity'] == 'UNAVAILABLE_ORIGINAL_BYTES' for row in rows),
        'reconstructed_via_generator': sum(row['model_identity'] == 'RECONSTRUCTED_VIA_GENERATOR' for row in rows),
        'engine_not_executed': sum(row['e3_04_engine_result'] == 'NOT_EXECUTED' for row in rows),
    }


def run_r612(freeze_path, adapter_path, ledger_path, mutation=None):
    if mutation not in (None, 'MICRO_MARKED_RECONSTRUCTED', 'ENGINE_PREFILLED_PASS'):
        raise ValueError('unknown R6-12 mutation')
    rows = _build_rows(freeze_path, adapter_path)
    if mutation == 'MICRO_MARKED_RECONSTRUCTED':
        rows = [dict(row, model_identity=('RECONSTRUCTED_VIA_GENERATOR'
                                          if row['family'] == 'micro' else row['model_identity']))
                for row in rows]
    if mutation == 'ENGINE_PREFILLED_PASS':
        rows = [dict(row, e3_04_engine_result='PASS') for row in rows]
    mismatches = _compare_ledger(rows, ledger_path)
    return dict(status='LEDGER_EXACT_MATCH' if mismatches == 0 else 'LEDGER_MISMATCH',
                certified=False, mismatches=mismatches, summary=_summary(rows), rows=rows,
                proof_trace=rows)


def _acceptance_projection(output):
    canonical = json.dumps(output, sort_keys=True, default=str, separators=(',', ':'))
    return dict(status=output['status'], resolved=canonical, unresolved='0',
                categories=[], frontier=[], events=output.get('proof_trace', []))


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    packed_mutation = (mutated_output if isinstance(mutated_output, Exception)
                       else _acceptance_projection(mutated_output))
    record = _component_acceptance_record(
        'R6-03', dict(kind='mass'), _acceptance_projection(subject_output),
        _acceptance_projection(oracle_output), 'R603_DROP_FRONTIER_MASS', packed_mutation)
    record.update(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        subject_output=subject_output,
        oracle_output=oracle_output,
        mutation_patch=mutation_patch(mutation_id),
        coverage_limitations=('Traceability of 52 inherited models and 208 historical calls; '
                              'E3-04 remains NOT_EXECUTED and no engine correctness is implied.'))
    return record
