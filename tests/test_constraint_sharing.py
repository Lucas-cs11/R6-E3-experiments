"""Regression: shared-prefix constraints preserve the old merged explorer exactly."""
import sys
import unittest
from collections import deque
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'implementations/subject'),
                str(ROOT / 'baseline_readonly/e2/implementations/generator_compat'),
                str(ROOT / 'tests')]
from src.benchmarks.rmt_fms_generator import generate_rmt_fms
from probe_scale import to_model
from reachability import (_complete, _validate, explore_merged,
                          merged_completion_intervals)


def _inline_old_explore_merged(model, node_budget):
    """The pre-refactor full-list payload algorithm, kept as an oracle."""
    hp, bc, ha, marking0, edges, goals = _validate(model)

    def enabled(marking):
        return {k for k, e in edges.items()
                if all(marking.get(p, 0) >= w for p, w in e[0].items())}

    def key_of(marking, ages):
        return (tuple(sorted((p, v) for p, v in marking.items() if v)),
                tuple(sorted(ages.items())))

    def fire(marking, ages, name):
        pre, post, lo, hi, *_ = edges[name]
        mid = {p: v - pre.get(p, 0) for p, v in marking.items()}
        if any(v < 0 for v in mid.values()):
            return None
        new_marking = {p: mid.get(p, 0) + post.get(p, 0)
                       for p in set(mid) | set(post)}
        mid_enabled = enabled(mid)
        post_enabled = enabled(new_marking)
        keep = (set(ages) & mid_enabled & post_enabled) - {name}
        new_ages = {k: (ages[k] + 1 if k in keep else 0) for k in post_enabled}
        return new_marking, new_ages

    root_ages = {k: -1 for k in enabled(marking0)}
    root_key = key_of(marking0, root_ages)
    nodes = {root_key: dict(marking=marking0, ages=root_ages, expanded_upto=0,
                            payload=[dict(seq=(), cons=[], word=(), fault=None,
                                          completed=None)])}
    order = deque([root_key])
    in_queue = {root_key}
    terminals = []
    expansions = 0
    payload_items = 1
    total_constraints = 0
    while order and expansions < node_budget:
        key = order.popleft()
        in_queue.discard(key)
        node = nodes[key]
        start = node['expanded_upto']
        if start == len(node['payload']):
            continue
        expansions += 1
        marking, ages = node['marking'], node['ages']
        en = enabled(marking)
        complete_here = _complete(marking, goals)
        if complete_here or not en:
            for item in node['payload'][start:]:
                terminals.append(dict(
                    item, marking=marking,
                    terminal='FIRST_COMPLETION' if complete_here else 'DEADLOCK',
                    completed=item['completed'] if item['completed'] is not None
                    else (len(item['seq']) if complete_here else None)))
            node['expanded_upto'] = len(node['payload'])
            continue
        urgent = [k for k in sorted(en) if edges[k][6]]
        for name in (urgent or sorted(en)):
            fired = fire(marking, ages, name)
            if fired is None:
                continue
            new_marking, new_ages = fired
            child_key = key_of(new_marking, new_ages)
            child = nodes.setdefault(child_key, dict(marking=new_marking, ages=new_ages,
                                                     expanded_upto=0, payload=[]))
            _pre, _post, lo, hi, is_fault, is_completion, immediate, label = edges[name]
            for item in node['payload'][start:]:
                i = len(item['seq']) + 1
                age = ages[name]
                base = 0 if age == -1 else (i - 1 - age)
                cons = list(item['cons'])
                cons.append((base, i, hi))
                cons.append((i, base, -lo))
                if i > 1:
                    cons.append((i, i - 1, F(0)))
                if immediate:
                    prev = i - 1 if i > 1 else 0
                    cons.append((i, prev, F(0)))
                    cons.append((prev, i, F(0)))
                cons.append((0, i, ha))
                cons.append((i, 0, F(0)))
                child['payload'].append(dict(
                    seq=item['seq'] + (name,), cons=cons,
                    word=item['word'] if label is None else item['word'] + (label,),
                    fault=item['fault'] if item['fault'] is not None else (i if is_fault else None),
                    completed=i if is_completion else item['completed']))
                payload_items += 1
                total_constraints += len(cons)
            node['expanded_upto'] = len(node['payload'])
            if child_key not in in_queue:
                in_queue.add(child_key)
                order.append(child_key)
    pending_nodes = [k for k in order if nodes[k]['expanded_upto'] < len(nodes[k]['payload'])]
    pending = [dict(key=k, payload=len(nodes[k]['payload']), terminal='UNRESOLVED',
                    reason='NODE_BUDGET') for k in pending_nodes]
    return dict(status='UNRESOLVED' if pending else 'EXHAUSTED_FOR_MODEL',
                expansions=expansions, abstract_states=len(nodes),
                payload_items=payload_items, total_constraints=total_constraints,
                terminals=terminals, pending=pending, node_budget=node_budget,
                constraint_budget=None)


def _model(params):
    net, _L, H = generate_rmt_fms(**params, seed=0, machine_capacity=1,
                                  n_configs=2, repair_domain='standard')
    return to_model(net, F(str(H)))


M2_J1 = dict(n_machines=2, n_parts=1, ops_per_part=2, wip_bound=1,
             unobservable_ratio=0.1, fault_locations=1,
             interval_width_factor=0.5, adjustable_ratio=0.1)
M2_J2 = dict(n_machines=2, n_parts=2, ops_per_part=2, wip_bound=2,
             unobservable_ratio=0.3, fault_locations=2,
             interval_width_factor=1.0, adjustable_ratio=0.25)


class ConstraintSharingTests(unittest.TestCase):
    def test_m2_j2_intervals_match_inline_old_algorithm_and_memory_shrinks(self):
        model = _model(M2_J2)
        old = _inline_old_explore_merged(model, 2000000)
        new = explore_merged(model, 2000000)
        self.assertEqual(old['abstract_states'], 137)
        self.assertEqual(old['total_constraints'], 436098)
        self.assertEqual(new['abstract_states'], old['abstract_states'])
        self.assertEqual(new['expansions'], old['expansions'])
        self.assertEqual(new['payload_items'], old['payload_items'])
        old_rows = merged_completion_intervals(model, old)
        new_rows = merged_completion_intervals(model, new)
        self.assertEqual(len(old_rows), 800)
        self.assertEqual(new_rows, old_rows)
        self.assertTrue(all('delta' in item and 'cons' not in item
                            for item in new['terminals']))
        self.assertLess(new['total_constraints'], old['total_constraints'] // 2)

    def test_m2_j1_counts_and_intervals_are_unchanged(self):
        model = _model(M2_J1)
        old = _inline_old_explore_merged(model, 2000000)
        new = explore_merged(model, 2000000)
        self.assertEqual(new['abstract_states'], 10)
        self.assertEqual(new['expansions'], old['expansions'])
        self.assertEqual(new['payload_items'], old['payload_items'])
        self.assertEqual(len(merged_completion_intervals(model, new)), 2)
        self.assertEqual(merged_completion_intervals(model, new),
                         merged_completion_intervals(model, old))

    def test_node_and_constraint_budget_semantics_are_preserved(self):
        model = _model(M2_J1)
        node_limited = explore_merged(model, 1)
        self.assertEqual(node_limited['status'], 'UNRESOLVED')
        self.assertEqual(node_limited['expansions'], 1)
        self.assertTrue(node_limited['pending'])
        self.assertEqual(node_limited['pending'][0]['reason'], 'NODE_BUDGET')

        full = explore_merged(model, 2000000)
        exact_budget = explore_merged(model, 2000000,
                                      constraint_budget=full['total_constraints'])
        self.assertEqual(exact_budget['status'], 'EXHAUSTED_FOR_MODEL')
        constrained = explore_merged(model, 2000000, constraint_budget=1)
        self.assertEqual(constrained['status'], 'UNRESOLVED')
        self.assertEqual(constrained['pending'][0]['reason'], 'CONSTRAINT_MEMORY_BUDGET')
        self.assertGreater(constrained['total_constraints'], 1)
        self.assertEqual(constrained['pending'][0]['budget'], 1)


if __name__ == '__main__':
    unittest.main()
