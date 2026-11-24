import importlib.util
import itertools
import json
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ap41', ROOT/'implementations/subject/ap41_intervals.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


def b(lo, hi):
    return {'low': str(lo), 'high': str(hi)}


def base():
    return dict(q0=b('1/2','1/2'), q1=b('1/2','1/2'), pi0='1/2', pi1='1/2',
                epsilon='1/4', delta='1/4', gamma='1/2', v_c='1', Pe=b(0,'1/8'), Gamma=b('3/4',1))


class LocalIntervalTests(unittest.TestCase):
    def test_legacy_shared_failures(self):
        rows = json.loads((ROOT/'runs/math_p0/legacy_probability_reproduction.json').read_text())
        self.assertEqual(len(rows), 3)
        for row in rows:
            with self.subTest(row=row['id']):
                self.assertIn(row['old_subject']['v_P'], {'0','1'})
                self.assertIn(row['old_reference']['v_P'], {'0','1'})
                got = subject.evaluate(row['input'])
                self.assertEqual(got['status'], 'INVALID_EVIDENCE')
                self.assertNotIn('conditional_verdict', got)

    def test_loose_and_impossible_bounds(self):
        got = subject.evaluate(base() | {'Q0_Y': b(0,'3/4'), 'Pe': b(0,2)})
        self.assertEqual(got['status'], 'CONDITIONAL_ONLY')
        self.assertEqual(got['categories'][0]['B'], (0,F(1,2)))
        self.assertEqual(got['Pe'], (0,F(1,2)))
        self.assertFalse(got['certified'])
        self.assertEqual(subject.evaluate(base() | {'Q0_Y': b('3/5','3/4')})['status'], 'INVALID_EVIDENCE')

    def test_applicability_and_untrusted_flag(self):
        self.assertEqual(subject.evaluate(base() | {'pi0':'0','pi1':'1'})['status'], 'INVALID_INPUT')
        for q0,q1,expected in [(b(0,0),b(1,1),'0'),(b(0,1),b(0,1),'PERP')]:
            got = subject.evaluate(base() | dict(q0=q0,q1=q1,evidence_valid=True))
            self.assertEqual((got['a_P'],got['conditional_verdict'],got['certified']), (expected,None,False))
        self.assertFalse(subject.evaluate(base() | {'evidence_valid':True})['certified'])

    def test_joint_complement_contradiction(self):
        # Each partition is individually feasible, but both demand >= 3/5.
        data = base() | dict(q0=b(0,1), q1=b(0,1),
                             categories0={'a':b('3/5','7/10')},
                             categories1={'b':b('3/5','7/10')})
        got = subject.evaluate(data)
        self.assertEqual(got['status'], 'INVALID_EVIDENCE')
        self.assertNotIn('conditional_verdict', got)

    def test_partition_frontier_and_complement_tighten(self):
        data = base() | dict(q0=b(0,1), q1=b(0,1),
                             categories0={'a':b('1/4','1/2')}, frontier0=b('1/4','1/4'),
                             categories1={'b':b('3/8','3/8')})
        got = subject.evaluate(data)
        self.assertEqual(got['q'], [(F(1,2),F(5,8)),(F(3,8),F(1,2))])
        self.assertEqual(got['categories'][0]['a'], (F(1,4),F(3,8)))

    def test_small_exact_partition_by_enumeration(self):
        # Independent enumeration of four equal mass atoms: categories, frontier, other H1.
        ticks = [F(i,4) for i in range(5)]
        bounds = [(F(0),F(1,4)),(F(1,4),F(1,2)),(F(1,2),F(1,2))]
        allocations = [x for x in itertools.product(ticks,repeat=4) if sum(x)==1]
        for a,d in itertools.product(bounds,repeat=2):
            for frontier in (None,*bounds):
                data = base() | {'categories0':{'a':b(*a),'d':b(*d)}}
                if frontier is not None:
                    data['frontier0']=b(*frontier)
                feasible = [x for x in allocations if a[0]<=x[0]<=a[1] and d[0]<=x[1]<=d[1]
                            and x[3]==F(1,2) and (frontier is None or frontier[0]<=x[2]<=frontier[1])]
                got = subject.evaluate(data)
                with self.subTest(a=a,d=d,frontier=frontier):
                    if not feasible:
                        self.assertEqual(got['status'],'INVALID_EVIDENCE')
                    else:
                        self.assertEqual(got['status'],'CONDITIONAL_ONLY')
                        for i,k in enumerate(('a','d','@frontier') if frontier is not None else ('a','d')):
                            self.assertEqual(got['categories'][0][k],(min(x[i] for x in feasible),max(x[i] for x in feasible)))


if __name__ == '__main__':
    unittest.main()
