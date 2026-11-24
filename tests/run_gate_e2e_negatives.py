"""End-to-end accept_e3 negative runs: six tamper classes on one disposable root."""
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DISPOSABLE = ROOT / 'runs/math_p0/content_gate/disposable'
OUT = ROOT / 'runs/math_p0/gate_semantic_v3/e2e_negatives'
RETRY_SHARD = DISPOSABLE / 'runs/tina_cloud_45192651608/download/tina-retry-batch-180'
INITIAL_SHARD = DISPOSABLE / 'runs/tina_cloud_45127189704/download/tina-results-batch-1'
R604 = DISPOSABLE / 'runs/g2_r604/results.csv'
RECOVERABLE = 'RMT_m10_j6_ops4_wip4_u0.1_f4_w0.5_a0.1'


def run_gate(name):
    proc = subprocess.run([sys.executable, '-B', 'tests/accept_e3.py', '--evidence-root', str(DISPOSABLE)],
                          cwd=ROOT, capture_output=True, timeout=300)
    (OUT / f'{name}.stdout.json').write_bytes(proc.stdout)
    (OUT / f'{name}.stderr.log').write_bytes(proc.stderr)
    (OUT / f'{name}.exit_code').write_text(f'{proc.returncode}\n')
    issues = []
    if proc.stdout:
        issues = [i['code'] for i in json.loads(proc.stdout)['issues']]
    return proc.returncode, issues


def load_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def save_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Rebuild the disposable root from the frozen snapshot: the previous
    # content_gate copy is itself a doubly-tampered fixture.
    if DISPOSABLE.exists():
        shutil.rmtree(DISPOSABLE)
    shutil.copytree(ROOT / 'baseline_readonly/e2', DISPOSABLE)
    for path in DISPOSABLE.rglob('*'):
        if path.is_dir():
            continue
        path.chmod(path.stat().st_mode | 0o200)
    results = []
    retry_raw = RETRY_SHARD / 'tina_batch_180.jsonl.gz'
    retry_csv = RETRY_SHARD / 'tina_batch_180.csv'
    initial_raw = INITIAL_SHARD / 'tina_batch_1.jsonl.gz'
    backups = {}
    for path in (retry_raw, retry_csv, initial_raw, R604):
        backups[path] = path.read_bytes()
    cases = [
        ('e2e_timeout_stdout_unbounded', retry_raw, lambda b: b.replace(
            b'"stdout": "Tina version 4.0.0 -- 07/04/26 -- LAAS/CNRS\\n\\nmode -R',
            b'"stdout": "Tina version 4.0.0 -- 07/04/26 -- LAAS/CNRS\\n\\nmode -R', 1)),
    ]
    # Case 1: recoverable row's bounded verdict flipped to unbounded (declared stays TIMEOUT).
    rows = load_rows(retry_raw)
    hit = [r for r in rows if r['candidate_id'] == RECOVERABLE]
    assert len(hit) == 1 and 'bounded' in hit[0]['stdout']
    hit[0]['stdout'] = hit[0]['stdout'].replace('\nbounded\n', '\nunbounded\n')
    save_rows(retry_raw, rows)
    rc, issues = run_gate('e2e_timeout_stdout_unbounded')
    results.append(dict(case='e2e_timeout_stdout_unbounded', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'TINA_RAW_REPLAY_MISMATCH' in issues))
    retry_raw.write_bytes(backups[retry_raw])

    # Case 2: retry stderr tamper.
    rows = load_rows(retry_raw)
    rows[0]['stderr'] = 'tampered-by-negative-test'
    save_rows(retry_raw, rows)
    rc, issues = run_gate('e2e_retry_stderr_tamper')
    results.append(dict(case='e2e_retry_stderr_tamper', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'TINA_RAW_REPLAY_MISMATCH' in issues))
    retry_raw.write_bytes(backups[retry_raw])

    # Case 3: retry places tamper with CSV synced.
    rows = load_rows(retry_raw)
    old_places = rows[0]['places']
    rows[0]['places'] = old_places + 1
    save_rows(retry_raw, rows)
    text = retry_csv.read_text()
    retry_csv.write_text(text.replace(f',{old_places},', f',{old_places + 1},', 1))
    rc, issues = run_gate('e2e_retry_places_csv_synced')
    results.append(dict(case='e2e_retry_places_csv_synced', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'TINA_RAW_REPLAY_MISMATCH' in issues))
    retry_raw.write_bytes(backups[retry_raw])
    retry_csv.write_bytes(backups[retry_csv])

    # Case 4: bounded verdict deleted from a recoverable row.
    rows = load_rows(retry_raw)
    hit = [r for r in rows if r['candidate_id'] == RECOVERABLE]
    hit[0]['stdout'] = 'Tina version 4.0.0\nINPUT NET ---\nparsing interrupted\n'
    save_rows(retry_raw, rows)
    rc, issues = run_gate('e2e_bounded_verdict_deleted')
    results.append(dict(case='e2e_bounded_verdict_deleted', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'TINA_RAW_REPLAY_MISMATCH' in issues))
    retry_raw.write_bytes(backups[retry_raw])

    # Case 5: initial-shard raw metadata tamper.
    rows = load_rows(initial_raw)
    rows[0]['transitions'] = rows[0]['transitions'] + 1
    save_rows(initial_raw, rows)
    rc, issues = run_gate('e2e_initial_raw_metadata_tamper')
    results.append(dict(case='e2e_initial_raw_metadata_tamper', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'TINA_RAW_REPLAY_MISMATCH' in issues))
    initial_raw.write_bytes(backups[initial_raw])

    # Case 6: R604 ledger semantic flip (status/PASS kept).
    data = R604.read_bytes()
    R604.write_bytes(data.replace(b'COMPLETED_IN_TIME,COMPLETED_IN_TIME,3', b'COMPLETED_IN_TIME,VIOLATION,3', 1))
    rc, issues = run_gate('e2e_r604_outcome_flip')
    results.append(dict(case='e2e_r604_outcome_flip', exit_code=rc, issues=issues,
                        detected=rc == 1 and 'R604_PN_WITNESS_REPLAY_MISMATCH' in issues))
    R604.write_bytes(backups[R604])

    # Restore-verify: clean root passes again.
    rc, issues = run_gate('e2e_restored_control')
    results.append(dict(case='e2e_restored_control', exit_code=rc, issues=issues,
                        detected=rc == 0 and not issues))
    (OUT / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return int(not all(r['detected'] for r in results))


if __name__ == '__main__':
    sys.exit(main())
