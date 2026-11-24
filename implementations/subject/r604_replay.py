"""Replay the six frozen scalar R604 fixtures as explicit executable PN witnesses.

The frozen E2 component stored only scalar timestamps, not original PNML or
raw firing histories. These generated nets are therefore *reconstructed
witnesses*, not recovered historical models. They exercise the E3 trace
semantics and detect changes to the inherited component ledger.
"""
import ast
from fractions import Fraction as F
import hashlib

from timed_trace import replay

GENERATOR_SHA256 = 'a28e403875f6ed2225c914ac2bba4e4d4f77ed4570de7ecd32fc9c8373e8bf3e'


def _literal(node):
    if isinstance(node, ast.Constant) and (node.value is None or type(node.value) in (str, int, float)):
        return node.value
    raise ValueError('only scalar constants are accepted in frozen R604 cases')


def load_legacy_cases(generator_bytes):
    if hashlib.sha256(generator_bytes).hexdigest() != GENERATOR_SHA256:
        raise ValueError('R604_GENERATOR_SHA_MISMATCH')
    tree = ast.parse(generator_bytes.decode('utf-8'))
    assignment = next((n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'cases' for t in n.targets)), None)
    if assignment is None or not isinstance(assignment.value, ast.List):
        raise ValueError('R604_CASE_LIST_NOT_FOUND')
    result = []
    for item in assignment.value.elts:
        if not isinstance(item, ast.Tuple) or len(item.elts) != 3:
            raise ValueError('malformed R604 case')
        name = _literal(item.elts[0])
        call = item.elts[1]
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'run' or call.keywords:
            raise ValueError('only run(tf,Bc,Ha,tc) calls are accepted')
        values = [_literal(x) for x in call.args]
        if not 3 <= len(values) <= 4:
            raise ValueError('invalid run arity')
        tf, bc, ha = values[:3]
        tc = values[3] if len(values) == 4 else None
        run = dict(first_fault_time=tf, B_c=bc, H_A=ha)
        if tc is not None:
            run['completion_time'] = tc
        result.append((name, run, _literal(item.elts[2])))
    if len(result) != 6 or len({x[0] for x in result}) != 6:
        raise ValueError('unexpected R604 fixture population')
    return result


def witness(run, short_prefix=False):
    tf, bc, legacy_ha = (F(run[k]) for k in ('first_fault_time', 'B_c', 'H_A'))
    tc = F(run['completion_time']) if 'completion_time' in run else None
    if tf < 0 or bc <= 0 or legacy_ha < 0 or (tc is not None and not tf <= tc <= legacy_ha):
        raise ValueError('legacy fixture outside reconstruction domain')
    # A short prefix is not a complete H_A history. Give its model a later
    # formal horizon while preserving the recorded observation endpoint.
    horizon = max(F(4), tf + bc) if short_prefix else legacy_ha
    hpsi = tf
    bd = horizon - hpsi - bc
    if bd < 0:
        raise ValueError('negative observation padding')
    net = dict(H_psi=str(hpsi), B_c=str(bc), B_d=str(bd), H_A=str(horizon),
               initial={'start': 1, 'work': 0, 'stopped': 0, 'done': 0},
               completion_marking={'done': 1}, transitions={})
    net['transitions']['fault'] = dict(pre={'start': 1},
        post={'work': 1} if tc is not None or short_prefix else {'stopped': 1},
        interval=[str(tf), str(tf)], fault=True, completion=False,
        immediate=tf == 0, label=None)
    fires = [{'transition': 'fault', 'at': str(tf)}]
    if tc is not None or short_prefix:
        delay = tc - tf if tc is not None else bc
        net['transitions']['complete'] = dict(pre={'work': 1}, post={'done': 1},
            interval=[str(delay), str(delay)], fault=False, completion=True,
            immediate=delay == 0, label='done')
        if tc is not None:
            fires.append({'transition': 'complete', 'at': str(tc)})
    history = dict(fires=fires, end=str(tc if tc is not None else legacy_ha))
    return net, history


def replay_cases(generator_bytes):
    output = {}
    for name, run, expected in load_legacy_cases(generator_bytes):
        net, history = witness(run, short_prefix=name == 'SHORT_PREFIX_NOT_DUE')
        result = replay(net, history)
        if result['status'] != 'REPLAYED_HISTORY':
            raise ValueError(f'{name}: reconstructed witness rejected: {result}')
        tf, bc, ha = (F(run[k]) for k in ('first_fault_time', 'B_c', 'H_A'))
        tc = F(run['completion_time']) if 'completion_time' in run else None
        deadline = tf + bc
        output[name] = dict(legacy_input=run, legacy_expected=expected,
            reconstructed_model=net, reconstructed_history=history, trace_result=result,
            outcome=result['outcome'], post_fault_deadline=str(deadline),
            endpoint_exact_pass=tc is not None and tc == ha and deadline == ha)
    return output
