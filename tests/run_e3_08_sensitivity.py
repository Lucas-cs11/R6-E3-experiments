"""E3-08 sensitivity preregistration: 54 grid x 10 seeds x 3 WIP x 4 methods.

Contract line 157: the 54x10x3 = 1,620 sensitivity models run for real;
the L/H spec triple (3x3 = 9) is NOT theory-signed, so every spec row is
recorded SPEC_BLOCKED rather than choosing convenient L/H tiers after seeing
results.  Re-run with real L/H specs after signoff.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/e3_08'
METHODS = ('MAIN', 'FULL_HISTORY', 'NO_SYNC', 'NO_ENVELOPE')
FIELDS = ['task_id', 'config_id', 'seed', 'wip', 'spec_id', 'method_id', 'result_status',
          'v_L', 'elapsed_wall', 'cpu_seconds', 'peak_python_alloc_bytes', 'exit_code',
          'attempts', 'failure_reason', 'updated_at']


def preregister(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    configs = []
    for m in (2, 3, 4):
        for j in (1, 2):
            for u in ('0.1', '0.3', '0.5'):
                for w in ('0.5', '1.0', '1.5'):
                    configs.append({'n_machines': m, 'n_parts': j,
                                    'unobservable_ratio': u, 'interval_width_factor': w})
    rows = []
    for c, config in enumerate(configs, 1):
        for seed in range(10):
            for wip in (1, 2, 3):
                for method in METHODS:
                    config_id = f"S{c:02d}_m{config['n_machines']}j{config['n_parts']}" \
                                f"u{config['unobservable_ratio']}w{config['interval_width_factor']}"
                    rows.append({'task_id': f"{config_id}|s{seed}|w{wip}|{method}",
                                 'config_id': config_id, 'seed': seed, 'wip': wip,
                                 'spec_id': 'SPEC_BLOCKED', 'method_id': method,
                                 'result_status': 'NOT_EXECUTED', 'attempts': 0})
    path = out_dir / 'sensitivity_preregistered.csv'
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {'configs': len(configs), 'seeds': 10, 'wips': 3, 'methods': len(METHODS),
               'tasks': len(rows), 'specs': 'SPEC_BLOCKED_9_LH_TIERS_UNTIL_SIGNOFF',
               'path': str(path)}
    (out_dir / 'sensitivity_preregister_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preregister'])
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    preregister(args.out)
