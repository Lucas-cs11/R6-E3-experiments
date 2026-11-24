"""Exact weighted conflict and mass-ledger regressions on a real P/T fixture."""
import copy
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/probability', 'oracles/independent')]
from immediate_mass import propagate
from immediate_mass_reference import distribution


class ImmediateMassTests(unittest.TestCase):
    def setUp(self):
        self.net = json.loads((ROOT / 'models/regression/immediate_mass.json').read_text())

    def test_conflict_and_rejoined_history(self):
        got = propagate(self.net, 100)
        ref = distribution(self.net)
        expected = {(0, 'FIRST_COMPLETION', ('done',)): F(3,16), (0, 'DEADLOCK', ()): F(1,16),
                    (1, 'FIRST_COMPLETION', ('done',)): F(3,8), (1, 'DEADLOCK', ()): F(3,8)}
        actual = {(x['hypothesis'], x['terminal'], tuple(x['word'])): F(x['mass']) for x in got['categories']}
        print(json.dumps({'case':'weighted_conflict', 'actual':got, 'reference':[
            [i,t,w,str(v)] for (i,t,w),v in sorted(ref.items())]}))
        self.assertEqual(got['status'], 'EXACT_IMMEDIATE_PATH_MASS')
        self.assertEqual(actual, expected)
        self.assertEqual(actual, ref)
        self.assertEqual({c['transition'] for c in got['events'][0]['children']}, {'normal','fault','extra'})
        self.assertFalse(any('after_done' in x['path'] for x in got['events']))
        work = [x for x in got['events'] if x['marking']['work']]
        self.assertEqual({(x['hypothesis'],F(x['mass'])) for x in work}, {(0,F(1,4)),(1,F(1,2))})
        for node in got['events']:
            if node['children']:
                self.assertEqual(sum(F(x['mass']) for x in node['children']), F(node['mass']))

    def test_budget_and_cycles_keep_unresolved_mass(self):
        full = propagate(self.net, 100)
        for budget in range(1,len(full['events'])):
            got = propagate(self.net,budget)
            print(json.dumps({'case':'bounded_prefix', 'budget':budget, 'actual':got}))
            self.assertEqual(got['status'],'UNRESOLVED')
            self.assertEqual(sum(F(x['mass']) for x in got['frontier']), F(got['unresolved']))
            self.assertEqual(F(got['resolved'])+F(got['unresolved']), 1)
        cycle = copy.deepcopy(self.net)
        cycle['transitions']['loop'] = dict(cycle['transitions']['normal'],post={'root':1})
        got = propagate(cycle,20)
        print(json.dumps({'case':'zero_time_cycle','budget':20,'actual':got}))
        self.assertEqual(got['status'],'UNRESOLVED')
        self.assertGreater(F(got['unresolved']),0)
        self.assertEqual(F(got['resolved'])+F(got['unresolved']),1)
        with self.assertRaisesRegex(ValueError,'depth exhausted'):
            distribution(cycle,max_depth=4)

    def test_reject_non_immediate_model(self):
        self.net['transitions']['normal']['interval'] = [0,1]
        with self.assertRaisesRegex(ValueError,'unsupported transition'):
            propagate(self.net,100)
        with self.assertRaisesRegex(ValueError,'outside immediate-only'):
            distribution(self.net)
