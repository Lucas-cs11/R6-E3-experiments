"""Cross-layer alignment checks on evidence recomputed from models."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject')]
from cross_layer import check_alignment
from test_reachability import edge, net


def pair(lm, pm, evidence={'raw': True}):
    return {'logical_model': lm, 'probability_model': pm,
            'external_completion_evidence': evidence}


class CrossLayerTests(unittest.TestCase):
    def aligned_model(self):
        return net({'ca': edge({'s': 1}, {'d': 1}, [1, 1], completion=True, label='done')},
                   ha=4, hpsi=2, bc=1)

    def test_applicable_on_injective_aligned_models(self):
        m = self.aligned_model()
        got = check_alignment(pair(m, m), 50)
        print(json.dumps({'case': 'applicable', 'result': got}))
        self.assertEqual(got['status'], 'THEOREM_APPLICABLE')
        self.assertFalse(got['counterexample_claimed'])

    def test_word_collision_forbids_strict_theorem(self):
        model = net({
            'sel_a': edge({'s': 1}, {'a': 1}, [0, 0], immediate=True),
            'sel_b': edge({'s': 1}, {'b': 1}, [0, 0], immediate=True),
            'ca': edge({'a': 1}, {'d': 1}, [1, 1], completion=True, label='done'),
            'cb': edge({'b': 1}, {'d': 1}, [2, 2], completion=True, label='done'),
        }, initial={'s': 1, 'a': 0, 'b': 0, 'd': 0})
        got = check_alignment(pair(model, model), 50)
        print(json.dumps({'case': 'collision', 'result': got}))
        self.assertEqual(got['status'], 'THEOREM_NOT_APPLICABLE')
        self.assertFalse(got['counterexample_claimed'])
        self.assertIn('collision_witness', got)

    def test_model_mismatch_is_not_applicable(self):
        m = self.aligned_model()
        other = net({'ca': edge({'s': 1}, {'d': 1}, [2, 2], completion=True, label='done')},
                    ha=4, hpsi=2, bc=1)
        got = check_alignment(pair(m, other), 50)
        print(json.dumps({'case': 'mismatch', 'result': got}))
        self.assertEqual(got['status'], 'THEOREM_NOT_APPLICABLE')

    def test_bare_flag_without_evidence_is_not_certified(self):
        m = self.aligned_model()
        got = check_alignment(pair(m, m, evidence=None), 50)
        print(json.dumps({'case': 'no_evidence', 'result': got}))
        self.assertEqual(got['status'], 'NOT_CERTIFIED')
        got2 = check_alignment(pair(m, m, evidence={'raw': False}), 50)
        self.assertEqual(got2['status'], 'NOT_CERTIFIED')

    def test_uncompleted_indistinguishable_from_completed_fails(self):
        # Branch b fires a non-completion transition labelled 'done' then
        # deadlocks: its observation word equals the completed run's word,
        # so uncompleted runs are NOT distinguishable from completed ones.
        model = net({
            'sel_a': edge({'s': 1}, {'a': 1}, [0, 0], immediate=True),
            'sel_b': edge({'s': 1}, {'b': 1}, [0, 0], immediate=True),
            'ca': edge({'a': 1}, {'d': 1}, [1, 1], completion=True, label='done'),
            'noise': edge({'b': 1}, {'z': 1}, [1, 1], label='done'),
        }, initial={'s': 1, 'a': 0, 'b': 0, 'd': 0, 'z': 0})
        got = check_alignment(pair(model, model), 50)
        print(json.dumps({'case': 'uncompleted_collision', 'result': got}))
        self.assertEqual(got['status'], 'NOT_CERTIFIED')
        self.assertFalse(got['checks']['uncompleted_distinguishable'])

    def test_budget_exhaustion_is_not_certified(self):
        m = net({'loop': edge({'s': 1}, {'s': 1}, [0, 0], immediate=True),
                 'done': edge({'s': 1}, {'d': 1}, [1, 1], completion=True, label='done')})
        got = check_alignment(pair(m, m), 8)
        print(json.dumps({'case': 'budget', 'result': got}))
        self.assertEqual(got['status'], 'NOT_CERTIFIED')
        self.assertEqual(got['reason'], 'exploration budget exhausted')


if __name__ == '__main__':
    unittest.main()
