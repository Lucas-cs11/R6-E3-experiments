import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from merge_final_ledger import merge, FIELDS


def write_shard(path, rows):
    padded = [{k: r.get(k, '') for k in FIELDS} for r in rows]
    with open(path, 'w', newline='') as h:
        w = csv.DictWriter(h, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(padded)


class MergeFinalLedgerTests(unittest.TestCase):
    def test_merge_counts_and_uniqueness(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for s in range(2):
                rows = []
                for i in range(3):
                    rows.append({'task_id': f'cand_{s}_{i}|MAIN', 'candidate_id': f'cand_{s}_{i}',
                                 'method_id': 'MAIN', 'result_status': 'NOT_EXECUTED',
                                 'v_L': '', 'model_sha256': '', 'attempts': 0})
                p = Path(tmp) / f'shard_{s}.csv'
                write_shard(p, rows)
                paths.append(p)
            out = merge(paths)
            self.assertEqual(out['rows'], 6)
            self.assertEqual(out['task_ids_unique'], 6)
            self.assertEqual(out['status_counts'], {'NOT_EXECUTED': 6})

    def test_duplicate_task_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = {'task_id': 'x|MAIN', 'candidate_id': 'x', 'method_id': 'MAIN',
                   'result_status': 'NOT_EXECUTED', 'v_L': '', 'model_sha256': '', 'attempts': 0}
            p1 = Path(tmp) / 'a.csv'
            p2 = Path(tmp) / 'b.csv'
            write_shard(p1, [row])
            write_shard(p2, [row])
            with self.assertRaises(ValueError):
                merge([p1, p2])

    def test_content_level_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [{'task_id': 'c1|MAIN', 'candidate_id': 'c1', 'method_id': 'MAIN',
                     'result_status': 'EXHAUSTED_FOR_MODEL', 'v_L': '1', 'model_sha256': 'h1', 'attempts': 1},
                    {'task_id': 'c1|FULL_HISTORY', 'candidate_id': 'c1', 'method_id': 'FULL_HISTORY',
                     'result_status': 'EXHAUSTED_FOR_MODEL', 'v_L': '1', 'model_sha256': 'h1', 'attempts': 1}]
            p = Path(tmp) / 's0.csv'
            write_shard(p, rows)
            out = merge([p])
            self.assertEqual(out['content_level_counts'], {'h1': 2})


if __name__ == '__main__':
    unittest.main()
