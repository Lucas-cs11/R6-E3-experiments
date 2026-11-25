"""TDD for R6-09 exact piecewise-rational integration and UNSUPPORTED classification."""
import copy
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject',
                                       'implementations/probability', 'oracles/independent')]
from r6_components_e import make_acceptance_record, run_r609
from r6_components_e_reference import reference_r609


def load(name):
    return json.loads((ROOT / 'models/regression' / name).read_text())


class R609ExactIntegrationTests(unittest.TestCase):
    def test_linear_piecewise_and_rectangle_exact_masses(self):
        cases = [
            ('r609_linear.json', dict(case_id='r609_linear', kind='integrate', role='POSITIVE'), '1'),
            ('r609_piecewise.json', dict(case_id='r609_discontinuous', kind='integrate', role='POSITIVE'), '1'),
            ('r609_rectangle.json', dict(case_id='r609_rectangle', kind='integrate', role='POSITIVE'), '1'),
        ]
        outputs = []
        for filename, case, total in cases:
            with self.subTest(case=case['case_id']):
                model = load(filename)
                subject = run_r609(model, case)
                reference = reference_r609(model, case)
                self.assertEqual(subject, reference)
                self.assertEqual(subject['status'], 'EXACT_PIECEWISE_RATIONAL_INTEGRAL')
                self.assertEqual(subject['total_mass'], total)
                outputs.append((model, case, subject, reference))
        self.assertEqual([row['mass'] for row in outputs[1][2]['segments']], ['1/8', '7/8'])
        cells = {row['id']: row['mass'] for row in outputs[2][2]['cells']}
        self.assertEqual(cells, {'left': '1/4', 'right': '3/4'})

    def test_invalid_density_and_two_specific_mutations(self):
        linear = load('r609_linear.json')
        nonunit = copy.deepcopy(linear)
        nonunit['segments'][0]['coefficients'] = ['0', '1']
        case = dict(case_id='r609_nonunit_mass', kind='integrate', role='NEGATIVE')
        subject = run_r609(nonunit, case)
        self.assertEqual(subject, reference_r609(nonunit, case))
        self.assertEqual((subject['status'], subject['reason']), ('INVALID_EVIDENCE', 'TOTAL_MASS_NOT_ONE'))

        negative = copy.deepcopy(linear)
        negative['segments'][0]['coefficients'] = ['-1', '1']
        negative_case = dict(case_id='r609_negative_density', kind='integrate', role='NEGATIVE')
        rejected = run_r609(negative, negative_case)
        self.assertEqual(rejected, reference_r609(negative, negative_case))
        self.assertEqual((rejected['status'], rejected['reason']), ('INVALID_EVIDENCE', 'NEGATIVE_DENSITY'))

        piecewise = load('r609_piecewise.json')
        boundary_case = dict(case_id='r609_boundary_gap', kind='integrate', role='NEGATIVE',
                             drop_boundary=True)
        baseline = run_r609(piecewise, boundary_case)
        self.assertEqual(baseline['status'], 'INVALID_EVIDENCE')
        mutated = run_r609(piecewise, boundary_case, mutation='DROP_SEGMENT_BOUNDARY')
        self.assertEqual(mutated['status'], 'EXACT_PIECEWISE_RATIONAL_INTEGRAL')
        valid_case = dict(case_id='r609_discontinuous', kind='integrate', role='POSITIVE')
        valid = run_r609(piecewise, valid_case)
        record = make_acceptance_record('R6-09', valid_case, valid, reference_r609(piecewise, valid_case),
                                        'DROP_SEGMENT_BOUNDARY', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')

        clipped = copy.deepcopy(linear)
        clipped['segments'][0]['coefficients'] = ['2']
        clip_case = dict(case_id='r609_clip_nonunit', kind='integrate', role='NEGATIVE', clip_upper='1')
        clipped_baseline = run_r609(clipped, clip_case)
        self.assertEqual(clipped_baseline['status'], 'INVALID_EVIDENCE')
        clip_mutated = run_r609(clipped, clip_case, mutation='CLIP_UPPER')
        self.assertEqual(clip_mutated['total_mass'], '2')
        self.assertEqual(clip_mutated['status'], 'EXACT_PIECEWISE_RATIONAL_INTEGRAL')
        self.assertEqual(len((case, negative_case, boundary_case, clip_case)), 4)


class R609UnsupportedTests(unittest.TestCase):
    def test_limits_reasons_and_unsupported_as_zero_mutation(self):
        linear = load('r609_linear.json')
        cases = []
        for name, patch, expected, reason in [
            ('depth_limit', {'depth': 5}, 'UNRESOLVED', 'DEPTH_LIMIT_EXCEEDED'),
            ('time_limit', {'time': '3'}, 'UNRESOLVED', 'HORIZON_LIMIT_EXCEEDED'),
            ('finite_time_boundary', {'time': '2'}, 'EXACT_PIECEWISE_RATIONAL_INTEGRAL', None),
        ]:
            case = dict(case_id=f'r609_{name}', kind='integrate', role='BOUNDARY', **patch)
            subject = run_r609(linear, case)
            self.assertEqual(subject, reference_r609(linear, case))
            self.assertEqual(subject['status'], expected)
            if reason is not None:
                self.assertEqual(subject['reason'], reason)
                self.assertIsNone(subject['conditional_verdict'])
                self.assertFalse(subject['certified'])
            cases.append(case)

        unsupported_cases = []
        nonrational = copy.deepcopy(linear)
        nonrational['segments'][0]['coefficients'] = {'kind': 'sqrt'}
        unsupported_cases.append(('nonrational', nonrational, 'NON_RATIONAL_POLYNOMIAL'))
        nonfinite = copy.deepcopy(linear)
        nonfinite['segments'][0]['high'] = None
        unsupported_cases.append(('nonfinite', nonfinite, 'NON_FINITE_DOMAIN'))
        ellipse = load('r609_rectangle.json')
        ellipse['category'] = {'kind': 'ellipse'}
        unsupported_cases.append(('non_polyhedral', ellipse, 'NON_POLYHEDRAL_CATEGORY'))
        mutation_record = None
        for name, model, reason in unsupported_cases:
            with self.subTest(case=name):
                case = dict(case_id=f'r609_{name}', kind='integrate', role='NEGATIVE')
                subject = run_r609(model, case)
                reference = reference_r609(model, case)
                self.assertEqual(subject, reference)
                self.assertEqual((subject['status'], subject['reason']), ('UNSUPPORTED', reason))
                self.assertFalse(subject['certified'])
                self.assertIsNone(subject['conditional_verdict'])
                if name == 'nonrational':
                    mutated = run_r609(model, case, mutation='UNSUPPORTED_AS_ZERO')
                    self.assertEqual(mutated['status'], 'EXACT_PIECEWISE_RATIONAL_INTEGRAL')
                    self.assertEqual(mutated['total_mass'], '0')
                    self.assertTrue(mutated['certified'])
                    mutation_record = make_acceptance_record('R6-09', case, subject, reference,
                                                             'UNSUPPORTED_AS_ZERO', mutated)
        self.assertEqual(mutation_record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(mutation_record['mutation_detected'])
        self.assertEqual(len(cases) + len(unsupported_cases), 6)


if __name__ == '__main__':
    unittest.main()
