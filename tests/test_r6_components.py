"""Real-PN integration evidence for R6-01 and R6-02 (batch 1)."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'implementations/probability'),
                str(ROOT / 'oracles/independent')]
from r6_components import make_acceptance_record, run_case
from r6_components_reference import reference_case


def history(*events, end):
    return {'fires': [{'transition': name, 'at': at} for name, at in events], 'end': end}


def load(name):
    return json.loads((ROOT / 'models/regression' / name).read_text())


class R6ComponentBatch1Tests(unittest.TestCase):
    def compare(self, component, model, case):
        subject = run_case(component, model, case)
        reference = reference_case(component, model, case)
        self.assertEqual(subject['status'], reference['status'], case['case_id'])
        if case['kind'] == 'timed' and subject['status'] == 'REPLAYED_HISTORY':
            for key in ('terminal', 'outcome', 'first_fault_time', 'completion_time',
                        'endpoint_enabled_to_fire'):
                self.assertEqual(subject[key], reference[key], (case['case_id'], key))
        if case['kind'] == 'mass':
            for key in ('resolved', 'unresolved', 'categories'):
                self.assertEqual(subject[key], reference[key], (case['case_id'], key))
        return subject, reference

    def test_r601_clock_reset_priority_and_weighted_roots(self):
        model = load('r601_clock_reset.json')
        cases = [
            dict(case_id='r601_reset_then_complete', kind='timed', role='POSITIVE',
                 history=history(('x', 1), ('imm', 1), ('Y', 3), end=3)),
            dict(case_id='r601_old_clock_early', kind='timed', role='NEGATIVE',
                 history=history(('x', 1), ('imm', 1), ('Y', 2), end=2)),
            dict(case_id='r601_immediate_priority', kind='timed', role='NEGATIVE',
                 history=history(('x', 1), ('Y', 3), end=3)),
        ]
        positive, _ = self.compare('R6-01', model, cases[0])
        self.assertEqual(positive['outcome'], 'COMPLETED_IN_TIME')
        self.assertEqual(positive['trace'][0]['middle']['py'], 0)
        self.assertEqual(positive['trace'][0]['after']['py'], 1)
        self.assertEqual(positive['trace'][0]['clocks_after']['Y'], '0')
        self.assertIn('Y', positive['trace'][1]['persistent'])
        for case in cases[1:]:
            result, _ = self.compare('R6-01', model, case)
            self.assertEqual(result['status'], 'INVALID_INPUT_OR_HISTORY')

        mutated = run_case('R6-01', model, cases[1], mutation='R601_PERSIST_MIDDLE_CLOCK')
        self.assertEqual(mutated['status'], 'REPLAYED_HISTORY')
        self.assertEqual(mutated['completion_time'], '2')
        record = make_acceptance_record('R6-01', cases[0], positive,
                                        reference_case('R6-01', model, cases[0]),
                                        'R601_PERSIST_MIDDLE_CLOCK',
                                        subject_matches_oracle=True, mutation_detected=True)
        self.assertEqual(record['invariant_verdict'], 'COMPONENT_REGRESSION_PASS')
        self.assertTrue(record['actual_network_trace'])
        self.assertIn('old', record['mutation_patch'])

        root_model = load('immediate_mass.json')
        root_case = dict(case_id='r601_all_immediate_roots', kind='mass', role='POSITIVE', budget=100)
        root, _ = self.compare('R6-01', root_model, root_case)
        root_children = {row['transition']: row['mass'] for row in root['events'][0]['children']}
        self.assertEqual(root_children, {'normal': '1/4', 'fault': '1/2', 'extra': '1/4'})
        self.assertEqual(len(cases) + 1, 4)

    def test_r602_zero_delay_endpoint_external_and_window_mutation(self):
        model = load('r602_completion.json')
        cases = [
            dict(case_id='r602_same_fault_completion', kind='timed', role='POSITIVE',
                 history=history(('same_fire', 1), end=1)),
            dict(case_id='r602_exact_window_endpoint', kind='timed', role='POSITIVE',
                 history=history(('fault', 1), ('complete_window', 2), end=2)),
            dict(case_id='r602_outside_window', kind='timed', role='NEGATIVE',
                 history=history(('fault', 1), ('complete_window', 4), end=4)),
            dict(case_id='r602_external_completion', kind='timed', role='POSITIVE',
                 model_overlay={'initial': {'external_done': 1}},
                 history=history(('fault', 1), ('external_complete', 1), end=1)),
            dict(case_id='r602_external_channel_absent', kind='timed', role='NEGATIVE',
                 history=history(('fault', 1), ('external_complete', 1), end=1)),
            dict(case_id='r602_completion_beyond_horizon', kind='timed', role='NEGATIVE',
                 history=history(('fault', 1), ('complete_window', 5), end=5)),
        ]
        outputs = []
        for case in cases:
            current = copy.deepcopy(model)
            for key, values in case.get('model_overlay', {}).items():
                current[key].update(values)
            subject, _ = self.compare('R6-02', current, case)
            outputs.append((case, subject, current))
        self.assertEqual(outputs[0][1]['first_fault_time'], outputs[0][1]['completion_time'])
        self.assertEqual(outputs[0][1]['outcome'], 'COMPLETED_IN_TIME')
        self.assertEqual(outputs[1][1]['outcome'], 'COMPLETED_IN_TIME')
        self.assertEqual(outputs[2][1]['outcome'], 'VIOLATION')
        self.assertEqual(outputs[3][1]['outcome'], 'COMPLETED_IN_TIME')
        self.assertEqual(outputs[4][1]['status'], 'INVALID_INPUT_OR_HISTORY')
        self.assertEqual(outputs[5][1]['status'], 'INVALID_INPUT_OR_HISTORY')

        case, baseline, current = outputs[2]
        mutated = run_case('R6-02', current, case, mutation='R602_IGNORE_COMPLETION_WINDOW')
        self.assertEqual(mutated['outcome'], 'COMPLETED_IN_TIME')
        self.assertNotEqual(mutated['outcome'], baseline['outcome'])
        record = make_acceptance_record('R6-02', cases[0], outputs[0][1],
                                        reference_case('R6-02', current, cases[0]),
                                        'R602_IGNORE_COMPLETION_WINDOW',
                                        subject_matches_oracle=True, mutation_detected=True)
        self.assertTrue(record['actual_network_trace'])
        self.assertTrue(record['mutation_detected'])
        self.assertEqual(len(cases), 6)


class R6ComponentBatch2Tests(unittest.TestCase):
    def compare(self, component, model, case):
        subject = run_case(component, model, case)
        reference = reference_case(component, model, case)
        self.assertEqual(subject['status'], reference['status'], case['case_id'])
        if case['kind'] == 'timed' and subject['status'] == 'REPLAYED_HISTORY':
            for key in ('terminal', 'outcome', 'first_fault_time', 'completion_time',
                        'endpoint_enabled_to_fire'):
                self.assertEqual(subject[key], reference[key], (case['case_id'], key))
        elif case['kind'] == 'mass':
            for key in ('resolved', 'unresolved', 'categories', 'frontier'):
                self.assertEqual(subject[key], reference[key], (case['case_id'], key))
        elif case['kind'] == 'endpoint':
            self.assertEqual(subject['visited'], reference['visited'])
            simplify = lambda rows: [(tuple(row['suffix']), row['result']['terminal'],
                                      row['result']['outcome']) for row in rows]
            self.assertEqual(simplify(subject['terminals']), simplify(reference['terminals']))
            self.assertEqual(subject['pending'], reference['pending'])
        return subject, reference

    def test_r603_five_terminal_classes_and_mass_conservation(self):
        model = load('r603_immediate.json')
        full_case = dict(case_id='r603_full_three_branches', kind='mass', role='POSITIVE', budget=20)
        full, _ = self.compare('R6-03', model, full_case)
        terminal_classes = {row['terminal'] for row in full['categories']}
        self.assertEqual(terminal_classes,
                         {'FIRST_COMPLETION', 'NON_COMPLETION_TERMINAL', 'DEADLOCK'})
        self.assertEqual({row['mass'] for row in full['categories']}, {'1/3'})
        self.assertEqual(full['resolved'], '1')
        self.assertFalse(any('after_done' in row['path'] for row in full['events']))

        budget_case = dict(case_id='r603_budget_frontier', kind='mass', role='POSITIVE', budget=2)
        bounded, _ = self.compare('R6-03', model, budget_case)
        self.assertEqual(bounded['status'], 'UNRESOLVED')
        self.assertEqual((bounded['resolved'], bounded['unresolved']), ('1/3', '2/3'))
        self.assertEqual(len(bounded['frontier']), 2)
        with self.assertRaisesRegex(ArithmeticError, 'path mass not conserved'):
            run_case('R6-03', model, budget_case, mutation='R603_DROP_FRONTIER_MASS')

        horizon_model = load('r603_horizon.json')
        horizon_case = dict(case_id='r603_horizon_truncation', kind='timed', role='POSITIVE',
                            history=history(('fault', 1), end=4))
        horizon, _ = self.compare('R6-03', horizon_model, horizon_case)
        self.assertEqual(horizon['terminal'], 'HORIZON_TRUNCATION')
        invalid_case = dict(case_id='r603_completion_before_earliest', kind='timed', role='NEGATIVE',
                            history=history(('fault', 1), ('complete', 4), end=4))
        invalid, _ = self.compare('R6-03', horizon_model, invalid_case)
        self.assertEqual(invalid['status'], 'INVALID_INPUT_OR_HISTORY')
        record = make_acceptance_record('R6-03', full_case, full,
                                        reference_case('R6-03', model, full_case),
                                        'R603_DROP_FRONTIER_MASS',
                                        subject_matches_oracle=True, mutation_detected=True)
        self.assertTrue(record['actual_network_trace'])
        self.assertEqual(len((full_case, budget_case, horizon_case, invalid_case)), 4)

    def test_r604_endpoint_closure_window_and_post_completion_fault(self):
        model = load('r604_endpoint.json')
        endpoint_case = dict(case_id='r604_right_endpoint_immediate_closure', kind='endpoint', role='POSITIVE',
                             prefix=history(('fault', 1), end=2), budget=20)
        endpoint, _ = self.compare('R6-04', model, endpoint_case)
        branches = {tuple(row['suffix']): row['result'] for row in endpoint['terminals']}
        self.assertEqual(branches[('advance', 'finish')]['outcome'], 'COMPLETED_IN_TIME')
        self.assertEqual(branches[('advance', 'finish')]['completion_time'], '2')
        self.assertEqual(branches[('advance', 'abort')]['terminal'], 'DEADLOCK')
        self.assertEqual(endpoint['status'], 'EXHAUSTED_AT_ENDPOINT_FOR_PREFIX')
        with self.assertRaises(RuntimeError):
            run_case('R6-04', model, endpoint_case, mutation='R604_ALL_SUCCESSORS_CLEARED')
        # Specific misclassification: the horizon cut silently loses the
        # immediate completion branch instead of failing loudly.
        misclassified = run_case('R6-04', model, endpoint_case,
                                 mutation='R604_HORIZON_CUT_LOSES_COMPLETION')
        self.assertEqual(misclassified['status'], 'EXHAUSTED_AT_ENDPOINT_FOR_PREFIX')
        lost = [(tuple(row['suffix']), row['result']['terminal']) for row in misclassified['terminals']]
        self.assertEqual(lost, [((), 'HORIZON_TRUNCATION')])
        self.assertFalse(any(row['result']['terminal'] == 'FIRST_COMPLETION'
                             for row in misclassified['terminals']))

        late_case = dict(case_id='r604_fault_after_completion', kind='timed', role='NEGATIVE',
                         history=history(('fault', 1), ('advance', 2), ('finish', 2),
                                         ('late_fault', 2), end=2))
        late, _ = self.compare('R6-04', model, late_case)
        self.assertEqual(late['status'], 'INVALID_INPUT_OR_HISTORY')

        inconsistent = copy.deepcopy(model)
        inconsistent['B_c'] = 0
        invalid_case = dict(case_id='r604_inconsistent_Bc_HA', kind='timed', role='NEGATIVE',
                            history=history(('fault', 1), end=2))
        invalid, _ = self.compare('R6-04', inconsistent, invalid_case)
        self.assertEqual(invalid['status'], 'INVALID_INPUT_OR_HISTORY')
        record = make_acceptance_record('R6-04', endpoint_case, endpoint,
                                        reference_case('R6-04', model, endpoint_case),
                                        'R604_HORIZON_CUT_LOSES_COMPLETION',
                                        subject_matches_oracle=True, mutation_detected=True)
        self.assertTrue(record['actual_network_trace'])
        self.assertEqual(len((endpoint_case, late_case, invalid_case)), 3)


if __name__ == '__main__':
    unittest.main()
