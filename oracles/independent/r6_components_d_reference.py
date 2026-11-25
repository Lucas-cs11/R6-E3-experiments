"""Independent R6-10 reference: concrete PN exploration and absolute-time replay."""
from collections import deque
from fractions import Fraction as Q
import json
import math
from itertools import product

from absolute_schedule import assess


def _enumerate(model, budget):
    transitions = model['transitions']

    def enabled(marking):
        return {name for name, edge in transitions.items()
                if all(marking.get(place, 0) >= weight for place, weight in edge['pre'].items())}

    initial = dict(model['initial'])
    clocks = {name: Q(0) for name in enabled(initial)}
    queue = deque([((), (), initial, clocks, ())])
    terminals = []
    visits = 0
    while queue and visits < budget:
        sequence, dates, marking, clocks, word = queue.popleft()
        visits += 1
        completed = all(marking.get(place, 0) >= weight
                        for place, weight in model['completion_marking'].items())
        active = enabled(marking)
        if completed or not active:
            terminals.append(dict(sequence=list(sequence), word=list(word),
                                  terminal='FIRST_COMPLETION' if completed else 'DEADLOCK',
                                  completion_time=str(dates[-1]) if completed else None))
            continue
        urgent = sorted(name for name in active if transitions[name]['immediate'])
        now = dates[-1] if dates else Q(0)
        if urgent:
            options = [(name, now) for name in urgent]
        else:
            deadline = min([Q(model['H_A']),
                            *[clocks[name] + Q(transitions[name]['interval'][1]) for name in active]])
            options = []
            for name in sorted(active):
                low, high = map(Q, transitions[name]['interval'])
                first = max(now, clocks[name] + low)
                last = min(deadline, clocks[name] + high)
                options.extend((name, Q(tick)) for tick in range(math.ceil(first), math.floor(last) + 1))
        for name, at in options:
            edge = transitions[name]
            history = {'fires': [{'transition': transition, 'at': str(time)}
                                 for transition, time in zip((*sequence, name), (*dates, at))],
                       'end': str(at)}
            checked = assess(model, history)
            if checked['status'] != 'REPLAYED_HISTORY':
                raise RuntimeError(f'independent concrete path rejected: {checked}')
            middle = {place: marking.get(place, 0) - edge['pre'].get(place, 0)
                      for place in marking}
            after = {place: middle.get(place, 0) + edge['post'].get(place, 0)
                     for place in set(middle) | set(edge['post'])}
            keep = active & enabled(middle) & enabled(after) - {name}
            next_clocks = {other: clocks[other] if other in keep else at
                           for other in enabled(after)}
            label = edge['label']
            queue.append(((*sequence, name), (*dates, at), after, next_clocks,
                          word if label is None else (*word, label)))
    return dict(terminals=terminals, complete=not queue, pending=len(queue))


def _canonical(model):
    return json.dumps(model, sort_keys=True, default=str, separators=(',', ':'))


def _projection(exploration):
    return sorted((tuple(row['word']), row['completion_time'], tuple(row['sequence']))
                  for row in exploration['terminals'] if row['terminal'] == 'FIRST_COMPLETION')


def reference_r610(model_pair, case):
    """Recompute all cross-layer checks without the production explorer."""
    logical = model_pair['logical_model']
    probability = model_pair['probability_model']
    left = _enumerate(logical, case['budget'])
    right = _enumerate(probability, case['budget'])
    same_structure = _canonical(logical) == _canonical(probability)
    evidence = model_pair.get('external_completion_evidence')
    external = evidence is not None and evidence.get('raw') is True
    projection_l, projection_p = _projection(left), _projection(right)
    complete = left['complete'] and right['complete']
    completed_words = {word for word, _time, _sequence in projection_l}
    uncompleted_words = {tuple(row['word']) for row in left['terminals']
                         if row['terminal'] != 'FIRST_COMPLETION'}

    images = {}
    for word, time, _sequence in projection_l:
        omega = (word, time)
        images.setdefault(omega, omega)
    checks = {
        'discrete_structure': same_structure,
        'external_completion_evidence': external,
        'exploration_complete': complete,
        'same_time_semantics': same_structure,
        'omega_c_injective_on_completed': all(image == omega for omega, image in images.items()),
        'observation_projection_agreement': projection_l == projection_p,
        'sample_support_matches': complete and projection_l == projection_p,
        'uncompleted_distinguishable': uncompleted_words.isdisjoint(completed_words) and external,
    }
    if not same_structure:
        return dict(status='THEOREM_NOT_APPLICABLE', reason='models differ', checks=checks,
                    counterexample_claimed=False, proof_trace=left['terminals'])
    if not complete:
        return dict(status='NOT_CERTIFIED', reason='exploration budget exhausted', checks=checks,
                    counterexample_claimed=False, pending_logical=left['pending'],
                    pending_probability=right['pending'], proof_trace=left['terminals'])
    if not all(checks.values()):
        return dict(status='NOT_CERTIFIED',
                    reason='required evidence not established; bare flags cannot certify',
                    checks=checks, counterexample_claimed=False, proof_trace=left['terminals'])
    by_word = {}
    for word, time, sequence in projection_l:
        by_word.setdefault(word, set()).add(time)
    collision = next(((word, times) for word, times in by_word.items() if len(times) > 1), None)
    if collision is not None:
        return dict(status='THEOREM_NOT_APPLICABLE',
                    reason='distinct omega_c map to same word observation; strict cross-layer theorem must not be used',
                    checks=checks, collision_witness=collision, counterexample_claimed=False,
                    proof_trace=left['terminals'])
    return dict(status='THEOREM_APPLICABLE', checks=checks,
                counterexample_claimed=False, proof_trace=left['terminals'])


def _integrate(intercept, slope, low, high):
    return intercept * (high - low) + slope * (high * high - low * low) / 2


def _decision_error(joint):
    errors = []
    for decisions in product((0, 1), repeat=len(joint)):
        errors.append(sum((mass[1 - decision] for mass, decision in zip(joint, decisions)), Q(0)))
    return min(errors)


def _coverage_rows(joint, delta):
    rows = []
    for left, right in joint:
        mixture = left + right
        posterior = min(left, right) / mixture
        rows.append(dict(joint=[str(left), str(right)], posterior_error=str(posterior),
                         reliable=posterior <= delta))
    return rows


def reference_r611(model, case):
    """Independent antiderivative and exhaustive deterministic decision rules."""
    if case['kind'] == 'zero_measure':
        spec = model['zero_measure']
        low, high = map(Q, spec['interval'])
        constant = Q(spec['density0']['value'])
        slope = Q(spec['density1']['coefficient'])
        if (_integrate(constant, Q(0), low, high) != 1 or
                _integrate(Q(0), slope, low, high) != 1):
            return dict(status='INVALID_EVIDENCE', reason='DENSITY_NOT_NORMALIZED')
        crossing = constant / slope
        # Independent region decision: H1 on [0,crossing], H0 afterward.
        error = (Q(spec['prior1']) * _integrate(Q(0), slope, low, crossing) +
                 Q(spec['prior0']) * _integrate(constant, Q(0), crossing, high))
        return dict(status='ZERO_MEASURE_SHARED_POINT', mass_added='0',
                    Pe_before=str(error), Pe_after=str(error), delta_Pe='0')

    spec = model['atomic']
    atoms = list(spec['atoms'])
    if case.get('drop_atom'):
        atoms = atoms[:-1]
    if any(sum(Q(atom[f'h{i}']) for atom in atoms) != 1 for i in range(2)):
        return dict(status='INVALID_EVIDENCE', reason='HYPOTHESIS_MASS_NOT_ONE')
    pi0, pi1, delta = Q(spec['prior0']), Q(spec['prior1']), Q(spec['delta'])
    fine = [(pi0 * Q(atom['h0']), pi1 * Q(atom['h1'])) for atom in atoms]
    coarse = [(sum((row[0] for row in fine), Q(0)), sum((row[1] for row in fine), Q(0)))]
    before = _coverage_rows(fine, delta)
    after = _coverage_rows(coarse, delta)
    gamma_before = sum((Q(row['joint'][0]) + Q(row['joint'][1])
                        for row in before if row['reliable']), Q(0))
    gamma_after = sum((Q(row['joint'][0]) + Q(row['joint'][1])
                       for row in after if row['reliable']), Q(0))
    pe_before, pe_after = _decision_error(fine), _decision_error(coarse)
    return dict(status='EXACT_COARSENING_PAIR', Pe_before=str(pe_before),
                Pe_after=str(pe_after), Gamma_before=str(gamma_before),
                Gamma_after=str(gamma_after), monotonic_Pe=pe_after >= pe_before,
                atoms_before=before, atoms_after=after, proof_trace=[*before, *after])
