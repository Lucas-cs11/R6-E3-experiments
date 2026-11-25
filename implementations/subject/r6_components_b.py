"""R6-05..07 model-driven component implementations, committed incrementally."""
from fractions import Fraction as F
from itertools import combinations
from collections import defaultdict, deque
import math

from ap41_polytope import solve_square
from timed_trace import replay


_PATCHES = {
    'R605_COLLAPSE_MIXED_CLASS': dict(
        component_id='R6-05', old='retain both exact difference cells',
        new='discard VIOLATION cell from a mixed parent class'),
    'R606_DROP_FAULT_HISTORY': dict(
        component_id='R6-06', old='retain every validated normal/fault history',
        new='drop FAULT history after identical observation grouping'),
    'R607_IGNORE_HISTORY_DENSITY': dict(
        component_id='R6-07', old='apply weight_by_fault to shared history-dependent selectors',
        new='use base selector weight for both NORMAL and FAULT histories'),
}

_LIMITATIONS = {
    'R6-05': 'Two-variable bounded DBM difference cells with rational open/closed boundaries.',
    'R6-06': 'Explicit finite histories and a two-coordinate coupled rational LP on shared root weights.',
    'R6-07': 'Finite integer-time discrete density tree; no continuous-time or general LSTPN density claim.',
}


def mutation_patch(mutation_id):
    patch = _PATCHES[mutation_id]
    return dict(patch, mutation_id=mutation_id, mode='SPECIFIC_SEMANTIC_BRANCH_MUTATION')


def _coefficients(expression, variables):
    coefficients = [F(0)] * len(variables)
    for sign, name in ((1, expression), (-1, expression[1:] if expression.startswith('-') else None)):
        if name in variables:
            coefficients[variables.index(name)] = sign
            return coefficients
    if '-' in expression:
        left, right = expression.split('-', 1)
        coefficients[variables.index(left)] = 1
        coefficients[variables.index(right)] = -1
        return coefficients
    raise ValueError(f'unknown DBM expression: {expression}')


def _base_constraints(model):
    state = model['state_class']
    variables = state['variables']
    rows = []
    for name in variables:
        low, high = state['variable_bounds'][name]
        rows.extend([dict(expression=name, op='>=', bound=str(low)),
                     dict(expression=name, op='<=', bound=str(high))])
    difference = state['difference']
    rows.extend([dict(expression=difference['expression'], op='>=', bound=str(difference['low'])),
                 dict(expression=difference['expression'], op='<=', bound=str(difference['high']))])
    return rows


def _satisfies(constraints, point, variables):
    for row in constraints:
        coefficients = _coefficients(row['expression'], variables)
        value = sum((a * x for a, x in zip(coefficients, point)), F(0))
        bound = F(row['bound'])
        if ((row['op'] == '>=' and value < bound) or
                (row['op'] == '<=' and value > bound) or
                (row['op'] == '>' and value <= bound)):
            return False
    return True


def _vertices(constraints, variables):
    points = set()
    for first, second in combinations(constraints, 2):
        a = _coefficients(first['expression'], variables)
        b = _coefficients(second['expression'], variables)
        point = solve_square([[*a, F(first['bound'])], [*b, F(second['bound'])]])
        if point is not None and _satisfies(constraints, point, variables):
            points.add(tuple(point))
    return sorted(points)


def run_r605(model, case, mutation=None):
    """Split one bounded two-variable DBM class by an exact complement."""
    if mutation not in (None, 'R605_COLLAPSE_MIXED_CLASS'):
        raise ValueError('unknown R6-05 mutation')
    variables = model['state_class']['variables']
    if len(variables) != 2:
        raise ValueError('R6-05 regression supports exactly two variables')
    split_at = str(case['split_at'])
    base = _base_constraints(model)
    difference = model['state_class']['difference']['expression']
    cells = []
    for classification, extra in (
            ('NON_VIOLATION', dict(expression=difference, op='<=', bound=split_at)),
            ('VIOLATION', dict(expression=difference, op='>', bound=split_at))):
        constraints = [*base, extra]
        vertices = _vertices(constraints, variables)
        cells.append(dict(classification=classification, constraints=constraints,
                          nonempty=bool(vertices),
                          vertices=[[str(x) for x in point] for point in vertices]))
    if mutation == 'R605_COLLAPSE_MIXED_CLASS':
        cells = [cell for cell in cells if cell['classification'] != 'VIOLATION']
    return dict(status='EXACT_DBM_DIFFERENCE_SPLIT', parent_class='STATE_CLASS_0',
                split_at=split_at, cells=cells)


def _observation_groups(histories):
    groups = {}
    for row in histories:
        key = (tuple(row['word']), row['completion_time'])
        groups.setdefault(key, []).append(row['history_id'])
    return [dict(word=list(word), completion_time=time, members=sorted(members))
            for (word, time), members in sorted(groups.items())]


def run_r606(model, case, mutation=None):
    """Replay every witness and solve the root-weight coupled rational LP."""
    if mutation not in (None, 'R606_DROP_FAULT_HISTORY'):
        raise ValueError('unknown R6-06 mutation')
    histories = []
    for witness in case['witnesses']:
        history = witness['history']
        result = replay(model, history)
        if result['status'] != 'REPLAYED_HISTORY':
            return dict(status='INVALID_INPUT_OR_HISTORY',
                        invalid_history=witness['history_id'])
        events = history['fires']
        hypothesis = ('FAULT' if any(model['transitions'][e['transition']]['fault']
                                    for e in events) else 'NORMAL')
        histories.append(dict(
            history_id=witness['history_id'], hypothesis=hypothesis,
            word=result['omega_c'][0], completion_time=result['completion_time'],
            events=[dict(transition=e['transition'], at=str(F(e['at']))) for e in events],
            trace=result['trace']))
    if mutation == 'R606_DROP_FAULT_HISTORY':
        histories = [row for row in histories if row['hypothesis'] != 'FAULT']
    first_names = [witness['history']['fires'][0]['transition'] for witness in case['witnesses']]
    normal_weight = sum((F(model['transitions'][name]['weight']) for name in first_names
                         if not model['transitions'][name]['fault']), F(0))
    fault_weight = sum((F(model['transitions'][name]['weight']) for name in first_names
                        if model['transitions'][name]['fault']), F(0))
    solution = solve_square([[F(1), F(1), F(1)],
                             [fault_weight, -normal_weight, F(0)]])
    if solution is None:
        raise ValueError('coupled history LP is singular')
    return dict(status='LOSSLESS_HISTORY_LP', histories=histories,
                observation_groups=_observation_groups(histories),
                lp_solution=dict(normal=str(solution[0]), fault=str(solution[1])))


def _tree_candidates(model, marking, activation, now):
    enabled = {name for name, transition in model['transitions'].items()
               if all(marking.get(p, 0) >= w for p, w in transition['pre'].items())}
    immediate = sorted(name for name in enabled if model['transitions'][name]['immediate'])
    if immediate:
        return enabled, [(name, now) for name in immediate]
    deadline = min([F(model['H_A']),
                    *[activation[name] + F(model['transitions'][name]['interval'][1])
                      for name in enabled]])
    candidates = []
    for name in sorted(enabled):
        lower, upper = map(F, model['transitions'][name]['interval'])
        start = max(now, activation[name] + lower)
        stop = min(deadline, activation[name] + upper)
        for tick in range(math.ceil(start), math.floor(stop) + 1):
            candidates.append((name, F(tick)))
    return enabled, candidates


def _tree_weight(model, name, hypothesis, mutation):
    transition = model['transitions'][name]
    if mutation is None and hypothesis is not None and 'weight_by_fault' in transition:
        return F(transition['weight_by_fault'][hypothesis])
    return F(transition.get('weight', 1))


def run_r607(model, case, mutation=None):
    """Propagate exact rational joint mass over a finite integer-time PN tree."""
    if mutation not in (None, 'R607_IGNORE_HISTORY_DENSITY'):
        raise ValueError('unknown R6-07 mutation')
    budget = case['budget']
    if type(budget) is not int or budget < 1:
        raise ValueError('positive integer node budget required')
    root_marking = dict(model['initial'])
    initial_activation = {name: F(0) for name, transition in model['transitions'].items()
                          if all(root_marking.get(p, 0) >= w for p, w in transition['pre'].items())}
    queue = deque([((), root_marking, F(0), None, (), F(1), initial_activation)])
    nodes = []
    categories = defaultdict(F)
    while queue and len(nodes) < budget:
        path, marking, now, hypothesis, word, probability, activation = queue.popleft()
        complete = all(marking.get(p, 0) >= w for p, w in model['completion_marking'].items())
        enabled, candidates = _tree_candidates(model, marking, activation, now)
        terminal = 'FIRST_COMPLETION' if complete else 'DEADLOCK' if not enabled else None
        node = dict(path=list(path), marking=marking, hypothesis=hypothesis,
                    time=str(now), mass=str(probability),
                    clock_activations={name: str(activation[name]) for name in sorted(activation)},
                    clock_ages={name: str(now - activation[name]) for name in sorted(activation)},
                    terminal=terminal, children=[])
        nodes.append(node)
        if terminal:
            categories[(hypothesis, terminal, word,
                        str(now) if complete else None)] += probability
            continue
        weights = {name: _tree_weight(model, name, hypothesis, mutation)
                   for name, _time in candidates}
        normalizer = sum(weights.values(), F(0))
        option_counts = defaultdict(int)
        for name, _time in candidates:
            option_counts[name] += 1
        for name, at in candidates:
            transition = model['transitions'][name]
            middle = {p: marking.get(p, 0) - transition['pre'].get(p, 0) for p in marking}
            after = {p: middle.get(p, 0) + transition['post'].get(p, 0)
                     for p in set(middle) | set(transition['post'])}
            post_enabled = {other for other, t in model['transitions'].items()
                            if all(after.get(p, 0) >= w for p, w in t['pre'].items())}
            mid_enabled = {other for other, t in model['transitions'].items()
                           if all(middle.get(p, 0) >= w for p, w in t['pre'].items())}
            keep = (enabled & mid_enabled & post_enabled) - {name}
            new_activation = {other: activation[other] if other in keep else at
                              for other in post_enabled}
            child_hypothesis = 'FAULT' if hypothesis == 'FAULT' or transition['fault'] else 'NORMAL'
            child_probability = probability * weights[name] / normalizer / option_counts[name]
            label = transition['label']
            child_word = word if label is None else (*word, label)
            node['children'].append(dict(
                transition=name, at=str(at), mass=str(child_probability),
                persistent_clocks=sorted(keep),
                fired_clock_ages={other: str(at - activation[other]) for other in sorted(activation)}))
            queue.append(((*path, name), after, at, child_hypothesis, child_word,
                          child_probability, new_activation))
    frontier = [dict(path=list(path), time=str(now), hypothesis=hypothesis,
                     mass=str(probability)) for path, marking, now, hypothesis,
                word, probability, activation in queue]
    resolved = sum(categories.values(), F(0))
    unresolved = sum((item[5] for item in queue), F(0))
    if resolved + unresolved != 1:
        raise ArithmeticError('joint tree mass not conserved')
    return dict(status='UNRESOLVED' if queue else 'EXACT_JOINT_DENSITY_TREE',
                resolved=str(resolved), unresolved=str(unresolved),
                categories=[dict(hypothesis=h, terminal=t, word=list(w), completion_time=time,
                                 mass=str(mass))
                            for (h, t, w, time), mass in sorted(
                                categories.items(), key=lambda item: (item[0][0], item[0][1],
                                                                      item[0][2], str(item[0][3])))],
                frontier=frontier, nodes=nodes)


def _comparison_output(component_id, output):
    if component_id == 'R6-07':
        return {key: output[key] for key in
                ('status', 'resolved', 'unresolved', 'categories', 'frontier')}
    if component_id != 'R6-06':
        return output
    # The subject stores full replay traces for audit; the independent absolute
    # reference intentionally has a different trace representation.  Compare
    # every lossless semantic field while excluding only that representation.
    result = dict(output)
    result['histories'] = [{key: value for key, value in row.items() if key != 'trace'}
                           for row in output.get('histories', [])]
    return result


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    """Compute subject/reference agreement and specific-mutation detection."""
    subject_matches_oracle = (_comparison_output(component_id, subject_output) ==
                              _comparison_output(component_id, oracle_output))
    mutation_detected = (not isinstance(mutated_output, Exception) and
                         mutated_output != subject_output)
    trace = (subject_output.get('cells') or subject_output.get('histories') or
             subject_output.get('nodes') or [])
    passed = subject_matches_oracle and mutation_detected
    return dict(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        actual_network_trace=trace,
        subject_output=subject_output,
        oracle_output=oracle_output,
        invariant_verdict='COMPONENT_REGRESSION_PASS' if passed else 'COMPONENT_REGRESSION_FAIL',
        mutation_patch=mutation_patch(mutation_id),
        mutation_detected=mutation_detected,
        mutation_raised=isinstance(mutated_output, Exception),
        coverage_limitations=_LIMITATIONS[component_id],
    )
