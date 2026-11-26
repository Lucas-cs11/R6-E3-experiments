# E3-10 stage-4 sensitivity and uncertainty

Common denominator: **1421 shared valid IDs** (sha256 `bac92f1af0557331ca6f772817d67bfb6e421c74bda590ad37974e1d929ee3dd`).
The held_out 2500 workpieces remain untouched by outer-fold training.  **不得用32工况子集支撑全量严格风险结论**.

## Stratification

Input types (COMPLETE/MISSING/EMPTY): {'COMPLETE': 1421, 'MISSING': 0, 'EMPTY': 0}.  Other strata cover 16 observed classes, left/right, COMPLETED, and five outer folds.  The JSON stores exact AUROC/Brier/NLL/balanced accuracy/risk-coverage per input type, class, side, completion status and outer fold in `stage4_sensitivity.json`.

## Deterministic sensitivity

- Median binarization: AUROC 0.858795745 → 0.793500437, delta -0.065295308.
- Thresholds 0.3/0.5/0.7 are recomputed on the same 1421 IDs, never on separate subsets.
- HGB random_state 4103/4201/4301 gives AUROC range 0.000000000 (min 0.858795745, max 0.858795745).
- Workpiece bootstrap uses seed 4105, 200 repetitions, both sides retained.  95% percentile intervals are listed in JSON.

All choices are fixed in source.  No time-dependent value or random seed is hidden.
