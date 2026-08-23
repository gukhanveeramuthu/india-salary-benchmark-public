"""
Pulls the India-resident rows out of foorilla/ai-jobs-net-salaries (CC0,
updated weekly: https://github.com/foorilla/ai-jobs-net-salaries) and
appends them to data/india_salaries_deduped.csv, in this project's exact
schema.

This is additive and idempotent-ish by design:
- Only rows with employee_residence == "IN" are kept.
- city is left blank (this source doesn't capture it) - honestly excluded
  from the city-specific cohort rung rather than guessed, same rule as
  every other source in this dataset.
- source_dataset is stamped as "ai_jobs_net_survey" so provenance always
  shows exactly which rows came from where.
- Nothing is deduplicated here - the engine's own load_observations()
  dedup (identity = every field except source_dataset) handles that at
  load time, same as it does for the other two sources.

Re-run this after re-cloning a fresher salaries.csv to refresh this source;
don't hand-edit rows into the CSV.

Usage:
    git clone --depth 1 https://github.com/foorilla/ai-jobs-net-salaries.git /tmp/ai-jobs-net-salaries
    python3 data/fetch_ai_jobs_net_survey.py /tmp/ai-jobs-net-salaries/salaries.csv
"""

import csv
import sys
from pathlib import Path

TARGET = Path(__file__).parent / "india_salaries_deduped.csv"

OUR_FIELDS = [
    "work_year", "experience_level", "employment_type", "job_title",
    "salary", "salary_currency", "salary_in_usd", "employee_residence",
    "remote_ratio", "company_location", "company_size", "city",
    "source_dataset",
]


def transform(src_csv_path: str) -> list[dict]:
    rows = []
    with open(src_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["employee_residence"] != "IN":
                continue
            rows.append({
                "work_year": row["work_year"],
                "experience_level": row["experience_level"],
                "employment_type": row["employment_type"],
                "job_title": row["job_title"],
                "salary": row["salary"],
                "salary_currency": row["salary_currency"],
                "salary_in_usd": row["salary_in_usd"],
                "employee_residence": row["employee_residence"],
                "remote_ratio": row["remote_ratio"],
                "company_location": row["company_location"],
                "company_size": row["company_size"],
                "city": "",
                "source_dataset": "ai_jobs_net_survey",
            })
    return rows


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    src_path = sys.argv[1]

    new_rows = transform(src_path)
    print(f"India-resident rows found in source: {len(new_rows)}")

    with open(TARGET, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == OUR_FIELDS, reader.fieldnames
        existing_rows = list(reader)

    # Avoid re-appending this source twice if the script is re-run.
    existing_rows = [r for r in existing_rows if r["source_dataset"] != "ai_jobs_net_survey"]

    with open(TARGET, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUR_FIELDS)
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerows(new_rows)

    print(f"Wrote {len(existing_rows) + len(new_rows)} total rows to {TARGET}")


if __name__ == "__main__":
    main()
