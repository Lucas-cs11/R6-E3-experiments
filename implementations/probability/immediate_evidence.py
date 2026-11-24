"""Bind a restricted immediate-net mass ledger to externally pinned inputs."""
import hashlib
import json
from collections import Counter
from fractions import Fraction

from immediate_mass import propagate


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(ledger):
    return json.dumps(ledger, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_object(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate JSON key')
    return obj


def verify(model_bytes, ledger_bytes, *, model_sha256, budget, reference):
    """Pins and independent reference come from the verifier, not the ledger.

    Even success only establishes restricted model/ledger agreement, not AP41.
    """
    def result(status, **details):
        return dict(status=status, certified=False, **details)

    if digest(model_bytes) != model_sha256:
        return result('INVALID_EVIDENCE', reason='MODEL_SHA_MISMATCH')
    try:
        model = json.loads(model_bytes, object_pairs_hook=unique_object)
        rebuilt = propagate(model, budget)
    except (ValueError, TypeError, KeyError, ZeroDivisionError, AttributeError) as exc:
        return result('INVALID_INPUT_OR_UNSUPPORTED', reason=str(exc))
    try:
        claimed = json.loads(ledger_bytes, object_pairs_hook=unique_object)
        if canonical(claimed) != canonical(rebuilt):
            return result('INVALID_EVIDENCE', reason='RAW_LEDGER_REPLAY_MISMATCH')
    except (ValueError, TypeError) as exc:
        return result('INVALID_EVIDENCE', reason=str(exc))
    details = dict(model_sha256=model_sha256, ledger_sha256=digest(ledger_bytes),
                   resolved=rebuilt['resolved'], unresolved=rebuilt['unresolved'])
    if rebuilt['frontier']:
        return result('UNRESOLVED', **details)
    try:
        expected = reference(model)
    except (ValueError, RecursionError) as exc:
        return result('REFERENCE_UNRESOLVED', reason=str(exc), **details)
    actual = Counter()
    for row in rebuilt['categories']:
        actual[(bool(row['hypothesis']), row['terminal'], tuple(row['word']))] += Fraction(row['mass'])
    if dict(actual) != dict(expected):
        return result('INVALID_EVIDENCE', reason='INDEPENDENT_MASS_MISMATCH', **details)
    return result('IMMEDIATE_MASS_REPLAY_MATCH', **details)
