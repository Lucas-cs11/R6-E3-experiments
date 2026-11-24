"""E3 content gate, initial scope: two inherited P0 evidence objects only."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/subject'))
sys.path.insert(0, str(ROOT / 'oracles/independent'))
from r604_replay import GENERATOR_SHA256 as R604_GENERATOR_SHA256, replay_cases
from tina_raw_replay import RawReplayError, replay as replay_tina_raw
FROZEN = ROOT / 'baseline_readonly/e2'
PINS = {
    'runs/g2_r604/results.csv': 'd935ac78dac59217e39dc2a7632247d3845ec226689702a021e24139e28b6771',
    'runs/tina_cloud_45192651608/merged_candidate_verdicts.csv': 'a614e8074b944890b82d7b0672f96e48a022d12a315b119f4ad6dd305153c682',
}


def read_rows(root, rel):
    raw = (root / rel).read_bytes()
    return hashlib.sha256(raw).hexdigest(), list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline='')))


def check(root):
    issues, checked = [], []
    for index, (rel, pin) in enumerate(PINS.items()):
        try:
            expected_digest, expected = read_rows(FROZEN, rel)
            if expected_digest != pin:
                issues.append(dict(file=rel, code='FROZEN_PIN_MISMATCH'))
                continue
            actual_digest, actual = read_rows(root, rel)
            field = ('subject_outcome', 'status')[index]
            key = ('test_id', 'candidate_id')[index]
            checked.append(dict(file=rel, rows=len(actual), sha256=actual_digest))
            if actual_digest != pin:
                issues.append(dict(file=rel, code='EVIDENCE_CONTENT_MISMATCH'))
            actual_by_id = {row[key]: row[field] for row in actual}
            expected_by_id = {row[key]: row[field] for row in expected}
            if len(actual_by_id) != len(actual) or actual_by_id.keys() != expected_by_id.keys():
                issues.append(dict(file=rel, code='ROW_IDENTITY_MISMATCH'))
            differences = [(k, v, actual_by_id[k]) for k,v in expected_by_id.items()
                           if k in actual_by_id and v != actual_by_id[k]]
            if differences:
                issues.append(dict(file=rel, code=('R604_SUBJECT_OUTCOME_CHANGED', 'TINA_STRICT_STATUS_CHANGED')[index],
                                   count=len(differences), examples=differences[:10]))
            if index == 0:
                generator_rel = 'tests/run_g2_r604.py'
                generator = (root / generator_rel).read_bytes()
                if hashlib.sha256(generator).hexdigest() != R604_GENERATOR_SHA256:
                    issues.append(dict(file=generator_rel, code='R604_GENERATOR_CONTENT_MISMATCH'))
                replayed = replay_cases((FROZEN / generator_rel).read_bytes())
                semantic_differences = []
                by_id = {row['test_id']: row for row in actual}
                for test_id, witness in replayed.items():
                    row = by_id.get(test_id)
                    if row is None:
                        continue
                    expected_values = {
                        'expected': witness['outcome'],
                        'subject_outcome': witness['outcome'],
                        'oracle_outcome': witness['outcome'],
                        'subject_deadline': witness['post_fault_deadline'],
                        'endpoint_exact': str(witness['endpoint_exact_pass']),
                        'status': 'PASS',
                    }
                    for field, expected_value in expected_values.items():
                        if row.get(field) != expected_value:
                            semantic_differences.append([test_id, field, expected_value, row.get(field)])
                if semantic_differences:
                    issues.append(dict(file=rel, code='R604_PN_WITNESS_REPLAY_MISMATCH',
                                       count=len(semantic_differences), examples=semantic_differences[:10]))
                checked.append(dict(file=generator_rel, sha256=R604_GENERATOR_SHA256,
                                    replayed_histories=len(replayed),
                                    scope='RECONSTRUCTED_WITNESSES_NOT_RECOVERED_ORIGINAL_PN'))
            if index == 1:
                try:
                    tina = replay_tina_raw(root)
                    checked.append(dict(file='tina_raw_replay', scope=tina['analysis_scope'],
                                        initial_shards=tina['initial']['shards'],
                                        retry_shards=tina['retry']['shards'],
                                        retry_rows=tina['retry']['rows'],
                                        final_rows=tina['final']['rows'],
                                        declared_status_counts=tina['final']['status_counts'],
                                        recoverable_timeout_with_verdict=tina['final']['recoverable_timeout_with_verdict'],
                                        strict_merged_exact_match=tina['final']['strict_merged_exact_match']))
                except (RawReplayError, OSError, json.JSONDecodeError) as exc:
                    issues.append(dict(file=rel, code='TINA_RAW_REPLAY_MISMATCH', detail=str(exc)))
        except (OSError, UnicodeError, csv.Error, KeyError, ValueError) as exc:
            issues.append(dict(file=rel, code='EVIDENCE_UNREADABLE', detail=str(exc)))
    return dict(status='FAIL' if issues else 'PASS', scope='TWO_INHERITED_P0_EVIDENCE_OBJECTS_ONLY',
                checked=checked, issues=issues)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, required=True)
    result = check(parser.parse_args().evidence_root)
    print(json.dumps(result, indent=2))
    raise SystemExit(int(result['status'] != 'PASS'))
