"""
Explicit, reviewable role-family groupings.

Deliberately NOT fuzzy matching (no string similarity, no embeddings).
Every title below was put in its family by a human decision, so the
mapping can be audited and disagreed with directly by reading it, and
title -> family lookups are stable and reproducible.

Titles are matched case-insensitively after trimming whitespace, but
otherwise must appear verbatim in this map. An unrecognized title
returns None rather than guessing - the cohort engine treats that as
"no family fallback available" (falls through to the next rung of the
ladder), which is the correct, honest behaviour.

This is demo/Phase-1 scope: families and their member titles were built
from titles actually observed in the underlying India datasets
(Glassdoor India salary reports + LeetCode Compensations forum posts),
plus the handful of ai-jobs.net-style titles used in the original
engine tests. Extend this map as new real titles are seen - never by
inferring a family from string similarity.
"""

from typing import Optional

ROLE_FAMILIES = {
    "Data Science": [
        "data scientist",
        "lead data scientist",
        "senior data scientist",
        "principal data scientist",
        "junior data scientist",
        "data science manager",
        "director of data science",
        "applied scientist",
        "research scientist",
    ],
    "Machine Learning": [
        "machine learning engineer",
        "ml engineer",
        "senior machine learning engineer",
        "ai engineer",
        "nlp engineer",
        "computer vision engineer",
    ],
    "Data Analytics": [
        "data analyst",
        "senior data analyst",
        "business intelligence analyst",
        "bi analyst",
        "analytics specialist",
        "reporting analyst",
    ],
    "Data Engineering": [
        "data engineer",
        "senior data engineer",
        "big data engineer",
        "etl developer",
        "data platform engineer",
    ],
    "Software Engineering": [
        "software engineer",
        "software developer",
        "senior software engineer",
        "senior software developer",
        "lead software engineer",
        "principal software engineer",
        "software development engineer",
        "sde",
        "sde 1",
        "sde 2",
        "sde-1",
        "sde-2",
        "full stack developer",
        "backend developer",
        "backend engineer",
        "frontend developer",
        "frontend engineer",
        "java developer",
        "python developer",
        ".net developer",
        "web developer",
    ],
    "Mobile Development": [
        "android developer",
        "ios developer",
        "mobile developer",
        "flutter developer",
        "react native developer",
    ],
    "DevOps / SRE": [
        "devops engineer",
        "site reliability engineer",
        "sre",
        "cloud engineer",
        "infrastructure engineer",
        "platform engineer",
    ],
    "Quality Assurance": [
        "qa engineer",
        "test engineer",
        "software test engineer",
        "automation test engineer",
        "sdet",
        "quality analyst",
    ],
    "Product Management": [
        "product manager",
        "senior product manager",
        "associate product manager",
        "group product manager",
        "director of product",
    ],
    "Project / Program Management": [
        "project manager",
        "program manager",
        "technical program manager",
        "delivery manager",
        "scrum master",
    ],
    "Business / Systems Analysis": [
        "business analyst",
        "systems analyst",
        "functional consultant",
    ],
    "UI/UX Design": [
        "ux designer",
        "ui designer",
        "product designer",
        "ui/ux designer",
    ],
    "Security": [
        "security analyst",
        "security engineer",
        "cybersecurity analyst",
        "information security analyst",
        "penetration tester",
    ],
    "IT Support / Systems Administration": [
        "system administrator",
        "network administrator",
        "it support engineer",
        "technical support engineer",
        "help desk analyst",
    ],
    "Engineering Leadership": [
        "engineering manager",
        "technical lead",
        "tech lead",
        "director of engineering",
        "vp of engineering",
        "cto",
    ],
}

# Reverse index: normalized title -> family name, built once at import time.
_TITLE_TO_FAMILY = {
    title: family
    for family, titles in ROLE_FAMILIES.items()
    for title in titles
}


def _normalize(job_title: str) -> str:
    return job_title.strip().lower()


def role_family(job_title: str) -> Optional[str]:
    """Return the family name for a job title, or None if the title
    isn't in the taxonomy. Never raises, never guesses."""
    return _TITLE_TO_FAMILY.get(_normalize(job_title))


def same_family(title_a: str, title_b: str) -> bool:
    """True if both titles resolve to the same known family. Two
    unrecognized titles are NOT considered the same family (both
    resolving to None would otherwise incorrectly match)."""
    fam_a = role_family(title_a)
    fam_b = role_family(title_b)
    return fam_a is not None and fam_a == fam_b
