"""
Orchestrator: query -> cohort -> confidence -> percentile -> provenance.

This is the one function the rest of the product (API, UI, CLI) should
call. It never fabricates a result: if the cohort is too small to say
anything trustworthy, bands and user_percentile come back as None
rather than a number dressed up to look precise.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from schema import SalaryObservation, currency_segment
from cohort_engine import find_cohort, CohortResult
from confidence import confidence_for, INSUFFICIENT
from percentile_engine import compute_bands, percentile_of_value, PercentileBands

# This benchmark is India-scoped by design - every query is implicitly
# "compared to other India-based professionals", so the country filter
# is applied here rather than left to the caller to remember.
COUNTRY_RESIDENCE = "IN"

MIXED_CURRENCY_WARNING = (
    "This cohort mixes INR-paid and USD-paid observations (roughly a 1.8x "
    "median gap in past audits) - treat the comparison with caution."
)


@dataclass
class BenchmarkResult:
    cohort: CohortResult
    confidence: str
    bands: Optional[PercentileBands]
    user_percentile: Optional[float]
    provenance: Dict
    warnings: List[str]


def _provenance(cohort_observations: List[SalaryObservation]) -> Dict:
    n = len(cohort_observations)
    sources: Dict[str, int] = {}
    for o in cohort_observations:
        sources[o.source_dataset] = sources.get(o.source_dataset, 0) + 1

    if n == 0:
        year_range = "n/a"
    else:
        years = [o.work_year for o in cohort_observations]
        year_range = f"{min(years)}-{max(years)}"

    return {"n": n, "sources": sources, "year_range": year_range}


def run_benchmark(
    observations: List[SalaryObservation],
    job_title: str,
    experience_level: str,
    salary_currency: str,
    user_salary_in_usd: float,
    city: Optional[str] = None,
) -> BenchmarkResult:
    """`city` is optional - omit it for the original country-wide ladder.
    Pass it to additionally try a city-specific cohort first (see
    cohort_engine.find_cohort for exactly how the fallback works)."""
    pay_population = currency_segment(salary_currency)

    cohort = find_cohort(
        observations,
        job_title=job_title,
        experience_level=experience_level,
        pay_population=pay_population,
        country_residence=COUNTRY_RESIDENCE,
        city=city,
    )

    n = len(cohort.observations)
    confidence = confidence_for(n)

    bands: Optional[PercentileBands] = None
    user_percentile: Optional[float] = None
    if confidence != INSUFFICIENT:
        cohort_salaries = [o.salary_in_usd for o in cohort.observations]
        bands = compute_bands(cohort_salaries)
        user_percentile = percentile_of_value(cohort_salaries, user_salary_in_usd)

    warnings: List[str] = []
    if cohort.mixed_currency_warning:
        warnings.append(MIXED_CURRENCY_WARNING)

    return BenchmarkResult(
        cohort=cohort,
        confidence=confidence,
        bands=bands,
        user_percentile=user_percentile,
        provenance=_provenance(cohort.observations),
        warnings=warnings,
    )
