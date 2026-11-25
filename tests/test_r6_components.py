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
                                        'R601_PERSIST_MIDDLE_CLOCK', 1)
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
                                        'R602_IGNORE_COMPLETION_WINDOW', 1)
        self.assertTrue(record['actual_network_trace'])
        self.assertEqual(record['mutation_exit_code'], 1)
        self.assertEqual(len(cases), 6)


if __name__ == '__main__':
    unittest.main()
