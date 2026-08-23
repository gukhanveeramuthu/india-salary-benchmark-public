"""
Schema loading edge cases: missing salary values, duplicate rows,
and invalid fields must never crash the loader or silently vanish -
every skip has to be counted in the LoadReport.
"""
import unittest
import tempfile
import csv
import os
from schema import load_observations

FIELDS = [
    "work_year", "experience_level", "employment_type", "job_title",
    "salary", "salary_currency", "salary_in_usd", "employee_residence",
    "remote_ratio", "company_location", "company_size", "source_dataset",
]


def write_csv(rows: list[dict]) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def base_row(**overrides) -> dict:
    row = {
        "work_year": "2025", "experience_level": "MI", "employment_type": "FT",
        "job_title": "Data Scientist", "salary": "3500000", "salary_currency": "INR",
        "salary_in_usd": "41000", "employee_residence": "IN", "remote_ratio": "0",
        "company_location": "IN", "company_size": "M", "source_dataset": "test",
    }
    row.update(overrides)
    return row


class TestSchemaLoading(unittest.TestCase):

    def test_normal_rows_load_cleanly(self):
        path = write_csv([base_row(), base_row()])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 2)
        self.assertEqual(report.rows_loaded, 2)
        self.assertEqual(report.rows_skipped_missing_salary, 0)

    def test_missing_salary_is_skipped_and_counted(self):
        path = write_csv([base_row(), base_row(salary="", salary_in_usd="")])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 1)
        self.assertEqual(report.rows_skipped_missing_salary, 1)
        self.assertEqual(report.rows_read, 2)

    def test_na_string_salary_is_skipped(self):
        path = write_csv([base_row(salary="N/A", salary_in_usd="N/A")])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 0)
        self.assertEqual(report.rows_skipped_missing_salary, 1)

    def test_non_numeric_salary_is_skipped_not_crashed(self):
        path = write_csv([base_row(salary="lots of money", salary_in_usd="lots")])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 0)
        self.assertEqual(report.rows_skipped_missing_salary, 1)

    def test_zero_or_negative_salary_is_skipped(self):
        path = write_csv([base_row(salary_in_usd="0"), base_row(salary_in_usd="-500")])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 0)
        self.assertEqual(report.rows_skipped_missing_salary, 2)

    def test_exact_duplicate_rows_removed_when_dedup_true(self):
        row = base_row()
        path = write_csv([row, dict(row)])  # identical row twice
        obs, report = load_observations(path, dedup=True)
        self.assertEqual(len(obs), 1)
        self.assertEqual(report.duplicate_rows_removed, 1)

    def test_duplicates_preserved_when_dedup_false(self):
        row = base_row()
        path = write_csv([row, dict(row)])
        obs, report = load_observations(path, dedup=False)
        self.assertEqual(len(obs), 2)
        self.assertEqual(report.duplicate_rows_removed, 0)

    def test_same_values_different_source_dataset_are_treated_as_duplicate(self):
        # Per the Phase-1 audit decision: identity excludes source_dataset,
        # so identical values reported in two different source surveys
        # collapse to one record. This is the deliberately conservative
        # choice - it may remove some real distinct respondents, but it
        # prevents coincidental/artifactual duplicates from inflating
        # cohort confidence (see data_quality_audit.md).
        row_a = base_row(source_dataset="source_a")
        row_b = base_row(source_dataset="source_b")
        path = write_csv([row_a, row_b])
        obs, report = load_observations(path, dedup=True)
        self.assertEqual(len(obs), 1)
        self.assertEqual(report.duplicate_rows_removed, 1)

    def test_empty_file_returns_empty_list_not_a_crash(self):
        path = write_csv([])
        obs, report = load_observations(path)
        self.assertEqual(len(obs), 0)
        self.assertEqual(report.rows_read, 0)

    def test_report_summary_does_not_crash(self):
        path = write_csv([base_row()])
        obs, report = load_observations(path)
        self.assertIsInstance(report.summary(), str)


if __name__ == "__main__":
    unittest.main()
