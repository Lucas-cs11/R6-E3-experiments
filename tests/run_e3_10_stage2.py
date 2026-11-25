"""E3-10 stage-2 deterministic features, models and shared-ID metric entry."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from pyscrew_features import extract_features, feature_vector
from pyscrew_metrics_reference import auroc, balanced_accuracy, brier, nll, risk_coverage


def self_test(raw_root=None):
    raw_path = Path(raw_root or '/Users/lucas/Downloads/results1005/pyscrew/raw_json/001_control-group/Ch_000001624346.json')
    raw = json.loads(raw_path.read_text())
    first = extract_features(raw)
    second = extract_features(raw)
    assert first == second
    assert first['step0_sample_count'] == 93
    assert abs(first['step0_duration'] - 0.1104) < 1e-12
    assert first['step0_angle_end'] == 101.25
    assert first['step0_torque_end'] == 0.13
    assert feature_vector(raw) == feature_vector(raw)
    y = [0, 0, 1, 1]
    p = [0.1, 0.4, 0.35, 0.9]
    assert auroc(y, p) == 0.75
    assert auroc(y, list(reversed(p))) == 0.25
    assert abs(brier(y, p) - 0.150625) < 1e-12
    assert nll(y, p) > 0
    assert balanced_accuracy(y, p) == 0.75
    coverage = risk_coverage(y, p, tolerances=(0.15,))
    assert coverage[0]['covered'] == 2
    assert coverage[0]['coverage'] == 0.5
    assert coverage[0]['risk'] == 0
    print(json.dumps({'status': 'SELF_TEST_PASS', 'feature_count': len(first),
                      'brier': brier(y, p), 'auroc': auroc(y, p),
                      'coverage_at_0_15': coverage[0]}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--raw-root')
    args = parser.parse_args(argv)
    if args.self_test:
        self_test(args.raw_root)
        return 0
    parser.error('use --self-test or the full-pipeline implementation in the next logical block')


if __name__ == '__main__':
    sys.exit(main())
