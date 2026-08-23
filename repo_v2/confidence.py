"""
Confidence tiers for a cohort's sample size.

Thresholds are deliberately simple, fixed integers, not statistical
significance tests - this is a Phase 1 (deterministic-only) engine, and
the tiers exist to communicate "how much should you trust this number"
in plain language, not to make a formal inference claim.
"""

INSUFFICIENT = "Insufficient"
LOW = "Low"
MODERATE = "Moderate"
HIGH = "High"


def confidence_for(n: int) -> str:
    """Map a cohort sample size to a confidence tier.

    n < 10          -> Insufficient
    10 <= n < 20     -> Low
    20 <= n < 50     -> Moderate
    n >= 50          -> High
    """
    if n < 10:
        return INSUFFICIENT
    if n < 20:
        return LOW
    if n < 50:
        return MODERATE
    return HIGH
