"""Unit and frozen-ledger tests for the independent raw TINA replay."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracles/independent"))

from tina_raw_replay import RawReplayError, classify_raw_record, replay


BOUNDED_STDOUT = """Tina version 4.0.0
REACHABILITY ANALYSIS -------------------------------------------

bounded

10 marking(s), 10 transition(s)
LIVENESS ANALYSIS -----------------------------------------------
not live
ANALYSIS COMPLETED ----------------------------------------------
# bounded, not live #
"""
UNBOUNDED_STDOUT = """Tina version 4.0.0
REACHABILITY ANALYSIS -------------------------------------------

unbounded

ANALYSIS COMPLETED ----------------------------------------------
"""
PARTIAL_STDOUT = """Tina version 4.0.0
INPUT NET -------------------------------------------------------
200 places, 259 transitions
0.005s
"""


def record(stdout, status, returncode, stderr=""):
    return {
        "candidate_id": "RMT_test",
        "status": status,
        "returncode": returncode,
        "pnml_sha256": "0" * 64,
        "places": 1,
        "transitions": 1,
        "stdout": stdout,
        "stderr": stderr,
    }


class RawClassificationTest(unittest.TestCase):
    def test_bounded_from_raw_stdout(self):
        self.assertEqual(classify_raw_record(record(BOUNDED_STDOUT, "BOUNDED", 0)), "BOUNDED")

    def test_unbounded_is_not_matched_as_bounded_substring(self):
        self.assertEqual(classify_raw_record(record(UNBOUNDED_STDOUT, "UNBOUNDED", 0)), "UNBOUNDED")

    def test_timeout_is_unresolved_not_unbounded(self):
        self.assertEqual(classify_raw_record(record(PARTIAL_STDOUT, "TIMEOUT", None)), "TIMEOUT")

    def test_timeout_with_reachability_verdict_is_recoverable(self):
        # Timeout during liveness after reachability already printed "bounded".
        self.assertEqual(classify_raw_record(record(BOUNDED_STDOUT, "TIMEOUT", None)), "BOUNDED")

    def test_timeout_cannot_hide_an_unbounded_verdict(self):
        with self.assertRaises(RawReplayError):
            classify_raw_record(record(UNBOUNDED_STDOUT, "BOUNDED", 0))

    def test_declared_bounded_without_stdout_verdict_is_rejected(self):
        with self.assertRaises(RawReplayError):
            classify_raw_record(record(PARTIAL_STDOUT, "BOUNDED", 0))

    def test_solver_error_is_not_timeout(self):
        with self.assertRaises(RawReplayError):
            classify_raw_record(record("", "ERROR", 1, "solver failed"))


class FrozenLedgerReplayTest(unittest.TestCase):
    def test_two_round_107520_row_exact_replay(self):
        result = replay(ROOT / "baseline_readonly/e2")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["analysis_scope"], "UNTIMED_P_T_ONLY_NO_TIMED_PROMOTION")
        self.assertEqual(result["initial"]["shards"], 10)
        self.assertEqual(result["initial"]["complete_shards"], [1, 2, 3, 6, 9])
        self.assertEqual(result["initial"]["incomplete_shards"], [4, 5, 7, 8, 10])
        self.assertEqual(result["initial"]["raw_rows"], 78443)
        self.assertEqual(result["initial"]["accepted_rows"], 53760)
        self.assertEqual(result["initial"]["accepted_status_counts"], {"BOUNDED": 52517, "TIMEOUT": 1243})
        self.assertEqual(result["initial"]["excluded_prefix_rows"], 24683)
        self.assertEqual(result["initial"]["retained_in_merged"], 52517)
        self.assertEqual(result["retry"]["shards"], 187)
        self.assertEqual(result["retry"]["rows"], 55003)
        self.assertEqual(result["retry"]["status_counts"], {"BOUNDED": 51535, "TIMEOUT": 3468})
        self.assertEqual(result["final"]["rows"], 107520)
        self.assertEqual(result["final"]["unique_candidate_ids"], 107520)
        self.assertEqual(result["final"]["status_counts"], {"BOUNDED": 104052, "TIMEOUT": 3468})
        self.assertEqual(
            result["final"]["strict_merged_sha256"],
            "a614e8074b944890b82d7b0672f96e48a022d12a315b119f4ad6dd305153c682",
        )
        self.assertEqual(result["final"]["raw_verdict_status_counts"], {"BOUNDED": 104212, "TIMEOUT": 3308})
        self.assertEqual(result["final"]["recoverable_timeout_with_verdict"], 160)
        self.assertTrue(all(result["checks"].values()))
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
