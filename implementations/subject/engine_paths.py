"""E3-04 four genuinely different finite search/diagnosis computation paths."""
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import time
import tracemalloc

from engine_interface import check_applicability
from reachability import (completion_intervals, explore, explore_merged,
                          merged_completion_intervals)


METHODS = ('MAIN', 'FULL_HISTORY', 'NO_SYNC', 'NO_ENVELOPE')
_ABLATION = {'MAIN': 'NONE', 'FULL_HISTORY': 'NO_PRUNING',
             'NO_SYNC': 'NO_SYNC', 'NO_ENVELOPE': 'NO_ENVELOPE'}


def _adapt(model):
    horizon = F(str(model['H']))
    deadline = F(str(model.get('diagnosis_window', horizon)))
    if deadline <= 0 or deadline > horizon:
        raise ValueError('diagnosis deadline outside (0,H]')
    transitions = {}
    for name, transition in model['transitions'].items():
        transitions[name] = dict(
            pre=dict(transition['pre']), post=dict(transition['post']),
            interval=[str(value) for value in transition['interval']],
            fault=bool(transition['is_fault']), completion=False,
            immediate=bool(transition['immediate']), label=transition['label'])
    return dict(H_psi='0', B_c=str(deadline), B_d=str(horizon - deadline),
                H_A=str(horizon), initial=dict(model['initial_marking']),
                completion_markings=[dict(m) for m in model['completion_markings']],
                transitions=transitions), deadline


def _canonical(value):
    return json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()


def _sync_dominance(rows):
    retained = []
    seen = set()
    for row in rows:
        key = (tuple(row['word']), row['fault_step'],
               None if row['completion_interval'] is None else tuple(row['completion_interval']),
               row['feasible'])
        if key not in seen:
            seen.add(key)
            retained.append(row)
    return retained, len(rows) - len(retained)


def _envelope_split(rows, deadline):
    groups = defaultdict(set)
    for row in rows:
        if row['feasible'] and row['completion_interval'] is not None:
            groups[tuple(row['word'])].add(F(row['completion_interval'][1]) <= deadline)
    return sum(len(classes) > 1 for classes in groups.values())


def _has_noncompletion_self_loop(model):
    """A concrete zero-time self-loop prevents an exhaustion claim here."""
    return any(transition['pre'] and transition['pre'] == transition['post']
               for transition in model['transitions'].values())


def _diagnose(exploration, rows, deadline, use_envelope):
    if exploration['status'] != 'EXHAUSTED_FOR_MODEL':
        return 'PERP'
    fault_terminals = [row for row in exploration['terminals'] if row.get('fault') is not None]
    if any(row['terminal'] == 'DEADLOCK' for row in fault_terminals):
        return '0'
    fault_rows = [row for row in rows if row['fault_step'] is not None]
    if any(not row['feasible'] for row in fault_rows):
        return 'PERP'
    if use_envelope:
        grouped = defaultdict(list)
        for row in fault_rows:
            grouped[tuple(row['word'])].append(F(row['completion_interval'][1]))
        if any(max(bounds) > deadline for bounds in grouped.values()):
            return '0'
    elif any(F(row['completion_interval'][1]) > deadline for row in fault_rows):
        return '0'
    if (fault_terminals and fault_rows and
            all(row['terminal'] == 'FIRST_COMPLETION' for row in fault_terminals)):
        return '1'
    return 'PERP'


def _execute(model, method, node_budget, constraint_budget=None):
    applicability = check_applicability(model)
    if not applicability['supported']:
        return dict(status='UNSUPPORTED', verdict='PERP', reasons=applicability['reasons'],
                    method=method, trace=[], certificate=None,
                    path_stats=dict(expansions=0, state_classes=0, sync_pairs=0,
                                    lp_calls=0, ablation_point=_ABLATION[method]))
    adapted, deadline = _adapt(model)
    if method == 'FULL_HISTORY':
        exploration = explore(adapted, node_budget)
        rows = completion_intervals(adapted, exploration)
        expansions = exploration['visited']
        base_classes = exploration['visited']
        call_sequence = ['PARSE', 'EXPLORE_FULL', 'EXACT_LP']
    else:
        exploration = explore_merged(adapted, node_budget, constraint_budget=constraint_budget)
        rows = merged_completion_intervals(adapted, exploration)
        expansions = exploration['expansions']
        base_classes = exploration['abstract_states']
        call_sequence = ['PARSE', 'EXPLORE_MERGED', 'EXACT_LP']
    if _has_noncompletion_self_loop(model) and exploration['status'] == 'EXHAUSTED_FOR_MODEL':
        # A merged key can be revisited forever with fresh histories.  Preserve
        # that unresolved sequence space instead of equating quotient closure
        # with path exhaustion.
        exploration = dict(exploration)
        exploration['status'] = 'UNRESOLVED'
        exploration['pending'] = [*exploration['pending'],
                                  dict(reason='POTENTIAL_NONCOMPLETION_CYCLE', terminal='UNRESOLVED')]
    all_rows = list(rows)
    sync_pairs = 0
    if method in ('MAIN', 'NO_ENVELOPE'):
        rows, sync_pairs = _sync_dominance(rows)
        call_sequence.append('SYNC_DOMINANCE')
    envelope_splits = 0
    if method in ('MAIN', 'NO_SYNC'):
        envelope_splits = _envelope_split(rows, deadline)
        call_sequence.append('TIME_ENVELOPE')
    call_sequence.append('DIAGNOSE')
    verdict = _diagnose(exploration, rows, deadline, method in ('MAIN', 'NO_SYNC'))
    state_classes = base_classes + len({tuple(row['sequence']) for row in rows}) + envelope_splits
    stats = dict(expansions=expansions, state_classes=state_classes,
                 sync_pairs=sync_pairs, lp_calls=len(all_rows),
                 ablation_point=_ABLATION[method],
                 envelope_splits=envelope_splits,
                 payload_items=exploration.get('payload_items', exploration.get('visited')))
    trace = rows + [dict(terminal=row['terminal'], sequence=list(row['sequence']),
                         fault_step=row.get('fault')) for row in exploration['terminals']
                    if row['terminal'] == 'DEADLOCK']
    certificate = dict(model_sha256=hashlib.sha256(_canonical(model)).hexdigest(),
                       trace_sha256=hashlib.sha256(_canonical(trace)).hexdigest(),
                       status=exploration['status'], pending=len(exploration['pending']),
                       search_evidence=dict(node_budget=node_budget, expansions=expansions,
                                            terminal_count=len(exploration['terminals'])),
                       diagnosis_rule=f'absolute completion upper bound <= {deadline}')
    return dict(status=exploration['status'], verdict=verdict, method=method,
                trace=trace, certificate=certificate, path_stats=stats,
                call_sequence=call_sequence, reasons=[])


def run_path(model, method, node_budget, constraint_budget=None):
    """Run one real path and measure time, CPU and Python allocation peak."""
    if method not in METHODS:
        raise ValueError('unknown engine method')
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    tracemalloc.start()
    try:
        result = _execute(model, method, node_budget, constraint_budget)
    finally:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        wall = time.perf_counter() - wall_start
        cpu = time.process_time() - cpu_start
    result['resources'] = dict(wall_seconds=wall, cpu_seconds=cpu,
                               peak_memory_bytes=peak,
                               states=result['path_stats']['state_classes'],
                               lp_calls=result['path_stats']['lp_calls'])
    return result
