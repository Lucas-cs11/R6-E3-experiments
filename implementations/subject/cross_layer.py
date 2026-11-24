"""E3 cross-layer alignment checker (successor of frozen E2 R6-10).

Checks are evidence-driven: only what is recomputed from models and explored
runs counts.  Bare ``True`` flags supplied without raw evidence leave the
pair NOT_CERTIFIED rather than THEOREM_APPLICABLE.
"""
import json

from reachability import completion_intervals, explore, omega_injectivity


def _canonical(model):
    return json.dumps({
        'H_psi': str(model['H_psi']), 'B_c': str(model['B_c']), 'B_d': str(model['B_d']),
        'H_A': str(model['H_A']),
        'initial': model['initial'],
        'completion_marking': model['completion_marking'],
        'transitions': {k: {f: ([str(v) for v in t[f]] if f == 'interval' else t[f])
                            for f in ('pre', 'post', 'interval', 'fault', 'completion',
                                      'immediate', 'label')}
                        for k, t in sorted(model['transitions'].items())},
    }, sort_keys=True)


def _observation_set(rows):
    """Observation records of completed runs over the explored set."""
    return [dict(word=row['word'], interval=row['completion_interval'], row=row) for row in rows
            if row['completion_interval'] is not None]


def check_alignment(pair, node_budget):
    """Evaluate the cross-layer sufficient conditions on both models.

    pair: {'logical_model': ..., 'probability_model': ...,
           'external_completion_evidence': {...} or None}
    Returns a status dict; never fabricates certificates.
    """
    checks = {}
    logical, probability = pair['logical_model'], pair['probability_model']
    checks['discrete_structure'] = _canonical(logical) == _canonical(probability)
    evidence = pair.get('external_completion_evidence')
    if evidence is not None and evidence.get('raw') is not True:
        checks['external_completion_evidence'] = False
    else:
        checks['external_completion_evidence'] = evidence is not None

    expl_l = explore(logical, node_budget)
    expl_p = explore(probability, node_budget)
    rows_l = completion_intervals(logical, expl_l)
    rows_p = completion_intervals(probability, expl_p)
    checks['exploration_complete'] = expl_l['status'] == 'EXHAUSTED_FOR_MODEL' \
        and expl_p['status'] == 'EXHAUSTED_FOR_MODEL'
    obs_l, obs_p = _observation_set(rows_l), _observation_set(rows_p)
    checks['same_time_semantics'] = checks['discrete_structure']  # same model => same semantics
    checks['omega_c_injective_on_completed'] = (
        omega_injectivity(rows_l, 'word_and_time')['status'] != 'COLLISION')
    checks['observation_projection_agreement'] = obs_l == obs_p
    checks['sample_support_matches'] = checks['exploration_complete'] and obs_l == obs_p

    # Uncompleted runs must be distinguishable from completed runs by a real
    # external completion record, never by an internal deadlock flag.
    uncompleted_words = {tuple(t['word']) for t in expl_l['terminals']
                         if t['terminal'] in ('DEADLOCK', 'FRONTIER')}
    completed_words = {tuple(o['word']) for o in obs_l}
    checks['uncompleted_distinguishable'] = uncompleted_words.isdisjoint(completed_words) \
        and checks['external_completion_evidence']

    if not checks['discrete_structure']:
        return dict(status='THEOREM_NOT_APPLICABLE', reason='models differ',
                    checks=checks, counterexample_claimed=False)
    if not checks['exploration_complete']:
        return dict(status='NOT_CERTIFIED', reason='exploration budget exhausted',
                    checks=checks, counterexample_claimed=False,
                    pending_logical=len(expl_l['pending']), pending_probability=len(expl_p['pending']))
    if not all(checks.values()):
        return dict(status='NOT_CERTIFIED',
                    reason='required evidence not established; bare flags cannot certify',
                    checks=checks, counterexample_claimed=False)
    verdict = omega_injectivity(rows_l, 'word')
    if verdict['status'] == 'COLLISION':
        return dict(status='THEOREM_NOT_APPLICABLE',
                    reason='distinct omega_c map to same word observation; '
                           'strict cross-layer theorem must not be used',
                    checks=checks, collision_witness=verdict['witness'], counterexample_claimed=False)
    return dict(status='THEOREM_APPLICABLE', checks=checks, counterexample_claimed=False)
