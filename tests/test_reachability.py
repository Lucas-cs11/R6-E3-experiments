"""Cross-check symbolic reachability against the independent absolute oracle."""
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from reachability import completion_intervals, explore, omega_injectivity
from timed_trace import replay
from absolute_schedule import assess, projection_status


def edge(pre, post, interval, *, immediate=False, completion=False, fault=False, label=None):
    return dict(pre=pre, post=post, interval=interval, immediate=immediate,
                completion=completion, fault=fault, label=label)


def net(transitions, initial=None, ha=4, hpsi=2, bc=1):
    bd = F(ha) - F(hpsi) - F(bc)
    return dict(H_psi=str(hpsi), B_c=str(bc), B_d=str(bd), H_A=str(ha),
                initial=initial or {'s': 1, 'w': 0, 'd': 0},
                completion_marking={'d': 1}, transitions=transitions)


class ReachabilityTests(unittest.TestCase):
    def test_two_point_times_same_word_collide_word_only(self):
        model = net({
            'sel_a': edge({'s': 1}, {'a': 1}, [0, 0], immediate=True),
            'sel_b': edge({'s': 1}, {'b': 1}, [0, 0], immediate=True),
            'ca': edge({'a': 1}, {'d': 1}, [1, 1], completion=True, label='done'),
            'cb': edge({'b': 1}, {'d': 1}, [2, 2], completion=True, label='done'),
        }, initial={'s': 1, 'a': 0, 'b': 0, 'd': 0})
        exploration = explore(model, 50)
        rows = completion_intervals(model, exploration)
        verdict = omega_injectivity(rows, 'word')
        print(json.dumps({'case': 'two_point_times', 'rows': rows, 'verdict': verdict}))
        self.assertEqual(exploration['status'], 'EXHAUSTED_FOR_MODEL')
        self.assertEqual(len(rows), 2)
        self.assertEqual({tuple(r['completion_interval']) for r in rows}, {('1', '1'), ('2', '2')})
        self.assertEqual(verdict['status'], 'COLLISION')
        # Independent cross-check with concrete histories and the absolute oracle.
        histories = [dict(fires=[{'transition': s, 'at': 0}, {'transition': k, 'at': t}], end=t)
                     for s, k, t in (('sel_a', 'ca', 1), ('sel_b', 'cb', 2))]
        replays = [replay(model, h) for h in histories]
        self.assertTrue(all(r['status'] == 'REPLAYED_HISTORY' for r in replays))
        self.assertEqual(projection_status(replays, 'word'), 'COLLISION')
        self.assertEqual(assess(model, histories[0])['omega_c'], replays[0]['omega_c'])

    def test_unique_point_time_is_injective_word_only(self):
        model = net({'ca': edge({'s': 1}, {'d': 1}, [1, 1], completion=True, label='done')})
        rows = completion_intervals(model, explore(model, 50))
        print(json.dumps({'case': 'unique_point', 'rows': rows}))
        self.assertEqual(omega_injectivity(rows, 'word')['status'], 'INJECTIVE_ON_EXPLORED_SET')
        self.assertEqual(rows[0]['completion_interval'], ['1', '1'])

    def test_interval_completion_continuum_collides_both_modes(self):
        model = net({'ca': edge({'s': 1}, {'d': 1}, [1, 2], completion=True, label='done')})
        rows = completion_intervals(model, explore(model, 50))
        print(json.dumps({'case': 'continuum', 'rows': rows}))
        self.assertEqual(rows[0]['completion_interval'], ['1', '2'])
        self.assertEqual(omega_injectivity(rows, 'word')['status'], 'COLLISION')
        self.assertEqual(omega_injectivity(rows, 'word_and_time')['status'], 'COLLISION')

    def test_age_accumulation_couples_downstream_earliest(self):
        # 'slow' [2,2] enabled at start; 'fast' [0,0] fires first without
        # consuming slow's token.  Persistent age makes completion fire at
        # date 2 exactly, so the completion interval is a single point.
        model = net({
            'fast': edge({'w': 1}, {'g': 1}, [0, 0], immediate=True),
            'slow': edge({'s': 1}, {'d': 1}, [2, 2], completion=True, label='done'),
        }, initial={'s': 1, 'w': 1, 'g': 0, 'd': 0})
        rows = completion_intervals(model, explore(model, 50))
        print(json.dumps({'case': 'age_accumulation', 'rows': rows}))
        self.assertEqual(rows[0]['completion_interval'], ['2', '2'])
        self.assertEqual(omega_injectivity(rows, 'word')['status'], 'INJECTIVE_ON_EXPLORED_SET')

    def test_budget_exhaustion_stays_unresolved(self):
        model = net({'loop': edge({'s': 1}, {'s': 1}, [0, 0], immediate=True),
                     'done': edge({'s': 1}, {'d': 1}, [1, 1], completion=True, label='done')})
        exploration = explore(model, 8)
        print(json.dumps({'case': 'budget', 'status': exploration['status'],
                          'pending': len(exploration['pending'])}))
        self.assertEqual(exploration['status'], 'UNRESOLVED')
        self.assertTrue(exploration['pending'])

    def test_fault_before_completion_marks_h1(self):
        model = net({
            'flt': edge({'s': 1}, {'w': 1}, [1, 1], fault=True),
            'done': edge({'w': 1}, {'d': 1}, [0, 1], completion=True, label='done'),
        })
        rows = completion_intervals(model, explore(model, 50))
        print(json.dumps({'case': 'fault_then_done', 'rows': rows}))
        self.assertEqual(rows[0]['fault_step'], 1)
        self.assertEqual(rows[0]['completion_interval'], ['1', '2'])


if __name__ == '__main__':
    unittest.main()
