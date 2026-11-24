"""R604 legacy-ledger replay through explicit E3 PN firing histories."""
import csv
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/subject'))
from r604_replay import GENERATOR_SHA256, load_legacy_cases, replay_cases


class R604ReplayTests(unittest.TestCase):
    def setUp(self):
        self.generator = (ROOT / 'baseline_readonly/e2/tests/run_g2_r604.py').read_bytes()
        with (ROOT / 'baseline_readonly/e2/runs/g2_r604/results.csv').open(newline='') as stream:
            self.rows = list(csv.DictReader(stream))

    def test_six_reconstructed_histories_match_legacy_ledger(self):
        replayed = replay_cases(self.generator)
        print(json.dumps({'case':'r604_pn_replay', 'generator_sha256':GENERATOR_SHA256,
                          'scope':'RECONSTRUCTED_WITNESSES_NOT_RECOVERED_ORIGINAL_PN',
                          'results':replayed}))
        self.assertEqual(len(replayed), 6)
        for row in self.rows:
            got = replayed[row['test_id']]
            self.assertEqual(got['outcome'], row['expected'])
            self.assertEqual(got['outcome'], row['subject_outcome'])
            self.assertEqual(got['outcome'], row['oracle_outcome'])
            self.assertEqual(got['post_fault_deadline'], row['subject_deadline'])
            self.assertEqual(str(got['endpoint_exact_pass']), row['endpoint_exact'])
            self.assertEqual(got['trace_result']['status'], 'REPLAYED_HISTORY')
        self.assertEqual(replayed['SHORT_PREFIX_NOT_DUE']['trace_result']['terminal'], 'FRONTIER')
        self.assertEqual(replayed['INCOMPLETE_PAST_DEADLINE']['trace_result']['terminal'], 'DEADLOCK')

    def test_generator_identity_and_ast_execution_boundary(self):
        with self.assertRaisesRegex(ValueError, 'GENERATOR_SHA_MISMATCH'):
            load_legacy_cases(self.generator + b'\n# changed\n')
        tree = (b'import os\nos.system("touch forbidden")\n'
                b'cases = [("X", run("0", "1", "2", "1"), "COMPLETED_IN_TIME")]\n')
        # Identity is checked before parsing; no source is imported or executed.
        with self.assertRaisesRegex(ValueError, 'GENERATOR_SHA_MISMATCH'):
            load_legacy_cases(tree)
        self.assertFalse((ROOT / 'forbidden').exists())
