"""Independent R6-12/13 reconstruction; no subject-module imports."""
import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path


def reference_r612(freeze_path, adapter_path, ledger_path):
    """Traverse in reverse, then sort by historical task id and aggregate."""
    with Path(adapter_path).open(newline='', encoding='utf-8') as handle:
        adapter = {row['case_id']: row for row in csv.DictReader(handle)}
    tasks = json.loads(Path(freeze_path).read_text())['tasks']
    rows = []
    for task in reversed(tasks):
        if task['family'] not in ('micro', 'rmt_original_subset'):
            continue
        micro = task['family'] == 'micro'
        evidence = adapter[task['case_id']]
        rows.append(dict(
            case_id=task['case_id'], family=task['family'], method=task['method'],
            historical_task_id=str(task['id']),
            model_source=task['path'] if micro else 'freeze.json:params',
            model_identity='UNAVAILABLE_ORIGINAL_BYTES' if micro else 'RECONSTRUCTED_VIA_GENERATOR',
            params='' if micro else json.dumps(task['params'], sort_keys=True),
            adapter_status=evidence['status'], adapter_sha256=evidence['model_sha256'],
            e3_04_engine_result='NOT_EXECUTED',
            note=('E3-04 engine pending; original bytes absent' if micro else
                  'adapter validated vs historical structure')))
    rows.sort(key=lambda row: int(row['historical_task_id']))
    with Path(ledger_path).open(newline='', encoding='utf-8') as handle:
        expected = list(csv.DictReader(handle))
    mismatches = sum(actual != other for actual, other in zip(rows, expected)) + abs(len(rows) - len(expected))
    identities = Counter(row['model_identity'] for row in rows)
    engine = Counter(row['e3_04_engine_result'] for row in rows)
    micro_cases = {row['case_id'] for row in rows if row['family'] == 'micro'}
    generated_cases = {row['case_id'] for row in rows if row['family'] == 'rmt_original_subset'}
    summary = {
        'cases': len(micro_cases | generated_cases), 'rows': len(rows),
        'micro_cases': len(micro_cases), 'generated_cases': len(generated_cases),
        'micro_rows': sum(row['family'] == 'micro' for row in rows),
        'generated_rows': sum(row['family'] == 'rmt_original_subset' for row in rows),
        'unavailable_original_bytes': identities['UNAVAILABLE_ORIGINAL_BYTES'],
        'reconstructed_via_generator': identities['RECONSTRUCTED_VIA_GENERATOR'],
        'engine_not_executed': engine['NOT_EXECUTED'],
    }
    return dict(status='LEDGER_EXACT_MATCH' if mismatches == 0 else 'LEDGER_MISMATCH',
                certified=False, mismatches=mismatches, summary=summary,
                rows=rows, proof_trace=rows)


def _read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _raw_reference(rows, root):
    if not root:
        return dict(status='SKIPPED_NO_RAW_DATA', verified=0, mismatches=None,
                    reason='RAW_JSON_ROOT_NOT_PROVIDED')
    root = Path(root)
    if not root.is_dir():
        return dict(status='INVALID_EVIDENCE', verified=0, mismatches=len(rows),
                    reason='RAW_JSON_ROOT_NOT_FOUND')
    files = list(root.rglob('*.json'))
    names = [path.name for path in files]
    if len(names) != len(set(names)):
        return dict(status='INVALID_EVIDENCE', verified=0, mismatches=len(rows),
                    reason='DUPLICATE_RAW_BASENAME')
    by_name = {path.name: path for path in files}
    verified = 0
    mismatches = 0
    for row in reversed(rows):
        path = by_name.get(row['file_name'])
        if path is None:
            mismatches += 1
            continue
        verified += 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['file_sha256']:
            mismatches += 1
    return dict(status='INVALID_EVIDENCE' if mismatches else 'SHA_ZERO_MISMATCH',
                verified=verified, mismatches=mismatches)


def reference_r613(manifest_path, predictions_path, history_path, raw_json_root=None):
    """Independent reverse-order aggregation and raw SHA verification."""
    if raw_json_root is None:
        raw_json_root = os.environ.get('PYSCREW_RAW_JSON_ROOT')
    rows = _read_csv(manifest_path)
    pairs = {}
    for row in rows:
        pairs.setdefault(row['workpiece_id'], set()).add(row['location'])
    pair_failures = sum(locations != {'left', 'right'} for locations in pairs.values())
    class_counts = Counter(row['physical_class'] for row in rows)
    manifest = dict(
        rows=len(rows), workpieces=len(pairs), paired_workpieces=len(pairs)-pair_failures,
        pair_failures=pair_failures,
        left_workpieces=sum(row['location'] == 'left' for row in rows),
        right_workpieces=sum(row['location'] == 'right' for row in rows),
        classes=len(class_counts), classes_x200=sum(value == 200 for value in class_counts.values()),
        source_groups=len({row['source_group'] for row in rows}),
        result_counts=dict(Counter(row['workpiece_result'] for row in rows)),
        sha_declared=sum(bool(row['file_sha256']) for row in rows))
    predictions = _read_csv(predictions_path)
    main_count = sum(row['variant'] == 'main' and row['NI'] == 'False' for row in predictions)
    history_source = json.loads(Path(history_path).read_text())
    raw = _raw_reference(rows, raw_json_root)
    return dict(status='INVALID_EVIDENCE' if raw['status'] == 'INVALID_EVIDENCE' else 'FACT_AUDIT_COMPLETE',
                certified=False, manifest=manifest, raw_sha_audit=raw,
                history=dict(status=history_source['status'], main_non_NI=main_count,
                             historical_intersection_1413_source=history_source['historical_intersection_1413_source'],
                             difference_ids_unresolvable=history_source['difference_ids_unresolvable']),
                manifest_sha256=hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
                prediction_sha256=hashlib.sha256(Path(predictions_path).read_bytes()).hexdigest(),
                proof_trace=[dict(manifest_rows=len(rows), main_non_NI=main_count,
                                  raw_status=raw['status'])])
