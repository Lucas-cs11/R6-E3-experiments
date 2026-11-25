"""R6-05..07 model-driven component implementations, committed incrementally."""
from fractions import Fraction as F
from itertools import combinations

from ap41_polytope import solve_square
from timed_trace import replay


_PATCHES = {
    'R605_COLLAPSE_MIXED_CLASS': dict(
        component_id='R6-05', old='retain both exact difference cells',
        new='discard VIOLATION cell from a mixed parent class'),
    'R606_DROP_FAULT_HISTORY': dict(
        component_id='R6-06', old='retain every validated normal/fault history',
        new='drop FAULT history after identical observation grouping'),
}

_LIMITATIONS = {
    'R6-05': 'Two-variable bounded DBM difference cells with rational open/closed boundaries.',
    'R6-06': 'Explicit finite histories and a two-coordinate coupled rational LP on shared root weights.',
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


def _comparison_output(component_id, output):
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
