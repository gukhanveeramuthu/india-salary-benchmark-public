"""
Cohort engine tests, using synthetic data so cohort sizes can be set
exactly (n=0, n=1, n=2, exactly 10, exactly 20, mixed currency, unknown
role, unknown experience) rather than relying on whatever happens to
exist in the real dataset.
"""
import unittest
from schema import SalaryObservation, currency_segment
from cohort_engine import find_cohort


def make_obs(job_title, experience_level, currency, salary_usd=50000,
             residence="IN", source="synthetic", year=2025) -> SalaryObservation:
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
    )


class TestCohortFallbackLadder(unittest.TestCase):

    def test_level1_exact_match_when_available(self):
        obs = [make_obs("Data Scientist", "MI", "INR") for _ in range(5)]
        obs += [make_obs("Data Scientist", "MI", "USD") for _ in range(5)]  # different pop, should be ignored
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 1)
        self.assertEqual(len(result.observations), 5)

    def test_level2_relaxes_currency_when_exact_currency_has_nothing(self):
        obs = [make_obs("Data Scientist", "MI", "USD") for _ in range(4)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 2)
        self.assertEqual(len(result.observations), 4)
        self.assertTrue(result.mixed_currency_warning is False)  # only one pop present, so not "mixed"

    def test_level2_flags_mixed_currency_when_both_present(self):
        obs = [make_obs("Data Scientist", "MI", "USD") for _ in range(3)]
        obs += [make_obs("Data Scientist", "MI", "EUR") for _ in range(2)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 2)
        self.assertEqual(len(result.observations), 5)
        self.assertTrue(result.mixed_currency_warning)

    def test_level3_broadens_to_role_family(self):
        # "Data Scientist" has no data at MI, but "Lead Data Scientist"
        # (same family, per taxonomy.py) does.
        obs = [make_obs("Lead Data Scientist", "MI", "INR") for _ in range(6)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 3)
        self.assertEqual(len(result.observations), 6)
        self.assertIn("Data Science", result.description)  # family name surfaced

    def test_level4_drops_experience_requirement(self):
        obs = [make_obs("Data Scientist", "SE", "INR") for _ in range(3)]
        obs += [make_obs("Data Scientist", "EX", "INR") for _ in range(2)]
        # querying for MI, which doesn't exist, and no family fallback applies
        # (Data Scientist has no MI-level family members here either)
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 4)
        self.assertEqual(len(result.observations), 5)

    def test_level5_when_nothing_at_all_matches(self):
        obs = [make_obs("Data Scientist", "MI", "INR")]
        result = find_cohort(obs, "Astronaut", "SE", "INR_domestic")
        self.assertEqual(result.level, 5)
        self.assertEqual(len(result.observations), 0)

    def test_unknown_role_never_crashes(self):
        obs = [make_obs("Data Scientist", "MI", "INR")]
        result = find_cohort(obs, "Underwater Basket Weaver", "MI", "INR_domestic")
        self.assertEqual(result.level, 5)

    def test_unknown_experience_level_falls_through_to_level4_if_title_exists(self):
        obs = [make_obs("Data Scientist", "SE", "INR") for _ in range(3)]
        # "XX" isn't a real experience code, but level 4 ignores experience entirely
        result = find_cohort(obs, "Data Scientist", "XX", "INR_domestic")
        self.assertEqual(result.level, 4)
        self.assertEqual(len(result.observations), 3)

    def test_empty_dataset_returns_level5_not_a_crash(self):
        result = find_cohort([], "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(result.level, 5)
        self.assertEqual(len(result.observations), 0)

    def test_country_filter_excludes_other_countries(self):
        obs = [make_obs("Data Scientist", "MI", "INR", residence="US") for _ in range(20)]
        result = find_cohort(obs, "Data Scientist", "MI", "INR_domestic", country_residence="IN")
        self.assertEqual(result.level, 5)  # none of the US rows should count

    def test_exactly_ten_and_exactly_twenty_row_cohorts_pass_through_intact(self):
        obs10 = [make_obs("Data Scientist", "MI", "INR") for _ in range(10)]
        result10 = find_cohort(obs10, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(len(result10.observations), 10)

        obs20 = [make_obs("Data Scientist", "MI", "INR") for _ in range(20)]
        result20 = find_cohort(obs20, "Data Scientist", "MI", "INR_domestic")
        self.assertEqual(len(result20.observations), 20)


class TestExperienceLevelNoneMeansAnyBand(unittest.TestCase):
    """experience_level=None pools every self-reported band together,
    following the same Optional-filter pattern as city/country_residence.
    Existing callers passing a real EN/MI/SE/EX code are unaffected -
    every test above this class still passes unmodified."""

    def test_none_pools_all_bands_at_level1(self):
        obs = (
            [make_obs("Analyst", "EN", "INR") for _ in range(10)]
            + [make_obs("Analyst", "MI", "INR") for _ in range(4)]
            + [make_obs("Analyst", "SE", "INR") for _ in range(2)]
        )
        result = find_cohort(obs, "Analyst", None, "INR_domestic")
        self.assertEqual(result.level, 1)  # exact title, exact currency, any band
        self.assertEqual(len(result.observations), 16)

    def test_none_still_broadens_by_family_when_title_itself_is_thin(self):
        # "BI Analyst" and "Data Analyst" share a role family in
        # taxonomy.py. Querying for "Data Analyst" should find nothing
        # at level 1/2 (exact title), then broaden to the family at
        # level 3, pooling every band since experience_level=None.
        obs = (
            [make_obs("BI Analyst", "EN", "INR") for _ in range(3)]
            + [make_obs("BI Analyst", "SE", "INR") for _ in range(3)]
        )
        result = find_cohort(obs, "Data Analyst", None, "INR_domestic")
        self.assertEqual(result.level, 3)
        self.assertEqual(len(result.observations), 6)

    def test_real_experience_code_still_matches_exactly_with_none_present(self):
        # A real code alongside None-eligible data should still only match
        # its own band - None is opt-in, not a silent default.
        obs = (
            [make_obs("Analyst", "EN", "INR") for _ in range(10)]
            + [make_obs("Analyst", "MI", "INR") for _ in range(4)]
        )
        result = find_cohort(obs, "Analyst", "MI", "INR_domestic")
        self.assertEqual(len(result.observations), 4)


if __name__ == "__main__":
    unittest.main()
