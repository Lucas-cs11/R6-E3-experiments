"""Independent R6-09 reference using exact Simpson quadrature, not antiderivatives."""
from fractions import Fraction as Q


class _Invalid(ValueError):
    pass


class _Unsupported(ValueError):
    pass


def _rational(value):
    if type(value) not in (int, str, Q):
        raise _Invalid('NON_RATIONAL_COEFFICIENT')
    try:
        return Q(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise _Invalid('NON_RATIONAL_COEFFICIENT') from exc


def _value(coefficients, x):
    return sum((coefficient * x ** power for power, coefficient in enumerate(coefficients)), Q(0))


def _nonnegative(coefficients, low, high):
    if len(coefficients) > 3:
        raise _Invalid('POLYNOMIAL_DEGREE_UNSUPPORTED')
    candidates = [low, high]
    if len(coefficients) == 3 and coefficients[2]:
        vertex = -coefficients[1] / (2 * coefficients[2])
        if low < vertex < high:
            candidates.append(vertex)
    if any(_value(coefficients, point) < 0 for point in candidates):
        raise _Invalid('NEGATIVE_DENSITY')


def _simpson(segments, drop_boundary=False):
    if not isinstance(segments, list) or not segments:
        raise _Invalid('EMPTY_PIECEWISE_DOMAIN')
    previous = None
    rows = []
    total = Q(0)
    for index, segment in enumerate(segments):
        if any(segment.get(key) is None or
               (isinstance(segment.get(key), str) and segment[key].lower() in
                ('inf', '+inf', '-inf', 'infinity', '+infinity', '-infinity'))
               for key in ('low', 'high')):
            raise _Unsupported('NON_FINITE_DOMAIN')
        if not isinstance(segment.get('coefficients'), list):
            raise _Unsupported('NON_RATIONAL_POLYNOMIAL')
        low, high = _rational(segment['low']), _rational(segment['high'])
        coefficients = [_rational(value) for value in segment['coefficients']]
        include_low, include_high = segment['include_low'], segment['include_high']
        if low >= high:
            raise _Invalid('EMPTY_OR_REVERSED_SEGMENT')
        if type(include_low) is not bool or type(include_high) is not bool:
            raise _Invalid('BOUNDARY_FLAG_NOT_BOOLEAN')
        if index == 0 and not include_low:
            raise _Invalid('LEFT_DOMAIN_ENDPOINT_UNOWNED')
        if previous is not None:
            if previous[0] != low:
                raise _Invalid('NON_CONTIGUOUS_SEGMENTS')
            if previous[1] == include_low and not drop_boundary:
                raise _Invalid('BOUNDARY_OWNERSHIP')
        _nonnegative(coefficients, low, high)
        midpoint = (low + high) / 2
        mass = ((high - low) / 6 *
                (_value(coefficients, low) + 4 * _value(coefficients, midpoint) +
                 _value(coefficients, high)))
        total += mass
        rows.append(dict(index=index, low=str(low), high=str(high), mass=str(mass),
                         boundary_ownership=('LOW_CLOSED_' if include_low else 'LOW_OPEN_') +
                                            ('HIGH_CLOSED' if include_high else 'HIGH_OPEN')))
        previous = (high, include_high)
    if not segments[-1]['include_high']:
        raise _Invalid('RIGHT_DOMAIN_ENDPOINT_UNOWNED')
    return rows, total


def reference_r609(model, case, mutation=None):
    """Simpson reference; mutation is accepted only to compare identical invalid calls."""
    if mutation not in (None, 'DROP_SEGMENT_BOUNDARY', 'CLIP_UPPER'):
        raise ValueError('unknown reference mutation')
    if 'depth' in case and case['depth'] > model['max_depth']:
        return dict(status='UNRESOLVED', certified=False, conditional_verdict=None,
                    reason='DEPTH_LIMIT_EXCEEDED')
    if 'time' in case and (Q(case['time']) > Q(model['max_time']) or
                           Q(case['time']) > Q(model['H_A'])):
        return dict(status='UNRESOLVED', certified=False, conditional_verdict=None,
                    reason='HORIZON_LIMIT_EXCEEDED')
    try:
        if case.get('drop_boundary'):
            model = dict(model)
            model['segments'] = [dict(segment) for segment in model['segments']]
            model['segments'][0]['include_high'] = False
            model['segments'][1]['include_low'] = False
        allow_nonunit = mutation == 'CLIP_UPPER'
        if model['kind'] == 'piecewise_polynomial':
            rows, total = _simpson(model['segments'], case.get('drop_boundary'))
            if total != 1 and not allow_nonunit:
                raise _Invalid('TOTAL_MASS_NOT_ONE')
            return dict(status='EXACT_PIECEWISE_RATIONAL_INTEGRAL', certified=False,
                        conditional_verdict=None, total_mass=str(total), segments=rows)
        if model['kind'] == 'rectangle_product':
            if model['category'].get('kind') != 'rectangles':
                raise _Unsupported('NON_POLYHEDRAL_CATEGORY')
            cells = []
            total = Q(0)
            for rectangle in model['category']['rectangles']:
                product = Q(1)
                axis_masses = []
                for axis in rectangle['axes']:
                    _rows, mass = _simpson(axis['segments'])
                    product *= mass
                    axis_masses.append(str(mass))
                cells.append(dict(id=rectangle['id'], mass=str(product), axes=axis_masses))
                total += product
            if total != 1 and not allow_nonunit:
                raise _Invalid('TOTAL_MASS_NOT_ONE')
            return dict(status='EXACT_PIECEWISE_RATIONAL_INTEGRAL', certified=False,
                        conditional_verdict=None, total_mass=str(total), cells=cells)
        raise _Invalid('UNSUPPORTED_MODEL_KIND')
    except _Unsupported as exc:
        return dict(status='UNSUPPORTED', certified=False,
                    conditional_verdict=None, reason=str(exc))
    except _Invalid as exc:
        return dict(status='INVALID_EVIDENCE', certified=False,
                    conditional_verdict=None, reason=str(exc))
