"""TDD integration tests for R6-05..07; one component is committed at a time."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from r6_components_b import make_acceptance_record, run_r605, run_r606
from r6_components_b_reference import reference_r605, reference_r606


def load(name):
    return json.loads((ROOT / 'models/regression' / name).read_text())


class R605DBMTests(unittest.TestCase):
    def test_exact_mixed_class_split_and_specific_collapse_mutation(self):
        model = load('r605_dbm_split.json')
        positive = dict(case_id='r605_mixed_class', kind='dbm', role='POSITIVE', split_at='1')
        subject = run_r605(model, positive)
        reference = reference_r605(model, positive)
        self.assertEqual(subject, reference)
        self.assertEqual(subject['status'], 'EXACT_DBM_DIFFERENCE_SPLIT')
        cells = {row['classification']: row for row in subject['cells']}
        self.assertTrue(cells['NON_VIOLATION']['nonempty'])
        self.assertTrue(cells['VIOLATION']['nonempty'])
        self.assertTrue(any(row['op'] == '<=' and row['bound'] == '1'
                            for row in cells['NON_VIOLATION']['constraints']))
        self.assertTrue(any(row['op'] == '>' and row['bound'] == '1'
                            for row in cells['VIOLATION']['constraints']))

        negative = dict(case_id='r605_empty_violation_difference', kind='dbm',
                        role='NEGATIVE', split_at='4')
        empty = run_r605(model, negative)
        self.assertEqual(empty, reference_r605(model, negative))
        empty_cells = {row['classification']: row for row in empty['cells']}
        self.assertTrue(empty_cells['NON_VIOLATION']['nonempty'])
        self.assertFalse(empty_cells['VIOLATION']['nonempty'])

        mutated = run_r605(model, positive, mutation='R605_COLLAPSE_MIXED_CLASS')
        self.assertEqual([row['classification'] for row in mutated['cells']], ['NON_VIOLATION'])
        record = make_acceptance_record('R6-05', positive, subject, reference,
                                        'R605_COLLAPSE_MIXED_CLASS', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len((positive, negative)), 2)


class R606HistoryLPTests(unittest.TestCase):
    def test_lossless_normal_fault_histories_and_coupled_lp(self):
        model = load('r606_history_lp.json')
        positive = dict(
            case_id='r606_same_omega_normal_fault', kind='history_lp', role='POSITIVE',
            witnesses=[
                dict(history_id='normal', history={'fires': [
                    {'transition': 'normal_root', 'at': 0},
                    {'transition': 'normal_complete', 'at': 2}], 'end': 2}),
                dict(history_id='fault', history={'fires': [
                    {'transition': 'fault_root', 'at': 0},
                    {'transition': 'fault_complete', 'at': 2}], 'end': 2}),
            ])
        subject = run_r606(model, positive)
        reference = reference_r606(model, positive)
        self.assertEqual(subject['status'], reference['status'])
        self.assertEqual(len(subject['histories']), 2)
        self.assertEqual({row['hypothesis'] for row in subject['histories']}, {'NORMAL', 'FAULT'})
        self.assertEqual(len(subject['observation_groups']), 1)
        self.assertEqual(subject['observation_groups'][0]['members'], ['fault', 'normal'])
        self.assertEqual(subject['lp_solution'], {'normal': '2/3', 'fault': '1/3'})
        self.assertTrue(all(row['trace'] for row in subject['histories']))

        negative = dict(
            case_id='r606_tampered_completion_claim', kind='history_lp', role='NEGATIVE',
            witnesses=[dict(history_id='normal_bad_claim', history={
                'fires': [{'transition': 'normal_root', 'at': 0},
                          {'transition': 'normal_complete', 'at': 2}],
                'end': 2, 'completion_time': 1})])
        invalid_subject = run_r606(model, negative)
        invalid_reference = reference_r606(model, negative)
        self.assertEqual(invalid_subject, invalid_reference)
        self.assertEqual(invalid_subject['status'], 'INVALID_INPUT_OR_HISTORY')

        mutated = run_r606(model, positive, mutation='R606_DROP_FAULT_HISTORY')
        self.assertEqual([row['history_id'] for row in mutated['histories']], ['normal'])
        self.assertEqual(mutated['observation_groups'][0]['members'], ['normal'])
        record = make_acceptance_record('R6-06', positive, subject, reference,
                                        'R606_DROP_FAULT_HISTORY', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len((positive, negative)), 2)


if __name__ == '__main__':
    unittest.main()
