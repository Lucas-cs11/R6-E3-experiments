"""Merge the 64 release shard ledgers into the final 430,080-row ledger."""
import csv
import json
from collections import Counter
from pathlib import Path

FIELDS = ['task_id', 'candidate_id', 'spec_id', 'method_id', 'result_status', 'v_L',
          'witness_path', 'completeness_certificate', 'timed_trace', 'symbolic_state_count',
          'synchronized_pair_count', 'LP_count', 'elapsed_wall', 'cpu_seconds',
          'peak_python_alloc_bytes', 'exit_code', 'attempts', 'failure_reason',
          'model_sha256', 'updated_at']


def merge(shard_paths, expected_rows=None):
    rows, seen = [], set()
    fields = None
    for path in sorted(shard_paths):
        with open(path, newline='') as handle:
            reader = csv.DictReader(handle)
            fields = fields or reader.fieldnames
            for row in reader:
                if row['task_id'] in seen:
                    raise ValueError(f'duplicate task_id {row["task_id"]} in {path}')
                seen.add(row['task_id'])
                rows.append(row)
    if expected_rows is not None and len(rows) != expected_rows:
        raise ValueError(f'expected {expected_rows} rows, got {len(rows)}')
    status = Counter(r['result_status'] for r in rows)
    contents = Counter(r.get('model_sha256') or '' for r in rows if r['result_status'] != 'NOT_EXECUTED')
    return {'rows': len(rows), 'task_ids_unique': len(seen),
            'status_counts': dict(status),
            'content_level_counts': {k: v for k, v in contents.items() if k},
            'fields': fields}


def main(shard_dir, out_path=None, expected=430080):
    shard_dir = Path(shard_dir)
    shards = sorted(shard_dir.glob('shard_*.csv'))
    result = merge(shards, expected_rows=expected)
    if out_path:
        rows = []
        for path in shards:
            with open(path, newline='') as handle:
                rows.extend(csv.DictReader(handle))
        with open(out_path, 'w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=result['fields'])
            writer.writeheader()
            writer.writerows(rows)
        result['out_path'] = str(out_path)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import sys
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
