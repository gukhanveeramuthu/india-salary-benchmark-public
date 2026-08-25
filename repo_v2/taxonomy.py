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

This file has two layers of history:
1. The original Phase-1 taxonomy (Data Science, Project/Program
   Management, UI/UX Design, Security, DevOps/SRE, Engineering
   Leadership, Business/Systems Analysis, IT Support/Systems Admin,
   Product Management) - untouched since it was first written, and not
   part of the review below.
2. A full re-review of every title actually observed in the live
   dataset's dropdown (325 distinct titles), done together with the
   project owner: every title was inspected, explicitly grouped or
   explicitly left standalone, and verified against real salary data
   (e.g. intern vs. full-time pay ratios) before merging anything.
   This replaced the old, much coarser "Software Engineering" and
   "Mobile Development" and "Quality Assurance" families with more
   specific ones (Backend/Frontend/Java/Python SDE, Android Developer,
   iOS Software Developer, QA Tester, Database Administrator, etc.).
   A handful of titles from the old families that had no real observed
   data (.net developer, flutter developer, react native developer,
   quality analyst) were preserved in the closest new family so they
   don't silently lose their fallback behaviour.

Titles the project owner explicitly marked "Ignore" (front end cashier,
mobile technician, graduate engineer trainee) are deliberately absent
from every family - they're real titles in the data, kept standalone,
not merged anywhere, because they're either not software roles at all
or too ambiguous to guess at.
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
        "data science",
    ],
    "Product Management": [
        "product manager",
        "senior product manager",
        "associate product manager",
        "group product manager",
        "director of product",
        "product management",
    ],
    "Project / Program Management": [
        "project manager",
        "program manager",
        "technical program manager",
        "delivery manager",
        "scrum master",
        "project / program management",
    ],
    "Business / Systems Analysis": [
        "business analyst",
        "systems analyst",
        "functional consultant",
        "business / systems analysis",
    ],
    "UI/UX Design": [
        "ux designer",
        "ui designer",
        "product designer",
        "ui/ux designer",
        "ui/ux design",
    ],
    "Security": [
        "security analyst",
        "security engineer",
        "cybersecurity analyst",
        "information security analyst",
        "penetration tester",
        "security",
    ],
    "IT Support / Systems Administration": [
        "system administrator",
        "network administrator",
        "it support engineer",
        "technical support engineer",
        "help desk analyst",
        "it support / systems administration",
    ],
    "Engineering Leadership": [
        "engineering manager",
        "technical lead",
        "tech lead",
        "director of engineering",
        "vp of engineering",
        "cto",
        "engineering leadership",
    ],
    "DevOps / SRE": [
        "devops engineer",
        "site reliability engineer",
        "sre",
        "cloud engineer",
        "infrastructure engineer",
        "platform engineer",
        "devops / sre",
    ],
    "Data Engineer": [
        "data engineer",
        "senior data engineer",
        "big data engineer",
        "etl developer",
        "data platform engineer",
    ],
    "Data Analyst": [
        "data analyst",
        "senior data analyst",
        "business intelligence analyst",
        "bi analyst",
        "analytics specialist",
        "reporting analyst",
    ],
    "Machine Learning Engineer": [
        "machine learning engineer",
        "ml engineer",
        "mle",
        "senior machine learning engineer",
        "ai engineer",
        "nlp engineer",
        "computer vision engineer",
    ],
    "Software Development Engineer": [
        "amazon software development engineer",
        "associate software development engineer",
        "associate software engineer",
        "developer",
        "engineer",
        "full stack developer",
        "junior software development engineer",
        "lead software development engineer",
        "lead software engineer",
        "microsoft software development engineer",
        "principal software development engineer",
        "principal software engineer",
        "sde",
        "sde - 1",
        "sde 1",
        "sde 2",
        "sde 21",
        "sde 3",
        "sde-1",
        "sde-2",
        "sde1",
        "sde2",
        "senior engineer",
        "senior software developer",
        "senior software development engineer",
        "senior software engineer",
        "senior software engineer - product development",
        "software dev. i",
        "software developer",
        "software developer - python(fresher)",
        "software development engineer",
        "software development engineer (sde)",
        "software development engineer (sde) - contractor",
        "software development engineer (sde) contractor",
        "software development engineer (sde) i",
        "software development engineer (sde) ii",
        "software development engineer (sde) iii",
        "software development engineer (sde1)",
        "software development engineer - contractor",
        "software development engineer - i",
        "software development engineer 1",
        "software development engineer contractor",
        "software development engineer i",
        "software development engineer ii",
        "software development engineer iii",
        "software development engineer-1",
        "software development engineer-i",
        "software development engineer-ii",
        "software development engineer-iii",
        "software engineer",
        "software engineer 1",
        "software engineer 2",
        "software engineer development",
        "software engineer i",
        "software engineer-product development",
        "sr software development engineer",
        "sse",
        ".net developer",
    ],
    "Software Development Engineer - Intern": [
        "software development engineer - intern",
        "software development engineer (sde) - intern",
        "junior software development engineer - intern",
        "software development engineer - i - intern",
        "java software development engineer - intern",
        "software development engineer(sde) - intern",
    ],
    "Backend Software Development Engineer": [
        "backend",
        "backend developer",
        "backend engineer",
        "backend process",
        "backend software developer",
        "backend software engineer",
        "backend web developer",
        "java backend developer ()",
        "junior backend developer",
        "nodejs backend developer",
        "sde-2 backend",
        "senior backend developer",
        "senior backend engineer",
        "software developer (backend)",
        "software engineer, backend",
        "backend software development engineer",
    ],
    "Backend SDE Intern": [
        "backend developer - intern",
        "backend engineer - intern",
        "software engineer, backend - intern",
        "backend sde intern",
    ],
    "Frontend Software Development Engineer": [
        "front end developer",
        "front end developer - contractor",
        "front end developer contractor",
        "front end engineer",
        "front end lead",
        "front end react developer",
        "front end ui developer",
        "front end web developer",
        "front-end developer",
        "front-end web developer",
        "frontend developer",
        "frontend engineer",
        "junior front end developer",
        "lead front end developer",
        "senior front end developer",
        "senior front end engineer",
        "senior front-end developer",
        "software engineer - front end",
        "sr. front end developer",
        "frontend software development engineer",
    ],
    "Frontend SDE Intern": [
        "front end developer - intern",
        "front end web developer - intern",
        "front end - intern",
        "front-end developer - intern",
        "frontend sde intern",
    ],
    "Web Developer": [
        "web developer",
        "web developer - contractor",
        "web developer contractor",
    ],
    "Java Software Development Engineer": [
        "associate java developer",
        "avp-java developer",
        "entry level java developer",
        "full stack java developer",
        "java",
        "java applications developer",
        "java developer",
        "java developer - contractor",
        "java developer contractor",
        "java devlopers",
        "java full stack developer",
        "java programmer",
        "java software developer",
        "java software engineer",
        "java sse",
        "java tech lead",
        "java/j2ee developer",
        "junior java developer",
        "junior java developer - contractor",
        "junior java developer contractor",
        "lead java developer",
        "senior java developer",
        "senior java developer - contractor",
        "senior java developer contractor",
        "senior java developer/lead",
        "senior java/j2ee developer",
        "senior software engineer - java developer",
        "software engineer - java developer",
        "technical lead - java",
        "java software development engineer",
    ],
    "Python Software Development Engineer": [
        "senior python developer",
        "systems developer/python developer",
        "python/django developer",
        "junior python developer",
        "python developer",
        "python developer - contractor",
        "python developer contractor",
        "python automation engineer",
        "python programmer",
        "python/odoo developer",
        "python",
        "python full stack developer",
        "python engineer",
        "full stack python developer",
        "junior python/django developer",
        "python aws developer",
        "python software development engineer",
    ],
    "Python Software Development Engineer - Intern": [
        "python/django developer - intern",
        "python programmer - intern",
        "python software development engineer - intern",
    ],
    "Android Developer": [
        "android",
        "android app developer",
        "android applications developer",
        "android architect",
        "android developer",
        "android developer - contractor",
        "android developer contractor",
        "android development",
        "android engineer",
        "android framework developer",
        "android software developer",
        "android software engineer",
        "android technical lead",
        "junior android developer",
        "lead android developer",
        "senior android applications developer",
        "senior android developer",
        "senior android developer and team lead",
        "senior android developer contractor",
        "senior android engineer",
        "software engineer - android",
        "sr android developer",
        "sr. android developer",
    ],
    "Android Developer - Intern": [
        "android developer - intern",
        "android developer contractor - intern",
        "android - intern",
        "android applications developer - intern",
        "junior android developer - intern",
        "senior android developer - intern",
    ],
    "iOS Software Developer": [
        "ios app developer",
        "ios applications developer",
        "ios developer",
        "ios development",
        "ios engineer",
        "ios software developer",
        "ios software engineer",
        "junior ios developer",
        "lead ios developer",
        "middle ios developer",
        "senior ios developer",
        "senior ios engineer",
        "software engineer (ios developer)",
        "software engineer - ios",
        "sr ios developer",
    ],
    "iOS Software Developer - Intern": [
        "ios developer - intern",
        "junior ios developer - intern",
        "ios applications developer - intern",
        "ios software developer - intern",
    ],
    "Mobile App Developer": [
        "mobile app developer",
        "mobile applications developer",
        "mobile developer",
        "mobile engineer",
        "senior mobile applications developer",
        "senior mobile developer",
        "flutter developer",
        "react native developer",
    ],
    "Mobile App Developer - Intern": [
        "mobile app developer - intern",
    ],
    "QA Tester": [
        "automation test engineer",
        "lead software development engineer in test",
        "lead software development engineer in test (sdet)",
        "performance test engineer",
        "qa engineer",
        "qa test engineer",
        "sdet",
        "senior software development engineer in test",
        "senior software development engineer in test (sdet)",
        "senior software test engineer",
        "senior test engineer",
        "software development engineer in test",
        "software development engineer in test (sdet)",
        "software development engineer in test (sdet) - contractor",
        "software development engineer in test (sdet) ii",
        "software development engineer in test i",
        "software development engineer in test ii",
        "software development engineer in test lead",
        "software test engineer",
        "software tester",
        "software testing engineer",
        "sr software development engineer in test",
        "test analyst",
        "test automation engineer",
        "test engineer",
        "test engineer - contractor",
        "test engineer contractor",
        "test lead",
        "test manager",
        "tester",
        "testing engineer",
        "quality analyst",
        "qa tester",
    ],
    "QA Tester - Intern": [
        "software development engineer in test (sdet) - intern",
        "quality assurance - intern",
        "test engineer - intern",
        "qa tester - intern",
    ],
    "Database Administrator": [
        "database administrator",
        "database administrator (database administrator)",
        "database administrator (database administrator) oracle",
        "database administrator (dba)",
        "database administrator - contractor",
        "db2 database administrator",
        "lead database administrator",
        "lead oracle database administrator",
        "ms sql server database administrator",
        "mssql database administrator",
        "mysql database administrator",
        "oracle applications database administrator",
        "oracle applications database administrator (database administrator)",
        "oracle database administrator",
        "oracle database administrator - contractor",
        "senior database administrator",
        "senior db2 database administrator",
        "senior oracle database administrator",
        "senior oracle-dba",
        "senior sql server database administrator",
        "sql database administrator",
        "sql server database administrator",
        "sql server database administrator - contractor",
        "sql-dba",
        "sybase database administrator",
        "team lead-dba",
    ],
    "IT Associate": [
        "associate",
        "it associate",
    ],
    "IT Analyst": [
        "analyst",
        "it analyst",
    ],
    "Support Team": [
        "l4",
        "l3",
        "support team",
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
