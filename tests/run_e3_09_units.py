"""E3-09: execute all 76,545 decision units (567 configs x 135 specs)."""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/probability'))
from parallel_config_runner import evaluate_config


def load(path):
    with open(path, newline='') as handle:
        return list(csv.DictReader(handle))


def main(out_dir=None):
    out_dir = Path(out_dir or ROOT / 'runs/e3_09')
    out_dir.mkdir(parents=True, exist_ok=True)
    configs = load(ROOT / 'contracts/e3_09/frozen_567_configs.csv')
    specs = load(ROOT / 'contracts/e3_09/frozen_135_specs.csv')
    rows = []
    t0 = time.perf_counter()
    for config in configs:
        rows.extend(evaluate_config(config, specs))
    elapsed = time.perf_counter() - t0
    with (out_dir / 'units_results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['unit_id', 'config_id', 'spec_id',
                                                    'v_P', 'R_delta', 'reason'])
        writer.writeheader()
        writer.writerows(rows)
    from collections import Counter
    summary = {'units': len(rows), 'expected': 567 * 135,
               'v_P_counts': dict(Counter(r['v_P'] for r in rows)),
               'reasons': dict(Counter(r['reason'] for r in rows if r['reason'])),
               'elapsed_seconds': round(elapsed, 2)}
    (out_dir / 'units_results_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
