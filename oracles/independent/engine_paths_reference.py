"""Independent small-model engine oracle: sequence enumeration + rational vertex LP."""
from collections import deque
from fractions import Fraction as Q
from itertools import combinations
import hashlib
import json

from absolute_schedule import date
from ap41_polytope import solve_square
from engine_interface import check_applicability


def _enumerate(model, budget):
    transitions = model['transitions']

    def enabled(marking):
        return {name for name, edge in transitions.items()
                if all(marking.get(place, 0) >= weight for place, weight in edge['pre'].items())}

    initial = dict(model['initial_marking'])
    activation = {name: -1 for name in enabled(initial)}
    queue = deque([((), initial, activation, (), None)])
    terminals = []
    visits = 0
    while queue and visits < budget:
        sequence, marking, activation, word, fault = queue.popleft()
        visits += 1
        complete = any(all(marking.get(place, 0) >= weight for place, weight in goal.items())
                       for goal in model['completion_markings'])
        active = enabled(marking)
        if complete or not active:
            terminals.append(dict(sequence=sequence, word=word, fault=fault,
                                  terminal='FIRST_COMPLETION' if complete else 'DEADLOCK'))
            continue
        urgent = sorted(name for name in active if transitions[name]['immediate'])
        for name in urgent or sorted(active):
            edge = transitions[name]
            middle = {place: marking.get(place, 0) - edge['pre'].get(place, 0)
                      for place in marking}
            after = {place: middle.get(place, 0) + edge['post'].get(place, 0)
                     for place in set(middle) | set(edge['post'])}
            step = len(sequence) + 1
            keep = active & enabled(middle) & enabled(after) - {name}
            next_activation = {other: activation[other] if other in keep else step
                               for other in enabled(after)}
            label = edge['label']
            queue.append(((*sequence, name), after, next_activation,
                          word if label is None else (*word, label),
                          fault if fault is not None else (step if edge['is_fault'] else None)))
    return dict(terminals=terminals, pending=len(queue), visits=visits,
                status='UNRESOLVED' if queue else 'EXHAUSTED_FOR_MODEL')


def _constraints(model, terminal):
    sequence = terminal['sequence']
    horizon = date(model['H'])
    activation_maps = []
    marking = dict(model['initial_marking'])
    activation = {name: -1 for name, edge in model['transitions'].items()
                  if all(marking.get(place, 0) >= weight for place, weight in edge['pre'].items())}
    for step, fired in enumerate(sequence, 1):
        activation_maps.append(dict(activation))
        current = model['transitions'][fired]
        middle = {place: marking.get(place, 0) - current['pre'].get(place, 0)
                  for place in marking}
        marking = {place: middle.get(place, 0) + current['post'].get(place, 0)
                   for place in set(middle) | set(current['post'])}

        def enabled(target):
            return {name for name, other in model['transitions'].items()
                    if all(target.get(place, 0) >= weight for place, weight in other['pre'].items())}

        keep = set(activation) & enabled(middle) & enabled(marking) - {fired}
        activation = {other: activation[other] if other in keep else step
                      for other in enabled(marking)}
    constraints = []
    for index, name in enumerate(sequence, 1):
        edge = model['transitions'][name]
        low, high = map(date, edge['interval'])
        activated = activation_maps[index - 1][name]
        base = 0 if activated == -1 else activated
        constraints.extend([(base, index, high), (index, base, -low)])
        if index > 1:
            constraints.append((index, index - 1, Q(0)))
        if edge['immediate']:
            previous = index - 1 if index > 1 else 0
            constraints.extend([(index, previous, Q(0)), (previous, index, Q(0))])
        constraints.extend([(0, index, horizon), (index, 0, Q(0))])
    return constraints


def _difference_interval(constraints, n):
    """Exact longest-path alternative for deeper difference-constraint LPs."""
    edges = list(constraints)

    def shortest(graph, source):
        distances = [None] * (n + 1)
        distances[source] = Q(0)
        for _ in range(n + 1):
            changed = False
            for source_node, target, bound in graph:
                if distances[source_node] is not None:
                    candidate = distances[source_node] + bound
                    if distances[target] is None or candidate < distances[target]:
                        distances[target] = candidate
                        changed = True
            if not changed:
                return distances, True
        return distances, False

    _all, feasible = shortest(edges + [(n, node, Q(0)) for node in range(n)], n)
    if not feasible:
        return None
    forward, ok_forward = shortest(edges, 0)
    reverse, ok_reverse = shortest([(target, source, bound) for source, target, bound in edges], 0)
    if not (ok_forward and ok_reverse) or forward[n] is None or reverse[n] is None:
        return None
    return -reverse[n], forward[n]


def _interval(constraints, n):
    if n > 4:
        return _difference_interval(constraints, n)
    inequalities = []
    for source, target, bound in constraints:
        row = [Q(0)] * (n + 2)
        row[target] = 1
        row[source] -= 1
        row[-1] = Q(bound)
        inequalities.append(tuple(row))
    anchor = (Q(1), *([Q(0)] * (n + 1)))
    vertices = set()
    for active in combinations(dict.fromkeys(inequalities), n):
        point = solve_square([anchor, *active])
        if point is None or point[0] != 0:
            continue
        if all(sum((a * x for a, x in zip(row[:-1], point)), Q(0)) <= row[-1]
               for row in inequalities):
            vertices.add(point)
    if not vertices:
        return None
    values = [point[n] for point in vertices]
    return min(values), max(values)


def reference_engine(model, budget):
    """Complete only within the explicit small finite sequence/LP domain."""
    canonical = json.dumps(model, sort_keys=True, default=str, separators=(',', ':')).encode()
    model_sha = hashlib.sha256(canonical).hexdigest()
    applicability = check_applicability(model)
    if not applicability['supported']:
        return dict(status='UNSUPPORTED', verdict='PERP', model_sha256=model_sha,
                    reasons=applicability['reasons'])
    exploration = _enumerate(model, budget)
    rows = []
    deadline = date(model.get('diagnosis_window', model['H']))
    for terminal in exploration['terminals']:
        if terminal['terminal'] != 'FIRST_COMPLETION':
            continue
        n = len(terminal['sequence'])
        if n > 9:
            return dict(status='UNSUPPORTED', verdict='PERP', model_sha256=model_sha,
                        reason='REFERENCE_COMPLETION_DEPTH_EXCEEDS_9')
        bounds = _interval(_constraints(model, terminal), n)
        rows.append(dict(sequence=list(terminal['sequence']), word=list(terminal['word']),
                         fault_step=terminal['fault'], feasible=bounds is not None,
                         completion_interval=None if bounds is None else [str(bounds[0]), str(bounds[1])]))
    if exploration['status'] != 'EXHAUSTED_FOR_MODEL':
        verdict = 'PERP'
    else:
        fault_terminals = [row for row in exploration['terminals'] if row['fault'] is not None]
        fault_rows = [row for row in rows if row['fault_step'] is not None and row['feasible']]
        if any(row['terminal'] == 'DEADLOCK' for row in fault_terminals):
            verdict = '0'
        elif any(Q(row['completion_interval'][1]) > deadline for row in fault_rows):
            verdict = '0'
        elif fault_rows and len(fault_rows) == len(fault_terminals):
            verdict = '1'
        else:
            verdict = 'PERP'
    return dict(status=exploration['status'], verdict=verdict, model_sha256=model_sha,
                rows=rows, pending=exploration['pending'],
                limits='FINITE_SEQUENCE_EXPLORATION_VERTEX_LP_LE_4_OR_EXACT_DIFFERENCE_LONGEST_PATH_LE_9')
