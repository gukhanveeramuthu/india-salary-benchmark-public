"""
Canonical schema for salary observations used by the benchmark engine.

Every raw source record is loaded into this shape before anything else
touches it. This is the contract the rest of the engine relies on.
"""

from dataclasses import dataclass
from typing import Optional
import csv

# Experience level codes as they appear in source data, mapped to a
# human label. We deliberately DO NOT collapse these into "years of
# experience" — sources define these buckets differently, so we keep
# the original code and only use it for cohort matching, never for
# arithmetic like "years + 2".
EXPERIENCE_LABELS = {
    "EN": "Entry-level",
    "MI": "Mid-level",
    "SE": "Senior-level",
    "EX": "Executive-level",
}

# Currency segmentation. This is the single most important cleaning
# decision from the Phase-1 audit: INR-paid and USD-paid India-based
# workers are NOT the same compensation population (median gap ~1.8x
# in the audited data), so every cohort must be built within one
# segment, never blended silently.
def currency_segment(currency: str) -> str:
    if currency == "INR":
        return "INR_domestic"
    if currency == "USD":
        return "USD_global"
    return "other_foreign_currency"


@dataclass
class SalaryObservation:
    source_dataset: str
    work_year: int
    experience_level: str          # EN / MI / SE / EX (raw, preserved)
    employment_type: str
    job_title_raw: str
    salary_amount: float
    salary_currency: str
    salary_in_usd: float
    employee_residence: str        # ISO-2 country code
    remote_ratio: int
    company_location: str          # ISO-2 country code
    company_size: str              # S / M / L
    pay_population: str            # derived: INR_domestic / USD_global / other_foreign_currency
    city: Optional[str] = None     # optional - many source rows won't have this

    @property
    def experience_label(self) -> str:
        return EXPERIENCE_LABELS.get(self.experience_level, self.experience_level)


@dataclass
class LoadReport:
    """What happened while loading - so bad rows never disappear silently."""
    rows_read: int = 0
    rows_loaded: int = 0
    rows_skipped_missing_salary: int = 0
    rows_skipped_invalid_field: int = 0
    duplicate_rows_removed: int = 0

    def summary(self) -> str:
        return (
            f"read={self.rows_read} loaded={self.rows_loaded} "
            f"skipped_missing_salary={self.rows_skipped_missing_salary} "
            f"skipped_invalid_field={self.rows_skipped_invalid_field} "
            f"duplicates_removed={self.duplicate_rows_removed}"
        )


def _row_identity(row: dict) -> tuple:
    """Identity used for dedup: every field except source_dataset, matching
    the rule used in the Phase-1 audit (a record could legitimately appear
    once per survey, but not twice within the same survey)."""
    return tuple(row[k] for k in row if k != "source_dataset")


def load_observations(csv_path: str, dedup: bool = True) -> tuple[list[SalaryObservation], LoadReport]:
    """Load a salary CSV into canonical SalaryObservation records.

    Bad rows are skipped, not silently dropped: every skip is counted in
    the returned LoadReport so data loss is always visible to the caller.
    Missing/blank/non-numeric salary fields are the one thing this engine
    refuses to guess at - a record with no usable salary can't contribute
    to a percentile, so it's excluded rather than defaulted to 0 or None.
    """
    report = LoadReport()
    observations: list[SalaryObservation] = []
    seen_identities: set = set()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            report.rows_read += 1

            if dedup:
                identity = _row_identity(row)
                if identity in seen_identities:
                    report.duplicate_rows_removed += 1
                    continue
                seen_identities.add(identity)

            # Missing/blank/unparseable salary -> skip, count it, move on.
            raw_salary = row.get("salary", "")
            raw_salary_usd = row.get("salary_in_usd", "")
            if raw_salary in (None, "", "NA", "N/A") or raw_salary_usd in (None, "", "NA", "N/A"):
                report.rows_skipped_missing_salary += 1
                continue
            try:
                salary_amount = float(raw_salary)
                salary_in_usd = float(raw_salary_usd)
            except (ValueError, TypeError):
                report.rows_skipped_missing_salary += 1
                continue
            if salary_in_usd <= 0:
                report.rows_skipped_missing_salary += 1
                continue

            # city is optional - older/other source files may not have this
            # column at all, and that's fine; it simply stays unset (None)
            # rather than being required or guessed.
            raw_city = row.get("city")
            city = raw_city.strip() if raw_city and raw_city.strip() else None

            try:
                observations.append(
                    SalaryObservation(
                        source_dataset=row["source_dataset"],
                        work_year=int(row["work_year"]),
                        experience_level=row["experience_level"],
                        employment_type=row["employment_type"],
                        job_title_raw=row["job_title"],
                        salary_amount=salary_amount,
                        salary_currency=row["salary_currency"],
                        salary_in_usd=salary_in_usd,
                        employee_residence=row["employee_residence"],
                        remote_ratio=int(row["remote_ratio"]),
                        company_location=row["company_location"],
                        company_size=row["company_size"],
                        pay_population=currency_segment(row["salary_currency"]),
                        city=city,
                    )
                )
                report.rows_loaded += 1
            except (ValueError, TypeError, KeyError):
                report.rows_skipped_invalid_field += 1
                continue

    return observations, report
