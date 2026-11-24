"""PN-driven regression of concrete histories; no continuous-domain exhaustion."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/p) for p in ('implementations/subject', 'oracles/independent')]
from timed_trace import check_projection, replay
from absolute_schedule import assess, projection_status


def history(*events, end=2, **claims):
    return {'fires': [{'transition': k, 'at': t} for k,t in events], 'end': end, **claims}


def edge(pre, post, interval, *, immediate=False, completion=False):
    return dict(pre=pre, post=post, interval=interval, immediate=immediate,
                completion=completion, fault=False, label='done' if completion else None)


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT/'models/regression/timed_trace.json').read_text())

    def run_case(self, name, candidate, model=None):
        model = self.model if model is None else model
        result = replay(model, candidate)
        reference = assess(model, candidate)
        print(json.dumps({'case':name, 'model':model, 'history':candidate, 'result':result, 'reference':reference}))
        self.assertEqual(result['status'], reference['status'])
        if reference['status'] == 'REPLAYED_HISTORY':
            self.assertEqual({k:result[k] for k in reference}, reference)
        return result

    def test_invalid_histories(self):
        for name,model,record in [
            ('completion_before_fault',self.model,history(('fault',1),('complete_a',2),completion_time='1/2')),
            ('completion_after_horizon',self.model,history(('fault',1),('complete_a',20),end=20)),
            ('negative_fault',self.model,history(('fault',-1))),
            ('zero_deadline',self.model | {'B_c':0},history(('same_fire',1),end=1)),
            ('completion_followed_by_firing',self.model,history(('same_fire',1),('fault',1),end=1)),
            ('disabled_completion',self.model,history(('complete_a',0),end=0)),
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.run_case(name,record,model)['status'],'INVALID_INPUT_OR_HISTORY')

    def test_completion_and_unresolved_endpoint(self):
        a = self.run_case('same_firing',history(('same_fire',1),end=1))
        self.assertEqual((a['first_fault_time'],a['completion_time'],a['outcome']),('1','1','COMPLETED_IN_TIME'))
        b = self.run_case('endpoint_completion',history(('fault',1),('complete_a',2)))
        self.assertEqual((b['first_fault_time'],b['completion_time'],b['outcome']),('1','2','COMPLETED_IN_TIME'))
        for endpoint in (1,2):
            with self.subTest(case=f'open_prefix_{endpoint}'):
                c = self.run_case(f'open_prefix_{endpoint}',history(('fault',1),end=endpoint))
                self.assertEqual((c['terminal'],c['outcome']),('FRONTIER','PENDING'))
        self.assertEqual(c['endpoint_enabled_to_fire'],['complete_a','complete_b'])

    def test_observation_collision_requires_distinct_omega(self):
        a,b,c = [self.run_case(f'observation_{k}_{t}',history(('fault',1),(k,t),end=t))
                 for k,t in [('complete_a',2),('complete_b',2),('complete_b',1)]]
        for inputs, mode, expected in [([a,b],'word','INJECTIVE_ON_REPLAYED_SET'),
                                       ([a,c],'word','COLLISION'),
                                       ([a,c],'word_and_time','INJECTIVE_ON_REPLAYED_SET')]:
            got = check_projection(inputs,mode)
            ref = projection_status(inputs, mode)
            print(json.dumps({'case':'projection','mode':mode,'result':got,'reference_status':ref}))
            self.assertEqual(got['status'], ref)
            self.assertEqual(ref, expected)

    def test_middle_marking_resets_clock(self):
        m = copy.deepcopy(self.model)
        m['transitions'] = {
            'reset':edge({'start':1},{'start':1},[1,1]),
            'done':edge({'start':1},{'done':1},[2,2],completion=True),
        }
        with self.subTest(case='reset_blocks_old_clock'):
            self.assertEqual(self.run_case('reset_blocks_old_clock',history(('reset',1),('done',2)),m)['status'],
                             'INVALID_INPUT_OR_HISTORY')
        r = self.run_case('reset_clock_age',history(('reset',1),end=1),m)
        self.assertEqual(r['trace'][0]['clocks_after']['done'],'0')
        self.assertEqual(r['trace'][0]['middle']['start'],0)

    def test_immediate_priority(self):
        m = copy.deepcopy(self.model)
        m['transitions']['imm'] = edge({'start':1},{'work':1},[0,0],immediate=True)
        self.assertEqual(self.run_case('delay_with_immediate_enabled',history(('fault',1),end=1),m)['status'],
                         'INVALID_INPUT_OR_HISTORY')
        # At time zero the ordinary transition meets its own interval and
        # does not overrun any deadline; only immediate priority excludes it.
        m['transitions']['ordinary_zero'] = edge({'start':1},{'done':1},[0,1],completion=True)
        with self.subTest(case='ordinary_zero_blocked_by_immediate'):
            self.assertEqual(self.run_case('ordinary_zero_blocked_by_immediate',
                                           history(('ordinary_zero',0),end=0),m)['status'],
                             'INVALID_INPUT_OR_HISTORY')
        r = self.run_case('immediate_then_completion',history(('imm',0),('complete_a',0),end=0),m)
        self.assertEqual((r['terminal'],r['completion_time']),('FIRST_COMPLETION','0'))
