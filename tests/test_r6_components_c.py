"""TDD for R6-08: joint interval feasibility first, certificate binding second."""
import copy
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject',
                                       'implementations/probability', 'oracles/independent')]
from r6_components_c import make_acceptance_record, r608_evaluate
from r6_components_c_reference import reference_r608


def b(lo, hi):
    return {'low': str(lo), 'high': str(hi)}


def base():
    return json.loads((ROOT / 'models/regression/r608_base.json').read_text())


class R608AlgebraTests(unittest.TestCase):
    def test_all_contract_interval_and_applicability_classes(self):
        uncertain = copy.deepcopy(base())
        uncertain['q0'] = uncertain['q1'] = b(0, 1)
        cases = [
            ('gamma_above_one', {'Gamma': b(2, 3)}, 'INVALID_EVIDENCE'),
            ('gamma_below_zero', {'Gamma': b(-2, -1)}, 'INVALID_EVIDENCE'),
            ('negative_pe', {'Pe': b('-1/4', '-1/8')}, 'INVALID_EVIDENCE'),
            ('feasible_category_tightening', {'Q0_Y': b(0, '3/4')}, 'CONDITIONAL_ONLY'),
            ('category_contradiction', {'Q0_Y': b('3/5', '3/4')}, 'INVALID_EVIDENCE'),
            ('loose_pe', {'Pe': b(0, 2)}, 'CONDITIONAL_ONLY'),
            ('mutual_category_lower_sum_exceeds_q',
             {'categories0': {'a': b('1/3', '1/3'), 'b': b('1/3', '1/3')}}, 'INVALID_EVIDENCE'),
            ('joint_confidence_enclosure_contradiction',
             {'q0': b(0, 1), 'q1': b(0, 1),
              'categories0': {'a': b('3/5', '7/10')},
              'categories1': {'b': b('3/5', '7/10')}}, 'INVALID_EVIDENCE'),
            ('zero_prior', {'pi0': '0', 'pi1': '1'}, 'INVALID_INPUT'),
            ('zero_hypothesis', {'q0': b(0, 0), 'q1': b(1, 1)}, 'CONDITIONAL_ONLY'),
            ('unproven_positive_applicability', {}, 'CONDITIONAL_ONLY'),
        ]
        for name, patch, expected in cases:
            with self.subTest(case=name):
                data = copy.deepcopy(base())
                if name == 'unproven_positive_applicability':
                    data = copy.deepcopy(uncertain)
                else:
                    data.update(patch)
                subject = r608_evaluate(data)
                reference = reference_r608(data)
                self.assertEqual(subject['status'], expected)
                self.assertEqual(reference['status'], expected)
                self.assertFalse(subject['certified'])
                if expected != 'CONDITIONAL_ONLY':
                    self.assertNotIn('conditional_verdict', subject)
                else:
                    for key in ('a_P', 'conditional_verdict', 'q', 'categories', 'Pe', 'Gamma', 'certified'):
                        self.assertEqual(subject[key], reference[key], (name, key))
                if name == 'feasible_category_tightening':
                    self.assertEqual(subject['categories'][0]['B'], (F(0), F(1, 2)))
                if name == 'loose_pe':
                    self.assertEqual(subject['Pe'], (F(0), F(1, 2)))
                    self.assertEqual(subject['conditional_verdict'], 'PERP')
                if name == 'zero_hypothesis':
                    self.assertEqual((subject['a_P'], subject['conditional_verdict']), ('0', None))
                if name == 'unproven_positive_applicability':
                    self.assertEqual((subject['a_P'], subject['conditional_verdict']), ('PERP', None))

    def test_loose_upper_cannot_become_certified(self):
        case = dict(case_id='r608_loose_upper_mutation', kind='ap41', role='NEGATIVE')
        data = base() | {'Pe': b(0, 2)}
        subject = r608_evaluate(data)
        reference = reference_r608(data)
        mutated = r608_evaluate(data, mutation='LOOSE_UPPER_CERTIFY')
        self.assertEqual(mutated['Pe'], (F(0), F(2)))
        self.assertEqual(mutated['status'], 'CERTIFIED')
        record = make_acceptance_record('R6-08', case, subject, reference,
                                        'LOOSE_UPPER_CERTIFY', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(record['mutation_detected'])


if __name__ == '__main__':
    unittest.main()
