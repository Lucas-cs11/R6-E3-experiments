"""Integration: exact exploration counts on real generated models (seed 0)."""
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat'),
                str(ROOT / 'tests')]
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402
from probe_scale import to_model  # noqa: E402
from reachability import completion_intervals, explore, omega_injectivity  # noqa: E402

CASES = [
    ('RMT_m2_j1_ops2_wip1_u0.1_f1_w0.5_a0.1',
     dict(n_machines=2, n_parts=1, ops_per_part=2, wip_bound=1, unobservable_ratio=0.1,
          fault_locations=1, interval_width_factor=0.5, adjustable_ratio=0.1),
     dict(visited=14, completed=2, status='EXHAUSTED_FOR_MODEL', verdict='COLLISION')),
    ('RMT_m2_j2_ops2_wip2_u0.3_f2_w1.0_a0.25',
     dict(n_machines=2, n_parts=2, ops_per_part=2, wip_bound=2, unobservable_ratio=0.3,
          fault_locations=2, interval_width_factor=1.0, adjustable_ratio=0.25),
     dict(visited=5585, completed=800, status='EXHAUSTED_FOR_MODEL', verdict='COLLISION')),
]


class ScaleProbeTests(unittest.TestCase):
    def test_real_model_exploration_counts(self):
        for candidate, params, expected in CASES:
            with self.subTest(candidate=candidate):
                net, L, H = generate_rmt_fms(**params, seed=0, machine_capacity=1,
                                             n_configs=2, repair_domain='standard')
                model = to_model(net, Fraction(str(H)))
                exploration = explore(model, 2000000)
                rows = completion_intervals(model, exploration)
                verdict = omega_injectivity(rows, 'word')
                got = dict(status=exploration['status'], visited=exploration['visited'],
                           completed=len(rows), pending=len(exploration['pending']),
                           verdict=verdict['status'])
                print(json.dumps({'candidate_id': candidate, 'L': str(L), 'H': str(H), **got}))
                self.assertEqual(got['status'], expected['status'])
                self.assertEqual(got['visited'], expected['visited'])
                self.assertEqual(got['completed'], expected['completed'])
                self.assertEqual(got['pending'], 0)
                self.assertEqual(got['verdict'], expected['verdict'])


if __name__ == '__main__':
    unittest.main()
