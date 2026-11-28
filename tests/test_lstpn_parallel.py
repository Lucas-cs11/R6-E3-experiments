import sys
from fractions import Fraction
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/probability'))
from lstpn_parallel import (closed_form, f0, f1, gamma_structural, pe_exact,
                            twenty_one_points_exact)


class ParallelLstpnTests(unittest.TestCase):
    def test_f0_normalization(self):
        # integrate f0 exactly on breakpoints 2,3,4
        def antider(lo, hi, slope, inter):
            return slope * hi * hi / 2 + inter * hi - (slope * lo * lo / 2 + inter * lo)
        total = antider(2, 3, Fraction(1, 2), Fraction(-3, 4)) + antider(3, 4, 0, Fraction(1, 2))
        self.assertEqual(total, 1)

    def test_f0_piecewise_matches_max_derivation(self):
        # F0(y)=P(X3<=y)P(X5<=y); density at sample points
        for y in (Fraction(5, 2), Fraction(7, 2)):
            numeric = (f0(y - Fraction(1, 1000)) + f0(y + Fraction(1, 1000))) / 2
            self.assertEqual(numeric, f0(y))

    def test_21_points_match_closed_form(self):
        rows = twenty_one_points_exact()
        self.assertEqual(len(rows), 21)
        self.assertTrue(all(r['pe_match'] for r in rows))
        self.assertTrue(all(r['gamma_match'] for r in rows))

    def test_anchor_values(self):
        rows = {r['k']: r for r in twenty_one_points_exact()}
        self.assertEqual((rows[0]['pe_engine'], rows[0]['gamma_structural']),
                         (Fraction(1, 4), Fraction(1, 2)))
        self.assertEqual((rows[10]['pe_engine'], rows[10]['gamma_structural']),
                         (Fraction(1, 8), Fraction(17, 24)))
        self.assertEqual((rows[20]['pe_engine'], rows[20]['gamma_structural']),
                         (Fraction(0), Fraction(1)))

    def test_posterior_coverage_equals_closed_form(self):
        rows = twenty_one_points_exact()
        self.assertTrue(all(r['gamma_posterior'] == r['gamma_closed'] for r in rows))

    def test_pe_monotone_decreasing(self):
        rows = twenty_one_points_exact()
        pes = [r['pe_engine'] for r in rows]
        self.assertTrue(all(a > b for a, b in zip(pes, pes[1:])))


if __name__ == '__main__':
    unittest.main()
