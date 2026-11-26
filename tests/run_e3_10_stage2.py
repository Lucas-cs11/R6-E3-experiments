"""E3-10 stage-2 deterministic features, models and shared-ID metric entry."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import os
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent')]
from pyscrew_features import extract_features, feature_vector
from pyscrew_metrics_reference import (auroc, balanced_accuracy, brier, nll, risk_coverage,
                                       classification_metrics, stratified_metrics)


def self_test(raw_root=None):
    raw_root = raw_root or os.environ.get('PYSCREW_RAW_JSON_ROOT', '')
    if not raw_root:
        raise ValueError('self-test requires --raw-root or PYSCREW_RAW_JSON_ROOT')
    raw_path = Path(raw_root) / '001_control-group' / 'Ch_000001624346.json'
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


RELEASE = dict(tag='pyscrew-raw-v1', asset='pyscrew_raw_5000.tar.gz',
               sha256='de161758a6918bc70e3b24a0327b5d719b882395df81b5d481071b5abf22d545',
               bytes=61846400)
RANDOM_STATES = {'LogisticRegression': 4101, 'RandomForest': 4102,
                 'HistGradientBoosting': 4103}
METHOD_NAMES = tuple(RANDOM_STATES)


def _read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _feature_data(raw_root, manifest):
    files = {}
    for path in Path(raw_root).rglob('*.json'):
        if path.name in files:
            raise ValueError(f'duplicate raw basename {path.name}')
        files[path.name] = path
    records = []
    errors = []
    for raw in manifest:
        try:
            raw_path = files[raw['file_name']]
            features = extract_features(raw_path.read_text())
            records.append(dict(raw_record_id=raw['run_id'],
                                physical_workpiece_id=raw['workpiece_id'],
                                side=raw['location'], **{'class': raw['physical_class']},
                                split=raw['split'], features=features))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(dict(raw_record_id=raw['run_id'], reason=f'FEATURE_ERROR:{exc}'))
    return records, errors


def _join_records(feature_records, split_plan, labels, outer_rows):
    splits = {row['run_id']: row for row in split_plan}
    label_map = {row['run_id']: row for row in labels}
    target_map = {row['run_id']: int(row['y']) for row in outer_rows
                  if row['variant'] == 'main' and row['NI'] == 'False'}
    joined = []
    for record in feature_records:
        run_id = record['raw_record_id']
        split = splits[run_id]
        label = label_map[run_id]
        if label['workpiece_result'] not in ('OK', 'NOK'):
            continue
        joined.append(dict(record, split=split['split'],
                           completion_status='COMPLETED' if split['completed'] == 'True' else 'NOT_COMPLETED',
                           y_true=target_map.get(run_id)))
    by_workpiece = {}
    for record in joined:
        by_workpiece.setdefault(record['physical_workpiece_id'], set()).add(record['split'])
    leaks = sorted(workpiece for workpiece, values in by_workpiece.items() if len(values) > 1)
    if leaks:
        raise ValueError(f'workpiece split leakage: {leaks[:3]}')
    return joined


def _train(records, outer_rows):
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    fold_map = {row['run_id']: int(row['fold']) for row in outer_rows
                if row['variant'] == 'main' and row['NI'] == 'False'}
    candidates = [row for row in records if row['split'] == 'calibration' and
                  row['raw_record_id'] in fold_map]
    names = sorted(candidates[0]['features'])
    test = []
    predictions = {name: {} for name in METHOD_NAMES}
    fold_train_counts = {}
    degenerate_folds = []
    for fold in sorted(set(fold_map.values())):
        train = [row for row in candidates if fold_map[row['raw_record_id']] != fold]
        current = [row for row in candidates if fold_map[row['raw_record_id']] == fold]
        if not train or not current:
            raise ValueError(f'invalid calibration outer fold {fold}')
        if {row['physical_workpiece_id'] for row in train} & {row['physical_workpiece_id'] for row in current}:
            raise ValueError(f'workpiece leakage in calibration outer fold {fold}')
        x_train = np.array([[row['features'][name] for name in names] for row in train], dtype=float)
        y_train = np.array([row['y_true'] for row in train])
        x_test = np.array([[row['features'][name] for name in names] for row in current], dtype=float)
        models = {
            'LogisticRegression': make_pipeline(
                StandardScaler(),
                LogisticRegression(random_state=RANDOM_STATES['LogisticRegression'],
                                   max_iter=2000, solver='lbfgs')),
            'RandomForest': RandomForestClassifier(random_state=RANDOM_STATES['RandomForest'],
                                                   n_estimators=100, n_jobs=1),
            'HistGradientBoosting': HistGradientBoostingClassifier(
                random_state=RANDOM_STATES['HistGradientBoosting'], max_iter=100, max_depth=3,
                learning_rate=0.1),
        }
        fold_train_counts[fold] = len(train)
        for name, model in models.items():
            if len(set(y_train)) < 2:
                constant = int(y_train[0])
                probabilities = np.full(len(current), float(constant))
                degenerate = dict(fold=fold, model=name, fallback='CONSTANT_CLASS_PRIOR',
                                  constant_class=constant)
                degenerate_folds.append(degenerate)
            else:
                model.fit(x_train, y_train)
                probabilities = model.predict_proba(x_test)[:, 1]
            for row, probability in zip(current, probabilities):
                predictions[name][row['raw_record_id']] = float(probability)
        test.extend(current)
    return test, predictions, fold_train_counts, degenerate_folds


def _evaluate(test, predictions, outer_rows):
    frozen = {row['run_id']: float(row['p']) for row in outer_rows
              if row['variant'] == 'main' and row['NI'] == 'False'}
    common_ids = sorted({row['raw_record_id'] for row in test} & set(frozen))
    if not common_ids:
        raise ValueError('no common valid evaluation IDs')
    by_id = {row['raw_record_id']: row for row in test}
    common = [by_id[run_id] for run_id in common_ids]
    y_true = [row['y_true'] for row in common]
    probability_map = {name: [predictions[name][run_id] for run_id in common_ids]
                       for name in METHOD_NAMES}
    probability_map['frozen_main'] = [frozen[run_id] for run_id in common_ids]
    model_metrics = {}
    for name, probabilities in probability_map.items():
        model_metrics[name] = dict(classification_metrics(y_true, probabilities))
        model_metrics[name]['stratified'] = stratified_metrics(
            [dict(row, probability=probability) for row, probability in zip(common, probabilities)])
    return common, probability_map, model_metrics


def _safe_extract(asset, destination):
    with tarfile.open(asset, 'r:gz') as archive:
        for member in archive.getmembers():
            target = Path(destination, member.name)
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise ValueError(f'unsafe archive member {member.name}')
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as output:
                output.write(source.read())


def _download_release(workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(['gh', 'release', 'download', RELEASE['tag'], '--repo', 'Lucas-cs11/R6-E3-experiments',
                    '--pattern', RELEASE['asset'], '--dir', str(workdir)], check=True)
    asset = workdir / RELEASE['asset']
    if asset.stat().st_size != RELEASE['bytes']:
        raise ValueError('release asset byte count mismatch')
    if hashlib.sha256(asset.read_bytes()).hexdigest() != RELEASE['sha256']:
        raise ValueError('release asset SHA-256 mismatch')
    raw_root = workdir / 'raw_json'
    raw_root.mkdir(exist_ok=True)
    _safe_extract(asset, raw_root)
    return raw_root


def run_pipeline(raw_root, output_dir):
    started, cpu_started = time.perf_counter(), time.process_time()
    manifest = _read_csv(ROOT / 'baseline_readonly/e2/scope/pyscrew_raw_manifest.csv')
    split_plan = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/split_plan.csv')
    labels = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/labels.csv')
    outer = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/outer_predictions.csv')
    feature_records, feature_errors = _feature_data(raw_root, manifest)
    records = _join_records(feature_records, split_plan, labels, outer)
    test, predictions, fold_train_counts, degenerate_folds = _train(records, outer)
    common, probability_map, model_metrics = _evaluate(test, predictions, outer)
    common_ids = {row['raw_record_id'] for row in common}
    excluded = []
    for raw in manifest:
        run_id = raw['run_id']
        if run_id in common_ids:
            continue
        split = next(row for row in split_plan if row['run_id'] == run_id)
        if split['split'] != 'held_out':
            reason = 'NOT_HELD_OUT'
        elif run_id not in {row['run_id'] for row in outer if row['variant'] == 'main' and row['NI'] == 'False'}:
            reason = 'FROZEN_MAIN_NOT_VALID'
        else:
            reason = 'NOT_EVALUABLE_LABEL_OR_FEATURE'
        excluded.append(dict(raw_record_id=run_id, reason=reason))
    excluded.extend(feature_errors)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / 'per_record_predictions.csv'
    fields = ['raw_record_id', 'physical_workpiece_id', 'side', 'class', 'split',
              'completion_status', 'y_true', *METHOD_NAMES, 'frozen_main']
    with csv_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(common):
            writer.writerow({key: row[key] for key in fields[:7]} |
                            {name: probability_map[name][index] for name in fields[7:]})
    ids_sha = hashlib.sha256('\n'.join(row['raw_record_id'] for row in common).encode()).hexdigest()
    result = dict(status='STAGE2_METRICS_COMPUTED', release=RELEASE,
                  split=dict(train='calibration_workpiece_outer5', evaluate='calibration_out_of_fold',
                             fold_train_counts=fold_train_counts, held_out_reserved=2500,
                             prediction_count=len(test), leak_count=0),
                  degenerate_folds=degenerate_folds,
                  common_evaluation=dict(count=len(common), ids_sha256=ids_sha,
                                         rule='all_three_models_and_frozen_main_NI_false'),
                  random_states=RANDOM_STATES, models=model_metrics,
                  excluded=excluded,
                  resources=dict(wall_seconds=time.perf_counter() - started,
                                 cpu_seconds=time.process_time() - cpu_started),
                  per_record_csv=str(csv_path))
    (output_dir / 'stage2_metrics.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'common_count': len(common),
                      'ids_sha256': ids_sha, 'metrics': str(output_dir / 'stage2_metrics.json')},
                     sort_keys=True))
    return result


def verify_saved_outputs(output_dir):
    """Independently recompute saved metrics from per-record predictions."""
    output_dir = Path(output_dir)
    saved = json.loads((output_dir / 'stage2_metrics.json').read_text())
    rows = _read_csv(output_dir / 'per_record_predictions.csv')
    if len(rows) != saved['common_evaluation']['count']:
        raise AssertionError('saved common count differs from prediction CSV')
    for name in (*METHOD_NAMES, 'frozen_main'):
        y_true = [int(row['y_true']) for row in rows]
        probabilities = [float(row[name]) for row in rows]
        expected = classification_metrics(y_true, probabilities)
        for key, value in expected.items():
            if key == 'risk_coverage':
                assert value == saved['models'][name][key]
            elif value is None:
                assert saved['models'][name][key] is None
            else:
                assert abs(value - saved['models'][name][key]) < 1e-12, (name, key)
        expected_strata = stratified_metrics(
            [dict(row, y_true=int(row['y_true']), probability=probability, **{'class': row['class']})
             for row, probability in zip(rows, probabilities)])
        assert expected_strata == saved['models'][name]['stratified'], name
    print(json.dumps({'status': 'INDEPENDENT_METRICS_VERIFIED', 'records': len(rows),
                      'ids_sha256': saved['common_evaluation']['ids_sha256']}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--raw-root')
    parser.add_argument('--workdir', default='/tmp/e3-10-stage2-release')
    parser.add_argument('--output-dir', default=str(ROOT / 'runs/e3_10'))
    args = parser.parse_args(argv)
    if args.self_test:
        self_test(args.raw_root)
    if args.download:
        raw_root = _download_release(args.workdir)
    else:
        raw_root = args.raw_root or os.environ.get('PYSCREW_RAW_JSON_ROOT',
                                                   '/Users/lucas/Downloads/results1005/pyscrew/raw_json')
    if args.run:
        run_pipeline(raw_root, args.output_dir)
    if args.verify:
        verify_saved_outputs(args.output_dir)
    if not args.self_test and not args.run and not args.verify and not args.download:
        parser.error('use --self-test, --run, or --download')


if __name__ == '__main__':
    sys.exit(main())
