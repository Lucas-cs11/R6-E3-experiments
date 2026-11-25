"""Independent R6-08 reference using rational LP vertices, never the subject evaluator."""
from fractions import Fraction as F
from collections import Counter, defaultdict
import hashlib
import json

from ap41_polytope import project
from immediate_mass_reference import distribution


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


def _reference_algebra(data):
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


def _reference_metrics(data, evidence):
    model_bytes = evidence['model_bytes'].encode('utf-8')
    pin = evidence['model_sha256']
    if hashlib.sha256(model_bytes).hexdigest() != pin:
        return dict(status='INVALID_EVIDENCE', certified=False, reason='MODEL_SHA_MISMATCH')
    model = json.loads(model_bytes)
    ledger = evidence['ledger']
    actual = Counter()
    for row in ledger['categories']:
        actual[(bool(row['hypothesis']), row['terminal'], tuple(row['word']))] += F(row['mass'])
    if dict(actual) != dict(distribution(model)):
        return dict(status='INVALID_EVIDENCE', certified=False, reason='INDEPENDENT_MASS_MISMATCH')
    joint = defaultdict(lambda: [F(0), F(0)])
    for row in ledger['categories']:
        joint[tuple(row['word'])][row['hypothesis']] += F(row['mass'])
    q = [sum((mass[i] for mass in joint.values()), F(0)) for i in range(2)]
    if q[0] == 0 or q[1] == 0:
        return dict(status='NOT_APPLICABLE_ZERO_HYPOTHESIS', certified=False,
                    q=list(map(str, q)))
    pi1, delta = F(data['pi1']), F(data['delta'])
    error = coverage = F(0)
    atoms = []
    for word, mass in sorted(joint.items()):
        normal = (1 - pi1) * mass[0] / q[0]
        faulty = pi1 * mass[1] / q[1]
        mixture = normal + faulty
        reliable = max(normal, faulty) >= (1 - delta) * mixture
        error += min(normal, faulty)
        if reliable:
            coverage += mixture
        atoms.append(dict(word=word, joint=list(map(str, mass)),
                          mixture=str(mixture), reliable=reliable))
    ledger_bytes = json.dumps(ledger, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return dict(status='EXACT_IMMEDIATE_WORD_METRICS', certified=False,
                model_sha256=pin, ledger_sha256=hashlib.sha256(ledger_bytes).hexdigest(),
                resolved=ledger['resolved'], unresolved=ledger['unresolved'],
                q=list(map(str, q)), observation='external visible word only',
                pi1=str(pi1), delta=str(delta), Pe=str(error), Gamma=str(coverage),
                atoms=atoms)


def reference_r608(data):
    """Independent interval decision plus model-bound exact metric reconstruction."""
    algebraic = _reference_algebra(data)
    if algebraic['status'] != 'CONDITIONAL_ONLY' or 'immediate_evidence' not in data:
        return algebraic
    metrics = _reference_metrics(data, data['immediate_evidence'])
    if metrics['status'] != 'EXACT_IMMEDIATE_WORD_METRICS':
        return dict(status=metrics['status'], certified=False,
                    reason=metrics.get('reason'), certificate=None, algebraic=algebraic)
    bounded = dict(data)
    bounded['Pe'] = {'low': metrics['Pe'], 'high': metrics['Pe']}
    bounded['Gamma'] = {'low': metrics['Gamma'], 'high': metrics['Gamma']}
    result = _reference_algebra(bounded)
    result['certificate'] = metrics
    result['certified'] = False
    return result
