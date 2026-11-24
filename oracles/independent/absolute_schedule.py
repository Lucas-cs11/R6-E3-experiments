"""Independent absolute-time reference for finite, concrete PN schedules.

The reference admits only the regression model schema; it does not explore
unlisted firings or certify continuous support. Earliest/latest firing times
are absolute dates reconstructed from the last clock activation.
"""
from fractions import Fraction as Q


def date(value):
    if type(value) not in (str, int, Q):
        raise ValueError('non-exact time')
    return Q(value)


def assess(net, schedule):
    try:
        window, budget, padding, horizon = map(date, (net[k] for k in ('H_psi', 'B_c', 'B_d', 'H_A')))
        if min(window, padding) < 0 or budget <= 0 or horizon != window + budget + padding:
            raise ValueError('invalid horizon')
        places = tuple(net['initial'])
        m = tuple(net['initial'][p] for p in places)
        if not places or any(type(n) is not int or n < 0 for n in m):
            raise ValueError('invalid marking')

        def vector(arcs):
            if set(arcs) - set(places) or any(type(n) is not int or n <= 0 for n in arcs.values()):
                raise ValueError('invalid weights')
            return tuple(arcs.get(p, 0) for p in places)

        if not net['completion_marking']:
            raise ValueError('empty completion predicate')
        goal = vector(net['completion_marking'])
        def covers(mark, target):
            return not any(x < y for x, y in zip(mark, target))

        edges = {}
        for name, t in net['transitions'].items():
            lower, upper = map(date, t['interval'])
            flags = tuple(t[k] for k in ('fault', 'completion', 'immediate'))
            label = t['label']
            if lower < 0 or upper < lower or any(type(flag) is not bool for flag in flags):
                raise ValueError('invalid timing or flags')
            if (flags[2] and upper != 0) or (label is not None and (type(label) is not str or not label)):
                raise ValueError('invalid immediate interval or label')
            edges[name] = (vector(t['pre']), vector(t['post']), lower, upper, *flags, label)
        if covers(m, goal):
            raise ValueError('initial completion outside reference scope')
        opened = {k: Q(0) for k, e in edges.items() if covers(m, e[0])}
        accepted = []
        now = Q(0)
        for event in schedule['fires']:
            name, time = event['transition'], date(event['at'])
            if (accepted and accepted[-1][2]) or name not in opened or time < now or time > horizon:
                raise ValueError('firing outside schedule domain')
            pre, post, lower, _, fault, completion, immediate, label = edges[name]
            if any(edges[k][6] for k in opened) and (time != now or not immediate):
                raise ValueError('immediate precedence')
            if time < opened[name] + lower or any(time > start + edges[k][3] for k, start in opened.items()):
                raise ValueError('absolute firing date outside bounds')
            consumed = tuple(x-y for x,y in zip(m,pre))
            m = tuple(x+y for x,y in zip(consumed,post))
            if completion != covers(m,goal):
                raise ValueError('completion boundary mismatch')
            opened = {k: opened[k] if k != name and k in opened and covers(consumed,e[0]) else time
                      for k,e in edges.items() if covers(m,e[0])}
            accepted.append((time,fault,completion,label)); now = time
        tf = next((t for t,f,_,_ in accepted if f and t <= window),None)
        tc = next((t for t,_,c,_ in accepted if c),None)
        end = date(schedule['end'])
        if end < now or end > horizon or (tc is not None and tc != end):
            raise ValueError('invalid end date')
        if tc is None and any(end > start + edges[k][3] for k,start in opened.items()):
            raise ValueError('end date crosses deadline')
        for key,value in (('first_fault_time',tf), ('completion_time',tc)):
            if key in schedule and (None if schedule[key] is None else date(schedule[key])) != value:
                raise ValueError('claimed time mismatch')
        ready = sorted(k for k,start in opened.items() if start + edges[k][2] <= end)
        terminal = ('FIRST_COMPLETION' if tc is not None else 'DEADLOCK' if not opened else
                    'HORIZON_TRUNCATION' if end == horizon and not ready else 'FRONTIER')
        outcome = ('PENDING' if terminal == 'FRONTIER' else 'NO_WINDOW_FAULT' if tf is None else
                   'COMPLETED_IN_TIME' if tc is not None and tc <= tf + budget else 'VIOLATION')
        return dict(status='REPLAYED_HISTORY',terminal=terminal,outcome=outcome,
                    first_fault_time=None if tf is None else str(tf), completion_time=None if tc is None else str(tc),
                    omega_c=None if tc is None else [[label for _,_,_,label in accepted if label is not None], str(tc)],
                    endpoint_enabled_to_fire=ready if terminal == 'FRONTIER' and end == horizon else [])
    except (ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError) as exc:
        return dict(status='INVALID_INPUT_OR_HISTORY',reason=str(exc))


def projection_status(replays, mode):
    from itertools import combinations
    if mode not in {'word', 'word_and_time'}:
        raise ValueError('unknown projection')
    if not replays or any(x['status'] != 'REPLAYED_HISTORY' or x['omega_c'] is None for x in replays):
        return 'UNRESOLVED'
    observations = [(tuple(w),date(t)) for w,t in (x['omega_c'] for x in replays)]
    if mode == 'word' and any(a[0] == b[0] and a[1] != b[1] for a,b in combinations(observations,2)):
        return 'COLLISION'
    return 'INJECTIVE_ON_REPLAYED_SET'
