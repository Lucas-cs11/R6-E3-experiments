"""TDD for R6-12 traceability ledger and R6-13 source-data reconciliation."""
import json
import os
import sys
import csv
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject',
                                       'implementations/probability', 'oracles/independent')]
from r6_components_f import make_acceptance_record, run_r612, run_r613
from r6_components_f_reference import reference_r612, reference_r613


class R612TraceabilityTests(unittest.TestCase):
    def test_208_rows_exact_and_two_specific_mutations(self):
        freeze = ROOT / 'baseline_readonly/e2/scope/freeze.json'
        adapter = ROOT / 'baseline_readonly/e2/results/baseline_adapter_52.csv'
        ledger = ROOT / 'reports/e3_06/r6_12_logic_52x4_ledger.csv'
        case = dict(case_id='r612_full_52x4', kind='traceability', role='POSITIVE')
        subject = run_r612(freeze, adapter, ledger)
        reference = reference_r612(freeze, adapter, ledger)
        self.assertEqual(subject, reference)
        self.assertEqual(subject['status'], 'LEDGER_EXACT_MATCH')
        self.assertEqual(len(subject['rows']), 208)
        self.assertEqual(subject['summary'], {
            'cases': 52, 'rows': 208, 'micro_cases': 16, 'generated_cases': 36,
            'micro_rows': 64, 'generated_rows': 144,
            'unavailable_original_bytes': 64, 'reconstructed_via_generator': 144,
            'engine_not_executed': 208,
        })
        self.assertEqual(subject['mismatches'], 0)

        micro_mutated = run_r612(freeze, adapter, ledger, mutation='MICRO_MARKED_RECONSTRUCTED')
        self.assertEqual(micro_mutated['status'], 'LEDGER_MISMATCH')
        self.assertEqual(micro_mutated['mismatches'], 64)
        record = make_acceptance_record('R6-12', case, subject, reference,
                                        'MICRO_MARKED_RECONSTRUCTED', micro_mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')

        engine_mutated = run_r612(freeze, adapter, ledger, mutation='ENGINE_PREFILLED_PASS')
        self.assertEqual(engine_mutated['mismatches'], 208)
        self.assertTrue(all(row['e3_04_engine_result'] == 'PASS' for row in engine_mutated['rows']))
        record = make_acceptance_record('R6-12', case, subject, reference,
                                        'ENGINE_PREFILLED_PASS', engine_mutated)
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len(subject['rows']), 208)


class R613SourceReconciliationTests(unittest.TestCase):
    def test_manifest_1421_skip_without_raw_and_two_mutations(self):
        manifest = ROOT / 'baseline_readonly/e2/scope/pyscrew_raw_manifest.csv'
        predictions = ROOT / 'baseline_readonly/e2/chapter6/outer_predictions.csv'
        history = ROOT / 'runs/domain_audit/historical_1413_1421_summary.json'
        case = dict(case_id='r613_manifest_without_raw', kind='source_reconciliation', role='POSITIVE')
        with mock.patch.dict(os.environ, {'PYSCREW_RAW_JSON_ROOT': ''}):
            subject = run_r613(manifest, predictions, history, raw_json_root=None)
            reference = reference_r613(manifest, predictions, history, raw_json_root=None)
        self.assertEqual(subject, reference)
        self.assertEqual(subject['status'], 'FACT_AUDIT_COMPLETE')
        self.assertEqual(subject['manifest']['rows'], 5000)
        self.assertEqual(subject['manifest']['workpieces'], 2500)
        self.assertEqual(subject['manifest']['paired_workpieces'], 2500)
        self.assertEqual(subject['manifest']['classes'], 25)
        self.assertEqual(subject['manifest']['classes_x200'], 25)
        self.assertEqual(subject['manifest']['source_groups'], 50)
        self.assertEqual(subject['manifest']['result_counts'], {'OK': 4307, 'NOK': 693})
        self.assertEqual(subject['raw_sha_audit']['status'], 'SKIPPED_NO_RAW_DATA')
        self.assertIsNone(subject['raw_sha_audit']['mismatches'])
        self.assertEqual(subject['history']['main_non_NI'], 1421)
        self.assertEqual(subject['history']['difference_ids_unresolvable'], 8)
        self.assertFalse(subject['certified'])
        print(json.dumps({'case': case['case_id'], 'raw_sha_audit': subject['raw_sha_audit'],
                          'history': subject['history']}))

        inflated = run_r613(manifest, predictions, history, raw_json_root='',
                            mutation='COUNT_1421_INFLATED')
        self.assertEqual(inflated['history']['main_non_NI'], 1422)
        record = make_acceptance_record('R6-13', case, subject, reference,
                                        'COUNT_1421_INFLATED', inflated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')

        ignored = run_r613(manifest, predictions, history, raw_json_root='',
                           mutation='MISSING_SHA_IGNORED')
        self.assertEqual(ignored['raw_sha_audit']['status'], 'SHA_ZERO_MISMATCH')
        self.assertEqual(ignored['raw_sha_audit']['verified'], 5000)
        record = make_acceptance_record('R6-13', case, subject, reference,
                                        'MISSING_SHA_IGNORED', ignored)
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len((case,)), 1)

    def test_duplicate_left_row_is_a_pair_failure_in_both_implementations(self):
        with tempfile.TemporaryDirectory(prefix='r613-pair-') as tmp:
            manifest = Path(tmp) / 'manifest.csv'
            fields = ['workpiece_id', 'location', 'physical_class', 'source_group',
                      'workpiece_result', 'file_sha256', 'file_name']
            with manifest.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for location, filename in (('left', 'a.json'), ('left', 'b.json'), ('right', 'c.json')):
                    writer.writerow(dict(workpiece_id='W', location=location, physical_class='C',
                                         source_group=f'C|{location}', workpiece_result='OK',
                                         file_sha256='0' * 64, file_name=filename))
            predictions = ROOT / 'baseline_readonly/e2/chapter6/outer_predictions.csv'
            history = ROOT / 'runs/domain_audit/historical_1413_1421_summary.json'
            subject = run_r613(manifest, predictions, history, raw_json_root='')
            reference = reference_r613(manifest, predictions, history, raw_json_root='')
            self.assertEqual(subject, reference)
            self.assertEqual(subject['manifest']['pair_failures'], 1)
            self.assertEqual(subject['manifest']['paired_workpieces'], 0)
            self.assertEqual(subject['raw_sha_audit']['status'], 'SKIPPED_NO_RAW_DATA')


if __name__ == '__main__':
    unittest.main()
