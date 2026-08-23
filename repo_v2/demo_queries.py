"""
Runs real queries end-to-end against the real, combined India dataset
(data/india_salaries_deduped.csv - Glassdoor India salary reports +
LeetCode Compensations forum posts, see data/README.md for provenance).

This is not a formatting exercise - every number below comes from an
actual run of load_observations() -> run_benchmark() against real rows.
"""

from schema import load_observations
from benchmark import run_benchmark

DATA_PATH = "data/india_salaries_deduped.csv"

QUERIES = [
    # (job_title, experience_level, salary_currency, user_salary_in_usd, city)
    ("Android Developer", "EN", "INR", 9_000, None),
    ("Data Scientist", "EN", "INR", 22_000, None),
    ("Data Scientist", "EN", "INR", 22_000, "Bengaluru"),   # city-specific match -> level 1
    ("Data Scientist", "EN", "INR", 22_000, "Kochi"),       # no data in this city -> falls back, shifted level
    ("Data Scientist", "MI", "INR", 25_000, None),
    ("Software Engineer", "EN", "INR", 8_000, None),
    ("Lead Data Scientist", "MI", "INR", 30_000, None),
    ("Product Manager", "MI", "INR", 25_000, None),
    ("Astronaut", "SE", "INR", 50_000, None),
]


def format_money(x: float) -> str:
    return f"${x:,.0f}"


def main() -> None:
    observations, report = load_observations(DATA_PATH)
    print(f"Load report: {report.summary()}\n")

    for job_title, experience_level, currency, user_salary, city in QUERIES:
        result = run_benchmark(
            observations, job_title, experience_level, currency,
            user_salary_in_usd=user_salary, city=city,
        )
        city_label = f" | {city}" if city else ""
        print(f"Query: {job_title} | {experience_level} | {currency}{city_label} "
              f"| user salary {format_money(user_salary)}")
        print(f"Cohort (fallback level {result.cohort.level}): {result.cohort.description}")
        n = result.provenance["n"]
        print(f"Sample size: n={n}  ->  Confidence: {result.confidence}")

        if result.bands is not None:
            b = result.bands
            print(f"  P10={format_money(b.p10)}  P25={format_money(b.p25)}  "
                  f"P50={format_money(b.p50)}  P75={format_money(b.p75)}  "
                  f"P90={format_money(b.p90)}")
            print(f"  User's estimated percentile: {result.user_percentile:.1f}th")
        else:
            print("  Not enough comparable data to show percentile bands.")

        for w in result.warnings:
            print(f"  Warning: {w}")

        print(f"  Provenance: {result.provenance}")
        print("-" * 100)


if __name__ == "__main__":
    main()
