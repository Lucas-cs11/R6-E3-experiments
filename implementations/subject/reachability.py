"""Bounded exhaustive exploration of strong-time firing sequences.

Each explored sequence carries symbolic activation steps for every enabled
transition, so its timing constraints form an exact system of difference
constraints on absolute firing dates.  Feasibility and the exact completion
date interval are computed by Bellman-Ford longest/shortest paths — no
earliest-firing approximation.  Exploration is finite only under an explicit
node budget; exhausted budgets stay UNRESOLVED.
"""
from collections import deque
from fractions import Fraction as F

from timed_trace import exact


def _validate(model):
    hp, bc, bd, ha = (exact(model[k]) for k in ('H_psi', 'B_c', 'B_d', 'H_A'))
    if hp < 0 or bc <= 0 or bd < 0 or ha != hp + bc + bd:
        raise ValueError('invalid horizon specification')
    marking = dict(model['initial'])
    if not marking or any(type(x) is not int or x < 0 for x in marking.values()):
        raise ValueError('invalid initial marking')
    edges = {}
    for name, t in model['transitions'].items():
        lo, hi = map(exact, t['interval'])
        if not 0 <= lo <= hi or (t['immediate'] and (lo or hi)):
            raise ValueError('invalid interval')
        edges[name] = (dict(t['pre']), dict(t['post']), lo, hi,
                       t['fault'], t['completion'], t['immediate'], t['label'])
    if 'completion_markings' in model:
        goals = [dict(g) for g in model['completion_markings']]
    else:
        goals = [dict(model['completion_marking'])]
    if not goals or any(not g for g in goals):
        raise ValueError('empty completion predicate')
    return hp, bc, ha, marking, edges, goals


def _enabled(marking, edges):
    return {k for k, e in edges.items() if all(marking.get(p, 0) >= w for p, w in e[0].items())}


def _complete(marking, goals):
    return any(all(marking.get(p, 0) >= w for p, w in g.items()) for g in goals)


def _solve_difference(constraints, nodes, obj):
    """Exact bounds for x[obj] under x[j] - x[i] <= c constraints.

    Edge (i, j, c) means x[j] <= x[i] + c.  Feasibility fails on a negative
    cycle.  With the anchor x[0] = 0: max x[obj] is the shortest 0->obj path,
    min x[obj] is minus the shortest obj->0 path.  Returns
    (feasible, lo, hi) with Fraction values.
    """
    edges = list(constraints)

    def bellman(graph, source):
        dist = [None] * nodes
        dist[source] = F(0)
        for _ in range(nodes):
            updated = False
            for i, j, c in graph:
                if dist[i] is not None and (dist[j] is None or dist[i] + c < dist[j]):
                    dist[j] = dist[i] + c
                    updated = True
            if not updated:
                return dist, True
        return dist, False  # still relaxable -> negative cycle

    # Feasibility: super-source reaches every node with weight 0.
    full = edges + [(nodes - 1, v, F(0)) for v in range(nodes - 1)]
    _dist, ok = bellman(full, nodes - 1)
    if not ok:
        return False, None, None
    fwd, ok1 = bellman(edges, 0)
    rev, ok2 = bellman([(j, i, c) for i, j, c in edges], 0)
    if not (ok1 and ok2):
        return False, None, None
    hi = fwd[obj]
    lo = None if rev[obj] is None else -rev[obj]
    if hi is None or lo is None or lo > hi:
        return False, None, None
    return True, lo, hi


def _sequence_constraints(sequence, activations, edges, ha):
    """Difference constraints for one explored sequence.

    Variables x[1..n] are absolute firing dates; node 0 is the anchor x[0]=0.
    activations[i][name] is the enabling step of `name` just before firing
    i+1 (-1 = enabled initially at date 0).
    """
    n = len(sequence)
    cons = []
    for i, name in enumerate(sequence, start=1):
        _pre, _post, lo, hi, _f, _c, immediate, _l = edges[name]
        act = activations[i - 1][name]
        base = 0 if act == -1 else act
        cons.append((base, i, hi))            # x_i <= x_base + hi
        cons.append((i, base, -lo))           # x_i >= x_base + lo
        if i > 1:
            cons.append((i, i - 1, F(0)))     # x_i >= x_{i-1} (nondecreasing)
        if immediate:
            prev = i - 1 if i > 1 else 0
            cons.append((i, prev, F(0)))      # x_i <= x_prev
            cons.append((prev, i, F(0)))      # x_prev <= x_i (same instant)
        cons.append((0, i, ha))               # x_i <= H_A
        cons.append((i, 0, F(0)))             # x_i >= 0
    return cons


def explore(model, node_budget):
    """Explore firing sequences; each terminal carries exact timing data."""
    if type(node_budget) is not int or node_budget < 1:
        raise ValueError('positive integer node budget required')
    hp, bc, ha, marking0, edges, goals = _validate(model)
    if _complete(marking0, goals):
        raise ValueError('initial completion outside explorer interface')

    def fire(marking, ages, activation, now_step, name):
        pre, post, lo, hi, *_ = edges[name]
        mid = {p: v - pre.get(p, 0) for p, v in marking.items()}
        if any(v < 0 for v in mid.values()):
            return None
        new_marking = {p: mid.get(p, 0) + post.get(p, 0) for p in set(mid) | set(post)}
        mid_enabled = _enabled(mid, edges)
        post_enabled = _enabled(new_marking, edges)
        keep = (set(ages) & mid_enabled & post_enabled) - {name}
        new_ages = {k: (ages[k] if k in keep else None) for k in post_enabled}
        new_activation = {k: (activation[k] if k in keep else now_step) for k in post_enabled}
        return new_marking, new_ages, new_activation

    root = dict(sequence=(), activations=(), marking=marking0,
                ages={k: None for k in _enabled(marking0, edges)},
                activation={k: -1 for k in _enabled(marking0, edges)},
                word=(), fault=None, completed=None, last_step=0)
    queue = deque([root])
    terminals = []
    visited = 0
    while queue and visited < node_budget:
        state = queue.popleft()
        visited += 1
        step = len(state['sequence']) + 1
        if state['completed'] is not None or _complete(state['marking'], goals):
            # First entry into the completion-marking set defines task
            # completion; a transition-level completion flag is honoured too.
            terminals.append(dict(state, terminal='FIRST_COMPLETION',
                                  completed=state['completed'] if state['completed'] is not None
                                  else len(state['sequence'])))
            continue
        en = _enabled(state['marking'], edges)
        if not en:
            terminals.append(dict(state, terminal='DEADLOCK'))
            continue
        urgent = [k for k in sorted(en) if edges[k][6]]
        for name in (urgent or sorted(en)):
            fired = fire(state['marking'], state['ages'], state['activation'], step, name)
            if fired is None:
                continue
            new_marking, new_ages, new_activation = fired
            _pre, _post, lo, hi, is_fault, is_completion, _imm, label = edges[name]
            child = dict(sequence=state['sequence'] + (name,),
                         activations=state['activations'] + (dict(state['activation']),),
                         marking=new_marking, ages=new_ages, activation=new_activation,
                         word=state['word'] if label is None else state['word'] + (label,),
                         fault=state['fault'] if state['fault'] is not None else (step if is_fault else None),
                         completed=step if is_completion else None,
                         last_step=step)
            queue.append(child)
    pending = [dict(sequence=s['sequence'], word=s['word'], terminal='UNRESOLVED', reason='NODE_BUDGET')
               for s in queue]
    return dict(status='UNRESOLVED' if pending else 'EXHAUSTED_FOR_MODEL',
                visited=visited, terminals=terminals, pending=pending, node_budget=node_budget)


def completion_intervals(model, exploration):
    """Exact completion-date interval per completed terminal sequence."""
    hp, _bc, ha, _m, edges, _g = _validate(model)
    rows = []
    for t in exploration['terminals']:
        if t['terminal'] != 'FIRST_COMPLETION':
            continue
        cons = _sequence_constraints(t['sequence'], t['activations'], edges, ha)
        n = len(t['sequence'])
        feasible, lo, hi = _solve_difference(cons, n + 1, n)
        rows.append(dict(sequence=list(t['sequence']), word=list(t['word']),
                         fault_step=t['fault'], completion_step=t['completed'],
                         feasible=feasible,
                         completion_interval=None if not feasible else [str(lo), str(hi)]))
    return rows


def omega_injectivity(rows, mode):
    """Injectivity verdict over explored completed sequences."""
    if mode not in ('word', 'word_and_time'):
        raise ValueError('unsupported projection')
    images = {}
    for row in rows:
        if not row['feasible'] or row['completion_interval'] is None:
            return dict(status='UNRESOLVED', reason='infeasible sequence constraints', row=row)
        lo, hi = row['completion_interval']
        word = tuple(row['word'])
        if mode == 'word_and_time':
            if lo != hi:
                return dict(status='COLLISION',
                            witness=dict(word=list(word), interval=[lo, hi],
                                         reason='completion date not unique within one sequence'))
            images.setdefault((word, lo), row)
            continue
        if lo != hi:
            return dict(status='COLLISION',
                        witness=dict(word=list(word), interval=[lo, hi],
                                     reason='one sequence yields a continuum of distinct omega_c '
                                            'with identical word projection'))
        if word in images and images[word]['completion_interval'] != row['completion_interval']:
            return dict(status='COLLISION', witness=[images[word], row])
        images.setdefault(word, row)
    return dict(status='INJECTIVE_ON_EXPLORED_SET' if rows else 'UNRESOLVED', images=len(images))

def explore_merged(model, node_budget, constraint_budget=None):
    """Quotient exploration over (marking, per-transition activation age).

    States with identical marking and identical per-transition activation
    ages share one expansion.  Every incoming sequence shares its parent's
    immutable constraint prefix and stores only this step's delta; the chain
    is materialized only when completion intervals are requested.  Stored
    payload growth is reported, never hidden.
    """
    if type(node_budget) is not int or node_budget < 1:
        raise ValueError('positive integer node budget required')
    if constraint_budget is not None and (type(constraint_budget) is not int or constraint_budget < 1):
        raise ValueError('positive integer constraint budget required')
    hp, bc, ha, marking0, edges, goals = _validate(model)
    if _complete(marking0, goals):
        raise ValueError('initial completion outside explorer interface')

    def enabled(marking):
        return {k for k, e in edges.items()
                if all(marking.get(p, 0) >= w for p, w in e[0].items())}

    total_constraints = [0]

    def key_of(marking, ages):
        return (tuple(sorted((p, v) for p, v in marking.items() if v)),
                tuple(sorted(ages.items())))

    def fire(marking, ages, name):
        pre, post, lo, hi, *_ = edges[name]
        mid = {p: v - pre.get(p, 0) for p, v in marking.items()}
        if any(v < 0 for v in mid.values()):
            return None
        new_marking = {p: mid.get(p, 0) + post.get(p, 0) for p in set(mid) | set(post)}
        mid_enabled = enabled(mid)
        post_enabled = enabled(new_marking)
        keep = (set(ages) & mid_enabled & post_enabled) - {name}
        new_ages = {k: (ages[k] + 1 if k in keep else 0) for k in post_enabled}
        return new_marking, new_ages

    root_ages = {k: -1 for k in enabled(marking0)}
    root_key = key_of(marking0, root_ages)
    # node: key -> {'marking':, 'ages':, 'payload': [item], 'expanded_upto': int}
    # payload item: parent pointer + this step's constraint delta.
    nodes = {root_key: dict(marking=marking0, ages=root_ages, expanded_upto=0,
                            payload=[dict(seq=(), delta=(), parent=None, word=(),
                                          fault=None, completed=None)])}
    order = deque([root_key])
    in_queue = {root_key}
    terminals = []
    expansions = 0
    payload_items = 1
    while order and expansions < node_budget:
        key = order.popleft()
        in_queue.discard(key)
        node = nodes[key]
        start = node['expanded_upto']
        if start == len(node['payload']):
            continue
        expansions += 1
        marking, ages = node['marking'], node['ages']
        en = enabled(marking)
        complete_here = _complete(marking, goals)
        if complete_here or not en:
            for item in node['payload'][start:]:
                terminals.append(dict(item, marking=marking,
                                      terminal='FIRST_COMPLETION' if complete_here else 'DEADLOCK',
                                      completed=item['completed'] if item['completed'] is not None
                                      else (len(item['seq']) if complete_here else None)))
            node['expanded_upto'] = len(node['payload'])
            continue
        urgent = [k for k in sorted(en) if edges[k][6]]
        for name in (urgent or sorted(en)):
            fired = fire(marking, ages, name)
            if fired is None:
                continue
            new_marking, new_ages = fired
            child_key = key_of(new_marking, new_ages)
            child = nodes.setdefault(child_key, dict(marking=new_marking, ages=new_ages,
                                                     expanded_upto=0, payload=[]))
            _pre, _post, lo, hi, is_fault, is_completion, immediate, label = edges[name]
            for item in node['payload'][start:]:
                i = len(item['seq']) + 1
                age = ages[name]
                base = 0 if age == -1 else (i - 1 - age)
                delta = [(base, i, hi), (i, base, -lo)]
                if i > 1:
                    delta.append((i, i - 1, F(0)))
                if immediate:
                    prev = i - 1 if i > 1 else 0
                    delta.append((i, prev, F(0)))
                    delta.append((prev, i, F(0)))
                delta.append((0, i, ha))
                delta.append((i, 0, F(0)))
                child['payload'].append(dict(
                    seq=item['seq'] + (name,), delta=tuple(delta), parent=item,
                    word=item['word'] if label is None else item['word'] + (label,),
                    fault=item['fault'] if item['fault'] is not None else (i if is_fault else None),
                    completed=i if is_completion else item['completed']))
                payload_items += 1
                total_constraints[0] += len(delta)
                if constraint_budget is not None and total_constraints[0] > constraint_budget:
                    pending = [dict(reason='CONSTRAINT_MEMORY_BUDGET',
                                    total_constraints=total_constraints[0],
                                    budget=constraint_budget,
                                    unexpanded_nodes=len(order) + 1,
                                    terminal='UNRESOLVED')]
                    return dict(status='UNRESOLVED', expansions=expansions,
                                abstract_states=len(nodes), payload_items=payload_items,
                                total_constraints=total_constraints[0],
                                terminals=terminals, pending=pending,
                                node_budget=node_budget, constraint_budget=constraint_budget)
            node['expanded_upto'] = len(node['payload'])
            if child_key not in in_queue:
                in_queue.add(child_key)
                order.append(child_key)
    pending_nodes = [k for k in order if nodes[k]['expanded_upto'] < len(nodes[k]['payload'])]
    pending = [dict(key=k, payload=len(nodes[k]['payload']), terminal='UNRESOLVED',
                    reason='NODE_BUDGET') for k in pending_nodes]
    return dict(status='UNRESOLVED' if pending else 'EXHAUSTED_FOR_MODEL',
                expansions=expansions, abstract_states=len(nodes),
                payload_items=payload_items, total_constraints=total_constraints[0],
                terminals=terminals, pending=pending,
                node_budget=node_budget, constraint_budget=constraint_budget)


def _materialize_payload_constraints(item):
    """Rebuild the exact old constraint list from newest to oldest deltas."""
    if 'cons' in item:  # read-only compatibility with pre-sharing explorations
        return item['cons']
    segments = []
    cursor = item
    while cursor is not None:
        segments.append(cursor['delta'])
        cursor = cursor['parent']
    return [constraint for delta in reversed(segments) for constraint in delta]


def merged_completion_intervals(model, exploration):
    """Exact completion intervals from shared per-sequence constraints."""
    hp, _bc, ha, _m, edges, _g = _validate(model)
    rows = []
    for t in exploration['terminals']:
        if t['terminal'] != 'FIRST_COMPLETION':
            continue
        n = len(t['seq'])
        cons = _materialize_payload_constraints(t)
        feasible, lo, hi = _solve_difference(cons, n + 1, n)
        rows.append(dict(sequence=list(t['seq']), word=list(t['word']),
                         fault_step=t['fault'], completion_step=t['completed'],
                         feasible=feasible,
                         completion_interval=None if not feasible else [str(lo), str(hi)]))
    return rows

