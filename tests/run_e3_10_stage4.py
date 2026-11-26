"""Deterministic E3-10 stage-4 sensitivity and uncertainty report."""
import csv
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'), str(ROOT / 'oracles/independent'), str(ROOT / 'tests')]
from pyscrew_features import extract_features
from pyscrew_metrics_reference import auroc, balanced_accuracy, classification_metrics, nll, brier
from run_e3_10_stage2 import _read_csv, _feature_data, _join_records

COMMON_COUNT = 1421
HGB = 'HistGradientBoosting'
MODELS = ('LogisticRegression', 'RandomForest', HGB, 'frozen_main')
OUT = ROOT / 'reports/e3_10'


def _predictions():
    with (ROOT / 'runs/e3_10/per_record_predictions.csv').open(newline='') as handle:
        return list(csv.DictReader(handle))


def _input_type_strata(rows):
    result = _strata(rows, 'input_type')
    for key in ('MISSING', 'EMPTY'):
        if key not in result:
            result[key] = dict(count=0, auroc=None, brier=None, nll=None,
                               balanced_accuracy=None, risk_coverage=[])
    return dict(sorted(result.items()))


def _auc(records, probability_key=HGB):
    return auroc([int(row['y_true']) for row in records],
                 [float(row[probability_key]) for row in records])


def _strata(records, field):
    groups = {}
    for row in records:
        groups.setdefault(row[field], []).append(row)
    return {key: dict(count=len(group),
                      **classification_metrics([int(row['y_true']) for row in group],
                                               [float(row[HGB]) for row in group]))
            for key, group in sorted(groups.items())}


def _train_hgb(records, outer_rows, seed, binarize=False):
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier

    fold_map = {row['run_id']: int(row['fold']) for row in outer_rows
                if row['variant'] == 'main' and row['NI'] == 'False'}
    candidates = [row for row in records if row['split'] == 'calibration' and
                  row['raw_record_id'] in fold_map]
    names = sorted(candidates[0]['features'])
    continuous = [name for name in names if name not in ('step_count',) and
                  not name.endswith(('_missing', '_empty', 'sample_count'))]
    predictions = {}
    for fold in sorted(set(fold_map.values())):
        train = [row for row in candidates if fold_map[row['raw_record_id']] != fold]
        current = [row for row in candidates if fold_map[row['raw_record_id']] == fold]
        if {row['physical_workpiece_id'] for row in train} & {row['physical_workpiece_id'] for row in current}:
            raise ValueError(f'workpiece leakage in fold {fold}')
        x_train = np.array([[row['features'][name] for name in names] for row in train], dtype=float)
        x_test = np.array([[row['features'][name] for name in names] for row in current], dtype=float)
        y_train = np.array([row['y_true'] for row in train])
        if binarize:
            positions = [names.index(name) for name in continuous]
            medians = np.median(x_train[:, positions], axis=0)
            x_train[:, positions] = (x_train[:, positions] > medians).astype(float)
            x_test[:, positions] = (x_test[:, positions] > medians).astype(float)
        if len(set(y_train)) < 2:
            probabilities = np.full(len(current), float(y_train[0]))
        else:
            model = HistGradientBoostingClassifier(random_state=seed, max_iter=100,
                                                   max_depth=3, learning_rate=0.1)
            model.fit(x_train, y_train)
            probabilities = model.predict_proba(x_test)[:, 1]
        for row, probability in zip(current, probabilities):
            predictions[row['raw_record_id']] = float(probability)
    return predictions


def _bootstrap(records, seed=4105, repetitions=200):
    by_workpiece = {}
    for row in records:
        by_workpiece.setdefault(row['physical_workpiece_id'], []).append(row)
    keys = sorted(by_workpiece)
    rng = random.Random(seed)
    samples = {key: [] for key in ('auroc', 'brier', 'nll', 'balanced_accuracy')}
    for _ in range(repetitions):
        chosen = [rng.choice(keys) for _ in keys]
        sample = [row for workpiece in chosen for row in by_workpiece[workpiece]]
        y = [int(row['y_true']) for row in sample]
        p = [float(row[HGB]) for row in sample]
        values = dict(auroc=auroc(y, p), brier=brier(y, p), nll=nll(y, p),
                      balanced_accuracy=balanced_accuracy(y, p))
        for key, value in values.items():
            if value is not None:
                samples[key].append(value)

    def interval(values):
        ordered = sorted(values)
        if not ordered:
            return None
        def percentile(fraction):
            position = fraction * (len(ordered) - 1)
            lower = int(position)
            upper = min(lower + 1, len(ordered) - 1)
            weight = position - lower
            return ordered[lower] * (1 - weight) + ordered[upper] * weight
        return [percentile(0.025), percentile(0.975)]
    return {key: interval(values) for key, values in samples.items()}


def run_stage4():
    saved = json.loads((ROOT / 'runs/e3_10/stage2_metrics.json').read_text())
    rows = _predictions()
    if len(rows) != COMMON_COUNT:
        raise AssertionError(f'expected {COMMON_COUNT} common IDs, got {len(rows)}')
    id_sha = hashlib.sha256('\n'.join(row['raw_record_id'] for row in rows).encode()).hexdigest()
    if id_sha != saved['common_evaluation']['ids_sha256']:
        raise AssertionError('common ID hash changed')
    outer = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/outer_predictions.csv')
    fold_map = {row['run_id']: int(row['fold']) for row in outer
                if row['variant'] == 'main' and row['NI'] == 'False'}
    for row in rows:
        row['fold'] = fold_map[row['raw_record_id']]
        raw = json.loads(next(Path('/Users/lucas/Downloads/results1005/pyscrew/raw_json').rglob(
            f"Ch_{int(row['raw_record_id']):012d}.json")).read_text())
        features = extract_features(raw)
        row['input_type'] = ('MISSING' if any(features[f'step{i}_missing'] for i in range(4)) else
                             'EMPTY' if any(features[f'step{i}_empty'] for i in range(4)) else 'COMPLETE')

    manifest = _read_csv(ROOT / 'baseline_readonly/e2/scope/pyscrew_raw_manifest.csv')
    labels = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/labels.csv')
    split = _read_csv(ROOT / 'baseline_readonly/e2/chapter6/split_plan.csv')
    feature_records, feature_errors = _feature_data('/Users/lucas/Downloads/results1005/pyscrew/raw_json', manifest)
    records = _join_records(feature_records, split, labels, outer)
    original = _train_hgb(records, outer, 4103)
    coarse = _train_hgb(records, outer, 4103, binarize=True)
    for row in rows:
        row['hgb_recomputed'] = original[row['raw_record_id']]
        row['hgb_binarized'] = coarse[row['raw_record_id']]
    original_auc = _auc(rows, 'hgb_recomputed')
    coarse_auc = _auc(rows, 'hgb_binarized')
    if abs(original_auc - saved['models'][HGB]['auroc']) > 1e-9:
        raise AssertionError('HGB deterministic rerun does not reproduce stage-2 AUROC')

    thresholds = {}
    for model in MODELS:
        thresholds[model] = {str(threshold): balanced_accuracy(
            [int(row['y_true']) for row in rows], [float(row[model]) for row in rows], threshold)
            for threshold in (0.3, 0.5, 0.7)}
    seed_results = {}
    for seed in (4103, 4201, 4301):
        probabilities = _train_hgb(records, outer, seed)
        for row in rows:
            row[f'hgb_seed_{seed}'] = probabilities[row['raw_record_id']]
        seed_results[str(seed)] = _auc(rows, f'hgb_seed_{seed}')
    seed_values = list(seed_results.values())
    seed_summary = dict(values=seed_results, min=min(seed_values), max=max(seed_values),
                        range=max(seed_values) - min(seed_values))
    result = dict(
        status='STAGE4_SENSITIVITY_COMPUTED',
        common_evaluation=dict(count=COMMON_COUNT, ids_sha256=id_sha,
                               rule='all_three_models_and_frozen_main_NI_false'),
        guardrail='不得用32工况子集支撑全量严格风险结论',
        stratified={
            'input_type': _input_type_strata(rows),
            'class': _strata(rows, 'class'),
            'side': _strata(rows, 'side'),
            'completion_status': _strata(rows, 'completion_status'),
            'fold': _strata(rows, 'fold'),
        },
        median_binarization=dict(model=HGB, random_state=4103,
                                 continuous_rule='fold-training median, value > median',
                                 original_auroc=original_auc, binarized_auroc=coarse_auc,
                                 delta_auroc=coarse_auc - original_auc),
        threshold_sensitivity=thresholds,
        seed_sensitivity=seed_summary,
        bootstrap=dict(seed=4105, repetitions=200, unit='physical_workpiece',
                       confidence_interval_95=_bootstrap(rows)),
    )
    return result


def _markdown(result):
    strata_counts = {key: result['stratified']['input_type'][key]['count'] for key in
                     ('COMPLETE', 'MISSING', 'EMPTY')}
    return f"""# E3-10 stage-4 sensitivity and uncertainty

Common denominator: **{COMMON_COUNT} shared valid IDs** (sha256 `{result['common_evaluation']['ids_sha256']}`).
The held_out 2500 workpieces remain untouched by outer-fold training.  **不得用32工况子集支撑全量严格风险结论**.

## Stratification

Input types (COMPLETE/MISSING/EMPTY): {strata_counts}.  Other strata cover 16 observed classes, left/right, COMPLETED, and five outer folds.  The JSON stores exact AUROC/Brier/NLL/balanced accuracy/risk-coverage per input type, class, side, completion status and outer fold in `stage4_sensitivity.json`.

## Deterministic sensitivity

- Median binarization: AUROC {result['median_binarization']['original_auroc']:.9f} → {result['median_binarization']['binarized_auroc']:.9f}, delta {result['median_binarization']['delta_auroc']:.9f}.
- Thresholds 0.3/0.5/0.7 are recomputed on the same 1421 IDs, never on separate subsets.
- HGB random_state 4103/4201/4301 gives AUROC range {result['seed_sensitivity']['range']:.9f} (min {result['seed_sensitivity']['min']:.9f}, max {result['seed_sensitivity']['max']:.9f}).
- Workpiece bootstrap uses seed 4105, 200 repetitions, both sides retained.  95% percentile intervals are listed in JSON.

All choices are fixed in source.  No time-dependent value or random seed is hidden.
"""


def self_test():
    result = run_stage4()
    assert result['common_evaluation']['count'] == COMMON_COUNT
    assert len(result['bootstrap']['confidence_interval_95']) == 4
    assert len(result['seed_sensitivity']['values']) == 3
    assert len(result['threshold_sensitivity']) == 4
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'stage4_sensitivity.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    (OUT / 'stage4_sensitivity.md').write_text(_markdown(result))
    print(json.dumps({'status': result['status'], 'common_count': COMMON_COUNT,
                      'binarization_delta': result['median_binarization']['delta_auroc'],
                      'seed_range': result['seed_sensitivity']['range'],
                      'bootstrap': result['bootstrap']['confidence_interval_95']}))


if __name__ == '__main__':
    self_test()
