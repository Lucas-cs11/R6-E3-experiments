"""E3-04 unified engine: real TPN model data interface and applicability.

Loads models from the frozen RMT-FMS generator or from E3 JSON fixtures and
checks every field the engine requires, returning per-field inspectable
reasons.  ``supported`` is never a bare boolean: each rejection names the
missing or invalid field and the observed value.
"""
import json
from fractions import Fraction as F


REQUIRED_MODEL_FIELDS = (
    'places', 'transitions', 'arcs', 'initial_marking', 'completion_markings',
    'L', 'H',
)
REQUIRED_TRANSITION_FIELDS = (
    'label', 'is_fault', 'is_adjustable', 'interval', 'immediate',
)
DISTRIBUTION_VERSIONS = ('deterministic', 'uniform', 'piecewise_rational')


def _reason(field, detail, observed=None):
    return {'field': field, 'detail': detail, 'observed': observed}


def from_generator_net(net, L, H, distribution_version='deterministic'):
    """Adapt a generator TPN object into the engine's plain-dict form."""
    transitions = {}
    for name, t in net.transitions.items():
        transitions[name] = {
            'label': t.label or None,
            'is_fault': bool(t.is_fault),
            'is_adjustable': bool(t.is_adjustable),
            'interval': [str(t.interval.earliest), str(t.interval.latest)],
            'immediate': t.interval.earliest == t.interval.latest == 0,
        }
    places = sorted(net.places)
    pre = {name: {} for name in transitions}
    post = {name: {} for name in transitions}
    for arc in net.arcs:
        if arc.from_node in transitions and arc.to_node not in transitions:
            post[arc.from_node][arc.to_node] = post[arc.from_node].get(arc.to_node, 0) + 1
        elif arc.to_node in transitions and arc.from_node not in transitions:
            pre[arc.to_node][arc.from_node] = pre[arc.to_node].get(arc.from_node, 0) + 1
        else:
            raise ValueError(f'unsupported arc shape {arc.from_node}->{arc.to_node}')
    for name in transitions:
        transitions[name]['pre'] = pre[name]
        transitions[name]['post'] = post[name]
    return {
        'places': places,
        'transitions': transitions,
        'arcs': [[a.from_node, a.to_node] for a in net.arcs],
        'initial_marking': dict(net.initial_marking),
        'completion_markings': [dict(m) for m in net.completion_markings],
        'L': str(L), 'H': str(H),
        'distribution_version': distribution_version,
    }


def load_json_model(path):
    model = json.loads(path.read_text() if hasattr(path, 'read_text') else open(path).read())
    return model


def check_applicability(model):
    """Return {'supported': bool, 'reasons': [...], 'checked_fields': [...]}.

    Every rejection lists the exact field and observed value; acceptance
    lists every field that was actually verified.
    """
    reasons = []
    checked = []
    if not isinstance(model, dict):
        return {'supported': False, 'reasons': [_reason('model', 'not a dict', type(model).__name__)],
                'checked_fields': []}
    for field in REQUIRED_MODEL_FIELDS:
        if field not in model:
            reasons.append(_reason(field, 'missing required field'))
        else:
            checked.append(field)
    if reasons:
        return {'supported': False, 'reasons': reasons, 'checked_fields': checked}

    places = model['places']
    if not isinstance(places, list) or not places or len(set(places)) != len(places):
        reasons.append(_reason('places', 'must be a non-empty list of unique names', places[:3] if isinstance(places, list) else places))
    initial = model['initial_marking']
    if not isinstance(initial, dict) or any(type(v) is not int or v < 0 for v in initial.values()):
        reasons.append(_reason('initial_marking', 'must map places to non-negative integers'))
    elif isinstance(places, list) and set(initial) - set(places):
        reasons.append(_reason('initial_marking', 'tokens on undeclared places', sorted(set(initial) - set(places))[:3]))
    completions = model['completion_markings']
    if not isinstance(completions, list) or not completions or any(not isinstance(m, dict) or not m for m in completions):
        reasons.append(_reason('completion_markings', 'must be a non-empty list of non-empty predicates'))

    transitions = model['transitions']
    if not isinstance(transitions, dict) or not transitions:
        reasons.append(_reason('transitions', 'must be a non-empty dict'))
        transitions = {}
    for name, t in transitions.items():
        if not isinstance(t, dict):
            reasons.append(_reason(f'transitions.{name}', 'must be a dict'))
            continue
        for field in REQUIRED_TRANSITION_FIELDS:
            if field not in t:
                reasons.append(_reason(f'transitions.{name}.{field}', 'missing required field'))
        interval = t.get('interval')
        if interval is not None:
            try:
                lo, hi = (F(str(interval[0])), F(str(interval[1])))
                if not (F(0) <= lo <= hi):
                    reasons.append(_reason(f'transitions.{name}.interval', 'requires 0<=lo<=hi', interval))
                if t.get('immediate') and (lo != 0 or hi != 0):
                    reasons.append(_reason(f'transitions.{name}.immediate', 'immediate requires interval [0,0]', interval))
            except (TypeError, ValueError, IndexError):
                reasons.append(_reason(f'transitions.{name}.interval', 'unparseable interval', interval))
        for side in ('pre', 'post'):
            arcs = t.get(side, {})
            if not isinstance(arcs, dict) or any(type(w) is not int or w <= 0 for w in arcs.values()):
                reasons.append(_reason(f'transitions.{name}.{side}', 'weights must be positive integers'))
            elif isinstance(places, list) and set(arcs) - set(places):
                reasons.append(_reason(f'transitions.{name}.{side}', 'arc on undeclared place',
                                       sorted(set(arcs) - set(places))[:3]))
    try:
        L, H = F(str(model['L'])), F(str(model['H']))
        if not (F(0) < L <= H):
            reasons.append(_reason('L/H', 'requires 0<L<=H', [model['L'], model['H']]))
    except (TypeError, ValueError):
        reasons.append(_reason('L/H', 'unparseable', [model.get('L'), model.get('H')]))
    version = model.get('distribution_version', 'deterministic')
    if version not in DISTRIBUTION_VERSIONS:
        reasons.append(_reason('distribution_version', f'must be one of {DISTRIBUTION_VERSIONS}', version))
    if not any(t.get('is_fault') for t in transitions.values() if isinstance(t, dict)):
        reasons.append(_reason('transitions', 'no fault transition declared; H1 would be empty'))
    if isinstance(initial, dict) and isinstance(completions, list):
        for index, goal in enumerate(completions):
            if isinstance(goal, dict) and goal and all(initial.get(p, 0) >= w for p, w in goal.items()):
                reasons.append(_reason('completion_markings',
                                       'initial marking already satisfies a completion predicate',
                                       {'index': index, 'predicate': goal}))
                break
    return {'supported': not reasons, 'reasons': reasons, 'checked_fields': checked,
            'fault_transitions': sorted(n for n, t in transitions.items() if isinstance(t, dict) and t.get('is_fault'))}
