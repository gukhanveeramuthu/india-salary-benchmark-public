"""
Empirical percentile engine. No modelling, no distribution assumptions -
Phase 1 is deterministic-only by design. Two operations:

  compute_bands(values)        -> P10/P25/P50/P75/P90 of a cohort
  percentile_of_value(values, x) -> where does x sit within that cohort

Both use linear interpolation between order statistics (the same method
NumPy and Excel's PERCENTILE.INC default to), so results are exactly
reproducible without a NumPy dependency.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PercentileBands:
    n: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


def _interpolated_percentile(sorted_values: List[float], pct: float) -> float:
    """pct in [0, 100]. Linear interpolation between order statistics."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (n - 1)
    lower_idx = int(rank)
    upper_idx = min(lower_idx + 1, n - 1)
    frac = rank - lower_idx
    return sorted_values[lower_idx] + frac * (sorted_values[upper_idx] - sorted_values[lower_idx])


def compute_bands(values: List[float]) -> PercentileBands:
    """Compute P10/P25/P50/P75/P90 for a cohort. Caller must ensure
    values is non-empty - this function does not fabricate bands for
    an empty cohort."""
    if not values:
        raise ValueError("compute_bands: cannot compute percentile bands for an empty cohort")

    sorted_values = sorted(values)
    n = len(sorted_values)
    return PercentileBands(
        n=n,
        p10=_interpolated_percentile(sorted_values, 10),
        p25=_interpolated_percentile(sorted_values, 25),
        p50=_interpolated_percentile(sorted_values, 50),
        p75=_interpolated_percentile(sorted_values, 75),
        p90=_interpolated_percentile(sorted_values, 90),
    )


def percentile_of_value(values: List[float], value: float) -> float:
    """Where does `value` rank within `values`, as a percentile 0-100.

    Uses the standard "midpoint" rule for ties: a value tied with k
    other cohort members is treated as sitting in the middle of that
    tied block, rather than arbitrarily above or below all of them.

        rank = count_below + (count_equal / 2)
        percentile = rank / n * 100

    This one formula naturally handles values above/below the entire
    cohort too (falls out to 100.0 / 0.0 respectively) without a
    special case.
    """
    if not values:
        raise ValueError("percentile_of_value: cannot rank a value against an empty cohort")

    n = len(values)
    count_below = sum(1 for v in values if v < value)
    count_equal = sum(1 for v in values if v == value)
    rank = count_below + (count_equal / 2.0)
    return (rank / n) * 100.0
