"""Exact path mass for a restricted, all-immediate weighted P/T net.

No continuous clocks or end-to-end AP41 certification are implemented here.
Unexpanded mass stays joint and unclassified rather than being renormalized.
"""
from collections import defaultdict, deque
from fractions import Fraction as F


def propagate(model, budget):
    if type(budget) is not int or budget < 1:
        raise ValueError('positive integer budget required')
    initial = dict(model['initial'])
    if not initial or any(type(n) is not int or n < 0 for n in initial.values()):
        raise ValueError('invalid initial marking')

    def arcs(spec):
        if not isinstance(spec, dict) or spec.keys() - initial.keys() or any(
            type(w) is not int or w <= 0 for w in spec.values()
        ):
            raise ValueError('invalid weighted arcs')
        return spec

    goal = arcs(model['completion_marking'])
    if not goal or all(initial[p] >= w for p, w in goal.items()):
        raise ValueError('completion predicate missing or initially satisfied')
    edges = []
    for name, t in sorted(model['transitions'].items()):
        if t.get('immediate') is not True or t.get('interval') != [0, 0]:
            raise ValueError('unsupported transition: expected immediate [0,0]')
        if type(t['weight']) not in (str, int) or F(t['weight']) <= 0 or type(t['fault']) is not bool:
            raise ValueError('invalid weight or fault flag')
        label = t['label']
        if label is not None and (type(label) is not str or not label):
            raise ValueError('invalid visible label')
        edges.append((name, arcs(t['pre']), arcs(t['post']), F(t['weight']), t['fault'], label))
    queue = deque([((), initial, False, (), F(1))])
    mass = defaultdict(F)
    events = []
    while queue and len(events) < budget:
        path, marking, faulty, word, probability = queue.popleft()
        complete = all(marking[p] >= w for p, w in goal.items())
        enabled = [] if complete else [t for t in edges if all(marking[p] >= w for p, w in t[1].items())]
        terminal = 'FIRST_COMPLETION' if complete else 'DEADLOCK' if not enabled else None
        node = dict(path=path, marking=marking, hypothesis=int(faulty), word=word, mass=str(probability),
                    terminal=terminal, children=[])
        events.append(node)
        if terminal:
            mass[int(faulty), terminal, word] += probability
            continue
        total = sum(t[3] for t in enabled)
        for name, pre, post, weight, fault, label in enabled:
            middle = {p: v-pre.get(p, 0) for p, v in marking.items()}
            after = {p: v+post.get(p, 0) for p, v in middle.items()}
            child_mass = probability * weight / total
            node['children'].append(dict(transition=name, middle=middle, weight=str(weight), mass=str(child_mass)))
            queue.append(((*path, name), after, faulty or fault, word if label is None else (*word, label), child_mass))
    frontier = [dict(path=path, marking=m, fault_already_seen=fault, word=word, mass=str(p))
                for path, m, fault, word, p in queue]
    unresolved = sum((p for *_, p in queue), F(0))
    resolved = sum(mass.values(), F(0))
    if resolved + unresolved != 1:
        raise ArithmeticError('path mass not conserved')
    return dict(status='UNRESOLVED' if queue else 'EXACT_IMMEDIATE_PATH_MASS', resolved=str(resolved),
                unresolved=str(unresolved), events=events, frontier=frontier,
                categories=[dict(hypothesis=i, terminal=t, word=w, mass=str(p))
                            for (i,t,w),p in sorted(mass.items())])
