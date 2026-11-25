"""E3-10 stage-1 full-source ledger and workpiece-split leakage tests."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from pyscrew_ledger import build_ledger
from pyscrew_ledger_reference import reference_ledger


class PyScrewLedgerTests(unittest.TestCase):
    def setUp(self):
        self.manifest = ROOT / 'baseline_readonly/e2/scope/pyscrew_raw_manifest.csv'
        self.split = ROOT / 'baseline_readonly/e2/chapter6/split_plan.csv'
        self.labels = ROOT / 'baseline_readonly/e2/chapter6/labels.csv'

    def test_full_ledger_without_raw_root_and_independent_reference(self):
        case = dict(case_id='e3_10_full_source_no_raw', kind='ledger', role='POSITIVE')
        subject = build_ledger(self.manifest, self.split, self.labels, raw_json_root='')
        reference = reference_ledger(self.manifest, self.split, self.labels, raw_json_root='')
        self.assertEqual(subject, reference)
        self.assertEqual(subject['status'], 'LEDGER_COMPLETE')
        self.assertEqual(len(subject['records']), 5000)
        self.assertEqual(subject['summary']['records'], 5000)
        self.assertEqual(subject['summary']['workpieces'], 2500)
        self.assertEqual(subject['summary']['classes'], 25)
        self.assertEqual(subject['summary']['source_groups'], 50)
        self.assertEqual(subject['summary']['result_counts'], {'OK': 4307, 'NOK': 693})
        self.assertEqual(subject['leaks'], [])
        self.assertEqual(subject['raw_verification']['status'], 'RAW_NOT_VERIFIED_ON_AUDITOR_MACHINE')
        self.assertIsNone(subject['raw_verification']['mismatches'])
        self.assertEqual(subject['raw_verification']['verified'], 0)
        nok = [row for row in subject['records'] if row['label'] == 'NOK']
        self.assertEqual(len(nok), 693)
        self.assertTrue(all(row['reason_for_exclusion'] for row in nok))
        self.assertTrue(all(row['feature_status'] == 'NOT_EXTRACTED_STAGE2' for row in subject['records']))
        required = {'raw_record_id', 'physical_workpiece_id', 'side', 'class', 'source_sha', 'split',
                    'raw_status', 'feature_status', 'completion_status', 'reason_for_exclusion', 'label'}
        self.assertEqual(set(subject['records'][0]), required)

    def test_constructed_workpiece_split_leak_is_detected_by_both(self):
        with tempfile.TemporaryDirectory(prefix='e3-10-leak-') as tmp:
            leaked = Path(tmp) / 'split_plan.csv'
            with self.split.open(newline='') as source, leaked.open('w', newline='') as target:
                reader = csv.DictReader(source)
                writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
                writer.writeheader()
                for index, row in enumerate(reader):
                    if index == 0:
                        row['split'] = 'calibration'
                    writer.writerow(row)
            subject = build_ledger(self.manifest, leaked, self.labels, raw_json_root='')
            reference = reference_ledger(self.manifest, leaked, self.labels, raw_json_root='')
            self.assertEqual(subject, reference)
            self.assertEqual(subject['status'], 'LEAKAGE_DETECTED')
            self.assertEqual(len(subject['leaks']), 1)
            self.assertEqual(subject['leaks'][0]['workpiece_id'], '40000000017401')
            self.assertIn('40000000017401', subject['reason'])
            self.assertEqual(len(subject['records']), 5000)


if __name__ == '__main__':
    unittest.main()
