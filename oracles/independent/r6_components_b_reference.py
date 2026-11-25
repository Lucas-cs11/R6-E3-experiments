"""Independent rational references for R6-05..07; no subject-module imports."""
from fractions import Fraction as Q
from itertools import combinations


def _coefficients(expression, variables):
    if '-' in expression:
        left, right = expression.split('-', 1)
        result = [Q(0)] * len(variables)
        result[variables.index(left)] = 1
        result[variables.index(right)] = -1
        return result
    result = [Q(0)] * len(variables)
    result[variables.index(expression)] = 1
    return result


def _constraints(model, split_at):
    state = model['state_class']
    variables = state['variables']
    result = []
    for name in variables:
        low, high = state['variable_bounds'][name]
        result += [dict(expression=name, op='>=', bound=str(low)),
                   dict(expression=name, op='<=', bound=str(high))]
    difference = state['difference']
    expression = difference['expression']
    result += [dict(expression=expression, op='>=', bound=str(difference['low'])),
               dict(expression=expression, op='<=', bound=str(difference['high']))]
    return result


def _accept(rows, point, variables):
    for row in rows:
        coefficients = _coefficients(row['expression'], variables)
        value = sum((a * x for a, x in zip(coefficients, point)), Q(0))
        bound = Q(row['bound'])
        if row['op'] == '>=' and not value >= bound:
            return False
        if row['op'] == '<=' and not value <= bound:
            return False
        if row['op'] == '>' and not value > bound:
            return False
    return True


def _vertices(rows, variables):
    vertices = set()
    for left, right in combinations(rows, 2):
        a, b = left, right
        ca = _coefficients(a['expression'], variables)
        cb = _coefficients(b['expression'], variables)
        determinant = ca[0] * cb[1] - ca[1] * cb[0]
        if determinant == 0:
            continue
        rhs_a, rhs_b = Q(a['bound']), Q(b['bound'])
        point = ((rhs_a * cb[1] - rhs_b * ca[1]) / determinant,
                 (ca[0] * rhs_b - cb[0] * rhs_a) / determinant)
        if _accept(rows, point, variables):
            vertices.add(point)
    return sorted(vertices)


def reference_r605(model, case):
    """Independent exact DBM cells via determinant-based vertex enumeration."""
    variables = model['state_class']['variables']
    split_at = str(case['split_at'])
    difference = model['state_class']['difference']['expression']
    base = _constraints(model, split_at)
    cells = []
    for classification, operator in (('NON_VIOLATION', '<='), ('VIOLATION', '>')):
        rows = [*base, dict(expression=difference, op=operator, bound=split_at)]
        vertices = _vertices(rows, variables)
        cells.append(dict(classification=classification, constraints=rows,
                          nonempty=bool(vertices),
                          vertices=[[str(value) for value in point] for point in vertices]))
    return dict(status='EXACT_DBM_DIFFERENCE_SPLIT', parent_class='STATE_CLASS_0',
                split_at=split_at, cells=cells)
