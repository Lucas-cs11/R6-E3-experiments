"""Exact conditional interval evaluator. This module does not authenticate evidence."""
from fractions import Fraction as F


class InvalidInput(ValueError):
    pass


class InvalidEvidence(ValueError):
    pass


def rational(value):
    if type(value) not in (int, str, F):
        raise InvalidInput('exact rational required')
    try:
        return F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise InvalidInput('malformed rational') from exc


def intersection(a, b, name):
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if lo > hi:
        raise InvalidEvidence(f'{name}: empty intersection')
    return lo, hi


def bound(data, name, ceiling=F(1)):
    if not isinstance(data, dict) or set(data) != {'low', 'high'}:
        raise InvalidInput(f'{name}: expected low/high')
    lo, hi = rational(data['low']), rational(data['high'])
    if lo > hi:
        raise InvalidInput(f'{name}: reversed bounds')
    return intersection((lo, hi), (F(0), ceiling), name)


def evaluate(data):
    """Condition only on supplied bounds, not on their asserted provenance.

    For each hypothesis, categories are mutually exclusive. When a frontier
    interval is supplied, categories plus frontier must sum exactly to q_i;
    otherwise unlisted mass is allowed. Model/path authenticity is not checked.
    """
    try:
        pi = [rational(data[k]) for k in ('pi0', 'pi1')]
        eps, delta, gamma = (rational(data[k]) for k in ('epsilon', 'delta', 'gamma'))
        vc = str(data['v_c'])
        if min(pi) <= 0 or sum(pi) != 1 or not (0 <= eps <= F(1, 2) and 0 < delta < F(1, 2) and 0 <= gamma <= 1) or vc not in {'0', '1', 'PERP'}:
            raise InvalidInput('invalid decision specification')
        pe = bound(data['Pe'], 'Pe', min(pi))
        coverage = bound(data['Gamma'], 'Gamma')
        q = [bound(data[f'q{i}'], f'q{i}') for i in range(2)]
        partitions = []
        for i in range(2):
            key = f'Q{i}_Y'
            raw = data.get(f'categories{i}', {})
            if not isinstance(raw, dict) or any(type(k) is not str or not k or k == '@frontier' for k in raw):
                raise InvalidInput('invalid category map')
            if key in data:
                if f'categories{i}' in data:
                    raise InvalidInput('ambiguous category definitions')
                raw = {'B': data[key]}
            cells = {k: bound(v, f'{key}:{k}') for k, v in raw.items()}
            frontier = f'frontier{i}'
            if frontier in data:
                cells['@frontier'] = bound(data[frontier], frontier)
            low = sum(a for a, _ in cells.values())
            upper = sum(b for _, b in cells.values()) if frontier in data else F(1)
            q[i] = intersection(q[i], (low, upper), f'partition{i}')
            partitions.append(cells)
        q0, q1 = q
        q = [intersection(q0, (1-q1[1], 1-q1[0]), 'q0+q1'),
             intersection(q1, (1-q0[1], 1-q0[0]), 'q0+q1')]
        tightened = []
        for i, cells in enumerate(partitions):
            lo_sum = sum(a for a, _ in cells.values())
            hi_sum = sum(b for _, b in cells.values())
            tightened.append({k: intersection((a, b),
                (q[i][0] - (hi_sum-b) if '@frontier' in cells else F(0),
                 q[i][1] - (lo_sum-a)), f'category{i}:{k}') for k, (a,b) in cells.items()})
        if any(b == 0 for _, b in q):
            app, verdict = '0', None
        elif any(a == 0 for a, _ in q):
            app, verdict = 'PERP', None
        elif vc == '0' or pe[0] > eps or coverage[1] < gamma:
            app, verdict = '1', '0'
        elif vc == '1' and pe[1] <= eps and coverage[0] >= gamma:
            app, verdict = '1', '1'
        else:
            app, verdict = '1', 'PERP'
        return dict(status='CONDITIONAL_ONLY', certified=False, a_P=app, conditional_verdict=verdict,
                    q=q, categories=tightened, Pe=pe, Gamma=coverage)
    except (InvalidInput, KeyError, TypeError, AttributeError) as exc:
        return dict(status='INVALID_INPUT', certified=False, reason=str(exc))
    except InvalidEvidence as exc:
        return dict(status='INVALID_EVIDENCE', certified=False, reason=str(exc))
