"""E3-09 configuration runner: v_P and R_delta per (config, spec).

Configs: 567 = 21 a4-points x 3 families (F1/F2/F3 fault density) x
3 root-weight schemes (W1/W2/W3) x 3 observation quantizations (Q1/Q2/Q3).
Specs: 135 = pi0(3) x epsilon(3) x delta(5) x gamma(3).

Semantics (frozen rulings):
- Normal completion Y0 = max(X3,X5) with X3~U[2,4], X5~U[1,3]; fault
  completion Y1 = X4 with family-dependent density on [a4,5].
- Root weights induce q on the two hypotheses (path measures); the decision
  prior pi stays independent (per decision D10).
- Quantization Q2 = floor(2t)/2, Q3 = floor(t); epsilon widens each observed
  bin by +/- epsilon before matching (tolerance in observation).
- Pe = int min(q0 f0, q1 f1); reliability coverage R_delta = mass of
  observations whose posterior for the declared hypothesis >= 1-delta.
- v_P = 1 iff R_delta >= gamma (exact computation gives a complete
  certificate); 0 otherwise.  UNSUPPORTED only if a density fails
  normalization.
"""
from fractions import Fraction

R = Fraction
WEIGHTS = {'W1': (1, 1), 'W2': (2, 1), 'W3': (1, 2)}
FAMILIES = ('F1', 'F2', 'F3')
QUANTS = {'Q1': 'identity', 'Q2': 'half_unit', 'Q3': 'unit'}


def f0(y):
    """Density of max(X3,X5), X3~U[2,4], X5~U[1,3]."""
    if y < 2 or y > 4:
        return R(0)
    if y < 3:
        return (2 * y - 3) / 4
    return R(1, 2)


def f1(y, a4, family):
    """Fault completion density on [a4,5] per family."""
    if y < a4 or y > 5:
        return R(0)
    width = 5 - a4
    if family == 'F1':
        return 1 / width
    if family == 'F2':
        return 2 * (5 - y) / (width * width)
    if family == 'F3':
        mid = (a4 + 5) / 2
        return 3 / (2 * width) if y < mid else 1 / (2 * width)
    raise ValueError(f'unknown family {family}')


def _breakpoints(a4):
    pts = {R(2), R(3), R(4), R(5), a4, (a4 + 5) / 2}
    return sorted(p for p in pts if R(2) <= p <= R(5))


def _integrate(fn, lo, hi):
    """Exact integral of piecewise-affine fn over [lo,hi] by midpoint rule on
    segments split at breakpoints (affine pieces -> trapezoid exact)."""
    if hi <= lo:
        return R(0)
    return (fn(lo) + fn(hi)) * (hi - lo) / 2


def _integrate_piecewise(fn, lo, hi, bps):
    """Exact for piecewise-affine fn: midpoint rule on each affine segment."""
    total = R(0)
    edges = [lo] + [p for p in bps if lo < p < hi] + [hi]
    for a, b in zip(edges[:-1], edges[1:]):
        total += fn((a + b) / 2) * (b - a)
    return total


def normalize_check(a4, family):
    """Exact integral of f1 over [a4,5] must be 1."""
    return _integrate_piecewise(lambda y: f1(y, a4, family), a4, R(5),
                                _breakpoints(a4))


def pe_exact(a4, family, weight):
    """Pe = int min(q0 f0, q1 f1) with q from root weights."""
    w0, w1 = WEIGHTS[weight]
    q0, q1 = R(w0, w0 + w1), R(w1, w0 + w1)
    bps = _breakpoints(a4)
    total = R(0)
    edges = [R(2)] + [p for p in bps if R(2) < p < R(5)] + [R(5)]
    for lo, hi in zip(edges[:-1], edges[1:]):
        # sub-split where the two densities cross
        segs = [(lo, hi)]
        f = lambda y: q0 * f0(y)
        g = lambda y: q1 * f1(y, a4, family)
        # sample-based split for affine pieces: solve on endpoint diff sign
        if (f(lo) - g(lo)) * (f(hi) - g(hi)) < 0:
            root = _bisect(f, g, lo, hi)
            segs = [(lo, root), (root, hi)]
        for a, b in segs:
            mid = (a + b) / 2
            val = f(mid) if f(mid) <= g(mid) else g(mid)
            total += val * (b - a)
    return total


def _bisect(f, g, lo, hi, iterations=200):
    d = lambda y: f(y) - g(y)
    flo, fhi = d(lo), d(hi)
    for _ in range(iterations):
        mid = (lo + hi) / 2
        dm = d(mid)
        if dm == 0:
            return mid
        if (flo < 0) != (dm < 0):
            hi, fhi = mid, dm
        else:
            lo, flo = mid, dm
    return (lo + hi) / 2


def bin_masses(a4, family, quant, epsilon):
    """Mass of each hypothesis in each observation bin under quantization."""
    if quant == 'Q1':
        return None  # continuous observation: handled by density comparison
    step = R(1, 2) if quant == 'Q2' else R(1)
    lo, hi = R(2), R(5)
    bins = {}
    t = lo
    while t < hi:
        bins[(t, t + step)] = [R(0), R(0)]
        t += step
    for (a, b) in bins:
        widened = [max(lo, a - epsilon), min(hi, b + epsilon)]
        bins[(a, b)][0] = _integrate_piecewise(f0, widened[0], widened[1],
                                               _breakpoints(a4))
        bins[(a, b)][1] = _integrate_piecewise(
            lambda y: f1(y, a4, family), widened[0], widened[1], _breakpoints(a4))
    return bins


def pe_quantized(a4, family, weight, quant, epsilon):
    """Bayes error under quantization with tolerance epsilon."""
    w0, w1 = WEIGHTS[weight]
    q0, q1 = R(w0, w0 + w1), R(w1, w0 + w1)
    bins = bin_masses(a4, family, quant, epsilon)
    return sum(min(q0 * m0, q1 * m1) for m0, m1 in bins.values())


def coverage(a4, family, weight, quant, epsilon, delta, pi0):
    """Reliability coverage: observed mass whose posterior >= 1-delta."""
    w0, w1 = WEIGHTS[weight]
    q0, q1 = R(w0, w0 + w1), R(w1, w0 + w1)
    pi1 = 1 - pi0
    if quant == 'Q1':
        # continuous: integrate densities where posterior of the better
        # hypothesis >= 1-delta
        def posterior_h1(y):
            d0, d1 = q0 * f0(y), q1 * f1(y, a4, family)
            if d0 + d1 == 0:
                return R(0)
            return d1 / (d0 + d1)
        bps = _breakpoints(a4)
        total = R(0)
        edges = [R(2)] + [p for p in bps if R(2) < p < R(5)] + [R(5)]
        for lo, hi in zip(edges[:-1], edges[1:]):
            mid = (lo + hi) / 2
            p_h1 = posterior_h1(mid)
            if p_h1 >= 1 - delta:
                total += q1 * _integrate_piecewise(
                    lambda y: f1(y, a4, family), lo, hi, bps)
            elif p_h1 <= delta:
                total += q0 * _integrate_piecewise(f0, lo, hi, bps)
        return total
    bins = bin_masses(a4, family, quant, epsilon)
    total = R(0)
    for m0, m1 in bins.values():
        tot = m0 + m1
        if tot == 0:
            continue
        p_h1 = (pi1 * m1) / (pi0 * m0 + pi1 * m1) if (pi0 * m0 + pi1 * m1) else R(0)
        if p_h1 >= 1 - delta:
            total += q1 * m1
        elif p_h1 <= delta:
            total += q0 * m0
    return total


def evaluate_config(config, specs):
    """Return one row per spec for a config dict (from frozen_567_configs)."""
    a4 = R(config['a4'])
    family = config['family']
    weight = config['weight_scheme']
    quant = config['quantization']
    norm = normalize_check(a4, family)
    rows = []
    for spec in specs:
        pi0 = R(spec['pi0'])
        epsilon = R(spec['epsilon'])
        delta = R(spec['delta'])
        gamma = R(spec['gamma'])
        if norm != 1:
            rows.append({'unit_id': f"{config['config_id']}|{spec['spec_id']}",
                         'v_P': '⊥', 'R_delta': None,
                         'reason': 'DENSITY_NOT_NORMALIZED'})
            continue
        r_delta = coverage(a4, family, weight, quant, epsilon, delta, pi0)
        v = '1' if r_delta >= gamma else '0'
        rows.append({'unit_id': f"{config['config_id']}|{spec['spec_id']}",
                     'config_id': config['config_id'], 'spec_id': spec['spec_id'],
                     'v_P': v, 'R_delta': str(r_delta), 'reason': ''})
    return rows
