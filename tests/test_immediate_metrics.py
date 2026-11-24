"""Check word-only metrics against hand values and enumerated decisions."""
import hashlib
import itertools
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/p) for p in ('implementations/probability', 'oracles/independent')]
from immediate_evidence import canonical
from immediate_mass import propagate
from immediate_mass_reference import distribution
from immediate_metrics import evaluate_word_metrics


class WordMetricsTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT/'models/regression/immediate_mass.json').read_bytes()
        self.net = json.loads(self.raw)
        self.pin = '22018cd29bb71dd4e3ab2f669068fc8552bc0febc489ff32104ff4d91b12d4e4'

    def compute(self, name, pi='1/2', delta='1/3', budget=100, ledger=None):
        if ledger is None:
            ledger = canonical(propagate(self.net, budget))
        got = evaluate_word_metrics(self.raw, ledger, model_sha256=self.pin, budget=budget,
                                    reference=distribution, pi1=pi, delta=delta)
        print(json.dumps(dict(case=name, model_sha256=self.pin, budget=budget, prior=pi,
                              delta=delta, ledger_sha256=hashlib.sha256(ledger).hexdigest(), result=got)))
        self.assertFalse(got['certified'])
        return got

    def test_exact_boundary_and_enumerated_rules(self):
        # Independently enumerated decisions from the known conditional word law.
        cond = [(F(1,4),F(1,2)), (F(3,4),F(1,2))]
        for pi, delta, coverage in [('1/2','1/3','3/8'),('1/2','1/4','0'),('1/2','2/5','1'),
                                    ('3/4','1/3','1')]:
            with self.subTest(pi=pi, delta=delta):
                got = self.compute('threshold',pi,delta)
                p = F(pi)
                weighted = [((1-p)*n,p*f) for n,f in cond]
                error = min(sum(pair[1-label] for pair,label in zip(weighted, decision))
                            for decision in itertools.product((0,1), repeat=len(cond)))
                self.assertEqual((got['status'],got['q'],F(got['Pe']),F(got['Gamma'])),
                                 ('EXACT_IMMEDIATE_WORD_METRICS',['1/4','3/4'],error,F(coverage)))

    def test_internal_terminal_type_is_not_observed(self):
        self.net['transitions']['finish']['label'] = None
        self.raw = canonical(self.net)
        self.pin = hashlib.sha256(self.raw).hexdigest()
        got = self.compute('hidden_terminal')
        self.assertEqual((got['Pe'],got['Gamma'],len(got['atoms'])),('1/2','0',1))
        self.assertEqual(got['atoms'][0]['joint'],['1/4','3/4'])

    def test_unresolved_and_invalid_inputs(self):
        unresolved = self.compute('frontier',budget=1)
        self.assertEqual(unresolved['status'],'UNRESOLVED')
        self.assertNotIn('Pe',unresolved)
        bad = self.compute('invalid_prior',pi='1')
        self.assertEqual(bad['status'],'INVALID_INPUT')
        ledger = propagate(self.net,100)
        ledger['categories'][0]['word'] = ['invented']
        tampered = self.compute('invented_observation',ledger=canonical(ledger))
        self.assertEqual(tampered['status'],'INVALID_EVIDENCE')
        self.assertNotIn('Pe',tampered)

    def test_zero_hypothesis_mass(self):
        for t in self.net['transitions'].values():
            t['fault'] = False
        self.raw = canonical(self.net)
        self.pin = hashlib.sha256(self.raw).hexdigest()
        got = self.compute('zero_hypothesis')
        self.assertEqual((got['status'],got['q']),('NOT_APPLICABLE_ZERO_HYPOTHESIS',['1','0']))
        self.assertNotIn('Gamma',got)
