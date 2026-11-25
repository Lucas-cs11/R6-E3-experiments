"""Independent R6-08 reference using rational LP vertices, never the subject evaluator."""
from fractions import Fraction as F

from ap41_polytope import project


class _InvalidInput(ValueError):
    pass


class _InvalidEvidence(ValueError):
    pass


def _number(value):
    if type(value) not in (int, str, F):
        raise _InvalidInput('exact rational required')
    try:
        return F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise _InvalidInput('malformed rational') from exc


def _pair(value):
    if not isinstance(value, dict) or set(value) != {'low', 'high'}:
        raise _InvalidInput('expected low/high')
    low, high = _number(value['low']), _number(value['high'])
    if low > high:
        raise _InvalidInput('reversed bounds')
    return low, high


def _natural(value, ceiling):
    low, high = _pair(value)
    low, high = max(low, F(0)), min(high, ceiling)
    if low > high:
        raise _InvalidEvidence('empty natural-domain intersection')
    return low, high


def reference_r608(data):
    """Compute exact feasible extrema and the conditional three-valued decision."""
    try:
        pi0, pi1 = _number(data['pi0']), _number(data['pi1'])
        epsilon, delta, gamma = (_number(data[key]) for key in ('epsilon', 'delta', 'gamma'))
        vc = str(data['v_c'])
        if (min(pi0, pi1) <= 0 or pi0 + pi1 != 1 or
                not (0 <= epsilon <= F(1, 2) and 0 < delta < F(1, 2) and 0 <= gamma <= 1) or
                vc not in {'0', '1', 'PERP'}):
            raise _InvalidInput('invalid decision specification')
        pe = _natural(data['Pe'], min(pi0, pi1))
        coverage = _natural(data['Gamma'], F(1))
        q = [_pair(data[f'q{i}']) for i in range(2)]
        groups = []
        closed = []
        for i in range(2):
            alias = f'Q{i}_Y'
            categories_key = f'categories{i}'
            if alias in data and categories_key in data:
                raise _InvalidInput('ambiguous categories')
            raw = ({'B': data[alias]} if alias in data else data.get(categories_key, {}))
            if not isinstance(raw, dict) or any(type(key) is not str or not key or key == '@frontier'
                                               for key in raw):
                raise _InvalidInput('invalid category map')
            cells = {key: _pair(value) for key, value in raw.items()}
            frontier = f'frontier{i}'
            closed.append(frontier in data)
            if frontier in data:
                cells['@frontier'] = _pair(data[frontier])
            groups.append(cells)
        feasible = project(q, groups, closed)
        if feasible is None:
            raise _InvalidEvidence('empty joint feasible region')
    except _InvalidEvidence as exc:
        return dict(status='INVALID_EVIDENCE', certified=False, reason=str(exc))
    except (_InvalidInput, KeyError, TypeError, AttributeError) as exc:
        return dict(status='INVALID_INPUT', certified=False, reason=str(exc))

    q0, q1 = feasible['q']
    if q0[1] == 0 or q1[1] == 0:
        applicability, verdict = '0', None
    elif q0[0] == 0 or q1[0] == 0:
        applicability, verdict = 'PERP', None
    elif vc == '0' or pe[0] > epsilon or coverage[1] < gamma:
        applicability, verdict = '1', '0'
    elif vc == '1' and pe[1] <= epsilon and coverage[0] >= gamma:
        applicability, verdict = '1', '1'
    else:
        applicability, verdict = '1', 'PERP'
    return dict(status='CONDITIONAL_ONLY', certified=False, a_P=applicability,
                conditional_verdict=verdict, q=feasible['q'],
                categories=feasible['categories'], Pe=pe, Gamma=coverage)
