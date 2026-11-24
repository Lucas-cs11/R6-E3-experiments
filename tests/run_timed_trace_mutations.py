"""Execute concrete timed-history semantic mutations in isolated E3 copies."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('implementations/subject/timed_trace.py')
MUTANTS = {
    'KEEP_CLOCK_ACROSS_MIDDLE_DISABLE': ('ages.keys() & enabled(mid) & enabled(post)', 'ages.keys() & enabled(post)', 'reset_blocks_old_clock'),
    'IGNORE_IMMEDIATE_PRIORITY': ('if urgent and (elapsed or k not in urgent):', 'if False:', 'ordinary_zero_blocked_by_immediate'),
    'CUT_OFF_READY_HORIZON': ('elif end == ha and not ready:', 'elif end == ha:', 'open_prefix_2'),
    'COMPARE_PATH_IDS_NOT_OMEGA': ('image in inverse and inverse[image] != omega', 'image in inverse', 'test_observation_collision_requires_distinct_omega'),
    'IGNORE_CLAIMED_FIRST_COMPLETION': ('if (None if claimed is None else exact(claimed)) != value:', 'if key != "completion_time" and (None if claimed is None else exact(claimed)) != value:', 'completion_before_fault'),
}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: run_timed_trace_mutations.py NEW_EVIDENCE_DIR')
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True)
    original = (ROOT / SOURCE).read_text()
    results = []
    for name, mutation in [('UNMODIFIED', None), *MUTANTS.items()]:
        d = out / name
        source = original
        if mutation:
            old, new, expected = mutation
            if original.count(old) != 1:
                raise ValueError(f'mutation anchor is not unique: {name}')
            source = original.replace(old, new, 1)
        (d / SOURCE.parent).mkdir(parents=True)
        (d / SOURCE).write_text(source)
        for name_to_copy in ('oracles/independent/absolute_schedule.py', 'tests/test_timed_trace.py', 'models/regression/timed_trace.json'):
            dest = d / name_to_copy
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name_to_copy, dest)
        (d / 'mutation.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile=str(SOURCE), tofile=str(SOURCE))))
        cmd = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_timed_trace.py', '-v']
        proc = subprocess.run(cmd, cwd=d, capture_output=True, timeout=60)
        (d / 'stdout.jsonl').write_bytes(proc.stdout)
        (d / 'stderr.log').write_bytes(proc.stderr)
        (d / 'exit_code').write_text(f'{proc.returncode}\n')
        err = proc.stderr.decode(errors='replace')
        failures = [line for line in err.splitlines() if line.startswith('FAIL: ')]
        ok = proc.returncode == 0 if not mutation else (proc.returncode == 1 and
            any(expected in line for line in failures) and 'ERROR:' not in err and 'Ran 5 tests' in err)
        results.append({'case': name, 'command': cmd, 'exit_code': proc.returncode, 'expected_detector': expected if mutation else None,
                        'observed_assertions': failures, 'as_expected': ok, 'source_sha256': hashlib.sha256((d / SOURCE).read_bytes()).hexdigest()})
    (out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return int(not all(row['as_expected'] for row in results))


if __name__ == '__main__':
    sys.exit(main())
