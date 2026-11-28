"""E3-09: exact parallel LSTPN probability engine (real topology X3/X5/X4).

Model (frozen TeX section 2/4): X3~U[2,4], X5~U[1,3] run in parallel; normal
completion Y0=max(X3,X5); fault completion X4~U[a4,5] with Y1=X4 (a.s.).
Observation = completion time.  Priors pi=(1/2,1/2).

All arithmetic exact via fractions.  This module computes the normal-completion
density from the parallel timers (not a hard-coded density), the Bayes error
Pe = pi0*int min(pi0 f0, pi1 f1) style overlap mass, and two candidate
reliability-coverage definitions which are then checked against the frozen
21-point anchors.
"""
from fractions import Fraction

R = Fraction


def _cdf_x3(y):
    """P(X3 <= y), X3 ~ U[2,4]."""
    if y < 2:
        return R(0)
    if y > 4:
        return R(1)
    return (y - 2) / 2


def _cdf_x5(y):
    """P(X5 <= y), X5 ~ U[1,3]."""
    if y < 1:
        return R(0)
    if y > 3:
        return R(1)
    return y - 1


def cdf_y0(y):
    """P(max(X3,X5) <= y) = P(X3<=y) P(X5<=y) by independence."""
    return _cdf_x3(y) * _cdf_x5(y)


def f0(y):
    """Normal completion density = d/dy P(max(X3,X5)<=y), piecewise exact."""
    if y < 2 or y > 4:
        return R(0)
    if y < 3:
        return (2 * y - 3) / 4          # derivative of (y-2)(y-1)/4
    return R(1, 2)                       # derivative of (y-2)/2


def f1(y, a4):
    """Fault completion density: X4 ~ U[a4,5]."""
    if y < a4 or y > 5:
        return R(0)
    return 1 / (5 - a4)


def integrate(piecewise, lo, hi, steps=2000):
    """Exact-rational quadrature of a piecewise-polynomial density on [lo,hi].

    The densities here are piecewise linear at worst, so midpoint trapezoid
    with rational breakpoints is exact up to segment subdivision.
    """
    if hi <= lo:
        return R(0)
    total = R(0)
    width = (hi - lo) / steps
    for k in range(steps):
        a = lo + width * k
        b = lo + width * (k + 1)
        fa = piecewise((a + b) / 2)
        total += fa * (b - a)
    return total


def pe_bayes(a4):
    """Bayes error Pe = int min(pi0 f0, pi1 f1) dy with pi=(1/2,1/2)."""
    lo, hi = R(2), R(5)
    steps = 600
    width = (hi - lo) / steps
    total = R(0)
    for k in range(steps):
        a = lo + width * k
        b = lo + width * (k + 1)
        mid = (a + b) / 2
        total += min(f0(mid) / 2, f1(mid, a4) / 2) * (b - a)
    return total


def gamma_posterior(a4, delta=R(15, 100)):
    """Coverage where posterior of the declared hypothesis >= 1-delta."""
    lo, hi = R(2), R(5)
    steps = 2000
    width = (hi - lo) / steps
    total = R(0)
    for k in range(steps):
        a = lo + width * k
        b = lo + width * (k + 1)
        mid = (a + b) / 2
        d0 = f0(mid) / 2
        d1 = f1(mid, a4) / 2
        tot = d0 + d1
        if tot == 0:
            continue
        p1 = d1 / tot
        if p1 >= 1 - delta:
            total += d1 * (b - a)      # mass under H1, reliable H1
        elif p1 <= delta:
            total += d0 * (b - a)      # mass under H0, reliable H0
    return total


def gamma_no_overlap(a4):
    """Coverage of observations outside the density overlap [a4,4]."""
    return (_cdf_x3(a4)) / 2 + (1 - (4 - a4) / (5 - a4)) / 2


def closed_form(a4):
    return (4 - a4) / 4, (a4 - 2) / 4 + 1 / (2 * (5 - a4))


def twenty_one_points():
    out = []
    for k in range(21):
        a4 = 3 + R(k, 20)
        pe = pe_bayes(a4)
        pe_cf, gamma_cf = closed_form(a4)
        out.append({'k': k, 'a4': a4, 'pe_engine': pe, 'pe_closed': pe_cf,
                    'pe_match': pe == pe_cf,
                    'gamma_posterior_015': gamma_posterior(a4),
                    'gamma_no_overlap': gamma_no_overlap(a4),
                    'gamma_closed': gamma_cf})
    return out


def _affine_segments(a4):
    """Breakpoints where f0 or f1 change form or cross: {2,3,a4,4,5} clipped."""
    pts = {R(2), R(3), R(4), R(5), a4}
    return sorted(p for p in pts if R(2) <= p <= R(5))


def _f0_affine(y):
    """f0 as affine coefficients (slope, intercept), zero outside [2,4]."""
    if y < 2 or y > 4:
        return R(0), R(0)
    if y < 3:
        return R(2, 4), R(-3, 4)      # (2y-3)/4
    return R(0), R(1, 2)


def _integrate_affine(seg_lo, seg_hi, slope, intercept):
    """Exact integral of slope*y+intercept over [lo,hi]."""
    def antider(y):
        return slope * y * y / 2 + intercept * y
    return antider(seg_hi) - antider(seg_lo)


def _split_at(root, lo, hi):
    """Return segments of [lo,hi] split at root if root lies strictly inside."""
    if lo < root < hi:
        return [(lo, root), (root, hi)]
    return [(lo, hi)]


def pe_exact(a4):
    """Exact Bayes error with pi=(1/2,1/2): 1/2 * int min(f0,f1)."""
    total = R(0)
    for s_lo, s_hi in zip(_affine_segments(a4)[:-1], _affine_segments(a4)[1:]):
        if s_hi <= s_lo:
            continue
        mid = (s_lo + s_hi) / 2
        f0_slope, f0_inter = _f0_affine(mid)
        f1_slope, f1_inter = (R(0), 1 / (5 - a4)) if mid >= a4 else (R(0), R(0))
        # solve f0 == f1: (f0_slope-f1_slope) y = f1_inter - f0_inter
        denom = f0_slope - f1_slope
        segments = [(s_lo, s_hi)]
        if denom != 0:
            root = (f1_inter - f0_inter) / denom
            segments = _split_at(root, s_lo, s_hi)
        for lo, hi in segments:
            m = (lo + hi) / 2
            if f0(m) <= f1(m, a4):
                total += _integrate_affine(lo, hi, f0_slope, f0_inter)
            else:
                total += _integrate_affine(lo, hi, f1_slope, f1_inter)
    return total / 2


def gamma_structural(a4):
    """TeX closed-form reliability coverage:
    Gamma = pi0*P(X3<=a4) + pi1*P(X4>=4), pi=(1/2,1/2).

    NOTE: this region is defined on the *planned* normal timer X3, not the
    observed completion Y0=max(X3,X5).  Posterior-threshold coverage on the
    observation (see gamma_exact) differs; the discrepancy is recorded for
    the theory reviewer (a4=7/2: posterior 15/16 vs closed form 3/4+1/3=17/24).
    """
    return ((a4 - 2) / R(2) + 1 / (5 - a4)) / 2


def gamma_exact(a4, delta=R(15, 100)):
    """Exact posterior-threshold coverage on the observation.

    Reliable H1: delta*f1 >= (1-delta)*f0; reliable H0: (1-delta)*f1 <= delta*f0.
    Split at crossovers.  Differs from gamma_structural for a4>3."""
    total = R(0)
    for s_lo, s_hi in zip(_affine_segments(a4)[:-1], _affine_segments(a4)[1:]):
        if s_hi <= s_lo:
            continue
        mid = (s_lo + s_hi) / 2
        f0_slope, f0_inter = _f0_affine(mid)
        f1_slope, f1_inter = (R(0), 1 / (5 - a4)) if mid >= a4 else (R(0), R(0))
        # H1 reliable: delta*f1 >= (1-delta)*f0  ->  delta*f1-(1-delta)*f0 >= 0
        a_slope = delta * f1_slope - (1 - delta) * f0_slope
        a_inter = delta * f1_inter - (1 - delta) * f0_inter
        segments = [(s_lo, s_hi)]
        if a_slope != 0:
            root = -a_inter / a_slope
            segments = _split_at(root, s_lo, s_hi)
        for lo, hi in segments:
            m = (lo + hi) / 2
            if a_slope * m + a_inter >= 0:
                total += _integrate_affine(lo, hi, f1_slope, f1_inter)
            else:
                # H0 reliable: (1-delta)*f1 <= delta*f0
                b_slope = (1 - delta) * f1_slope - delta * f0_slope
                b_inter = (1 - delta) * f1_inter - delta * f0_inter
                if b_slope * m + b_inter <= 0:
                    total += _integrate_affine(lo, hi, f0_slope, f0_inter)
    return total


def twenty_one_points_exact():
    out = []
    for k in range(21):
        a4 = 3 + R(k, 20)
        pe = pe_exact(a4)
        gamma_struct = gamma_structural(a4)
        gamma_post = gamma_exact(a4)
        pe_cf, gamma_cf = closed_form(a4)
        out.append({'k': k, 'a4': a4, 'pe_engine': pe, 'pe_closed': pe_cf,
                    'pe_match': pe == pe_cf, 'gamma_structural': gamma_struct,
                    'gamma_posterior': gamma_post,
                    'gamma_closed': gamma_cf, 'gamma_match': gamma_struct == gamma_cf})
    return out
