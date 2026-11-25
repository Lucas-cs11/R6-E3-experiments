"""E3-10 stage-1 per-record source ledger and split-leak audit."""
from collections import Counter
import hashlib
import os
from pathlib import Path


def _rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


import csv


def _by_id(rows):
    result = {}
    for row in rows:
        if row['run_id'] in result:
            raise ValueError(f"duplicate run_id {row['run_id']}")
        result[row['run_id']] = row
    return result


def _raw_verification(root, rows):
    if not root:
        return dict(status='RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE', verified=0, mismatches=None)
    # Implemented in the second logical block; current fixtures must not claim replay.
    return dict(status='RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE', verified=0, mismatches=None)


def build_ledger(manifest_path, split_plan_path, labels_path, raw_json_root=None):
    """Join all raw identities, preserve exclusions and audit workpiece splits."""
    if raw_json_root is None:
        raw_json_root = os.environ.get('PYSCREW_RAW_JSON_ROOT', '')
    manifest = _rows(manifest_path)
    split_plan = _by_id(_rows(split_plan_path))
    labels = _by_id(_rows(labels_path))
    if not (len(manifest) == len(split_plan) == len(labels)):
        raise ValueError('manifest/split_plan/labels row counts differ')
    records = []
    for raw in sorted(manifest, key=lambda row: row['run_id']):
        run_id = raw['run_id']
        split = split_plan[run_id]
        label = labels[run_id]
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
            raw_record_id=run_id,
            physical_workpiece_id=raw['workpiece_id'],
            side=raw['location'],
            **{'class': raw['physical_class']},
            source_sha=raw['file_sha256'],
            split=split['split'],
            raw_status='EXCLUDED_RAW_NOK' if 'RAW_RESULT_NOK' in reasons else 'SOURCE_RECORDED',
            feature_status='NOT_EXTRACTED_STAGE2',
            completion_status='COMPLETED' if split['completed'] == 'True' else 'NOT_COMPLETED',
            reason_for_exclusion=';'.join(reasons),
            label=label['workpiece_result'],
        ))

    by_workpiece = {}
    for record in records:
        by_workpiece.setdefault(record['physical_workpiece_id'], []).append(record)
    leaks = []
    for workpiece, group in sorted(by_workpiece.items()):
        splits = sorted({record['split'] for record in group})
        if len(splits) > 1:
            leaks.append(dict(workpiece_id=workpiece, splits=splits,
                              raw_record_ids=[record['raw_record_id'] for record in group]))
    result_counts = dict(Counter(record['label'] for record in records))
    summary = dict(
        records=len(records), workpieces=len(by_workpiece),
        classes=len({record['class'] for record in records}),
        source_groups=len({row['source_group'] for row in manifest}),
        result_counts=result_counts,
        excluded_nok=result_counts.get('NOK', 0),
        split_counts=dict(Counter(record['split'] for record in records)),
    )
    verification = _raw_verification(raw_json_root, manifest)
    status = 'LEAKAGE_DETECTED' if leaks else 'LEDGER_COMPLETE'
    if verification['status'] == 'RAW_REPLAY_MISMATCH':
        status = verification['status']
    return dict(status=status, records=records, summary=summary, leaks=leaks,
                reason='WORKPIECE_SPLIT_LEAK:' + leaks[0]['workpiece_id'] if leaks else '',
                raw_verification=verification,
                scope='SOURCE_LEDGER_AND_SPLIT_AUDIT_ONLY')
