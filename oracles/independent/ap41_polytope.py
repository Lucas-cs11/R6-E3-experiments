"""Small exact LP oracle: enumerate vertices of a bounded rational polytope.

Input is a mathematical mass problem, not a submitted certificate. Free
remainder coordinates account for any unlisted mass in an open partition.
"""
from fractions import Fraction as F
from itertools import combinations


def solve_square(rows):
    a = [[F(x) for x in row] for row in rows]
    for j in range(len(a)):
        pivot = next((i for i in range(j, len(a)) if a[i][j]), None)
        if pivot is None:
            return None
        a[j], a[pivot] = a[pivot], a[j]
        div = a[j][j]
        a[j] = [x / div for x in a[j]]
        for i in range(len(a)):
            if i != j and a[i][j]:
                k = a[i][j]
                a[i] = [x-k*y for x,y in zip(a[i],a[j])]
    return tuple(row[-1] for row in a)


def project(q, groups, closed):
    """Return exact coordinate extrema, or None for an empty feasible set."""
    keys = [(i,k) for i in range(2) for k in groups[i]]
    keys += [(i,None) for i in range(2) if not closed[i]]
    n = len(keys)
    if not 1 <= n <= 6:
        raise ValueError('oracle supports 1 to 6 mass coordinates')
    inequalities = []
    def constrain(coeff, lo, hi):
        inequalities.extend([(*coeff,F(hi)), (*(-x for x in coeff),-F(lo))])
    for j,(i,k) in enumerate(keys):
        basis = [int(t==j) for t in range(n)]
        constrain(basis, 0, 1)
        if k is not None:
            constrain(basis, *groups[i][k])
    selectors = [tuple(int(g==i) for g,_ in keys) for i in range(2)]
    for i in range(2):
        constrain(selectors[i], *q[i])
    def dot(a,b):
        return sum(x*y for x,y in zip(a,b))
    vertices = set()
    equality = (1,)*n+(1,)
    for active in combinations(dict.fromkeys(inequalities), n-1):
        v = solve_square([equality,*active])
        if v is not None and all(dot(row[:-1],v)<=row[-1] for row in inequalities):
            vertices.add(v)
    if not vertices:
        return None
    def extrema(values):
        values = tuple(values)
        return min(values),max(values)
    return {'q':[extrema(dot(a,v) for v in vertices) for a in selectors],
            'categories':[{k:extrema(v[j] for v in vertices) for j,(g,k) in enumerate(keys)
                           if g==i and k is not None} for i in range(2)],
            'vertices': sorted(vertices), 'coordinates': keys}
