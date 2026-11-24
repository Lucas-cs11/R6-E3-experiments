"""Exact conditional distribution by recursive backward evaluation.

Finite immediate-only regression domain; cycles or depth exhaustion yield no
reference result. This implementation does not import the forward propagator.
"""
from collections import Counter
from fractions import Fraction as F


def distribution(net, max_depth=12):
    places = sorted(net['initial'])
    transitions = net['transitions']
    if any(t['immediate'] is not True or t['interval'] != [0, 0] for t in transitions.values()):
        raise ValueError('outside immediate-only reference domain')

    def recurse(marking, remaining):
        if all(marking[places.index(p)] >= n for p,n in net['completion_marking'].items()):
            return {(False,'FIRST_COMPLETION',()): F(1)}
        enabled = [t for t in transitions.values()
                   if all(x >= t['pre'].get(p,0) for p,x in zip(places,marking))]
        if not enabled:
            return {(False,'DEADLOCK',()): F(1)}
        if remaining == 0:
            raise ValueError('reference depth exhausted')
        weights = [F(t['weight']) for t in enabled]
        normalizer = sum(weights)
        result = Counter()
        for edge,weight in zip(enabled,weights):
            after = tuple(x + edge['post'].get(p,0) - edge['pre'].get(p,0) for p,x in zip(places,marking))
            prefix = () if edge['label'] is None else (edge['label'],)
            for (f,terminal,word),mass in recurse(after, remaining-1).items():
                result[(f or edge['fault'],terminal,prefix+word)] += weight*mass/normalizer
        return result

    return recurse(tuple(net['initial'][p] for p in places), max_depth)
