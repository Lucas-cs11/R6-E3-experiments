"""A deliberately wrong weight rule in both research implementations.

The third check uses hand-derived root branch odds, not either terminal-law implementation.
"""
import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'models/regression/immediate_mass.json'
SOURCES = {
    'implementations/probability/immediate_mass.py': ("arcs(t['post']), F(t['weight']),", "arcs(t['post']), F(1),"),
    'oracles/independent/immediate_mass_reference.py': ("[F(t['weight']) for t in enabled]", "[F(1) for t in enabled]"),
}
PROBE = '''import json
import sys
from fractions import Fraction as F
from pathlib import Path
sys.path[:0] = ['implementations/probability', 'oracles/independent']
from immediate_mass import propagate
from immediate_mass_reference import distribution
net = json.loads(Path('models/regression/immediate_mass.json').read_bytes())
forward = propagate(net, 100)
reference = distribution(net)
actual = {(bool(r['hypothesis']), r['terminal'], tuple(r['word'])): F(r['mass']) for r in forward['categories']}
root = forward['events'][0]
root_mass = {r['transition']: F(r['mass']) for r in root['children']}
# Hand calculation for the fixed fixture: odds 2:1:1, total 4.
expected = {'fault': F(1,2), 'normal': F(1,4), 'extra': F(1,4)}
result = {'agreement': actual == reference, 'conserved': sum(actual.values()) == sum(reference.values()) == 1,
          'root_odds_match': root_mass == expected, 'observed_root': {k:str(v) for k,v in root_mass.items()},
          'expected_root': {k:str(v) for k,v in expected.items()}, 'forward': forward,
          'reference': [[int(i), t, w, str(v)] for (i,t,w),v in sorted(reference.items())]}
print(json.dumps(result))
if not result['agreement'] or not result['conserved']:
    print('BASELINE_COMPARISON_FAILED', file=sys.stderr)
    sys.exit(2)
if not result['root_odds_match']:
    print('EXTERNAL_ROOT_WEIGHT_ODDS_MISMATCH', file=sys.stderr)
    sys.exit(1)
'''


def main(output):
    out = Path(output).resolve()
    out.mkdir(parents=True)
    summary = []
    for case, mutate in [('UNMODIFIED', False), ('BOTH_IGNORE_WEIGHTS', True)]:
        d = out / case
        d.mkdir()
        items = {}
        for rel, (old, new) in SOURCES.items():
            base = (ROOT / rel).read_text()
            if base.count(old) != 1:
                raise ValueError(f'nonunique mutation anchor: {rel}')
            changed = base.replace(old, new, 1) if mutate else base
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(changed)
            items[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            (d / (p.name + '.patch')).write_text(''.join(difflib.unified_diff(
                base.splitlines(True), changed.splitlines(True), fromfile=rel, tofile=rel)))
        p = d / MODEL
        p.parent.mkdir(parents=True)
        p.write_bytes((ROOT / MODEL).read_bytes())
        (d / 'probe.py').write_text(PROBE)
        argv = [sys.executable, '-B', 'probe.py']
        r = subprocess.run(argv, cwd=d, capture_output=True, timeout=30)
        (d / 'stdout.json').write_bytes(r.stdout)
        (d / 'stderr.log').write_bytes(r.stderr)
        (d / 'exit_code').write_text(f'{r.returncode}\n')
        observed = json.loads(r.stdout) if r.stdout else {}
        passed = (r.returncode == int(mutate) and observed.get('agreement') is True
                  and observed.get('conserved') is True and observed.get('root_odds_match') is (not mutate)
                  and r.stderr == (b'EXTERNAL_ROOT_WEIGHT_ODDS_MISMATCH\n' if mutate else b''))
        summary.append(dict(case=case, as_expected=passed, exit_code=r.returncode,
                            agreement=observed.get('agreement'), conserved=observed.get('conserved'),
                            root_odds_match=observed.get('root_odds_match'), command=argv,
                            source_sha256=items, model_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return int(not all(r['as_expected'] for r in summary))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: run_shared_mass_mutation.py NEW_OUTPUT_DIR')
    raise SystemExit(main(sys.argv[1]))
