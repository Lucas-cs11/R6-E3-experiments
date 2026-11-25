"""Independent references for R6 component integration tests.

Concrete histories and endpoint suffixes use absolute-date reconstruction.  The
immediate probability reference is a separate BFS over concrete markings and
never imports the subject's forward propagator.
"""
from collections import defaultdict, deque
from fractions import Fraction as F

from absolute_schedule import assess, date


def _noncompletion(model, marking):
    predicate = model.get('noncompletion_marking', {})
    return bool(predicate) and all(marking.get(p, 0) >= w for p, w in predicate.items())


def _reference_mass(model, budget):
    initial = dict(model['initial'])
    goal = model['completion_marking']
    edges = []
    for name, transition in sorted(model['transitions'].items()):
        edges.append((name, transition))
    queue = deque([((), initial, False, (), F(1))])
    masses = defaultdict(F)
    visited = 0
    while queue and visited < budget:
        path, marking, faulty, word, probability = queue.popleft()
        visited += 1
        complete = all(marking.get(p, 0) >= w for p, w in goal.items())
        enabled = [] if complete else [
            item for item in edges
            if all(marking.get(p, 0) >= w for p, w in item[1]['pre'].items())]
        if complete:
            terminal = 'FIRST_COMPLETION'
        elif not enabled and _noncompletion(model, marking):
            terminal = 'NON_COMPLETION_TERMINAL'
        elif not enabled:
            terminal = 'DEADLOCK'
        else:
            terminal = None
        if terminal:
            masses[(int(faulty), terminal, word)] += probability
            continue
        normalizer = sum((F(item[1]['weight']) for item in enabled), F(0))
        for name, transition in enabled:
            after = {p: marking.get(p, 0) - transition['pre'].get(p, 0)
                     + transition['post'].get(p, 0)
                     for p in set(marking) | set(transition['post'])}
            child_probability = probability * F(transition['weight']) / normalizer
            label = transition['label']
            queue.append(((*path, name), after, faulty or transition['fault'],
                          word if label is None else (*word, label), child_probability))
    frontier = [dict(path=path, marking=marking, fault_already_seen=faulty,
                     word=word, mass=str(probability))
                for path, marking, faulty, word, probability in queue]
    resolved = sum(masses.values(), F(0))
    unresolved = sum((row[-1] for row in queue), F(0))
    if resolved + unresolved != 1:
        raise ArithmeticError('independent path mass not conserved')
    return dict(status='UNRESOLVED' if queue else 'EXACT_IMMEDIATE_PATH_MASS',
                resolved=str(resolved), unresolved=str(unresolved),
                categories=[dict(hypothesis=h, terminal=t, word=w, mass=str(p))
                            for (h, t, w), p in sorted(masses.items())],
                frontier=frontier)


def _reference_endpoint(model, prefix, budget):
    root = assess(model, prefix)
    if root['status'] != 'REPLAYED_HISTORY':
        return dict(status='INVALID_PREFIX', root=root)
    horizon = date(model['H_A'])
    if date(prefix['end']) != horizon:
        return dict(status='NOT_AT_HORIZON', root=root)

    def extend(suffix):
        return assess(model, {
            'end': str(horizon),
            'fires': [*prefix['fires'],
                      *[{'transition': name, 'at': str(horizon)} for name in suffix]]})

    queue = deque([()])
    terminals = []
    visited = 0
    while queue and visited < budget:
        suffix = queue.popleft()
        result = root if not suffix else extend(suffix)
        visited += 1
        if result['status'] != 'REPLAYED_HISTORY':
            raise RuntimeError(f'independent endpoint replay failed: {result}')
        if result['terminal'] != 'FRONTIER':
            terminals.append(dict(suffix=suffix, result=result))
            continue
        ready = result['endpoint_enabled_to_fire']
        immediate = [name for name in ready if model['transitions'][name]['immediate']]
        choices = immediate or ready
        if not choices:
            raise RuntimeError('independent endpoint frontier without successor')
        queue.extend((*suffix, name) for name in choices)
    pending = []
    for suffix in queue:
        result = extend(suffix)
        pending.append(dict(suffix=suffix, status='UNRESOLVED', reason='NODE_BUDGET',
                            replayed_terminal=result['terminal'],
                            next_ready=result['endpoint_enabled_to_fire']))
    return dict(status='UNRESOLVED' if pending else 'EXHAUSTED_AT_ENDPOINT_FOR_PREFIX',
                scope='CONCRETE_PREFIX_ONLY', visited=visited,
                terminals=terminals, pending=pending)


def reference_case(component_id, model, case):
    kind = case['kind']
    if kind == 'timed':
        return assess(model, case['history'])
    if kind == 'mass':
        return _reference_mass(model, case['budget'])
    if kind == 'endpoint':
        return _reference_endpoint(model, case['prefix'], case['budget'])
    raise ValueError(f'unsupported reference case kind: {kind}')
