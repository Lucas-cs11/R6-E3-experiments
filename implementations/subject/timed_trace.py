"""Replay one concrete strong-time PN history; no exhaustive-search claim."""
from fractions import Fraction as F


def exact(x):
    if type(x) not in (int, str, F):
        raise ValueError('exact rational required')
    return F(x)


def replay(model, history):
    audit = []
    try:
        hp, bc, bd, ha = (exact(model[k]) for k in ('H_psi', 'B_c', 'B_d', 'H_A'))
        if hp < 0 or bc <= 0 or bd < 0 or ha != hp + bc + bd:
            raise ValueError('invalid analysis horizon specification')
        marking = dict(model['initial'])
        if not marking or any(type(x) is not int or x < 0 for x in marking.values()):
            raise ValueError('invalid initial marking')
        transitions = model['transitions']
        goal = model['completion_marking']
        def weights(arcs):
            return bool(set(arcs) <= marking.keys()) and all(type(w) is int and w > 0 for w in arcs.values())
        if not goal or not weights(goal):
            raise ValueError('invalid completion predicate')
        intervals = {}
        for k, t in transitions.items():
            if not weights(t['pre']) or not weights(t['post']):
                raise ValueError('invalid arcs')
            lo, hi = map(exact, t['interval'])
            if not 0 <= lo <= hi or any(type(t[f]) is not bool for f in ('fault', 'completion', 'immediate')):
                raise ValueError('invalid transition')
            if t['immediate'] and (lo or hi):
                raise ValueError('immediate transition must have interval [0,0]')
            if t['label'] is not None and (type(t['label']) is not str or not t['label']):
                raise ValueError('invalid label')
            intervals[k] = lo, hi
        def enabled(mark):
            return {k for k, t in transitions.items() if all(mark[p] >= n for p, n in t['pre'].items())}
        def complete(mark):
            return all(mark[p] >= n for p, n in goal.items())
        if complete(marking):
            raise ValueError('initial completion outside replay interface')
        ages = dict.fromkeys(enabled(marking), F(0))
        now = F(0)
        fault = completed = None
        word = []
        for event in history['fires']:
            k, at = event['transition'], exact(event['at'])
            if completed is not None or not now <= at <= ha or k not in ages:
                raise ValueError('post-completion, out-of-horizon or disabled firing')
            elapsed = at - now
            urgent = {j for j in ages if transitions[j]['immediate']}
            if urgent and (elapsed or k not in urgent):
                raise ValueError('immediate priority violated')
            advanced = {j: a + elapsed for j, a in ages.items()}
            if any(a > intervals[j][1] for j, a in advanced.items()) or advanced[k] < intervals[k][0]:
                raise ValueError('strong-time interval violated')
            t = transitions[k]
            mid = {p: v - t['pre'].get(p, 0) for p, v in marking.items()}
            post = {p: v + t['post'].get(p, 0) for p, v in mid.items()}
            keep = (ages.keys() & enabled(mid) & enabled(post)) - {k}
            new = {j: advanced[j] if j in keep else F(0) for j in enabled(post)}
            audit.append(dict(transition=k, at=str(at), before=marking, middle=mid, after=post,
                              advanced={j: str(a) for j, a in sorted(advanced.items())}, persistent=sorted(keep),
                              clocks_after={j: str(a) for j, a in sorted(new.items())}))
            ages, marking, now = new, post, at
            if t['fault'] and fault is None and at <= hp:
                fault = at
            if t['label'] is not None:
                word.append(t['label'])
            if complete(marking) != t['completion']:
                raise ValueError('completion event and marking disagree on this history')
            if t['completion']:
                completed = at
        end = exact(history['end'])
        if not now <= end <= ha or (completed is not None and end != completed):
            raise ValueError('invalid observation end')
        end_ages = {k: a + end - now for k, a in ages.items()}
        if completed is None and any(a > intervals[k][1] for k, a in end_ages.items()):
            raise ValueError('observation end crosses a firing deadline')
        for key, value in (('first_fault_time', fault), ('completion_time', completed)):
            if key in history:
                claimed = history[key]
                if (None if claimed is None else exact(claimed)) != value:
                    raise ValueError(f'{key} disagrees with replay')
        ready = sorted(k for k, a in end_ages.items() if a >= intervals[k][0])
        if completed is not None:
            terminal = 'FIRST_COMPLETION'
        elif not ages:
            terminal = 'DEADLOCK'
        elif end == ha and not ready:
            terminal = 'HORIZON_TRUNCATION'
        else:
            terminal = 'FRONTIER'
        outcome = ('PENDING' if terminal == 'FRONTIER' else 'NO_WINDOW_FAULT' if fault is None else
                   'COMPLETED_IN_TIME' if completed is not None and completed - fault <= bc else 'VIOLATION')
        return dict(status='REPLAYED_HISTORY', terminal=terminal, outcome=outcome,
                    first_fault_time=None if fault is None else str(fault),
                    completion_time=None if completed is None else str(completed),
                    omega_c=None if completed is None else [word, str(completed)],
                    endpoint_enabled_to_fire=ready if terminal == 'FRONTIER' and end == ha else [], trace=audit)
    except (KeyError, ValueError, TypeError, AttributeError, ZeroDivisionError) as exc:
        return dict(status='INVALID_INPUT_OR_HISTORY', reason=str(exc), trace=audit)


def check_projection(replays, mode):
    """Injectivity only on explicitly replayed completed observations."""
    if mode not in ('word', 'word_and_time'):
        raise ValueError('unsupported projection')
    inverse = {}
    rows = []
    for r in replays:
        if r['status'] != 'REPLAYED_HISTORY' or r['omega_c'] is None:
            return dict(status='UNRESOLVED', rows=rows)
        word, time = r['omega_c']
        omega = (tuple(word), exact(time))
        image = omega if mode == 'word_and_time' else omega[0]
        collision = image in inverse and inverse[image] != omega
        rows.append(dict(omega_c=[word, time], Y=r['omega_c'] if mode == 'word_and_time' else word))
        if collision:
            first = inverse[image]
            return dict(status='COLLISION', rows=rows, witness=[[list(first[0]), str(first[1])], r['omega_c']])
        inverse[image] = omega
    return dict(status='INJECTIVE_ON_REPLAYED_SET' if rows else 'UNRESOLVED', rows=rows)
