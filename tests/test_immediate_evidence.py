"""Content replay controls for an externally pinned immediate-net fixture."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/probability', 'oracles/independent')]
from immediate_mass import propagate
from immediate_mass_reference import distribution
from immediate_evidence import canonical, verify


class ImmediateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / 'models/regression/immediate_mass.json').read_bytes()
        self.net = json.loads(self.raw)
        self.pin = '22018cd29bb71dd4e3ab2f669068fc8552bc0febc489ff32104ff4d91b12d4e4'

    def run_replay(self, name, model, ledger, expected, reason=None, budget=100, ref=distribution):
        got = verify(model, ledger, model_sha256=self.pin, budget=budget, reference=ref)
        print(json.dumps({'case':name, 'pinned_sha256':self.pin, 'budget':budget,
                          'model_text':model.decode(), 'ledger_text':ledger.decode(), 'result':got}))
        self.assertEqual((got['status'],got['certified']), (expected,False))
        if reason is not None:
            self.assertEqual(got['reason'],reason)

    def test_complete(self):
        self.run_replay('complete',self.raw,canonical(propagate(self.net,100)), 'IMMEDIATE_MASS_REPLAY_MATCH')

    def test_model_replacement_even_with_matching_ledger(self):
        self.net['transitions']['normal']['weight'] = 4
        self.run_replay('model_replacement',canonical(self.net),canonical(propagate(self.net,100)),
                        'INVALID_EVIDENCE','MODEL_SHA_MISMATCH')

    def test_content_mismatch_despite_retained_result_status(self):
        ledger = propagate(self.net,100)
        ledger['categories'][0]['mass'],ledger['categories'][1]['mass'] = ledger['categories'][1]['mass'],ledger['categories'][0]['mass']
        self.run_replay('swapped_categories',self.raw,canonical(ledger),'INVALID_EVIDENCE','RAW_LEDGER_REPLAY_MISMATCH')

    def test_unresolved_and_dropped_frontier(self):
        ledger = propagate(self.net,1)
        self.run_replay('unresolved',self.raw,canonical(ledger),'UNRESOLVED',budget=1)
        ledger['frontier'].pop()
        self.run_replay('dropped_frontier',self.raw,canonical(ledger),'INVALID_EVIDENCE','RAW_LEDGER_REPLAY_MISMATCH',budget=1)

    def test_reference_disagreement(self):
        self.run_replay('reference_disagreement',self.raw,canonical(propagate(self.net,100)),
                        'INVALID_EVIDENCE','INDEPENDENT_MASS_MISMATCH',ref=lambda _: {})

    def test_duplicate_status_key(self):
        ledger = b'{"status":"CERTIFIED",' + canonical(propagate(self.net,100))[1:]
        self.run_replay('duplicate_status',self.raw,ledger,'INVALID_EVIDENCE','duplicate JSON key')
