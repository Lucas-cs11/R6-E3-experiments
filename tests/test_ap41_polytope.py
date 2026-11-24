"""Cross-check interval projections against independent exact LP vertices."""
import json
import random
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject', 'oracles/independent')]
from ap41_intervals import evaluate
from ap41_polytope import project


def bound(pair):
    return dict(zip(('low', 'high'), map(str, pair)))


class ProjectionTest(unittest.TestCase):
    def test_exact_crosscheck(self):
        rng = random.Random(4101)
        bounds = lambda: tuple(sorted((F(rng.randrange(-2, 10), 7), F(rng.randrange(-2, 10), 7))))
        cases = [((bounds(), bounds()), ({'B': bounds()}, {'C': bounds()}), (False, False)) for _ in range(48)]
        cases += [(((0,1),(0,1)), ({'B':(F(1,7),F(3,7)), '@frontier':(F(1,7),F(2,7))}, {'B':(F(4,7),F(5,7))}), (True,False)),
                  (((0,1),(0,1)), ({'B':(F(4,7),1)}, {'C':(F(4,7),1)}), (False,False)),
                  (((0,1),(0,1)), ({'B':(F(1,7),F(3,7)), '@frontier':(F(1,7),F(2,7))}, {'C':(F(1,7),F(3,7)), '@frontier':(F(1,7),F(4,7))}), (True,True))]
        feasible = 0
        for idx,(q,groups,closed) in enumerate(cases):
            data = dict(pi0='1/2',pi1='1/2',epsilon='1/4',delta='1/4',gamma='1/2',v_c='PERP',Pe=bound((0,1)),Gamma=bound((0,1)))
            for i in range(2):
                data[f'q{i}'] = bound(q[i]); data[f'categories{i}'] = {k:bound(v) for k,v in groups[i].items() if k != '@frontier'}
                if closed[i]: data[f'frontier{i}'] = bound(groups[i]['@frontier'])
            got, ref = evaluate(data), project(q,groups,closed)
            with self.subTest(case=idx, input=json.dumps(data)):
                self.assertFalse(got['certified'])
                if ref is None:
                    self.assertEqual(got['status'], 'INVALID_EVIDENCE')
                else:
                    feasible += 1
                    self.assertEqual(got['status'], 'CONDITIONAL_ONLY')
                    self.assertEqual((got['q'],got['categories']), (ref['q'],ref['categories']))
        self.assertGreater(feasible, 0)
        self.assertLess(feasible, len(cases))
        print(json.dumps({'cases': len(cases), 'feasible': feasible, 'infeasible': len(cases)-feasible, 'seed': 4101}))
