"""
Fallback ladder for finding a defensible peer group.

Each level relaxes exactly one constraint from the level before it, and
names what it relaxed - so a result can always say *why* the cohort is
what it is, not just what it is.

Base ladder (used whenever no city is requested, or city can't help):

  Level 1: exact title, exact experience level, exact pay population
  Level 2: exact title, exact experience level, ANY pay population
           (currency requirement relaxed; flags mixed_currency_warning
           if more than one pay population is actually present)
  Level 3: same role family (via taxonomy.py), exact experience level,
           ANY pay population (title requirement relaxed to family)
  Level 4: exact title, ANY experience level, ANY pay population
           (experience requirement dropped entirely)
  Level 5: nothing matched - empty cohort, never a crash

City-aware ladder (used only when the caller passes `city=`):

  Level 1: exact title, exact experience, exact pay population,
           SAME CITY - the tightest, most locally-relevant cohort
           possible. City is checked first, ahead of every other
           relaxation, because "people like me, near me" is usually
           the most useful comparison when the data supports it.
  Levels 2-6: the base ladder above (levels 1-5), run unfiltered by
           city, each shifted up by one. Reached only when no
           city-specific match exists.

Passing no `city` argument reproduces the original 5-level ladder
exactly (same level numbers, same behaviour) - this is what makes it
safe for every existing caller and test.

A country_residence filter, if given, applies at every level, city or not.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from schema import SalaryObservation
from taxonomy import role_family


@dataclass
class CohortResult:
    level: int
    observations: List[SalaryObservation] = field(default_factory=list)
    mixed_currency_warning: bool = False
    description: str = ""


def _country_ok(obs: SalaryObservation, country_residence: Optional[str]) -> bool:
    if country_residence is None:
        return True
    return obs.employee_residence == country_residence


def _mixed_currency(observations: List[SalaryObservation]) -> bool:
    return len({o.pay_population for o in observations}) > 1


def _base_ladder(
    country_filtered: List[SalaryObservation],
    job_title: str,
    experience_level: str,
    pay_population: str,
    country_residence: Optional[str],
    level_offset: int,
    city_fallback_note: str = "",
) -> CohortResult:
    """The original 5-level ladder, unaware of city, with level numbers
    shifted by `level_offset` (0 when called directly with no city
    requested; 1 when a city was requested but its dedicated top rung
    came up empty, so we're falling back to the full country)."""
    title_norm = job_title.strip().lower()

    # Level (1 + offset): exact title, exact experience, exact pay population.
    level1 = [
        o for o in country_filtered
        if o.job_title_raw.strip().lower() == title_norm
        and o.experience_level == experience_level
        and o.pay_population == pay_population
    ]
    if level1:
        return CohortResult(
            level=1 + level_offset,
            observations=level1,
            mixed_currency_warning=False,
            description=f'"{job_title}" \u00b7 {experience_level} \u00b7 {pay_population}'
                        + (f" \u00b7 {country_residence}" if country_residence else "")
                        + city_fallback_note,
        )

    # Level (2 + offset): exact title, exact experience, any pay population.
    level2 = [
        o for o in country_filtered
        if o.job_title_raw.strip().lower() == title_norm
        and o.experience_level == experience_level
    ]
    if level2:
        return CohortResult(
            level=2 + level_offset,
            observations=level2,
            mixed_currency_warning=_mixed_currency(level2),
            description=f'"{job_title}" \u00b7 {experience_level} \u00b7 currency requirement relaxed'
                        + (f" \u00b7 {country_residence}" if country_residence else "")
                        + city_fallback_note,
        )

    # Level (3 + offset): same role family, exact experience, any pay population.
    family = role_family(job_title)
    level3: List[SalaryObservation] = []
    if family is not None:
        level3 = [
            o for o in country_filtered
            if role_family(o.job_title_raw) == family
            and o.experience_level == experience_level
        ]
    if level3:
        return CohortResult(
            level=3 + level_offset,
            observations=level3,
            mixed_currency_warning=_mixed_currency(level3),
            description=f'"{job_title}" not found directly \u2014 broadened to the '
                        f'"{family}" role family \u00b7 {experience_level}'
                        + (f" \u00b7 {country_residence}" if country_residence else "")
                        + city_fallback_note,
        )

    # Level (4 + offset): exact title, any experience level, any pay population.
    level4 = [
        o for o in country_filtered
        if o.job_title_raw.strip().lower() == title_norm
    ]
    if level4:
        return CohortResult(
            level=4 + level_offset,
            observations=level4,
            mixed_currency_warning=_mixed_currency(level4),
            description=f'"{job_title}" \u00b7 experience-level requirement dropped '
                        f'(insufficient data at {experience_level})'
                        + (f" \u00b7 {country_residence}" if country_residence else "")
                        + city_fallback_note,
        )

    # Level (5 + offset): nothing matched at all.
    return CohortResult(
        level=5 + level_offset,
        observations=[],
        mixed_currency_warning=False,
        description=f'No comparable observations found for "{job_title}"'
                    + (f" in {country_residence}" if country_residence else "")
                    + " for this pay population.",
    )


def find_cohort(
    observations: List[SalaryObservation],
    job_title: str,
    experience_level: str,
    pay_population: str,
    country_residence: Optional[str] = None,
    city: Optional[str] = None,
) -> CohortResult:
    """Walk the fallback ladder and return the first level with a
    non-empty cohort (or the final level, empty, if nothing matches at
    all). Never raises - an unknown role, an unknown experience code,
    an unrecognized city, or an empty dataset are all valid inputs that
    resolve to an empty cohort rather than crashing.

    `city` is optional. Omit it (or pass None) to get the original
    5-level ladder, unchanged. Pass it to additionally try a
    city-specific cohort first, ahead of every other relaxation.
    """
    country_filtered = [o for o in observations if _country_ok(o, country_residence)]

    if city is not None and city.strip():
        city_norm = city.strip().lower()
        city_filtered = [
            o for o in country_filtered
            if o.city is not None and o.city.strip().lower() == city_norm
        ]
        title_norm = job_title.strip().lower()
        city_level1 = [
            o for o in city_filtered
            if o.job_title_raw.strip().lower() == title_norm
            and o.experience_level == experience_level
            and o.pay_population == pay_population
        ]
        if city_level1:
            return CohortResult(
                level=1,
                observations=city_level1,
                mixed_currency_warning=False,
                description=f'"{job_title}" \u00b7 {experience_level} \u00b7 {pay_population} '
                            f'\u00b7 {city.strip()}',
            )
        # No city-specific match - fall back to the full country-wide
        # ladder, shifted up by one level, with a note that city-level
        # data wasn't available for this query.
        return _base_ladder(
            country_filtered, job_title, experience_level, pay_population,
            country_residence, level_offset=1,
            city_fallback_note=f" (no {city.strip()}-specific data \u2014 showing all of "
                                f"{country_residence or 'the dataset'})",
        )

    # No city requested: the original, unmodified 5-level ladder.
    return _base_ladder(
        country_filtered, job_title, experience_level, pay_population,
        country_residence, level_offset=0,
    )
