"""Finite word-observation metrics after a restricted immediate-net replay."""
from collections import defaultdict
from fractions import Fraction as F
import json

from immediate_evidence import verify


def evaluate_word_metrics(model_bytes, ledger_bytes, *, model_sha256, budget, reference, pi1, delta):
    """Report exact metrics only; no model-wide AP41 verdict is issued."""
    try:
        if any(type(v) not in (str, int, F) for v in (pi1, delta)):
            raise ValueError
        pi1, delta = F(pi1), F(delta)
        if not (0 < pi1 < 1 and 0 < delta < F(1, 2)):
            raise ValueError
    except (ValueError, ZeroDivisionError):
        return dict(status='INVALID_INPUT', certified=False, reason='INVALID_PRIOR_OR_DELTA')
    binding = verify(model_bytes, ledger_bytes, model_sha256=model_sha256, budget=budget, reference=reference)
    if binding['status'] != 'IMMEDIATE_MASS_REPLAY_MATCH':
        return binding
    joint = defaultdict(lambda: [F(0), F(0)])
    for row in json.loads(ledger_bytes)['categories']:
        joint[tuple(row['word'])][row['hypothesis']] += F(row['mass'])
    q = [sum((p[i] for p in joint.values()), F(0)) for i in range(2)]
    if q[0] == 0 or q[1] == 0:
        return {**binding, 'status':'NOT_APPLICABLE_ZERO_HYPOTHESIS', 'q':list(map(str,q))}
    error = coverage = F(0)
    atoms = []
    for word, mass in sorted(joint.items()):
        a, b = (1-pi1)*mass[0]/q[0], pi1*mass[1]/q[1]
        mix = a+b
        reliable = max(a,b) >= (1-delta)*mix
        error += min(a,b)
        if reliable:
            coverage += mix
        atoms.append(dict(word=word, joint=list(map(str,mass)), mixture=str(mix), reliable=reliable))
    return {**binding, 'status':'EXACT_IMMEDIATE_WORD_METRICS', 'q':list(map(str,q)),
            'observation':'external visible word only', 'pi1':str(pi1), 'delta':str(delta),
            'Pe':str(error), 'Gamma':str(coverage), 'atoms':atoms}
