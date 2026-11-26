"""Contract tests for the signed seed=0 domain and TINA query reconciliation."""
import csv
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrozenDomainTests(unittest.TestCase):
    def test_signed_domain_counts_and_saturation(self):
        data = json.loads((ROOT / 'contracts/frozen_full_domain.json').read_text())
        self.assertEqual(data['status'], 'MATH_SIGNED_SCOPE')
        self.assertEqual(data['seed'], 0)
        self.assertEqual(data['candidates'], 143360)
        self.assertEqual(data['valid_configs'], 107520)
        self.assertEqual(data['invalid_configs'], 35840)
        self.assertEqual(data['minimum_task_records'], 107520 * 4)
        self.assertEqual(data['minimum_task_records'], 430080)
        self.assertEqual(data['saturated_configurations'], 3840)
        self.assertEqual(data['distinct_semantic_net_contents'], 85024)
        self.assertEqual(data['declared_ledger'], {'BOUNDED': 104052, 'TIMEOUT': 3468})
        self.assertEqual(data['query_reconciled'],
                         {'boundedness_proved': 104212, 'boundedness_undetermined': 3308})
        self.assertEqual(data['sensitivity_B']['valid_configs'], 103680)
        self.assertEqual(data['sensitivity_B']['declared_ledger'],
                         {'BOUNDED': 100212, 'TIMEOUT': 3468})
        self.assertEqual(data['sensitivity_B']['query_reconciled'],
                         {'boundedness_proved': 100372, 'boundedness_undetermined': 3308})
        self.assertEqual(sum(data['declared_ledger'].values()), 107520)
        self.assertEqual(sum(data['query_reconciled'].values()), 107520)
        self.assertEqual(sum(data['sensitivity_B']['declared_ledger'].values()), 103680)
        self.assertEqual(sum(data['sensitivity_B']['query_reconciled'].values()), 103680)
        with (ROOT / 'contracts/domain_index.csv').open(newline='') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 107520)
        self.assertEqual(len({row['candidate_id'] for row in rows}), 107520)
        self.assertEqual(sum(int(row['saturated']) for row in rows), 3840)
        expected_axes = {'machine_counts', 'part_type_counts', 'operations_per_part', 'wip_bounds',
                         'unobservable_ratios', 'fault_locations', 'interval_width_factors',
                         'adjustable_ratios'}
        self.assertTrue(expected_axes <= set(rows[0]))
        saturated = next(row for row in rows if row['candidate_id'] ==
                         'RMT_m4_j1_ops2_wip1_u0.1_f4_w0.5_a0.1')
        self.assertEqual(saturated['saturated'], '1')
        self.assertEqual(saturated['fault_locations_requested'], '4')
        self.assertEqual(saturated['used_machine_count'], '2')
        self.assertEqual(saturated['actual_distinct_fault_machine_count'], '2')
        self.assertEqual(saturated['actual_fault_transition_count'], '4')
        self.assertEqual(saturated['n_configs'], '2')
        decision = (ROOT / 'contracts/domain_signed_decision.md').read_text()
        appendix = ROOT / 'reports/01_研究域_E3-05_主理论裁定附录.md'
        trace = ROOT / 'reports/decision_trace.csv'
        self.assertIn(hashlib.sha256(appendix.read_bytes()).hexdigest(), decision)
        self.assertIn(hashlib.sha256(trace.read_bytes()).hexdigest(), decision)
        self.assertIn('MATH_SIGNED_SCOPE', decision)
        self.assertIn('100,372', decision)


if __name__ == '__main__':
    unittest.main()
