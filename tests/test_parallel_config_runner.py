import sys
from fractions import Fraction
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'implementations/probability'))
from parallel_config_runner import (WEIGHTS, coverage, normalize_check, pe_exact,
                                    pe_quantized)


class ConfigRunnerTests(unittest.TestCase):
    def test_all_families_normalize(self):
        for family in ('F1', 'F2', 'F3'):
            for a4 in (Fraction(3), Fraction(7, 2), Fraction(4)):
                if a4 == 4 and family == 'F3':
                    continue
                self.assertEqual(normalize_check(a4, family), Fraction(1))

    def test_f1_baseline_pe_gamma(self):
        a4 = Fraction(3)
        self.assertEqual(pe_exact(a4, 'F1', 'W1'), Fraction(1, 4))
        self.assertEqual(coverage(a4, 'F1', 'W1', 'Q1', Fraction(0),
                                  Fraction(15, 100), Fraction(1, 2)), Fraction(1, 2))

    def test_weights_change_pe(self):
        a4 = Fraction(3)
        self.assertEqual(pe_exact(a4, 'F1', 'W1'), Fraction(1, 4))
        self.assertNotEqual(pe_exact(a4, 'F1', 'W2'), Fraction(1, 4))

    def test_f2_f3_positive_examples(self):
        for family in ('F2', 'F3'):
            pe = pe_exact(Fraction(7, 2), family, 'W1')
            self.assertGreater(pe, 0)
            self.assertLess(pe, Fraction(1, 4))

    def test_quantization_changes_result(self):
        # at a4=13/4 the half-unit grid merges the overlap band and lowers coverage
        a4 = Fraction(13, 4)
        q1 = coverage(a4, 'F1', 'W1', 'Q1', Fraction(0), Fraction(15, 100), Fraction(1, 2))
        q2 = coverage(a4, 'F1', 'W1', 'Q2', Fraction(0), Fraction(15, 100), Fraction(1, 2))
        self.assertNotEqual(q1, q2)
        self.assertGreaterEqual(q1, q2)
        # at a4=3 the grid coincides with the overlap band: equality is correct
        a4b = Fraction(3)
        self.assertEqual(
            coverage(a4b, 'F1', 'W1', 'Q1', Fraction(0), Fraction(15, 100), Fraction(1, 2)),
            coverage(a4b, 'F1', 'W1', 'Q2', Fraction(0), Fraction(15, 100), Fraction(1, 2)))

    def test_epsilon_widens_bins(self):
        a4 = Fraction(7, 2)
        e0 = coverage(a4, 'F1', 'W1', 'Q3', Fraction(0), Fraction(15, 100), Fraction(1, 2))
        e1 = coverage(a4, 'F1', 'W1', 'Q3', Fraction(1, 8), Fraction(15, 100), Fraction(1, 2))
        self.assertGreaterEqual(e1, e0)

    def test_pe_monotone_in_a4(self):
        prev = None
        for k in range(21):
            a4 = Fraction(3) + Fraction(k, 20)
            pe = pe_exact(a4, 'F1', 'W1')
            if prev is not None:
                self.assertLess(pe, prev)
            prev = pe


if __name__ == '__main__':
    unittest.main()
