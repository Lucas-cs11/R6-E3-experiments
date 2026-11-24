"""Negative tests for raw-evidence tampering on a synthetic two-round root."""
import gzip
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracles/independent"))
from tina_raw_replay import Pins, RawReplayError, _RowHasher, replay

BOUNDED = ("Tina version 4.0.0\nREACHABILITY ANALYSIS -------------------------------------------\n\n"
           "bounded\n\n10 marking(s), 10 transition(s)\n\nLIVENESS ANALYSIS ---\nnot live\n"
           "ANALYSIS COMPLETED ----------------------------------------------\n# bounded #\n")
UNBOUNDED = ("Tina version 4.0.0\nREACHABILITY ANALYSIS -------------------------------------------\n\n"
             "unbounded\n\nANALYSIS COMPLETED ----------------------------------------------\n")


def raw_row(candidate, status, stdout, returncode, places=20, transitions=16):
    return {"candidate_id": candidate, "status": status, "returncode": returncode,
            "pnml_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
            "places": places, "transitions": transitions, "stdout": stdout, "stderr": ""}


def write_shard(shard_dir, batch, rows, name):
    shard_dir.mkdir(parents=True)
    with gzip.open(shard_dir / f"tina_batch_{batch}.jsonl.gz", "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    import csv as _csv
    with (shard_dir / f"tina_batch_{batch}.csv").open("w", newline="") as handle:
        w = _csv.DictWriter(handle, fieldnames=["candidate_id", "status", "returncode",
                                                "pnml_sha256", "places", "transitions"])
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row[k] is None else row[k]) for k in w.fieldnames})
    from collections import Counter
    (shard_dir / "summary.json").write_text(json.dumps(
        {"batch": batch, "processed": len(rows),
         "statuses": dict(Counter(r["status"] for r in rows)), "smoke": False}))


def build_root(base, retry_stdout):
    """Two initial rows: one kept BOUNDED, one declared TIMEOUT retried."""
    initial = [raw_row("C_keep", "BOUNDED", BOUNDED, 0),
               raw_row("C_retry", "TIMEOUT", "", None)]
    retry = [raw_row("C_retry", "TIMEOUT", retry_stdout, None)]
    initial_dir = base / "runs/tina_cloud_45127189704/download/tina-results-batch-1"
    retry_dir = base / "runs/tina_cloud_45192651608/download/tina-retry-batch-1"
    write_shard(initial_dir, 1, initial, "tina_batch_1")
    write_shard(retry_dir, 1, retry, "tina_batch_1")
    plan = {"run_id": 45127189704, "expected": 2, "retry_candidates": 1,
            "shards": [{"batch": 1, "state": "COMPLETE_VERDICT_REPLAY", "parsed_rows": 2,
                        "counts": {"BOUNDED": 1, "TIMEOUT": 1}, "retry_ids": ["C_retry"],
                        "raw_sha256": hashlib.sha256(
                            (initial_dir / "tina_batch_1.jsonl.gz").read_bytes()).hexdigest()}]}
    plan_bytes = json.dumps(plan).encode()
    (base / "runs/tina_cloud_45127189704/retry_plan.json").write_bytes(plan_bytes)
    scope = {"source_run": 45127189704,
             "source_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
             "batches": [{"source_batch": 1, "timeout": 120, "ids": ["C_retry"]}]}
    (base / "scope").mkdir(parents=True, exist_ok=True)
    (base / "scope/tina_retry_45127189704.json").write_text(json.dumps(scope))
    import csv as _csv
    merged_path = base / "runs/tina_cloud_45192651608/merged_candidate_verdicts.csv"
    with merged_path.open("w", newline="") as handle:
        w = _csv.DictWriter(handle, fieldnames=["candidate_id", "status", "pnml_sha256", "run_id", "batch"])
        w.writeheader()
        w.writerow({"candidate_id": "C_keep", "status": "BOUNDED",
                    "pnml_sha256": initial[0]["pnml_sha256"], "run_id": "45127189704", "batch": "1"})
        w.writerow({"candidate_id": "C_retry", "status": "TIMEOUT",
                    "pnml_sha256": retry[0]["pnml_sha256"], "run_id": "45192651608", "batch": "1"})
    hasher = _RowHasher()
    for row in initial + retry:
        hasher.update(row)
    ini = _RowHasher()
    for row in initial:
        ini.update(row)
    rep = _RowHasher()
    for row in retry:
        rep.update(row)
    pins = Pins(scope_sha256=hashlib.sha256(json.dumps(scope).encode()).hexdigest(),
                plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
                initial_rows=2, initial_row_digest=ini.hexdigest(),
                retry_rows=1, retry_row_digest=rep.hexdigest(),
                final_raw_counts={"BOUNDED": 2}, recoverable_count=1)
    return pins


class RawTamperNegativeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tina-neg-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_synthetic_root_passes(self):
        pins = build_root(self.tmp, BOUNDED)
        result = replay(self.tmp, pins=pins)
        self.assertEqual(result["final"]["raw_verdict_status_counts"], {"BOUNDED": 2})

    def test_timeout_stdout_flipped_to_unbounded_is_caught(self):
        # The auditor's bypass: declared TIMEOUT stays, CSV/summary/ledger
        # untouched, only the raw stdout verdict flips.
        pins = build_root(self.tmp, UNBOUNDED)
        with self.assertRaisesRegex(RawReplayError, "raw-verdict status counts"):
            replay(self.tmp, pins=pins)

    def test_retry_raw_stderr_tamper_changes_pinned_digest(self):
        pins = build_root(self.tmp, BOUNDED)
        shard = self.tmp / "runs/tina_cloud_45192651608/download/tina-retry-batch-1"
        rows = [json.loads(line) for line in gzip.open(shard / "tina_batch_1.jsonl.gz", "rt")]
        rows[0]["stderr"] = "tampered"
        with gzip.open(shard / "tina_batch_1.jsonl.gz", "wt") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        with self.assertRaisesRegex(RawReplayError, "retry raw row evidence digest mismatch"):
            replay(self.tmp, pins=pins)

    def test_retry_raw_places_tamper_changes_pinned_digest(self):
        pins = build_root(self.tmp, BOUNDED)
        shard = self.tmp / "runs/tina_cloud_45192651608/download/tina-retry-batch-1"
        rows = [json.loads(line) for line in gzip.open(shard / "tina_batch_1.jsonl.gz", "rt")]
        rows[0]["places"] = 999
        with gzip.open(shard / "tina_batch_1.jsonl.gz", "wt") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        # CSV also syncs the lie; the pinned digest must still catch it.
        csv_path = shard / "tina_batch_1.csv"
        csv_path.write_text(csv_path.read_text().replace(",20,16", ",999,16"))
        with self.assertRaisesRegex(RawReplayError, "retry raw row evidence digest mismatch"):
            replay(self.tmp, pins=pins)

    def test_deleted_bounded_verdict_changes_recoverable_set(self):
        pins = build_root(self.tmp, "Tina version 4.0.0\nINPUT NET ---\nparsing\n")
        with self.assertRaisesRegex(RawReplayError, "raw-verdict status counts|recoverable"):
            replay(self.tmp, pins=pins)

    def test_frozen_pins_reject_altered_expectations(self):
        # Cheap proof the count assertions fire on the real frozen root.
        from tina_raw_replay import FROZEN_PINS
        bad = Pins(FROZEN_PINS.scope_sha256, FROZEN_PINS.plan_sha256,
                   FROZEN_PINS.initial_rows, FROZEN_PINS.initial_row_digest,
                   FROZEN_PINS.retry_rows, FROZEN_PINS.retry_row_digest,
                   {"BOUNDED": 104211, "UNBOUNDED": 1, "TIMEOUT": 3308},
                   FROZEN_PINS.recoverable_count)
        with self.assertRaisesRegex(RawReplayError, "raw-verdict status counts"):
            replay(ROOT / "baseline_readonly/e2", pins=bad)


if __name__ == "__main__":
    unittest.main()
