"""R6-09 exact finite piecewise-rational integration with explicit boundaries."""
from fractions import Fraction as F
import json

from r6_components import make_acceptance_record as _component_acceptance_record


_PATCHES = {
    'DROP_SEGMENT_BOUNDARY': dict(
        component_id='R6-09', old='require exactly one owner of each shared segment boundary',
        new='skip the boundary-gap check after dropping both owners'),
    'CLIP_UPPER': dict(
        component_id='R6-09', old='reject a clipped density whose total mass is not one',
        new='retain clipped mass above one as an exact certificate'),
}


class _EvidenceError(ValueError):
    pass


def mutation_patch(mutation_id):
    return dict(_PATCHES[mutation_id], mutation_id=mutation_id,
                mode='SPECIFIC_INTEGRATION_SEMANTIC_MUTATION')


def _number(value):
    if type(value) not in (int, str, F):
        raise _EvidenceError('NON_RATIONAL_COEFFICIENT')
    try:
        return F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise _EvidenceError('NON_RATIONAL_COEFFICIENT') from exc


def _polynomial_value(coefficients, point):
    return sum((coefficient * point ** degree for degree, coefficient in enumerate(coefficients)), F(0))


def _check_nonnegative(coefficients, low, high):
    degree = len(coefficients) - 1
    if degree > 2:
        raise _EvidenceError('POLYNOMIAL_DEGREE_UNSUPPORTED')
    points = [low, high]
    if degree == 2 and coefficients[2] != 0:
        vertex = -coefficients[1] / (2 * coefficients[2])
        if low < vertex < high:
            points.append(vertex)
    if any(_polynomial_value(coefficients, point) < 0 for point in points):
        raise _EvidenceError('NEGATIVE_DENSITY')


def _integrate_segments(segments, mutation=None):
    if not isinstance(segments, list) or not segments:
        raise _EvidenceError('EMPTY_PIECEWISE_DOMAIN')
    rows = []
    total = F(0)
    previous = None
    for index, segment in enumerate(segments):
        low, high = _number(segment['low']), _number(segment['high'])
        coefficients = [_number(value) for value in segment['coefficients']]
        if low >= high:
            raise _EvidenceError('EMPTY_OR_REVERSED_SEGMENT')
        include_low = segment['include_low']
        include_high = segment['include_high']
        if type(include_low) is not bool or type(include_high) is not bool:
            raise _EvidenceError('BOUNDARY_FLAG_NOT_BOOLEAN')
        if index == 0 and not include_low:
            raise _EvidenceError('LEFT_DOMAIN_ENDPOINT_UNOWNED')
        if previous is not None:
            if previous[1] != low:
                raise _EvidenceError('NON_CONTIGUOUS_SEGMENTS')
            if previous[2] == include_low and mutation != 'DROP_SEGMENT_BOUNDARY':
                raise _EvidenceError('BOUNDARY_OWNERSHIP')
        rows.append((index, low, high, coefficients, include_low, include_high))
        previous = (index, high, include_high)
    if not rows[-1][5]:
        raise _EvidenceError('RIGHT_DOMAIN_ENDPOINT_UNOWNED')

    result = []
    for index, low, high, coefficients, include_low, include_high in rows:
        _check_nonnegative(coefficients, low, high)
        mass = sum((coefficient / (degree + 1) *
                    (high ** (degree + 1) - low ** (degree + 1))
                    for degree, coefficient in enumerate(coefficients)), F(0))
        total += mass
        result.append(dict(index=index, low=str(low), high=str(high), mass=str(mass),
                           boundary_ownership=('LOW_CLOSED_' if include_low else 'LOW_OPEN_') +
                                              ('HIGH_CLOSED' if include_high else 'HIGH_OPEN')))
    return result, total


def _apply_case_mutation(model, case, mutation):
    if not case.get('drop_boundary'):
        return model
    mutated = dict(model)
    segments = [dict(segment) for segment in model['segments']]
    segments[0]['include_high'] = False
    segments[1]['include_low'] = False
    mutated['segments'] = segments
    return mutated


def run_r609(model, case, mutation=None):
    """Integrate finite polynomial segments or rectangle products exactly."""
    if mutation not in (None, 'DROP_SEGMENT_BOUNDARY', 'CLIP_UPPER'):
        raise ValueError('unknown R6-09 mutation')
    try:
        model = _apply_case_mutation(model, case, mutation)
        if model['kind'] == 'piecewise_polynomial':
            rows, total = _integrate_segments(model['segments'], mutation)
            if total != 1 and mutation != 'CLIP_UPPER':
                raise _EvidenceError('TOTAL_MASS_NOT_ONE')
            return dict(status='EXACT_PIECEWISE_RATIONAL_INTEGRAL', certified=False,
                        conditional_verdict=None, total_mass=str(total), segments=rows)
        if model['kind'] == 'rectangle_product':
            cells = []
            total = F(0)
            for rectangle in model['category']['rectangles']:
                axis_masses = []
                product = F(1)
                for axis in rectangle['axes']:
                    _rows, mass = _integrate_segments(axis['segments'], mutation)
                    axis_masses.append(str(mass))
                    product *= mass
                total += product
                cells.append(dict(id=rectangle['id'], mass=str(product), axes=axis_masses))
            if total != 1 and mutation != 'CLIP_UPPER':
                raise _EvidenceError('TOTAL_MASS_NOT_ONE')
            return dict(status='EXACT_PIECEWISE_RATIONAL_INTEGRAL', certified=False,
                        conditional_verdict=None, total_mass=str(total), cells=cells)
        raise _EvidenceError('UNSUPPORTED_MODEL_KIND')
    except _EvidenceError as exc:
        return dict(status='INVALID_EVIDENCE', certified=False,
                    conditional_verdict=None, reason=str(exc))


def _acceptance_projection(output):
    canonical = json.dumps(output, sort_keys=True, default=str, separators=(',', ':'))
    events = output.get('segments', output.get('cells', []))
    return dict(status=output['status'], resolved=canonical, unresolved='0',
                categories=[], frontier=[], events=events)


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    """Reuse full-output self-comparison from the component acceptance recorder."""
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
        coverage_limitations=('Finite low-degree rational piecewise integration and rectangle products; '
                              'no claim for infinite domains or non-polyhedral categories.'))
    return record
