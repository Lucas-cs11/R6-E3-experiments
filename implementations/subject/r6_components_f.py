"""R6-12/13 auditable traceability and source-data components."""
import csv
import hashlib
import json
import os
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
    'COUNT_1421_INFLATED': dict(
        component_id='R6-13', old='count main rows with NI=False',
        new='inflate the reproduced count from 1421 to 1422'),
    'MISSING_SHA_IGNORED': dict(
        component_id='R6-13', old='no raw_json root implies SKIPPED_NO_RAW_DATA',
        new='claim 5000 SHA verifications and zero mismatch without raw files'),
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


def _manifest_rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _manifest_facts(rows):
    by_workpiece = {}
    for row in rows:
        by_workpiece.setdefault(row['workpiece_id'], []).append(row)
    pair_failures = sum(len(group) != 2 or {row['location'] for row in group} != {'left', 'right'}
                        for group in by_workpiece.values())
    classes = Counter(row['physical_class'] for row in rows)
    return dict(
        rows=len(rows), workpieces=len(by_workpiece), paired_workpieces=len(by_workpiece)-pair_failures,
        pair_failures=pair_failures,
        left_workpieces=sum(row['location'] == 'left' for row in rows),
        right_workpieces=sum(row['location'] == 'right' for row in rows),
        classes=len(classes), classes_x200=sum(count == 200 for count in classes.values()),
        source_groups=len({row['source_group'] for row in rows}),
        result_counts=dict(Counter(row['workpiece_result'] for row in rows)),
        sha_declared=sum(bool(row['file_sha256']) for row in rows),
    )


def _raw_sha_audit(rows, raw_json_root, mutation):
    if not raw_json_root:
        if mutation == 'MISSING_SHA_IGNORED':
            return dict(status='SHA_ZERO_MISMATCH', verified=len(rows), mismatches=0,
                        fabricated=True)
        return dict(status='SKIPPED_NO_RAW_DATA', verified=0, mismatches=None,
                    reason='RAW_JSON_ROOT_NOT_PROVIDED')
    root = Path(raw_json_root)
    if not root.is_dir():
        return dict(status='INVALID_EVIDENCE', verified=0, mismatches=len(rows),
                    reason='RAW_JSON_ROOT_NOT_FOUND')
    files = {}
    for path in root.rglob('*.json'):
        if path.name in files:
            return dict(status='INVALID_EVIDENCE', verified=0, mismatches=len(rows),
                        reason='DUPLICATE_RAW_BASENAME')
        files[path.name] = path
    mismatches = 0
    verified = 0
    for row in rows:
        path = files.get(row['file_name'])
        if path is None:
            mismatches += 1
            continue
        verified += 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['file_sha256']:
            mismatches += 1
    return dict(status='INVALID_EVIDENCE' if mismatches else 'SHA_ZERO_MISMATCH',
                verified=verified, mismatches=mismatches)


def run_r613(manifest_path, predictions_path, history_path, raw_json_root=None, mutation=None):
    if mutation not in (None, 'COUNT_1421_INFLATED', 'MISSING_SHA_IGNORED'):
        raise ValueError('unknown R6-13 mutation')
    if raw_json_root is None:
        raw_json_root = os.environ.get('PYSCREW_RAW_JSON_ROOT')
    rows = _manifest_rows(manifest_path)
    predictions = _manifest_rows(predictions_path)
    history_source = json.loads(Path(history_path).read_text())
    main_count = sum(row['variant'] == 'main' and row['NI'] == 'False' for row in predictions)
    if mutation == 'COUNT_1421_INFLATED':
        main_count += 1
    raw_audit = _raw_sha_audit(rows, raw_json_root, mutation)
    history = dict(status=history_source['status'], main_non_NI=main_count,
                   historical_intersection_1413_source=history_source['historical_intersection_1413_source'],
                   difference_ids_unresolvable=history_source['difference_ids_unresolvable'])
    return dict(status='INVALID_EVIDENCE' if raw_audit['status'] == 'INVALID_EVIDENCE' else 'FACT_AUDIT_COMPLETE',
                certified=False, manifest=_manifest_facts(rows), raw_sha_audit=raw_audit,
                history=history,
                manifest_sha256=hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
                prediction_sha256=hashlib.sha256(Path(predictions_path).read_bytes()).hexdigest(),
                proof_trace=[dict(manifest_rows=len(rows), main_non_NI=main_count,
                                  raw_status=raw_audit['status'])])


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
