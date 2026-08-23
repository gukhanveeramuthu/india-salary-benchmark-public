"""
Percentile engine edge cases: minimum, median, maximum, ties, small cohorts.
"""
import unittest
from percentile_engine import compute_bands, percentile_of_value


class TestPercentileBands(unittest.TestCase):

    def test_n1_all_bands_equal_the_single_value(self):
        bands = compute_bands([50000])
        self.assertEqual(bands.n, 1)
        for v in (bands.p10, bands.p25, bands.p50, bands.p75, bands.p90):
            self.assertEqual(v, 50000)

    def test_n2_bands_interpolate_between_the_two(self):
        bands = compute_bands([10000, 20000])
        self.assertEqual(bands.n, 2)
        self.assertEqual(bands.p50, 15000)  # exact midpoint
        self.assertTrue(10000 <= bands.p10 <= bands.p90 <= 20000)

    def test_small_cohort_ordering_is_monotonic(self):
        bands = compute_bands([5, 40, 12, 100, 8, 60, 33])
        self.assertTrue(bands.p10 <= bands.p25 <= bands.p50 <= bands.p75 <= bands.p90)

    def test_median_of_odd_cohort_is_middle_value(self):
        bands = compute_bands([10, 20, 30])
        self.assertEqual(bands.p50, 20)

    def test_median_of_even_cohort_interpolates(self):
        bands = compute_bands([10, 20, 30, 40])
        self.assertEqual(bands.p50, 25)

    def test_ties_do_not_break_monotonicity(self):
        bands = compute_bands([50000, 50000, 50000, 50000, 50000])
        for v in (bands.p10, bands.p25, bands.p50, bands.p75, bands.p90):
            self.assertEqual(v, 50000)


class TestPercentileOfValue(unittest.TestCase):

    def test_value_at_minimum(self):
        p = percentile_of_value([10, 20, 30, 40, 50], 10)
        self.assertLess(p, 25)  # lowest value should sit near the bottom

    def test_value_at_maximum(self):
        p = percentile_of_value([10, 20, 30, 40, 50], 50)
        self.assertGreater(p, 75)  # highest value should sit near the top

    def test_value_at_median(self):
        p = percentile_of_value([10, 20, 30, 40, 50], 30)
        self.assertEqual(p, 50.0)

    def test_tied_value_uses_midpoint_rule(self):
        # value equal to one of the cohort members: should not silently
        # count as "below everyone" or "above everyone"
        p = percentile_of_value([10, 20, 20, 20, 30], 20)
        # 1 below (10), 3 equal (20,20,20) -> rank = 1 + 1.5 = 2.5 / 5 = 50%
        self.assertEqual(p, 50.0)

    def test_value_far_above_all_of_cohort(self):
        p = percentile_of_value([10, 20, 30], 1_000_000)
        self.assertEqual(p, 100.0)

    def test_value_far_below_all_of_cohort(self):
        p = percentile_of_value([10, 20, 30], -1_000_000)
        self.assertEqual(p, 0.0)

    def test_single_member_cohort(self):
        # value equal to the only member -> midpoint rule -> 50th
        self.assertEqual(percentile_of_value([50000], 50000), 50.0)

    def test_empty_cohort_raises_rather_than_fabricating(self):
        with self.assertRaises(ValueError):
            percentile_of_value([], 50000)

    def test_extreme_outlier_does_not_break_ordering(self):
        base = [10, 20, 30, 40, 50]
        with_outlier = base + [10_000_000]
        bands = compute_bands(with_outlier)
        # the outlier should pull P90 way up without corrupting the lower bands
        self.assertLess(bands.p50, 100)
        self.assertGreater(bands.p90, 1_000_000)
        self.assertTrue(bands.p10 <= bands.p25 <= bands.p50 <= bands.p75 <= bands.p90)


if __name__ == "__main__":
    unittest.main()
