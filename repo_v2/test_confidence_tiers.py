"""
Confidence tier boundary tests - exactly at the documented thresholds
(10, 20, 50) and one below/above each, since off-by-one errors here
directly change what a user is told about how trustworthy a result is.
"""
import unittest
from confidence_tiers import confidence_for, HIGH, MODERATE, LOW, INSUFFICIENT


class TestConfidenceThresholds(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(confidence_for(0), INSUFFICIENT)

    def test_one(self):
        self.assertEqual(confidence_for(1), INSUFFICIENT)

    def test_two(self):
        self.assertEqual(confidence_for(2), INSUFFICIENT)

    def test_nine_is_still_insufficient(self):
        self.assertEqual(confidence_for(9), INSUFFICIENT)

    def test_exactly_ten_is_low(self):
        self.assertEqual(confidence_for(10), LOW)

    def test_nineteen_is_still_low(self):
        self.assertEqual(confidence_for(19), LOW)

    def test_exactly_twenty_is_moderate(self):
        self.assertEqual(confidence_for(20), MODERATE)

    def test_forty_nine_is_still_moderate(self):
        self.assertEqual(confidence_for(49), MODERATE)

    def test_exactly_fifty_is_high(self):
        self.assertEqual(confidence_for(50), HIGH)

    def test_large_n_is_high(self):
        self.assertEqual(confidence_for(10_000), HIGH)


if __name__ == "__main__":
    unittest.main()
