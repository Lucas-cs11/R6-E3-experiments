"""Deterministic, label-blind features for pyscrew raw-v1 JSON records.

Feature list (stable lexical order): for each tightening step i, sample_count,
duration, angle_start/end/mean/peak, torque_mean/peak/min/end, gradient_mean,
gradient_abs_peak, and trapezoid torque_area over time.  Global features are
step_count, total_duration, angle_total_mean, torque_total_mean, torque_peak,
and final_torque.  ``time values`` supplies duration and trapezoid integration.
Missing steps use step{i}_missing=1 with zero-filled step metrics; actual
step_count is retained, so early termination is explicit rather than an error.
Only ``angle/torque/gradient/time values`` are read; result labels and metadata
never enter the feature vector.  Repeated input produces identical floats.
"""
from fractions import Fraction as F
import json


def _mean(values):
    return sum(values, F(0)) / len(values)


def _series(step, name):
    values = step['graph'][name]
    if not values or any(type(value) not in (int, float, str, F) for value in values):
        raise ValueError(f'invalid series {name}')
    return [F(str(value)) for value in values]


def _step_features(step, index):
    graph = step['graph']
    angle = _series(step, 'angle values')
    torque = _series(step, 'torque values')
    gradient = _series(step, 'gradient values')
    times = _series(step, 'time values')
    if len(angle) != len(torque) or len(angle) != len(gradient) or len(angle) != len(times) or not angle:
        raise ValueError('series length mismatch')
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError('non-monotonic time values')
    duration = times[-1] - times[0]
    if duration < 0:
        raise ValueError('negative duration')
    area = sum(((times[j] - times[j - 1]) * (torque[j] + torque[j - 1]) / 2
                for j in range(1, len(times))), F(0))
    prefix = f'step{index}_'
    return {
        prefix + 'sample_count': len(angle),
        prefix + 'duration': duration,
        prefix + 'angle_start': angle[0],
        prefix + 'angle_end': angle[-1],
        prefix + 'angle_mean': _mean(angle),
        prefix + 'angle_peak': max(angle),
        prefix + 'torque_mean': _mean(torque),
        prefix + 'torque_peak': max(torque),
        prefix + 'torque_min': min(torque),
        prefix + 'torque_end': torque[-1],
        prefix + 'gradient_mean': _mean(gradient),
        prefix + 'gradient_abs_peak': max(abs(value) for value in gradient),
        prefix + 'torque_area': area,
    }


def extract_features(raw):
    """Return an ordered {feature_name: float} mapping with no random choices."""
    if isinstance(raw, (str, bytes)):
        raw = json.loads(raw)
    steps = raw.get('tightening steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('tightening steps missing')
    values = {}
    all_angles, all_torques, all_times = [], [], []
    for index, step in enumerate(steps):
        values.update(_step_features(step, index))
        all_angles.extend(_series(step, 'angle values'))
        all_torques.extend(_series(step, 'torque values'))
        all_times.extend(_series(step, 'time values'))
    values.update({
        'step_count': len(steps),
        'total_duration': max(all_times) - min(all_times),
        'angle_total_mean': _mean(all_angles),
        'torque_total_mean': _mean(all_torques),
        'torque_peak': max(all_torques),
        'final_torque': all_torques[-1],
    })
    return {name: float(values[name]) for name in sorted(values)}


def feature_names(raw):
    return sorted(extract_features(raw))


def feature_vector(raw):
    values = extract_features(raw)
    return [values[name] for name in sorted(values)]
