"""TDD for R6-12 traceability ledger and R6-13 source-data reconciliation."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject',
                                       'implementations/probability', 'oracles/independent')]
from r6_components_f import make_acceptance_record, run_r612
from r6_components_f_reference import reference_r612


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


if __name__ == '__main__':
    unittest.main()
