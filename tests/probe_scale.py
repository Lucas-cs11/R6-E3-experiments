"""E3-02 scale probe: explore the smallest real generated RMT-FMS model."""
import json
from fractions import Fraction as F
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/subject'))
sys.path.insert(0, str(ROOT / 'baseline_readonly/e2/implementations/generator_compat'))
from src.benchmarks.rmt_fms_generator import generate_rmt_fms  # noqa: E402
from reachability import completion_intervals, explore, omega_injectivity  # noqa: E402

CANDIDATE = 'RMT_m2_j1_ops2_wip1_u0.1_f1_w0.5_a0.1'


def to_model(net, ha):
    transitions = {}
    for name, t in net.transitions.items():
        transitions[name] = dict(
            pre={}, post={}, interval=[str(t.interval.earliest), str(t.interval.latest)],
            fault=bool(t.is_fault), completion=False,
            immediate=(t.interval.earliest == t.interval.latest == 0),
            label=(t.label or None) if t.label != '' else None)
    names = set(transitions)
    for arc in net.arcs:
        src_place = arc.from_node not in names
        dst_place = arc.to_node not in names
        if src_place and not dst_place:
            transitions[arc.to_node]['pre'][arc.from_node] = transitions[arc.to_node]['pre'].get(arc.from_node, 0) + 1
        elif not src_place and dst_place:
            transitions[arc.from_node]['post'][arc.to_node] = transitions[arc.from_node]['post'].get(arc.to_node, 0) + 1
        else:
            raise ValueError(f'unsupported arc shape {arc.from_node}->{arc.to_node}')
    return dict(H_psi='0', B_c='1', B_d=str(F(ha) - 1), H_A=str(ha),
                initial=dict(net.initial_marking),
                completion_markings=[dict(m) for m in net.completion_markings],
                transitions=transitions)


def main():
    universe = list(csv_module.DictReader(open(ROOT / 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv')))
    row = next(r for r in universe if r['candidate_id'] == CANDIDATE)
    params = dict(n_machines=2, n_parts=1, ops_per_part=2, wip_bound=1,
                  unobservable_ratio=0.1, fault_locations=1, interval_width_factor=0.5,
                  adjustable_ratio=0.1, seed=0, machine_capacity=1, n_configs=2,
                  repair_domain='standard')
    net, L, H = generate_rmt_fms(**params)
    model = to_model(net, F(str(H)))
    out = {'candidate_id': CANDIDATE, 'L': str(L), 'H': str(H),
           'places': len(net.places), 'transitions': len(net.transitions), 'arcs': len(net.arcs),
           'completion_markings': len(net.completion_markings)}
    for budget in (1000, 20000, 200000):
        exploration = explore(model, budget)
        rows = completion_intervals(model, exploration)
        terminal_counts = {}
        for t in exploration['terminals']:
            terminal_counts[t['terminal']] = terminal_counts.get(t['terminal'], 0) + 1
        verdict = omega_injectivity(rows, 'word')
        out[f'budget_{budget}'] = dict(status=exploration['status'], visited=exploration['visited'],
                                       terminals=terminal_counts, pending=len(exploration['pending']),
                                       completed_sequences=len(rows), word_verdict=verdict['status'])
        print(json.dumps(out[f'budget_{budget}']), flush=True)
    print(json.dumps(out))
    return 0


import csv as csv_module

if __name__ == '__main__':
    sys.exit(main())
