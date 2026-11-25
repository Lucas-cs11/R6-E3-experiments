"""TDD integration tests for R6-05..07; one component is committed at a time."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from r6_components_b import make_acceptance_record, run_r605
from r6_components_b_reference import reference_r605


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


if __name__ == '__main__':
    unittest.main()
