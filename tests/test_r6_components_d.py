"""TDD for R6-10 independent cross-layer replay and R6-11 Bayes pairs."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject',
                                       'implementations/probability', 'oracles/independent')]
from r6_components_d import make_acceptance_record, run_r610
from r6_components_d_reference import reference_r610


def load(name):
    return json.loads((ROOT / 'models/regression' / name).read_text())


def pair(model, probability=None, evidence='RAW'):
    if evidence == 'RAW':
        evidence = {'raw': True}
    return {'logical_model': model,
            'probability_model': model if probability is None else probability,
            'external_completion_evidence': evidence}


class R610IndependentCrossLayerTests(unittest.TestCase):
    def test_cross_layer_reference_and_two_specific_mutations(self):
        aligned = load('r610_aligned.json')
        collision = load('r610_collision.json')
        uncompleted = load('r610_uncompleted_collision.json')
        budget = load('r610_budget.json')
        cases = [
            ('aligned', pair(aligned), 'THEOREM_APPLICABLE'),
            ('uncompleted_collision', pair(uncompleted), 'NOT_CERTIFIED'),
            ('word_collision', pair(collision), 'THEOREM_NOT_APPLICABLE'),
            ('model_mismatch', pair(aligned, collision), 'THEOREM_NOT_APPLICABLE'),
            ('bare_external_flag', pair(aligned, evidence=None), 'NOT_CERTIFIED'),
            ('unverified_external_flag', pair(aligned, evidence={'raw': False}), 'NOT_CERTIFIED'),
            ('budget', pair(budget), 'NOT_CERTIFIED'),
        ]
        outputs = {}
        for name, model_pair, expected in cases:
            with self.subTest(case=name):
                case = dict(case_id=f'r610_{name}', kind='cross_layer', role='CASE', budget=50)
                subject = run_r610(model_pair, case)
                reference = reference_r610(model_pair, case)
                outputs[name] = (case, model_pair, subject, reference)
                self.assertEqual(subject['status'], expected)
                self.assertEqual(reference['status'], expected)
                self.assertEqual(subject['checks'], reference['checks'])
                self.assertTrue(subject['proof_trace'] or name in ('model_mismatch', 'bare_external_flag',
                                                                  'unverified_external_flag'))
        self.assertFalse(outputs['uncompleted_collision'][2]['checks']['uncompleted_distinguishable'])
        self.assertEqual(outputs['budget'][2]['reason'], 'exploration budget exhausted')

        case, model_pair, baseline, reference = outputs['uncompleted_collision']
        mutated = run_r610(model_pair, case, mutation='DROP_UNCOMPLETED_DISTINGUISH')
        self.assertEqual(mutated['status'], 'THEOREM_APPLICABLE')
        record = make_acceptance_record('R6-10', case, baseline, reference,
                                        'DROP_UNCOMPLETED_DISTINGUISH', mutated)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')

        case, model_pair, baseline, reference = outputs['word_collision']
        mutated = run_r610(model_pair, case, mutation='COLLISION_AS_APPLICABLE')
        self.assertEqual(mutated['status'], 'THEOREM_APPLICABLE')
        record = make_acceptance_record('R6-10', case, baseline, reference,
                                        'COLLISION_AS_APPLICABLE', mutated)
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len(cases), 7)


if __name__ == '__main__':
    unittest.main()
