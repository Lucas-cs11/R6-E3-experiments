"""E3-04 engine interface tests: real generator models and fixture rejection."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat')]
from engine_interface import check_applicability, from_generator_net  # noqa: E402
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402


class EngineInterfaceTests(unittest.TestCase):
    def real_model(self):
        net, L, H = generate_rmt_fms(n_machines=2, n_parts=1, ops_per_part=2, wip_bound=1,
                                     unobservable_ratio=0.1, fault_locations=1,
                                     interval_width_factor=0.5, adjustable_ratio=0.1,
                                     seed=0, machine_capacity=1, n_configs=2,
                                     repair_domain='standard')
        return from_generator_net(net, L, H)

    def test_real_generator_model_supported(self):
        model = self.real_model()
        got = check_applicability(model)
        print(json.dumps({'case': 'real_model', 'supported': got['supported'],
                          'reasons': got['reasons'], 'fault_count': len(got['fault_transitions'])}))
        self.assertTrue(got['supported'])
        self.assertEqual(got['reasons'], [])
        self.assertTrue(got['fault_transitions'])
        self.assertEqual(sorted(got['checked_fields']),
                         ['H', 'L', 'arcs', 'completion_markings', 'initial_marking',
                          'places', 'transitions'])

    def test_each_missing_field_named(self):
        model = self.real_model()
        for field in ('places', 'transitions', 'initial_marking', 'completion_markings', 'L', 'H'):
            broken = {k: v for k, v in model.items() if k != field}
            got = check_applicability(broken)
            self.assertFalse(got['supported'])
            self.assertIn(field, [r['field'] for r in got['reasons']], field)

    def test_invalid_values_named_with_observed(self):
        model = self.real_model()
        broken = json.loads(json.dumps(model))
        name = next(iter(broken['transitions']))
        broken['transitions'][name]['interval'] = ['2', '1']
        broken['transitions'][name]['pre'] = {'ghost_place': 1}
        broken['L'] = '0'
        got = check_applicability(broken)
        fields = [r['field'] for r in got['reasons']]
        self.assertFalse(got['supported'])
        self.assertIn(f'transitions.{name}.interval', fields)
        self.assertIn(f'transitions.{name}.pre', fields)
        self.assertIn('L/H', fields)
        interval_reason = next(r for r in got['reasons'] if r['field'].endswith('.interval'))
        self.assertEqual(interval_reason['observed'], ['2', '1'])

    def test_immediate_with_nonzero_interval_rejected(self):
        model = self.real_model()
        broken = json.loads(json.dumps(model))
        name = next(iter(broken['transitions']))
        broken['transitions'][name]['immediate'] = True
        broken['transitions'][name]['interval'] = ['0', '1']
        got = check_applicability(broken)
        self.assertFalse(got['supported'])
        self.assertTrue(any('immediate' in r['field'] for r in got['reasons']))

    def test_initial_completion_rejected(self):
        model = self.real_model()
        broken = json.loads(json.dumps(model))
        broken['completion_markings'] = [dict(broken['initial_marking'])]
        got = check_applicability(broken)
        self.assertFalse(got['supported'])
        reason = next(r for r in got['reasons'] if r['field'] == 'completion_markings')
        self.assertIn('initial marking already satisfies', reason['detail'])

    def test_no_fault_transition_rejected(self):
        model = self.real_model()
        for t in model['transitions'].values():
            t['is_fault'] = False
        got = check_applicability(model)
        self.assertFalse(got['supported'])
        self.assertTrue(any('fault' in r['detail'] for r in got['reasons']))


if __name__ == '__main__':
    unittest.main()
