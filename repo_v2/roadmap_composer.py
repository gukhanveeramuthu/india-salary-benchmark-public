"""
Roadmap composer: combines benchmark.py (salary), skill_gap.py (skills),
role_transitions.csv (career paths), and taxonomy_bridge.py (the crosswalk
between the two role taxonomies) into a single phased career roadmap.

Still fully deterministic - no LLM layer. If a piece of evidence isn't
available (no salary coverage for a target role, no second-hop transition
on record, cohort too small), the corresponding field comes back None /
empty with a reason attached, rather than an invented number.

Phase design:
  - near_term:   skills the market currently expects in the user's own
                 role. If `user_known_skills` is supplied, this becomes a
                 real personal gap (skills expected but not in their
                 list); if not supplied, it's shown as market context
                 only - never invented as "your gap" without their input.
  - medium_term: the single highest-confidence transition out of the
                 user's current role (role_transitions.csv), with its
                 skill gap and - where salary data exists for that
                 target - a benchmark run for someone at that gap-closed
                 profile.
  - long_term:   the highest-confidence transition OUT OF the medium-term
                 target role (a second hop). None if no transition is on
                 record from there.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import csv

import taxonomy
from schema import SalaryObservation, currency_segment
from benchmark import run_benchmark, BenchmarkResult
from taxonomy_bridge import resolve_to_skills_family, salary_families_for_skills_family
from skill_gap import load_skill_profiles, skill_gap, RoleSkillProfile

CONFIDENCE_RANK = {"well-documented": 3, "medium-well": 2, "medium": 1, "thin": 0}


def load_transitions(csv_path: str) -> List[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def best_transition(transitions: List[dict], source_skills_family: str) -> Optional[dict]:
    """Highest-confidence-tier transition out of source_skills_family.
    Ties broken by leaving the first one found (input order) - transitions.csv
    isn't otherwise ordered, so this is an arbitrary but stable tiebreak."""
    candidates = [t for t in transitions if t["source_role"] == source_skills_family]
    if not candidates:
        return None
    return max(candidates, key=lambda t: CONFIDENCE_RANK.get(t["confidence_tier"], -1))


def _salary_phase(
    target_skills_family: str,
    observations: List[SalaryObservation],
    experience_level: Optional[str],
    salary_currency: str,
    user_salary_in_usd: float,
    city: Optional[str],
) -> Dict:
    """Runs a salary benchmark for target_skills_family if - and only if -
    the crosswalk has a salary-data source for it."""
    salary_families = salary_families_for_skills_family(target_skills_family)
    if not salary_families:
        return {
            "available": False,
            "reason": f"No salary data source maps to '{target_skills_family}' yet "
                      f"(see taxonomy_crosswalk.csv, status NO_SALARY_SOURCE).",
        }

    # If more than one taxonomy family feeds this skills family, try each
    # and keep the one with the largest cohort (most trustworthy), rather
    # than silently picking the first.
    best_result: Optional[BenchmarkResult] = None
    best_family = None
    for fam in salary_families:
        result = run_benchmark(
            observations,
            job_title=fam,
            experience_level=experience_level,
            salary_currency=salary_currency,
            user_salary_in_usd=user_salary_in_usd,
            city=city,
        )
        if best_result is None or len(result.cohort.observations) > len(best_result.cohort.observations):
            best_result = result
            best_family = fam

    return {
        "available": True,
        "salary_family_used": best_family,
        "confidence": best_result.confidence,
        "bands": best_result.bands,
        "user_percentile": best_result.user_percentile,
        "provenance": best_result.provenance,
        "warnings": best_result.warnings,
    }


def _skill_phase(
    profiles: Dict[str, RoleSkillProfile],
    current_skills_family: str,
    target_skills_family: str,
    user_known_skills: Optional[List[str]],
) -> Dict:
    gap = skill_gap(profiles, current_skills_family, target_skills_family)
    if gap is None:
        return {"available": False, "reason": "one or both roles not present in skills dataset"}

    result = {
        "available": True,
        "target_top_skills": gap.target_top_skills,
        "overlapping_with_current_role_market": gap.overlapping_skills,
        "missing_from_current_role_market": gap.missing_skills,
        "current_role_n_sources": gap.current_n_sources,
        "target_role_n_sources": gap.target_n_sources,
    }
    if user_known_skills is not None:
        known = set(s.lower() for s in user_known_skills)
        personal_gap = [s for s, _ in gap.target_top_skills if s.lower() not in known]
        result["personal_gap"] = personal_gap
        result["personal_gap_basis"] = "compared against your provided skill list"
    else:
        result["personal_gap"] = None
        result["personal_gap_basis"] = (
            "no personal skill list supplied - showing market-expected skills only, "
            "not a claim about what you personally lack"
        )
    return result


def compose_roadmap(
    raw_job_title: str,
    experience_level: Optional[str],
    salary_currency: str,
    user_salary_in_usd: float,
    observations: List[SalaryObservation],
    transitions: List[dict],
    skill_profiles: Dict[str, RoleSkillProfile],
    city: Optional[str] = None,
    user_known_skills: Optional[List[str]] = None,
) -> Dict:
    current_salary_family = taxonomy.role_family(raw_job_title)
    current_skills_family = resolve_to_skills_family(current_salary_family)

    roadmap: Dict = {
        "input": {
            "raw_job_title": raw_job_title,
            "current_salary_family": current_salary_family,
            "current_skills_family": current_skills_family,
        },
        "near_term": None,
        "medium_term": None,
        "long_term": None,
    }

    if current_salary_family is None:
        roadmap["error"] = (
            f"'{raw_job_title}' didn't match any known role family - can't build a roadmap "
            f"without knowing the starting role. Try a more standard title."
        )
        return roadmap
    if current_skills_family is None:
        roadmap["error"] = (
            f"'{current_salary_family}' has no entry in the taxonomy crosswalk - "
            f"this shouldn't happen for a mapped family; check taxonomy_bridge.py."
        )
        return roadmap

    # --- near term: current-role skill context / personal gap ---
    near_gap = skill_gap(skill_profiles, current_skills_family, current_skills_family)
    if near_gap is not None:
        top = near_gap.target_top_skills
        if user_known_skills is not None:
            known = set(s.lower() for s in user_known_skills)
            personal_gap = [s for s, _ in top if s.lower() not in known]
        else:
            personal_gap = None
        roadmap["near_term"] = {
            "role": current_skills_family,
            "market_top_skills": top,
            "personal_gap": personal_gap,
            "personal_gap_basis": (
                "compared against your provided skill list" if user_known_skills is not None
                else "no personal skill list supplied - showing market-expected skills only"
            ),
            "n_sources": near_gap.target_n_sources,
        }

    # --- medium term: best transition out of current role ---
    medium_transition = best_transition(transitions, current_skills_family)
    if medium_transition is None:
        roadmap["medium_term"] = {
            "available": False,
            "reason": f"No recorded transition out of '{current_skills_family}' in role_transitions.csv",
        }
        return roadmap

    medium_target = medium_transition["target_role"]
    roadmap["medium_term"] = {
        "available": True,
        "target_role": medium_target,
        "transition_type": medium_transition["transition_type"],
        "confidence_tier": medium_transition["confidence_tier"],
        "india_context": medium_transition["india_context"],
        "notes": medium_transition["skill_gap_notes"],
        "skills": _skill_phase(skill_profiles, current_skills_family, medium_target, user_known_skills),
        "salary": _salary_phase(medium_target, observations, experience_level, salary_currency,
                                  user_salary_in_usd, city),
    }

    # --- long term: best transition out of the medium-term target ---
    long_transition = best_transition(transitions, medium_target)
    if long_transition is None:
        roadmap["long_term"] = {
            "available": False,
            "reason": f"No recorded transition out of '{medium_target}' in role_transitions.csv",
        }
        return roadmap

    long_target = long_transition["target_role"]
    roadmap["long_term"] = {
        "available": True,
        "target_role": long_target,
        "transition_type": long_transition["transition_type"],
        "confidence_tier": long_transition["confidence_tier"],
        "india_context": long_transition["india_context"],
        "notes": long_transition["skill_gap_notes"],
        "skills": _skill_phase(skill_profiles, medium_target, long_target, user_known_skills),
        "salary": _salary_phase(long_target, observations, experience_level, salary_currency,
                                  user_salary_in_usd, city),
    }

    return roadmap
