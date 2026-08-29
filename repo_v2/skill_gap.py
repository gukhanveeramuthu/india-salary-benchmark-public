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


def skill_gap(
    profiles: Dict[str, RoleSkillProfile],
    current_skills_family: str,
    target_skills_family: str,
    top_n: int = 15,
) -> Optional[SkillGapResult]:
    """Returns None if either role isn't in the skills dataset at all
    (rather than silently comparing against an empty set)."""
    current = profiles.get(current_skills_family)
    target = profiles.get(target_skills_family)
    if current is None or target is None:
        return None

    target_ranked = sorted(target.skills.items(), key=lambda kv: -kv[1])
    target_top = target_ranked[:top_n]

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
