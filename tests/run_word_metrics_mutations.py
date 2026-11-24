"""Run isolated source mutations against the finite word-metrics regressions."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('implementations/probability/immediate_metrics.py')
MUTANTS = {
    'LEAK_TERMINAL_LABEL': ("joint[tuple(row['word'])]", "joint[(row['terminal'], *row['word'])]", 'test_internal_terminal_type_is_not_observed'),
    'STRICT_RELIABILITY_THRESHOLD': ('max(a,b) >= (1-delta)*mix', 'max(a,b) > (1-delta)*mix', 'test_exact_boundary_and_enumerated_rules'),
    'USE_JOINT_AS_CONDITIONAL': ('(1-pi1)*mass[0]/q[0], pi1*mass[1]/q[1]', '(1-pi1)*mass[0], pi1*mass[1]', 'test_exact_boundary_and_enumerated_rules'),
    'EMIT_METRICS_ON_UNRESOLVED': ('        return binding\n', "        return {**binding, 'Pe': '0'} if binding['status'] == 'UNRESOLVED' else binding\n", 'test_unresolved_and_invalid_inputs'),
    'USE_MAX_FOR_ERROR': ('error += min(a,b)', 'error += max(a,b)', 'test_exact_boundary_and_enumerated_rules'),
}
FILES = ('implementations/probability/immediate_mass.py', 'implementations/probability/immediate_evidence.py',
         'oracles/independent/immediate_mass_reference.py', 'tests/test_immediate_metrics.py',
         'models/regression/immediate_mass.json')


def main(output):
    output = Path(output).resolve()
    output.mkdir(parents=True)
    original = (ROOT / SOURCE).read_text()
    results = []
    cmd = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_immediate_metrics.py', '-v']
    for name, mutant in [('UNMODIFIED', None), *MUTANTS.items()]:
        run = output / name
        for rel in FILES:
            dest = run / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)
        changed, detector = original, None
        if mutant:
            before, after, detector = mutant
            if original.count(before) != 1:
                raise ValueError(f'nonunique mutation anchor: {name}')
            changed = original.replace(before, after, 1)
        (run / SOURCE).write_text(changed)
        (run / 'mutation.patch').write_text(''.join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True), fromfile=str(SOURCE), tofile=str(SOURCE))))
        proc = subprocess.run(cmd, cwd=run, capture_output=True, timeout=60)
        (run / 'stdout.jsonl').write_bytes(proc.stdout)
        (run / 'stderr.log').write_bytes(proc.stderr)
        (run / 'exit_code').write_text(f'{proc.returncode}\n')
        stderr = proc.stderr.decode(errors='replace')
        assertions = [s for s in stderr.splitlines() if s.startswith('FAIL: ')]
        ok = ('Ran 4 tests' in stderr and (proc.returncode == 0 if not mutant else
              proc.returncode == 1 and 'ERROR:' not in stderr and any(detector in s for s in assertions)))
        results.append(dict(case=name, exit_code=proc.returncode, expected_detector=detector,
                            observed_assertions=assertions, as_expected=ok, command=cmd,
                            source_sha256=hashlib.sha256((run / SOURCE).read_bytes()).hexdigest()))
    (output / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps([{k:r[k] for k in ('case', 'exit_code', 'as_expected')} for r in results]))
    return int(not all(r['as_expected'] for r in results))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: run_word_metrics_mutations.py NEW_OUTPUT_DIR')
    raise SystemExit(main(sys.argv[1]))
