"""
Integration tests: full pipeline end-to-end, plus the provenance
reproducibility check - every result should be traceable back to
exactly which rows produced it.
"""
import unittest
from schema import SalaryObservation, currency_segment
from benchmark import run_benchmark
from confidence_tiers import INSUFFICIENT, LOW


def make_obs(job_title, experience_level, currency, salary_usd,
             residence="IN", source="synthetic", year=2025):
    return SalaryObservation(
        source_dataset=source, work_year=year, experience_level=experience_level,
        employment_type="FT", job_title_raw=job_title, salary_amount=salary_usd,
        salary_currency=currency, salary_in_usd=salary_usd, employee_residence=residence,
        remote_ratio=0, company_location=residence, company_size="M",
        pay_population=currency_segment(currency),
    )


class TestBenchmarkIntegration(unittest.TestCase):

    def test_happy_path_returns_bands_and_percentile(self):
        obs = [make_obs("Data Scientist", "MI", "INR", v) for v in
               [20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000, 65000]]
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=42000)
        self.assertEqual(result.confidence, LOW)  # n=10
        self.assertIsNotNone(result.bands)
        self.assertIsNotNone(result.user_percentile)
        self.assertTrue(0 <= result.user_percentile <= 100)

    def test_insufficient_cohort_returns_no_bands_no_fabricated_percentile(self):
        obs = [make_obs("Data Scientist", "MI", "INR", 40000)]  # n=1
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=40000)
        self.assertEqual(result.confidence, INSUFFICIENT)
        self.assertIsNone(result.bands)
        self.assertIsNone(result.user_percentile)

    def test_unknown_role_never_crashes_and_is_insufficient(self):
        obs = [make_obs("Data Scientist", "MI", "INR", 40000) for _ in range(20)]
        result = run_benchmark(obs, "Time Traveler", "MI", "INR", user_salary_in_usd=40000)
        self.assertEqual(result.confidence, INSUFFICIENT)
        self.assertEqual(result.cohort.level, 5)

    def test_provenance_lists_correct_source_counts(self):
        obs = [make_obs("Data Scientist", "MI", "INR", 40000, source="src_a") for _ in range(6)]
        obs += [make_obs("Data Scientist", "MI", "INR", 41000, source="src_b") for _ in range(4)]
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=40500)
        self.assertEqual(result.provenance["n"], 10)
        self.assertEqual(result.provenance["sources"], {"src_a": 6, "src_b": 4})

    def test_provenance_year_range_reflects_actual_data(self):
        obs = [make_obs("Data Scientist", "MI", "INR", 40000, year=2021)]
        obs += [make_obs("Data Scientist", "MI", "INR", 41000, year=2024)]
        obs += [make_obs("Data Scientist", "MI", "INR", 42000, year=2023)] * 8  # push to n=10, Low confidence
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=40500)
        self.assertEqual(result.provenance["year_range"], "2021-2024")

    def test_mixed_currency_fallback_produces_a_warning(self):
        obs = [make_obs("Data Scientist", "MI", "USD", 90000) for _ in range(6)]
        obs += [make_obs("Data Scientist", "MI", "EUR", 85000) for _ in range(6)]
        # user is INR-paid, but no INR cohort exists -> level 2 fallback, mixed currency present
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=40000)
        self.assertEqual(result.cohort.level, 2)
        self.assertTrue(any("mixes INR-paid and USD-paid" in w or "1.8x" in w for w in result.warnings))

    def test_result_is_reproducible_given_same_input(self):
        obs = [make_obs("Data Scientist", "MI", "INR", v) for v in range(10000, 20000, 1000)]
        r1 = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=15000)
        r2 = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=15000)
        self.assertEqual(r1.user_percentile, r2.user_percentile)
        self.assertEqual(r1.confidence, r2.confidence)
        self.assertEqual(r1.provenance, r2.provenance)

    def test_extreme_outlier_in_cohort_does_not_crash_benchmark(self):
        obs = [make_obs("Data Scientist", "MI", "INR", v) for v in range(20000, 20000 + 9000, 1000)]
        obs.append(make_obs("Data Scientist", "MI", "INR", 50_000_000))  # extreme outlier
        result = run_benchmark(obs, "Data Scientist", "MI", "INR", user_salary_in_usd=25000)
        self.assertIsNotNone(result.bands)
        self.assertGreater(result.bands.p90, 1_000_000)  # outlier visibly pulls P90 up
        self.assertLess(result.bands.p10, 30000)          # but doesn't distort the low end


if __name__ == "__main__":
    unittest.main()
