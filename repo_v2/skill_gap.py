"""
Deterministic skill-gap engine: no LLM involved. Compares two role
families' skill sets, both drawn straight from
unified_skills_detail_base.csv (NASSCOM QP / StackOverflow India /
Naukri postings), and reports what the target role asks for that the
current role's postings don't mention.

Design choices, stated plainly:
  - "Missing" means the skill has zero recorded mentions in the
    current role's postings, not "mentioned less". A skill mentioned
    once in each role counts as present in both - we're not trying to
    quantify depth, just presence/absence, because depth isn't in the
    data.
  - Skills are ranked within a role by mention_count, used only as a
    proxy for "how often employers ask for it", not for the specific
    number of postings.
  - `n_sources` (from unified_skills_by_role_base.csv) is surfaced
    per role so a thin, single-source skill list (like most non-BA/DA
    roles) isn't presented with the same confidence as a role backed
    by 2-3 independently-sourced datasets.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import csv
from collections import defaultdict


@dataclass
class RoleSkillProfile:
    role_family: str
    n_sources: int
    total_mentions: int
    skills: Dict[str, int]  # canonical_skill -> summed mention_count


@dataclass
class SkillGapResult:
    current_role: str
    target_role: str
    current_n_sources: int
    target_n_sources: int
    overlapping_skills: List[str]          # present in both (any mention count)
    missing_skills: List[str]              # in target, absent from current - ranked by target mention_count desc
    target_top_skills: List[tuple]         # (skill, mention_count) top 15 of target, for context


def load_skill_profiles(detail_csv_path: str, by_role_csv_path: str) -> Dict[str, RoleSkillProfile]:
    n_sources_by_role: Dict[str, int] = {}
    with open(by_role_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n_sources_by_role[row["role_family"]] = int(row["n_sources"])

    skills_by_role: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    with open(detail_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            role = row["role_family"]
            skill = row["canonical_skill"]
            count = int(row["mention_count"])
            skills_by_role[role][skill] += count

    profiles: Dict[str, RoleSkillProfile] = {}
    for role, skills in skills_by_role.items():
        profiles[role] = RoleSkillProfile(
            role_family=role,
            n_sources=n_sources_by_role.get(role, 0),
            total_mentions=sum(skills.values()),
            skills=dict(skills),
        )
    return profiles


# Skills mentioned below this raw count within a role are excluded from
# distinctiveness ranking - with only 1-2 mentions, a lift ratio is just
# noise (one recruiter's odd keyword choice), not a real signal.
MIN_MENTIONS_FOR_DISTINCTIVENESS = 3


def _global_skill_rates(profiles: Dict[str, RoleSkillProfile]) -> Dict[str, float]:
    """Baseline rate of each skill across ALL roles pooled - i.e. how
    common a skill is in the job market generally, independent of role.
    Used as the denominator for distinctiveness (lift)."""
    totals: Dict[str, int] = defaultdict(int)
    grand_total = 0
    for profile in profiles.values():
        for skill, count in profile.skills.items():
            totals[skill] += count
            grand_total += count
    if grand_total == 0:
        return {}
    return {skill: count / grand_total for skill, count in totals.items()}


def rank_by_distinctiveness(
    profiles: Dict[str, RoleSkillProfile],
    role_family: str,
    top_n: int = 15,
) -> List[tuple]:
    """Ranks a role's skills by how disproportionately common they are
    IN THIS ROLE vs. the market baseline (lift = role rate / global
    rate), instead of raw mention count. This surfaces what actually
    sets the role apart - e.g. 'Product Strategy' (rare everywhere
    except Product Manager postings) - instead of boilerplate terms
    like 'SQL' or 'Computer science' that appear in most roles and
    would otherwise dominate a raw-frequency ranking.

    Returns (skill, mention_count, lift) tuples, highest lift first.
    Falls back to raw-frequency ranking if the role has too few skills
    above the noise floor to rank meaningfully."""
    profile = profiles.get(role_family)
    if profile is None:
        return []
    global_rates = _global_skill_rates(profiles)
    role_total = profile.total_mentions or 1

    scored = []
    for skill, count in profile.skills.items():
        if count < MIN_MENTIONS_FOR_DISTINCTIVENESS:
            continue
        role_rate = count / role_total
        global_rate = global_rates.get(skill, role_rate)  # skill only seen here -> maximal lift, don't div by ~0
        lift = role_rate / global_rate if global_rate > 0 else float("inf")
        scored.append((skill, count, lift))

    if not scored:
        # every skill for this role is below the noise floor - fall back
        # to raw frequency rather than returning nothing.
        return [(s, c, 1.0) for s, c in sorted(profile.skills.items(), key=lambda kv: -kv[1])[:top_n]]

    scored.sort(key=lambda t: -t[2])
    return scored[:top_n]


def skill_gap(
    profiles: Dict[str, RoleSkillProfile],
    current_skills_family: str,
    target_skills_family: str,
    top_n: int = 15,
) -> Optional[SkillGapResult]:
    """Returns None if either role isn't in the skills dataset at all
    (rather than silently comparing against an empty set).

    Ranks the target role's skills by distinctiveness (see
    rank_by_distinctiveness) rather than raw mention count, so the gap
    surfaces what actually sets the target role apart instead of
    boilerplate terms (SQL, Computer science, Analytical, ...) that show
    up in most roles' postings and would otherwise dominate."""
    current = profiles.get(current_skills_family)
    target = profiles.get(target_skills_family)
    if current is None or target is None:
        return None

    target_top = [(s, c) for s, c, _lift in rank_by_distinctiveness(profiles, target_skills_family, top_n)]

    overlapping = [s for s, _ in target_top if s in current.skills]
    missing = [s for s, _ in target_top if s not in current.skills]

    return SkillGapResult(
        current_role=current_skills_family,
        target_role=target_skills_family,
        current_n_sources=current.n_sources,
        target_n_sources=target.n_sources,
        overlapping_skills=overlapping,
        missing_skills=missing,
        target_top_skills=target_top,
    )
