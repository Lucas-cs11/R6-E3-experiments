"""E3-04 engine-path integration tests on JSON and real generated PN models."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('implementations/subject', 'oracles/independent',
                                       'baseline_readonly/e2/implementations/generator_compat')]
from engine_interface import from_generator_net
from engine_paths import METHODS, run_path
from engine_paths_reference import reference_engine
from src.benchmarks.rmt_fms_generator import generate_rmt_fms


def load(name):
    return json.loads((ROOT / 'models/regression' / name).read_text())


def generated(adjustable=0.1):
    params = dict(n_machines=2, n_parts=1, ops_per_part=2, wip_bound=1,
                  unobservable_ratio=0.1, fault_locations=1, interval_width_factor=0.5,
                  adjustable_ratio=adjustable)
    net, L, H = generate_rmt_fms(**params, seed=0, machine_capacity=1,
                                 n_configs=2, repair_domain='standard')
    return from_generator_net(net, L, H)


class EnginePathTests(unittest.TestCase):
    def test_fixture_four_real_paths_and_independent_lp(self):
        model = load('engine_fixture.json')
        reference = reference_engine(model, 100)
        self.assertEqual(reference['verdict'], '1')
        outputs = []
        for method in METHODS:
            result = run_path(model, method, 100)
            outputs.append(result)
            self.assertEqual(result['status'], 'EXHAUSTED_FOR_MODEL')
            self.assertEqual(result['verdict'], '1')
            self.assertEqual(result['verdict'], reference['verdict'])
            self.assertTrue(result['trace'])
            self.assertEqual(result['certificate']['model_sha256'], reference['model_sha256'])
            self.assertGreater(result['resources']['peak_memory_bytes'], 0)
            self.assertGreaterEqual(result['resources']['wall_seconds'], 0)
            self.assertGreaterEqual(result['resources']['cpu_seconds'], 0)
            self.assertEqual(result['resources']['states'], result['path_stats']['state_classes'])
            self.assertEqual(result['resources']['lp_calls'], result['path_stats']['lp_calls'])
        self.assertEqual({row['path_stats']['ablation_point'] for row in outputs},
                         {'NONE', 'NO_PRUNING', 'NO_SYNC', 'NO_ENVELOPE'})
        self.assertEqual(len({tuple(row['call_sequence']) for row in outputs}), 4)
        self.assertEqual(len({json.dumps(row['path_stats'], sort_keys=True) for row in outputs}), 4)

    def test_two_real_generated_models_match_independent_reference(self):
        for adjustable in (0.1, 0.25):
            model = generated(adjustable)
            reference = reference_engine(model, 1000)
            outputs = [run_path(model, method, 1000) for method in METHODS]
            with self.subTest(adjustable=adjustable, reference=reference['status']):
                self.assertEqual(reference['status'], 'EXHAUSTED_FOR_MODEL')
                self.assertEqual({row['verdict'] for row in outputs}, {reference['verdict']})
                full = next(row for row in outputs if row['method'] == 'FULL_HISTORY')
                main = next(row for row in outputs if row['method'] == 'MAIN')
                self.assertGreater(full['path_stats']['expansions'], main['path_stats']['expansions'])
                self.assertGreaterEqual(main['path_stats']['sync_pairs'], 0)
                self.assertTrue(all(row['trace'] for row in outputs))

    def test_infinite_loop_and_invalid_model_stay_unresolved_or_unsupported(self):
        model = load('engine_loop.json')
        reference = reference_engine(model, 8)
        self.assertEqual(reference['verdict'], 'PERP')
        for method in METHODS:
            result = run_path(model, method, 8)
            self.assertEqual(result['status'], 'UNRESOLVED')
            self.assertEqual(result['verdict'], 'PERP')
            self.assertGreater(result['certificate']['pending'], 0)
            self.assertNotEqual(result['verdict'], '1')
        invalid = copy.deepcopy(load('engine_fixture.json'))
        for transition in invalid['transitions'].values():
            transition['is_fault'] = False
        for method in METHODS:
            result = run_path(invalid, method, 100)
            self.assertEqual(result['status'], 'UNSUPPORTED')
            self.assertEqual(result['verdict'], 'PERP')
            self.assertTrue(result['reasons'])
    def test_sync_and_envelope_have_distinct_numeric_effects(self):
        model = load('engine_split.json')
        reference = reference_engine(model, 100)
        outputs = {method: run_path(model, method, 100) for method in METHODS}
        self.assertEqual({row['verdict'] for row in outputs.values()}, {reference['verdict']})
        self.assertEqual(reference['verdict'], '0')
        self.assertEqual(outputs['MAIN']['path_stats']['sync_pairs'], 1)
        self.assertEqual(outputs['NO_ENVELOPE']['path_stats']['sync_pairs'], 1)
        self.assertEqual(outputs['NO_SYNC']['path_stats']['sync_pairs'], 0)
        self.assertEqual(outputs['FULL_HISTORY']['path_stats']['sync_pairs'], 0)
        self.assertEqual(outputs['MAIN']['path_stats']['envelope_splits'], 1)
        self.assertEqual(outputs['NO_ENVELOPE']['path_stats']['envelope_splits'], 0)
        self.assertGreater(outputs['FULL_HISTORY']['path_stats']['expansions'],
                           outputs['MAIN']['path_stats']['expansions'])
        self.assertEqual(len({tuple(row['call_sequence']) for row in outputs.values()}), 4)
        print(json.dumps({method: row['path_stats'] for method, row in outputs.items()}, sort_keys=True))
    def test_duplicate_fault_histories_remain_proven_after_sync(self):
        model = load('engine_duplicate_fault.json')
        reference = reference_engine(model, 100)
        self.assertEqual(reference['verdict'], '1')
        outputs = [run_path(model, method, 100) for method in METHODS]
        self.assertEqual({row['verdict'] for row in outputs}, {'1'})
        main = next(row for row in outputs if row['method'] == 'MAIN')
        self.assertEqual(main['path_stats']['sync_pairs'], 1)
        self.assertEqual(len(main['trace']), 1)


if __name__ == '__main__':
    unittest.main()


class ConstraintBudgetTests(unittest.TestCase):
    def test_heavy_model_returns_unresolved_fast_with_constraint_budget(self):
        import time
        net, L, H = generate_rmt_fms(n_machines=3, n_parts=2, ops_per_part=4, wip_bound=2,
                                     unobservable_ratio=0.3, fault_locations=2,
                                     interval_width_factor=1.0, adjustable_ratio=0.25,
                                     seed=0, machine_capacity=1, n_configs=2,
                                     repair_domain='standard')
        model = from_generator_net(net, L, H)
        start = time.perf_counter()
        result = run_path(model, 'MAIN', 2000, constraint_budget=50000)
        elapsed = time.perf_counter() - start
        self.assertEqual(result['status'], 'UNRESOLVED')
        self.assertLess(elapsed, 30)
