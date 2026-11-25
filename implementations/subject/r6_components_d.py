"""R6-10/11 component integration with independent evidence comparison."""
import json
from fractions import Fraction as F

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
    'R611_IGNORE_COARSENING': dict(
        component_id='R6-11', old='recompute joint law after merging atoms',
        new='copy fine-grained Pe/Gamma onto the coarsened observation'),
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


def _integral(intercept, slope, low, high):
    return intercept * (high - low) + slope * (high * high - low * low) / 2


def _zero_measure_case(spec):
    low, high = map(F, spec['interval'])
    constant = F(spec['density0']['value'])
    slope = F(spec['density1']['coefficient'])
    if _integral(constant, F(0), low, high) != 1 or _integral(F(0), slope, low, high) != 1:
        return dict(status='INVALID_EVIDENCE', reason='DENSITY_NOT_NORMALIZED')
    crossing = constant / slope
    if not low < crossing < high:
        raise ValueError('regression requires one interior density crossing')
    # min(1,2x) is 2x left of 1/2 and 1 right of it.
    minimum_mass = (_integral(F(0), slope, low, crossing) +
                    _integral(constant, F(0), crossing, high))
    error = F(spec['prior0']) * minimum_mass
    return dict(status='ZERO_MEASURE_SHARED_POINT', mass_added='0',
                Pe_before=str(error), Pe_after=str(error), delta_Pe='0')


def _atom_rows(joint, delta):
    rows = []
    for left, right in joint:
        mixture = left + right
        error = min(left, right)
        posterior = error / mixture
        rows.append(dict(joint=[str(left), str(right)], posterior_error=str(posterior),
                         reliable=posterior <= delta))
    return rows


def _coarsening_case(spec, case, mutation):
    atoms = list(spec['atoms'])
    if case.get('drop_atom'):
        atoms = atoms[:-1]
    if any(sum(F(atom[f'h{i}']) for atom in atoms) != 1 for i in range(2)):
        return dict(status='INVALID_EVIDENCE', reason='HYPOTHESIS_MASS_NOT_ONE')
    pi0, pi1, delta = F(spec['prior0']), F(spec['prior1']), F(spec['delta'])
    joint = [(pi0 * F(atom['h0']), pi1 * F(atom['h1'])) for atom in atoms]
    merged = [(sum((row[0] for row in joint), F(0)),
               sum((row[1] for row in joint), F(0)))]
    before_rows, after_rows = _atom_rows(joint, delta), _atom_rows(merged, delta)
    pe_before = sum((min(row) for row in joint), F(0))
    pe_after = sum((min(row) for row in merged), F(0))
    gamma_before = sum((F(row['joint'][0]) + F(row['joint'][1])
                        for row in before_rows if row['reliable']), F(0))
    gamma_after = sum((F(row['joint'][0]) + F(row['joint'][1])
                       for row in after_rows if row['reliable']), F(0))
    if mutation == 'R611_IGNORE_COARSENING':
        pe_after, gamma_after = pe_before, gamma_before
    return dict(status='EXACT_COARSENING_PAIR', Pe_before=str(pe_before),
                Pe_after=str(pe_after), Gamma_before=str(gamma_before),
                Gamma_after=str(gamma_after), monotonic_Pe=pe_after >= pe_before,
                atoms_before=before_rows, atoms_after=after_rows,
                proof_trace=[*before_rows, *after_rows])


def run_r611(model, case, mutation=None):
    if mutation not in (None, 'R611_IGNORE_COARSENING'):
        raise ValueError('unknown R6-11 mutation')
    if case['kind'] == 'zero_measure':
        return _zero_measure_case(model['zero_measure'])
    if case['kind'] == 'coarsening':
        return _coarsening_case(model['atomic'], case, mutation)
    raise ValueError('unknown R6-11 case kind')


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
