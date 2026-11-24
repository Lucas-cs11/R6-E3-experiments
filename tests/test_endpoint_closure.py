"""Regression for zero-delay branching at the horizon of one concrete prefix."""
import json
import unittest
from itertools import product

from test_timed_trace import ROOT, assess, edge, history
from endpoint_closure import close_endpoint


class EndpointClosureTests(unittest.TestCase):
    def fixture(self):
        net = json.loads((ROOT / 'models/regression/timed_trace.json').read_text())
        net['initial']['gate'] = 0
        net['transitions'] = {
            'fault': net['transitions']['fault'],
            'advance': edge({'work': 1}, {'gate': 1}, [1, 1]),
            'finish': edge({'gate': 1}, {'done': 1}, [0, 0], immediate=True, completion=True),
            'abort': edge({'gate': 1}, {}, [0, 0], immediate=True),
            'ordinary': edge({'gate': 1}, {'done': 1}, [0, 1], completion=True),
        }
        return net, history(('fault', 1))

    def record(self, case, net, prefix, budget):
        result = close_endpoint(net, prefix, budget)
        print(json.dumps(dict(case=case, model=net, prefix=prefix, budget=budget, result=result)))
        return result

    def test_exhausted_suffixes_match_independent_schedule_enumeration(self):
        net, prefix = self.fixture()
        result = self.record('all_endpoint_branches', net, prefix, 20)
        # The fixture consumes one token per stage and never returns it to an
        # earlier place. After the prefix there are at most two more firings.
        expected = {}
        for length in range(3):
            for suffix in product(net['transitions'], repeat=length):
                schedule = dict(end=2, fires=prefix['fires'] + history(*[(x, 2) for x in suffix])['fires'])
                ref = assess(net, schedule)
                if ref['status'] == 'REPLAYED_HISTORY' and ref['terminal'] != 'FRONTIER':
                    expected[suffix] = (ref['terminal'], ref['outcome'])
        actual = {x['suffix']: (x['result']['terminal'], x['result']['outcome']) for x in result['terminals']}
        self.assertEqual(expected, {('advance', 'finish'): ('FIRST_COMPLETION', 'COMPLETED_IN_TIME'),
                                    ('advance', 'abort'): ('DEADLOCK', 'VIOLATION')})
        self.assertEqual(actual, expected)
        self.assertEqual(len(result['terminals']), len(expected))
        self.assertEqual((result['status'], result['pending'], result['visited']),
                         ('EXHAUSTED_AT_ENDPOINT_FOR_PREFIX', [], 4))

    def test_open_frontier_and_zero_time_loop(self):
        net, prefix = self.fixture()
        net['transitions']['loop'] = edge({'gate': 1}, {'gate': 1}, [0, 0], immediate=True)
        result = self.record('endpoint_loop_budget', net, prefix, 8)
        self.assertEqual((result['status'], result['visited']), ('UNRESOLVED', 8))
        self.assertTrue(result['pending'])
        self.assertTrue(all(x['status'] == 'UNRESOLVED' for x in result['pending']))
        self.assertTrue(any(x['suffix'][-1] == 'loop' for x in result['pending']))
        self.assertTrue(any(x['result']['terminal'] == 'FIRST_COMPLETION' for x in result['terminals']))

    def test_horizon_with_no_same_time_candidate(self):
        net, prefix = self.fixture()
        net['transitions']['advance']['interval'] = [2, 2]
        result = self.record('genuine_horizon_truncation', net, prefix, 1)
        self.assertEqual((result['status'], result['pending']), ('EXHAUSTED_AT_ENDPOINT_FOR_PREFIX', []))
        row, = result['terminals']
        self.assertEqual((row['suffix'], row['result']['terminal'], row['result']['outcome']),
                         ((), 'HORIZON_TRUNCATION', 'VIOLATION'))

    def test_invalid_prefix_and_early_stop(self):
        net, _ = self.fixture()
        self.assertEqual(self.record('disabled_prefix', net, history(('finish', 2)), 5)['status'], 'INVALID_PREFIX')
        self.assertEqual(self.record('before_horizon', net, history(('fault', 1), end=1), 5)['status'], 'NOT_AT_HORIZON')
