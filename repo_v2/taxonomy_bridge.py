"""
Bridges the two role taxonomies in this project:

  - taxonomy.py's 34 "salary families" (fine-grained, tech-stack-specific,
    derived from ~1,700 raw India job titles - see role_grouping_applied.xlsx)
  - the skills/transitions dataset's 35 "skills families" (coarser,
    role-shaped, derived from NASSCOM/StackOverflow/Naukri)

They overlap on name for some roles (Data Analyst, Data Engineer,
Machine Learning Engineer, ...) and diverge for others. Where a
taxonomy.py family maps to skills-family is genuinely ambiguous from the
title alone (e.g. "Java Software Development Engineer" could be Backend
Developer or generic Software Developer), a DEFAULT is chosen below and
clearly marked - override via `overrides` in resolve_to_skills_family()
if you disagree.

10 skills families have no taxonomy.py salary source at all (Cloud
Infra Engineer, Full-Stack Developer, Team Lead/Tech Lead, Technical
Architect, Data Architect, Network Administrator, IT/Tech Leadership,
Product/Research Analyst, Technical Writer, Webmaster, System Analyst*,
System Administrator*, Site Reliability Engineer*, DevOps Engineer*,
Business Intelligence Analyst - some of these get partial coverage via
an AMBIGUOUS default below, marked with *). For any skills family with
zero salary coverage, run_benchmark() will correctly return
"Insufficient data" - that's a true statement about this dataset, not
a bug.
"""

from typing import Optional

# taxonomy_family (as returned by taxonomy.role_family) -> resolved skills family.
# Entries marked DEFAULT were ambiguous in the crosswalk review; see
# taxonomy_crosswalk.csv for the alternatives that were considered.
SALARY_TO_SKILLS_FAMILY = {
    "Android Developer": "Mobile Developer",
    "Android Developer - Intern": "Mobile Developer",
    "iOS Software Developer": "Mobile Developer",
    "iOS Software Developer - Intern": "Mobile Developer",
    "Mobile App Developer": "Mobile Developer",
    "Mobile App Developer - Intern": "Mobile Developer",
    "Backend Software Development Engineer": "Backend Developer",
    "Backend SDE Intern": "Backend Developer",
    "Frontend Software Development Engineer": "Frontend Developer",
    "Frontend SDE Intern": "Frontend Developer",
    "Data Analyst": "Data Analyst",
    "Data Engineer": "Data Engineer",
    "Data Science": "Data Scientist",
    "Database Administrator": "Database Administrator (DBA)",
    "Machine Learning Engineer": "Machine Learning Engineer",
    "Product Management": "Product Manager",
    "Project / Program Management": "Project / Program Manager (IT)",
    "QA Tester": "Testing Engineer / QA",
    "QA Tester - Intern": "Testing Engineer / QA",
    "Support Team": "Technical Support Engineer",
    "Security": "System Security / Security Analyst",
    "Software Development Engineer": "Software Developer",
    "Software Development Engineer - Intern": "Software Developer",
    # --- ambiguous, DEFAULT chosen (see taxonomy_crosswalk.csv) ---
    "Java Software Development Engineer": "Backend Developer",          # DEFAULT (India Java roles skew backend)
    "Python Software Development Engineer": "Backend Developer",        # DEFAULT
    "Python Software Development Engineer - Intern": "Backend Developer",  # DEFAULT
    "Web Developer": "Frontend Developer",                              # DEFAULT (literal reading)
    "Business / Systems Analysis": "Business Analyst",                  # DEFAULT (n=2, low stakes)
    "DevOps / SRE": "DevOps Engineer",                                  # DEFAULT (n=5)
    "Engineering Leadership": "Team Lead / Technical Lead",             # DEFAULT (n=5)
    "IT Analyst": "System Analyst",                                     # DEFAULT
    "IT Associate": "Technical Support Engineer",                       # DEFAULT
    "IT Support / Systems Administration": "System Administrator",      # DEFAULT (n=1)
    "UI/UX Design": "Graphic / Web Designer",                           # DEFAULT (imperfect, only option)
}

# Reverse map: skills_family -> list of taxonomy_family(ies) that feed it.
# A skills family with an empty list has NO salary data source.
SKILLS_TO_SALARY_FAMILIES: dict[str, list[str]] = {}
for _sal, _skl in SALARY_TO_SKILLS_FAMILY.items():
    SKILLS_TO_SALARY_FAMILIES.setdefault(_skl, []).append(_sal)


def resolve_to_skills_family(taxonomy_family: Optional[str]) -> Optional[str]:
    """taxonomy.py family -> skills-dataset family, or None if unmapped
    (e.g. taxonomy_family is None, meaning taxonomy.role_family() didn't
    recognize the raw title)."""
    if taxonomy_family is None:
        return None
    return SALARY_TO_SKILLS_FAMILY.get(taxonomy_family)


def salary_families_for_skills_family(skills_family: str) -> list[str]:
    """skills-dataset family -> the taxonomy.py family/families that can be
    used to run a salary benchmark for it. Empty list = no salary data
    exists for this role yet."""
    return SKILLS_TO_SALARY_FAMILIES.get(skills_family, [])


def has_salary_coverage(skills_family: str) -> bool:
    return len(salary_families_for_skills_family(skills_family)) > 0
