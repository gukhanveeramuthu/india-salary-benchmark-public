"""
Tests for the city-aware cohort rung added on top of the original
5-level ladder. Kept in a separate file from the original test suite
deliberately - those 54 tests stay untouched as the contract that was
already agreed and passing.
"""
import unittest
from schema import SalaryObservation, currency_segment
from cohort_engine import find_cohort


def make_obs(job_title, experience_level, currency, salary_usd=50000,
             residence="IN", source="synthetic", year=2025, city=None) -> SalaryObservation:
    return SalaryObservation(
        source_dataset=source,
        work_year=year,
        experience_level=experience_level,
        employment_type="FT",
        job_title_raw=job_title,
        salary_amount=salary_usd,
        salary_currency=currency,
        salary_in_usd=salary_usd,
        employee_residence=residence,
        remote_ratio=0,
        company_location=residence,
        company_size="M",
        pay_population=currency_segment(currency),
        city=city,
    )


class TestCityRungBackwardCompatibility(unittest.TestCase):

    def test_omitting_city_reproduces_original_level1_exactly(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Bengaluru") for _ in range(5)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 5)

    def test_city_none_explicitly_behaves_like_omitted(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Pune") for _ in range(3)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city=None)
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 3)

    def test_blank_city_string_behaves_like_omitted(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Pune") for _ in range(3)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="   ")
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 3)


class TestCityRung(unittest.TestCase):

    def test_city_match_is_level1_and_excludes_other_cities(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Bengaluru") for _ in range(4)]
        obs += [make_obs("Data Scientist", "MI", "INR", city="Pune") for _ in range(6)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 4)
        self.assertTrue(all(o.city == "Bengaluru" for o in result.observations))

    def test_city_match_is_case_and_whitespace_insensitive(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Bengaluru") for _ in range(3)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="  bengaluru ")
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 3)

    def test_no_city_specific_data_falls_back_to_full_country_shifted_one_level(self):
        # 5 rows in Pune, none in the requested city (Chennai) - should
        # fall back to the old level-1 equivalent (title+exp+currency,
        # any city), now numbered level 2.
        obs = [make_obs("Data Scientist", "MI", "INR", city="Pune") for _ in range(5)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Chennai")
        self.assertEqual(result.level, 2)
        self.assertEqual(len(result.observations), 5)
        self.assertIn("Chennai", result.description)  # explains why it fell back

    def test_unknown_city_never_crashes_and_still_finds_country_wide_cohort(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Bengaluru") for _ in range(12)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Atlantis")
        self.assertEqual(result.level, 2)
        self.assertEqual(len(result.observations), 12)

    def test_city_requested_but_rows_have_no_city_at_all_falls_back_cleanly(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city=None) for _ in range(7)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 2)
        self.assertEqual(len(result.observations), 7)

    def test_city_requested_and_currency_also_needs_relaxing_shifts_to_level3(self):
        # No INR rows in any city; only USD rows exist, none in Bengaluru.
        obs = [make_obs("Data Scientist", "MI", "USD", city="Pune") for _ in range(4)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 3)  # old level 2 (currency relaxed), shifted by 1
        self.assertEqual(len(result.observations), 4)

    def test_city_requested_and_family_fallback_shifts_to_level4(self):
        obs = [make_obs("Lead Data Scientist", "MI", "INR", city="Pune") for _ in range(6)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 4)  # old level 3 (role family), shifted by 1
        self.assertEqual(len(result.observations), 6)

    def test_city_requested_and_experience_drop_shifts_to_level5(self):
        obs = [make_obs("Data Scientist", "SE", "INR", city="Pune") for _ in range(3)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 5)  # old level 4 (experience dropped), shifted by 1
        self.assertEqual(len(result.observations), 3)

    def test_city_requested_and_nothing_matches_anywhere_shifts_to_level6(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Pune")]
        result = find_cohort(obs, "Astronaut", "SE", "INR_domestic", city="Bengaluru")
        self.assertEqual(result.level, 6)  # old level 5 (empty), shifted by 1
        self.assertEqual(len(result.observations), 0)

    def test_city_filter_still_respects_country_filter(self):
        obs = [make_obs("Data Scientist", "MI", "INR", city="Bengaluru", residence="US") for _ in range(5)]
        result = find_cohort(
            obs, "Data Scientist", "MI", "INR_domestic",
            country_residence="IN", city="Bengaluru",
        )
        # country filter excludes everything before city is even considered
        self.assertEqual(result.level, 6)
        self.assertEqual(len(result.observations), 0)


if __name__ == "__main__":
    unittest.main()
