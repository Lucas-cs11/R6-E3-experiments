"""Independent full-source ledger reconstruction and split-leak cross-check."""
import csv
from collections import Counter
import hashlib
import os
from pathlib import Path


def _read(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _verification(root, rows):
    if not root:
        return dict(status='RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE', verified=0, mismatches=None)
    root = Path(root)
    if not root.is_dir():
        return dict(status='RAW_REPLAY_MISMATCH', verified=0, mismatches=len(rows),
                    examples=['RAW_JSON_ROOT_NOT_FOUND'])
    files = list(root.rglob('*.json'))
    by_name = {}
    for path in files:
        if path.name in by_name:
            return dict(status='RAW_REPLAY_MISMATCH', verified=0, mismatches=len(rows),
                        examples=[f'DUPLICATE_BASENAME:{path.name}'])
        by_name[path.name] = path
    verified = 0
    mismatches = 0
    examples = []
    for row in reversed(rows):
        path = by_name.get(row['file_name'])
        if path is None:
            mismatches += 1
            if len(examples) < 3:
                examples.append(f"MISSING:{row['file_name']}")
            continue
        verified += 1
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != row['file_sha256']:
            mismatches += 1
            if len(examples) < 3:
                examples.append(f"SHA_MISMATCH:{row['file_name']}")
    return dict(status='RAW_REPLAY_MISMATCH' if mismatches else 'AGENT_LOCAL_REPLAYED',
                verified=verified, mismatches=mismatches, examples=examples)


def reference_ledger(manifest_path, split_plan_path, labels_path, raw_json_root=None):
    """Rebuild records in reverse order and independently aggregate leakage."""
    if raw_json_root is None:
        raw_json_root = os.environ.get('PYSCREW_RAW_JSON_ROOT', '')
    manifest = _read(manifest_path)
    split_rows = {row['run_id']: row for row in _read(split_plan_path)}
    label_rows = {row['run_id']: row for row in _read(labels_path)}
    records = []
    for raw in reversed(manifest):
        run_id = raw['run_id']
        split = split_rows[run_id]
        label = label_rows[run_id]
        reasons = []
        if raw['workpiece_result'] == 'NOK' or raw['raw_result'] == 'NOK':
            reasons.append('RAW_RESULT_NOK')
        if split['split'] != raw['split']:
            reasons.append('SPLIT_MISMATCH')
        if split['completed'] != 'True':
            reasons.append('NOT_COMPLETED')
        if label['class_value'] != raw['physical_class']:
            reasons.append('LABEL_CLASS_MISMATCH')
        if label['workpiece_location'] != raw['location']:
            reasons.append('LABEL_SIDE_MISMATCH')
        records.append(dict(
            raw_record_id=run_id, physical_workpiece_id=raw['workpiece_id'],
            side=raw['location'], **{'class': raw['physical_class']},
            source_sha=raw['file_sha256'], split=split['split'],
            raw_status='EXCLUDED_RAW_NOK' if 'RAW_RESULT_NOK' in reasons else 'SOURCE_RECORDED',
            feature_status='NOT_EXTRACTED_STAGE2',
            completion_status='COMPLETED' if split['completed'] == 'True' else 'NOT_COMPLETED',
            reason_for_exclusion=';'.join(reasons), label=label['workpiece_result']))
    records.sort(key=lambda row: row['raw_record_id'])
    splits = {}
    for row in records:
        splits.setdefault(row['physical_workpiece_id'], set()).add(row['split'])
    leaks = []
    for workpiece, values in sorted(splits.items()):
        if len(values) > 1:
            ids = [row['raw_record_id'] for row in records
                   if row['physical_workpiece_id'] == workpiece]
            leaks.append(dict(workpiece_id=workpiece, splits=sorted(values), raw_record_ids=ids))
    counts = Counter(row['label'] for row in records)
    summary = dict(
        records=len(records), workpieces=len(splits),
        classes=len({row['class'] for row in records}),
        source_groups=len({row['source_group'] for row in manifest}),
        result_counts=dict(counts), excluded_nok=counts['NOK'],
        split_counts=dict(Counter(row['split'] for row in records)))
    verification = _verification(raw_json_root, manifest)
    status = 'LEAKAGE_DETECTED' if leaks else 'LEDGER_COMPLETE'
    if verification['status'] == 'RAW_REPLAY_MISMATCH':
        status = verification['status']
    return dict(status=status, records=records, summary=summary, leaks=leaks,
                reason='WORKPIECE_SPLIT_LEAK:' + leaks[0]['workpiece_id'] if leaks else '',
                raw_verification=verification,
                scope='SOURCE_LEDGER_AND_SPLIT_AUDIT_ONLY')
