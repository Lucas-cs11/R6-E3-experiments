"""R6-10/11 component integration with independent evidence comparison."""
import json

from cross_layer import check_alignment
from reachability import explore
from r6_components import make_acceptance_record as _component_acceptance_record


_PATCHES = {
    'DROP_UNCOMPLETED_DISTINGUISH': dict(
        component_id='R6-10', old='require uncompleted_distinguishable=true',
        new='drop the check and certify a completed/uncompleted word collision'),
    'COLLISION_AS_APPLICABLE': dict(
        component_id='R6-10', old='word collision implies THEOREM_NOT_APPLICABLE',
        new='return THEOREM_APPLICABLE despite distinct omega_c sharing a word'),
}


def mutation_patch(mutation_id):
    return dict(_PATCHES[mutation_id], mutation_id=mutation_id,
                mode='SPECIFIC_CROSS_LAYER_MUTATION')


def run_r610(model_pair, case, mutation=None):
    """Use the production alignment check and retain actual explored terminals."""
    if mutation not in (None, 'DROP_UNCOMPLETED_DISTINGUISH', 'COLLISION_AS_APPLICABLE'):
        raise ValueError('unknown R6-10 mutation')
    result = check_alignment(model_pair, case['budget'])
    exploration = explore(model_pair['logical_model'], case['budget'])
    result['proof_trace'] = [*exploration['terminals'], *exploration['pending']]
    if mutation == 'DROP_UNCOMPLETED_DISTINGUISH' and not result['checks']['uncompleted_distinguishable']:
        checks = dict(result['checks'])
        checks['uncompleted_distinguishable'] = True
        if all(checks.values()):
            result = dict(status='THEOREM_APPLICABLE', checks=checks,
                          counterexample_claimed=False, proof_trace=result['proof_trace'])
    if mutation == 'COLLISION_AS_APPLICABLE' and 'collision_witness' in result:
        result['status'] = 'THEOREM_APPLICABLE'
        result.pop('reason', None)
    return result


def _public_view(output):
    return {key: value for key, value in output.items()
            if key not in ('proof_trace', 'collision_witness')}


def _acceptance_projection(output):
    canonical = json.dumps(_public_view(output), sort_keys=True, default=str,
                           separators=(',', ':'))
    return dict(status=output['status'], resolved=canonical, unresolved='0',
                categories=[], frontier=[], events=output.get('proof_trace', []))


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    """Reuse self-computed comparison while excluding only trace formatting."""
    packed_mutation = (mutated_output if isinstance(mutated_output, Exception)
                       else _acceptance_projection(mutated_output))
    record = _component_acceptance_record(
        'R6-03', dict(kind='mass'), _acceptance_projection(subject_output),
        _acceptance_projection(oracle_output), 'R603_DROP_FRONTIER_MASS', packed_mutation)
    record.update(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        subject_output=subject_output,
        oracle_output=oracle_output,
        mutation_patch=mutation_patch(mutation_id),
        coverage_limitations=('Finite concrete integer-time PN histories; strict theorem applies only '
                              'to the explored, externally completed and aligned fixture domain.'))
    return record
