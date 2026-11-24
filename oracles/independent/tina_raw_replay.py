#!/usr/bin/env python3
"""Independent, read-only replay of the frozen two-round untimed TINA ledger.

The classifier reads raw stdout/stderr and process metadata.  In particular,
TIMEOUT is an unresolved execution outcome, never an UNBOUNDED verdict.  This
module has no timed-Petri-net inference path.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple


RETRY_RUN_ID = 45192651608
CSV_FIELDS = ["candidate_id", "status", "returncode", "pnml_sha256", "places", "transitions"]
MERGED_FIELDS = ["candidate_id", "status", "pnml_sha256", "run_id", "batch"]
VERDICT_RE = re.compile(r"^(bounded|unbounded)\s*$", re.MULTILINE)


class RawReplayError(ValueError):
    """Raw evidence, identities, or the strict merged ledger disagree."""


class Pins:
    """Trusted digests binding the frozen raw evidence population.

    ``row_digest`` covers, per raw JSONL row: candidate id, declared status,
    returncode, PNML digest, places/transitions, and stdout/stderr hashes.
    Any edit to a retry shard's raw output, stderr, or size metadata changes
    the digest even when the declared status and merged ledger stay fixed.
    """

    def __init__(self, scope_sha256, plan_sha256, initial_rows, initial_row_digest,
                 retry_rows, retry_row_digest, final_raw_counts, recoverable_count):
        self.scope_sha256 = scope_sha256
        self.plan_sha256 = plan_sha256
        self.initial_rows = initial_rows
        self.initial_row_digest = initial_row_digest
        self.retry_rows = retry_rows
        self.retry_row_digest = retry_row_digest
        self.final_raw_counts = dict(final_raw_counts)
        self.recoverable_count = recoverable_count


FROZEN_PINS = Pins(
    scope_sha256="070ee51312036e9a4c7d93372276165841c4aec99064daaf24ed027f946e0e90",
    plan_sha256="bdc3260e9037c400cb7d02d36ebdc1bf997830baf6916854054664c4b6aef0f6",
    initial_rows=78443,
    initial_row_digest="d68a1fbf93191c42013ec31a85178960156e81ec3f0032d214bef40535d1e427",
    retry_rows=55003,
    retry_row_digest="2657b4f802d0bb83f3911f417dc0ff7ee33394cf1c072f904a31fdc68b1abd1b",
    final_raw_counts={"BOUNDED": 104212, "TIMEOUT": 3308},
    recoverable_count=160,
)


class _RowHasher:
    """Incremental digest over canonical per-row raw evidence records."""

    def __init__(self):
        self._hash = hashlib.sha256()
        self.rows = 0

    def update(self, raw: Mapping[str, Any]) -> None:
        record = {
            "candidate_id": raw["candidate_id"],
            "declared": raw["status"],
            "returncode": raw.get("returncode"),
            "pnml_sha256": raw["pnml_sha256"],
            "places": raw.get("places"),
            "transitions": raw.get("transitions"),
            "stdout_sha256": hashlib.sha256(raw["stdout"].encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(raw["stderr"].encode("utf-8")).hexdigest(),
        }
        self._hash.update(json.dumps(record, sort_keys=True).encode("utf-8"))
        self._hash.update(b"\n")
        self.rows += 1

    def hexdigest(self) -> str:
        return self._hash.hexdigest()


def _reachability_verdict(stdout: str) -> Optional[str]:
    marker = "REACHABILITY ANALYSIS"
    if marker not in stdout:
        return None
    section = stdout.split(marker, 1)[1]
    for later in ("LIVENESS ANALYSIS", "ANALYSIS COMPLETED"):
        if later in section:
            section = section.split(later, 1)[0]
    matches = VERDICT_RE.findall(section)
    if len(matches) > 1:
        raise RawReplayError(f"multiple reachability verdicts: {matches}")
    return matches[0].upper() if matches else None


def classify_raw_record(record: Mapping[str, Any]) -> str:
    """Classify one raw record from stdout/stderr, not from declared status."""
    return classify_raw_record_detailed(record)[0]


def classify_raw_record_detailed(record: Mapping[str, Any]) -> Tuple[str, List[str]]:
    """Return (status, annotations) for one raw TINA record.

    A TIMEOUT row whose reachability section already printed a verdict is
    a *recoverable* TIMEOUT: the boundedness question is answered, but the
    overall solver run timed out during a later phase.  The boundedness
    verdict is returned; the annotation preserves the original timeout.
    A TIMEOUT with no verdict stays TIMEOUT and must never be read as
    UNBOUNDED.
    """
    if not isinstance(record, Mapping):
        raise RawReplayError("raw JSONL row is not an object")
    stdout = record.get("stdout")
    stderr = record.get("stderr")
    declared = record.get("status")
    returncode = record.get("returncode")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise RawReplayError("stdout and stderr must be strings")
    verdict = _reachability_verdict(stdout)
    completed = "ANALYSIS COMPLETED" in stdout
    annotations: List[str] = []
    if verdict is not None:
        if declared not in (verdict, "TIMEOUT"):
            raise RawReplayError(f"raw status {declared!r} conflicts with stdout verdict {verdict}")
        if declared != verdict and verdict in ("BOUNDED", "UNBOUNDED"):
            annotations.append("DECLARED_TIMEOUT_AFTER_REACHABILITY_VERDICT")
        if declared == verdict:
            if returncode != 0:
                raise RawReplayError(f"stdout verdict {verdict} has returncode {returncode!r}")
            if verdict == "BOUNDED" and not completed:
                raise RawReplayError("BOUNDED verdict lacks ANALYSIS COMPLETED")
        elif returncode is not None:
            raise RawReplayError(f"declared TIMEOUT row has returncode {returncode!r}")
        return verdict, annotations
    if declared == "TIMEOUT" and returncode is None and not completed:
        # No reachability verdict exists.  The null returncode and declared
        # control outcome distinguish an interrupted run from a solver error.
        return "TIMEOUT", annotations
    raise RawReplayError(
        f"no certified stdout verdict: declared={declared!r}, returncode={returncode!r}, "
        f"completed={completed}, stderr={stderr[:160]!r}"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(record: Mapping[str, Any]) -> Tuple[str, str]:
    candidate = record.get("candidate_id")
    digest = record.get("pnml_sha256")
    if not isinstance(candidate, str) or not candidate:
        raise RawReplayError("missing candidate_id")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RawReplayError(f"invalid pnml_sha256 for {candidate}")
    return candidate, digest


def _compare_csv_raw(csv_row: Mapping[str, str], raw: Mapping[str, Any], status: str, where: str) -> None:
    candidate, digest = _identity(raw)
    expected = {
        "candidate_id": candidate,
        "status": status,
        "returncode": "" if raw.get("returncode") is None else str(raw.get("returncode")),
        "pnml_sha256": digest,
        "places": str(raw.get("places")),
        "transitions": str(raw.get("transitions")),
    }
    actual = {field: csv_row.get(field) for field in CSV_FIELDS}
    if actual != expected:
        raise RawReplayError(f"CSV/JSONL mismatch at {where}: {actual!r} != {expected!r}")
    if csv_row.get("status") != raw.get("status"):
        raise RawReplayError(f"CSV/raw declared status mismatch at {where}")


def _iter_complete_shard(shard_dir: Path, batch: int, hasher: Optional["_RowHasher"] = None) -> Iterator[Dict[str, str]]:
    csv_path = shard_dir / f"tina_batch_{batch}.csv"
    raw_path = shard_dir / f"tina_batch_{batch}.jsonl.gz"
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as csv_handle, gzip.open(raw_path, "rt", encoding="utf-8") as raw_handle:
            reader = csv.DictReader(csv_handle)
            if reader.fieldnames != CSV_FIELDS:
                raise RawReplayError(f"unexpected CSV header at {csv_path}: {reader.fieldnames}")
            for line_number, line in enumerate(raw_handle, 1):
                where = f"{raw_path}:{line_number}"
                try:
                    raw = json.loads(line)
                    status, annotations = classify_raw_record_detailed(raw)
                    csv_row = next(reader)
                except StopIteration as exc:
                    raise RawReplayError(f"CSV ends before JSONL at {where}") from exc
                except json.JSONDecodeError as exc:
                    raise RawReplayError(f"invalid JSONL at {where}: {exc}") from exc
                if hasher is not None:
                    hasher.update(raw)
                _compare_csv_raw(csv_row, raw, raw["status"], where)
                candidate, digest = _identity(raw)
                yield {"candidate_id": candidate, "status": status,
                       "declared_status": raw["status"], "annotations": annotations,
                       "pnml_sha256": digest}
            try:
                extra = next(reader)
            except StopIteration:
                extra = None
            if extra is not None:
                raise RawReplayError(f"CSV has rows beyond JSONL at {csv_path}: {extra}")
    except (EOFError, gzip.BadGzipFile) as exc:
        raise RawReplayError(f"complete shard is truncated: {raw_path}: {exc}") from exc


def _scan_incomplete_prefix(raw_path: Path, hasher: Optional["_RowHasher"] = None) -> Tuple[List[Dict[str, str]], Optional[str]]:
    rows: List[Dict[str, str]] = []
    issue: Optional[str] = None
    try:
        with gzip.open(raw_path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    issue = f"JSONDecodeError: {exc}"
                    break
                if hasher is not None:
                    hasher.update(raw)
                status, annotations = classify_raw_record_detailed(raw)
                candidate, digest = _identity(raw)
                rows.append({"candidate_id": candidate, "status": status,
                             "declared_status": raw["status"], "annotations": annotations,
                             "pnml_sha256": digest})
    except (EOFError, gzip.BadGzipFile) as exc:
        issue = f"{type(exc).__name__}: {exc}"
    return rows, issue


def _check_summary(path: Path, batch: int, rows: int, counts: Counter) -> None:
    summary = json.loads(path.read_text(encoding="utf-8"))
    expected = {"batch": batch, "processed": rows, "statuses": dict(counts), "smoke": False}
    if summary != expected:
        raise RawReplayError(f"summary mismatch at {path}: {summary!r} != {expected!r}")


def _observe_identities(observed: Dict[str, str], rows: Sequence[Mapping[str, str]], where: str) -> None:
    for row in rows:
        candidate, digest = row["candidate_id"], row["pnml_sha256"]
        previous = observed.setdefault(candidate, digest)
        if previous != digest:
            raise RawReplayError(f"PNML identity changes for {candidate} at {where}")


def replay(e2_root: Path, retry_run_id: int = RETRY_RUN_ID, pins: Pins = FROZEN_PINS) -> Dict[str, Any]:
    """Replay frozen initial and retry shards and compare every merged field."""
    e2_root = Path(e2_root)
    plan_path = e2_root / "runs/tina_cloud_45127189704/retry_plan.json"
    scope_path = e2_root / "scope/tina_retry_45127189704.json"
    plan_bytes = plan_path.read_bytes()
    scope_bytes = scope_path.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != pins.plan_sha256:
        raise RawReplayError("retry_plan.json does not match the trusted frozen digest")
    if hashlib.sha256(scope_bytes).hexdigest() != pins.scope_sha256:
        raise RawReplayError("retry scope does not match the trusted frozen digest")
    plan = json.loads(plan_bytes)
    scope = json.loads(scope_bytes)
    if scope.get("source_run") != plan.get("run_id"):
        raise RawReplayError("retry scope/source run mismatch")
    if scope.get("source_plan_sha256") != hashlib.sha256(plan_bytes).hexdigest():
        raise RawReplayError("retry scope does not bind the supplied retry_plan")
    initial_hasher = _RowHasher()
    retry_hasher = _RowHasher()

    initial_root = e2_root / f"runs/tina_cloud_{plan['run_id']}/download"
    retry_root = e2_root / f"runs/tina_cloud_{retry_run_id}/download"
    scope_batches = scope.get("batches")
    if not isinstance(scope_batches, list) or not scope_batches:
        raise RawReplayError("retry scope has no batches")

    scope_by_source: Dict[int, List[Dict[str, Any]]] = {}
    retry_id_to_batch: Dict[str, int] = {}
    for retry_batch, group in enumerate(scope_batches, 1):
        source_batch = group.get("source_batch")
        ids = group.get("ids")
        if not isinstance(source_batch, int) or not isinstance(ids, list) or not ids:
            raise RawReplayError(f"invalid retry scope batch {retry_batch}")
        if len(set(ids)) != len(ids) or not all(isinstance(value, str) and value for value in ids):
            raise RawReplayError(f"duplicate/invalid retry id in scope batch {retry_batch}")
        scope_by_source.setdefault(source_batch, []).append(group)
        for candidate in ids:
            if candidate in retry_id_to_batch:
                raise RawReplayError(f"retry id appears in multiple scope batches: {candidate}")
            retry_id_to_batch[candidate] = retry_batch

    expected_retry_ids = set(retry_id_to_batch)
    if len(expected_retry_ids) != plan.get("retry_candidates"):
        raise RawReplayError("retry_candidates does not equal unique scope ids")

    observed_identities: Dict[str, str] = {}
    initial_kept: Dict[str, Dict[str, str]] = {}
    initial_raw_counts: Counter = Counter()
    initial_accepted_counts: Counter = Counter()
    initial_raw_rows = 0
    excluded_prefix_rows = 0
    complete_batches: List[int] = []
    incomplete_batches: List[int] = []
    initial_retry_ids: Dict[int, set] = {}

    for shard in plan.get("shards", []):
        batch = shard["batch"]
        shard_dir = initial_root / f"tina-results-batch-{batch}"
        raw_path = shard_dir / f"tina_batch_{batch}.jsonl.gz"
        actual_sha = _sha256_file(raw_path)
        if actual_sha != shard.get("raw_sha256"):
            raise RawReplayError(f"initial raw SHA mismatch at {raw_path}")
        if shard.get("state") == "COMPLETE_VERDICT_REPLAY":
            complete_batches.append(batch)
            rows = list(_iter_complete_shard(shard_dir, batch, initial_hasher))
            counts = Counter(row["declared_status"] for row in rows)
            if len(rows) != shard.get("parsed_rows") or counts != Counter(shard.get("counts", {})):
                raise RawReplayError(f"initial complete shard count mismatch at batch {batch}")
            _check_summary(shard_dir / "summary.json", batch, len(rows), counts)
            _observe_identities(observed_identities, rows, f"initial batch {batch}")
            initial_raw_rows += len(rows)
            initial_raw_counts.update(counts)
            initial_accepted_counts.update(counts)
            retry_ids = set(shard.get("retry_ids", []))
            initial_retry_ids[batch] = retry_ids
            timeout_ids = {row["candidate_id"] for row in rows if row["declared_status"] == "TIMEOUT"}
            if retry_ids != timeout_ids:
                raise RawReplayError(f"complete-shard retry ids are not exactly its declared TIMEOUT ids: batch {batch}")
            for row in rows:
                candidate = row["candidate_id"]
                if candidate in initial_kept:
                    raise RawReplayError(f"duplicate initial candidate {candidate}")
                if candidate not in retry_ids:
                    initial_kept[candidate] = {
                        **row,
                        "run_id": str(plan["run_id"]),
                        "batch": str(batch),
                    }
        elif shard.get("state") == "INCOMPLETE_RETRY":
            incomplete_batches.append(batch)
            rows, issue = _scan_incomplete_prefix(raw_path, initial_hasher)
            counts = Counter(row["declared_status"] for row in rows)
            if len(rows) != shard.get("parsed_rows") or counts != Counter(shard.get("counts", {})):
                raise RawReplayError(f"initial incomplete-prefix count mismatch at batch {batch}")
            planned_issue = shard.get("issue")
            if (issue is None) != (planned_issue is None) or (issue and not issue.startswith(planned_issue.split(":", 1)[0] + ":")):
                raise RawReplayError(f"prefix issue mismatch at batch {batch}: {issue!r} != {planned_issue!r}")
            _observe_identities(observed_identities, rows, f"initial prefix batch {batch}")
            initial_raw_rows += len(rows)
            initial_raw_counts.update(counts)
            excluded_prefix_rows += len(rows)
            retry_ids = set(shard.get("retry_ids", []))
            initial_retry_ids[batch] = retry_ids
        else:
            raise RawReplayError(f"unknown initial shard state at batch {batch}: {shard.get('state')}")

        source_groups = scope_by_source.get(batch, [])
        scope_ids = {candidate for group in source_groups for candidate in group["ids"]}
        if scope_ids != initial_retry_ids[batch]:
            raise RawReplayError(f"retry_plan/scope id mismatch for source batch {batch}")

    planned_retry_batches = {b for b, ids in initial_retry_ids.items() if ids}
    if set(scope_by_source) != planned_retry_batches:
        raise RawReplayError("retry scope source batches differ from retry_plan")
    if (initial_hasher.rows != pins.initial_rows
            or initial_hasher.hexdigest() != pins.initial_row_digest):
        raise RawReplayError(
            f"initial raw row evidence digest mismatch: rows={initial_hasher.rows}, "
            f"digest={initial_hasher.hexdigest()}")

    retry_rows: Dict[str, Dict[str, str]] = {}
    retry_counts: Counter = Counter()
    for retry_batch, group in enumerate(scope_batches, 1):
        shard_dir = retry_root / f"tina-retry-batch-{retry_batch}"
        rows = list(_iter_complete_shard(shard_dir, retry_batch, retry_hasher))
        counts = Counter(row["declared_status"] for row in rows)
        _check_summary(shard_dir / "summary.json", retry_batch, len(rows), counts)
        expected_ids = set(group["ids"])
        actual_ids = {row["candidate_id"] for row in rows}
        if len(rows) != len(expected_ids) or actual_ids != expected_ids:
            raise RawReplayError(f"retry shard id coverage mismatch at batch {retry_batch}")
        _observe_identities(observed_identities, rows, f"retry batch {retry_batch}")
        for row in rows:
            candidate = row["candidate_id"]
            if candidate in retry_rows:
                raise RawReplayError(f"duplicate retry candidate {candidate}")
            retry_rows[candidate] = {**row, "run_id": str(retry_run_id), "batch": str(retry_batch)}
        retry_counts.update(counts)

    if (retry_hasher.rows != pins.retry_rows
            or retry_hasher.hexdigest() != pins.retry_row_digest):
        raise RawReplayError(
            f"retry raw row evidence digest mismatch: rows={retry_hasher.rows}, "
            f"digest={retry_hasher.hexdigest()}")
    if set(retry_rows) != expected_retry_ids:
        raise RawReplayError("retry raw rows do not equal retry scope ids")
    overlap = set(initial_kept) & set(retry_rows)
    if overlap:
        raise RawReplayError(f"initial/retry merged overlap: {sorted(overlap)[:3]}")
    # The historical merged ledger was assembled from *declared* statuses.
    # Rebuild that exact view for tamper detection; separately report the
    # raw-verdict view, which upgrades recoverable TIMEOUT rows whose
    # reachability section already answered boundedness.
    merged = {**initial_kept, **retry_rows}
    if len(merged) != plan.get("expected"):
        raise RawReplayError(f"replayed population {len(merged)} != expected {plan.get('expected')}")
    declared_counts = Counter(row["declared_status"] for row in merged.values())
    raw_counts = Counter(row["status"] for row in merged.values())
    recoverable = sorted(row["candidate_id"] for row in merged.values()
                         if row["declared_status"] == "TIMEOUT" and row["status"] != "TIMEOUT")
    if dict(raw_counts) != pins.final_raw_counts:
        raise RawReplayError(
            f"raw-verdict status counts differ from frozen expectation: {dict(raw_counts)}")
    if len(recoverable) != pins.recoverable_count:
        raise RawReplayError(
            f"recoverable TIMEOUT-with-verdict population changed: {len(recoverable)} "
            f"!= {pins.recoverable_count}")
    if any(row["status"] == "UNBOUNDED" for row in merged.values()):
        raise RawReplayError("UNBOUNDED appeared in the replayed population")
    ledger_rows = [{"candidate_id": k, "status": v["declared_status"], "pnml_sha256": v["pnml_sha256"],
                    "run_id": v["run_id"], "batch": v["batch"]} for k, v in merged.items()]

    merged_path = e2_root / f"runs/tina_cloud_{retry_run_id}/merged_candidate_verdicts.csv"
    with merged_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MERGED_FIELDS:
            raise RawReplayError(f"unexpected merged header: {reader.fieldnames}")
        strict_rows = list(reader)
    replayed_rows = [ledger_rows[i] for i in sorted(range(len(ledger_rows)),
                                                    key=lambda i: ledger_rows[i]["candidate_id"])]
    strict_by_id = {}
    for row in strict_rows:
        if row["candidate_id"] in strict_by_id:
            raise RawReplayError(f"duplicate strict ledger id {row['candidate_id']}")
        strict_by_id[row["candidate_id"]] = row
    replay_by_id = {row["candidate_id"]: row for row in replayed_rows}
    if len(strict_by_id) != len(strict_rows) or set(strict_by_id) != set(replay_by_id):
        raise RawReplayError(
            f"strict merged id coverage mismatch: strict={len(strict_rows)}, replay={len(replayed_rows)}")
    mismatches = [(k, strict_by_id[k], replay_by_id[k])
                  for k in strict_by_id if strict_by_id[k] != replay_by_id[k]]
    if mismatches:
        raise RawReplayError(f"strict merged content mismatch: {len(mismatches)} rows, first={mismatches[0]}")
    if Counter(row["status"] for row in strict_rows) != declared_counts:
        raise RawReplayError("strict merged status counts differ from declared replay")

    return {
        "status": "PASS",
        "analysis_scope": "UNTIMED_P_T_ONLY_NO_TIMED_PROMOTION",
        "initial": {
            "run_id": plan["run_id"],
            "shards": len(plan["shards"]),
            "complete_shards": complete_batches,
            "incomplete_shards": incomplete_batches,
            "raw_rows": initial_raw_rows,
            "raw_status_counts": dict(initial_raw_counts),
            "accepted_rows": sum(initial_accepted_counts.values()),
            "accepted_status_counts": dict(initial_accepted_counts),
            "excluded_prefix_rows": excluded_prefix_rows,
            "retained_in_merged": len(initial_kept),
        },
        "retry": {
            "run_id": retry_run_id,
            "shards": len(scope_batches),
            "rows": len(retry_rows),
            "status_counts": dict(retry_counts),
        },
        "final": {
            "rows": len(merged),
            "unique_candidate_ids": len(merged),
            "status_counts": dict(declared_counts),
            "raw_verdict_status_counts": dict(raw_counts),
            "recoverable_timeout_with_verdict": len(recoverable),
            "recoverable_examples": recoverable[:10],
            "strict_merged_exact_match": True,
            "strict_merged_sha256": _sha256_file(merged_path),
        },
        "checks": {
            "initial_raw_sha256": True,
            "raw_stdout_stderr_classification": True,
            "csv_jsonl_identity": True,
            "retry_plan_scope_identity": True,
            "declared_ledger_exact_replay": True,
            "timeout_not_unbounded": True,
            "untimed_not_promoted_to_timed": True,
        },
        "advisories": ([
            f"{len(recoverable)} retry TIMEOUT rows already contain a bounded reachability verdict; "
            "the historical ledger conservatively kept TIMEOUT. Recoverable, not tampering.",
        ] if recoverable else []) + [
            "UNBOUNDED never appears in any raw shard; the merged ledger contains no UNBOUNDED row.",
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e2-root", type=Path, required=True, help="frozen R6 E2 workspace root")
    parser.add_argument("--retry-run-id", type=int, default=RETRY_RUN_ID)
    args = parser.parse_args(argv)
    try:
        result = replay(args.e2_root, args.retry_run_id)
    except (RawReplayError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
