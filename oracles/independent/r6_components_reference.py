"""Independent references for R6 component integration tests.

Concrete histories use the established absolute-date oracle, not the subject
replay.  Immediate roots use the separate backward recursive distribution.
"""
from fractions import Fraction as F

from absolute_schedule import assess
from immediate_mass_reference import distribution


def reference_case(component_id, model, case):
    kind = case['kind']
    if kind == 'timed':
        return assess(model, case['history'])
    if kind == 'mass':
        masses = distribution(model)
        categories = [dict(hypothesis=int(hypothesis), terminal=terminal,
                           word=word, mass=str(mass))
                      for (hypothesis, terminal, word), mass in sorted(masses.items())]
        return dict(status='EXACT_IMMEDIATE_PATH_MASS',
                    resolved=str(sum(masses.values(), F(0))), unresolved='0',
                    categories=categories)
    raise ValueError(f'unsupported reference case kind: {kind}')
