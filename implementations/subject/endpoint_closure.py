"""Explore zero-delay suffixes at H_A for one concrete, replayable prefix."""
from collections import deque

from timed_trace import exact, replay


def close_endpoint(model, prefix, node_budget):
    if type(node_budget) is not int or node_budget < 1:
        raise ValueError('node_budget must be a positive integer')
    root = replay(model, prefix)
    if root['status'] != 'REPLAYED_HISTORY':
        return dict(status='INVALID_PREFIX', root=root)
    horizon = exact(model['H_A'])
    if exact(prefix['end']) != horizon:
        return dict(status='NOT_AT_HORIZON', root=root)
    queue = deque([((), root)])
    terminals = []
    visited = 0
    while queue and visited < node_budget:
        suffix, result = queue.popleft()
        visited += 1
        if result['terminal'] != 'FRONTIER':
            terminals.append(dict(suffix=suffix, result=result))
            continue
        ready = result['endpoint_enabled_to_fire']
        immediate = [t for t in ready if model['transitions'][t]['immediate']]
        choices = immediate or ready
        if not choices:
            raise RuntimeError('endpoint frontier without a successor')
        for name in choices:
            branch = (*suffix, name)
            history = {'end': str(horizon), 'fires': [*prefix['fires'], *(
                {'transition': t, 'at': str(horizon)} for t in branch)]}
            successor = replay(model, history)
            if successor['status'] != 'REPLAYED_HISTORY':
                raise RuntimeError(f'endpoint successor failed replay: {successor}')
            queue.append((branch, successor))
    pending = [{'suffix': suffix, 'status': 'UNRESOLVED', 'reason': 'NODE_BUDGET',
                'replayed_terminal': result['terminal'], 'next_ready': result['endpoint_enabled_to_fire']}
               for suffix, result in queue]
    return dict(status='UNRESOLVED' if pending else 'EXHAUSTED_AT_ENDPOINT_FOR_PREFIX',
                scope='CONCRETE_PREFIX_ONLY', visited=visited, terminals=terminals, pending=pending)
