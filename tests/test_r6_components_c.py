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
from immediate_mass import propagate


def b(lo, hi):
    return {'low': str(lo), 'high': str(hi)}


def base():
    return json.loads((ROOT / 'models/regression/r608_base.json').read_text())


CERTIFICATE_PIN = '22018cd29bb71dd4e3ab2f669068fc8552bc0febc489ff32104ff4d91b12d4e4'


def certificate_input(replace=False):
    raw = (ROOT / 'models/regression/r608_immediate_certificate.json').read_text()
    model = json.loads(raw)
    if replace:
        model['transitions']['normal']['weight'] = 4
        raw = json.dumps(model, sort_keys=True, separators=(',', ':'))
    data = base()
    data['immediate_evidence'] = {
        'model_bytes': raw,
        'ledger': propagate(model, 100),
        'model_sha256': CERTIFICATE_PIN,
        'budget': 100,
    }
    return data


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


class R608CertificateTests(unittest.TestCase):
    def test_bound_metrics_and_model_replacement_with_trust_flag_mutation(self):
        positive_case = dict(case_id='r608_bound_immediate_metrics', kind='ap41', role='POSITIVE')
        data = certificate_input()
        subject = r608_evaluate(data)
        reference = reference_r608(data)
        self.assertEqual(subject['status'], 'CONDITIONAL_ONLY')
        self.assertEqual(subject['certificate']['status'], 'EXACT_IMMEDIATE_WORD_METRICS')
        self.assertEqual(subject['certificate']['model_sha256'], CERTIFICATE_PIN)
        self.assertEqual(subject['certificate']['q'], ['1/4', '3/4'])
        self.assertEqual((subject['Pe'], subject['Gamma']),
                         ((F(3, 8), F(3, 8)), (F(0), F(0))))
        self.assertEqual(subject['conditional_verdict'], '0')
        self.assertFalse(subject['certified'])
        for key in ('a_P', 'conditional_verdict', 'q', 'categories', 'Pe', 'Gamma', 'certified', 'certificate'):
            self.assertEqual(subject[key], reference[key], key)

        negative_case = dict(case_id='r608_model_replacement', kind='ap41', role='NEGATIVE')
        replaced = certificate_input(replace=True)
        replaced['evidence_valid'] = True
        rejected = r608_evaluate(replaced)
        rejected_reference = reference_r608(replaced)
        self.assertEqual(rejected['status'], 'INVALID_EVIDENCE')
        self.assertEqual(rejected['reason'], 'MODEL_SHA_MISMATCH')
        self.assertEqual(rejected, rejected_reference)
        self.assertNotIn('conditional_verdict', rejected)
        self.assertFalse(rejected['certified'])

        mutated = r608_evaluate(replaced, mutation='TRUST_FLAG')
        self.assertEqual(mutated['status'], 'CONDITIONAL_ONLY')
        self.assertTrue(mutated['certified'])
        self.assertEqual(mutated['certificate']['status'], 'TRUSTED_FLAG')
        record = make_acceptance_record('R6-08', negative_case, rejected, rejected_reference,
                                        'TRUST_FLAG', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len((positive_case, negative_case)), 2)


if __name__ == '__main__':
    unittest.main()
