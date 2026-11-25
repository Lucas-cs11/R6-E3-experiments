"""Independent R6-12/13 reconstruction; no subject-module imports."""
import csv
import json
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
