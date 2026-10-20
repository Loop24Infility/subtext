"""
Mechanism 1 — Executive & Company Baseline Modeling ("Abnormal Tone")

Core idea: don't score a disclosure against a fixed global sentiment scale.
Score it against that specific executive's OWN historical tone. The deviation
from THEIR baseline is the signal — not the raw sentiment number.

This module takes a sequence of per-quarter tone scores (produced upstream by
the extraction pipeline in extraction/) for one executive, and flags whether
the current quarter is an outlier relative to their own history.

No external dependencies, no network calls — this is pure logic, so it can be
unit-tested right now, independent of the data-ingestion and model-download
pieces that need to run in an environment with live network access.
"""

from dataclasses import dataclass
from statistics import mean, stdev
from typing import List


@dataclass
class DisclosureRecord:
    company: str
    executive: str
    quarter: str        # e.g. "Q1FY26"
    tone_score: float   # upstream sentiment/tone score for this quarter, -1..1


@dataclass
class BaselineResult:
    company: str
    executive: str
    quarter: str
    current_tone: float
    baseline_mean: float
    baseline_stdev: float
    deviation_score: float   # z-score vs. this executive's own history
    flag: str


def compute_baseline_deviation(
    history: List[DisclosureRecord],
    current: DisclosureRecord,
    min_history: int = 3,
    flag_threshold: float = 1.5,
) -> BaselineResult:
    """
    history: prior quarters for the SAME executive, current quarter excluded.
    current: this quarter's disclosure to be scored.
    """
    if len(history) < min_history:
        raise ValueError(
            f"Need at least {min_history} prior quarters to build a baseline "
            f"for {current.executive} at {current.company} — have {len(history)}. "
            f"Fall back to a sector-level baseline until enough history accumulates "
            f"(this is the expected cold-start path for newly-added companies)."
        )

    scores = [h.tone_score for h in history]
    baseline_mean = mean(scores)
    baseline_stdev = stdev(scores) if len(scores) > 1 else 1e-4  # avoid div-by-zero

    deviation = (current.tone_score - baseline_mean) / baseline_stdev

    if deviation >= flag_threshold:
        flag = "UNUSUALLY POSITIVE vs. own history"
    elif deviation <= -flag_threshold:
        flag = "UNUSUALLY NEGATIVE vs. own history"
    else:
        flag = "within normal range"

    return BaselineResult(
        company=current.company,
        executive=current.executive,
        quarter=current.quarter,
        current_tone=current.tone_score,
        baseline_mean=round(baseline_mean, 3),
        baseline_stdev=round(baseline_stdev, 3),
        deviation_score=round(deviation, 2),
        flag=flag,
    )


if __name__ == "__main__":
    # Worked example: a CFO who is normally guarded (low, stable tone scores)
    # suddenly sounds unusually confident this quarter.
    history = [
        DisclosureRecord("ExampleCo", "CFO", "Q1FY25", 0.10),
        DisclosureRecord("ExampleCo", "CFO", "Q2FY25", 0.05),
        DisclosureRecord("ExampleCo", "CFO", "Q3FY25", 0.12),
        DisclosureRecord("ExampleCo", "CFO", "Q4FY25", 0.08),
    ]
    current_guarded_cfo = DisclosureRecord("ExampleCo", "CFO", "Q1FY26", 0.55)

    result = compute_baseline_deviation(history, current_guarded_cfo)
    print("Case 1 — guarded CFO turns unusually confident:")
    print(f"  {result}\n")

    # Contrast: a CEO who is chronically upbeat. The SAME 0.55 raw score
    # barely registers, because it's close to their normal baseline. A global
    # sentiment model would score both cases identically; this model doesn't.
    upbeat_history = [
        DisclosureRecord("ExampleCo", "CEO", "Q1FY25", 0.50),
        DisclosureRecord("ExampleCo", "CEO", "Q2FY25", 0.48),
        DisclosureRecord("ExampleCo", "CEO", "Q3FY25", 0.53),
        DisclosureRecord("ExampleCo", "CEO", "Q4FY25", 0.51),
    ]
    current_upbeat_ceo = DisclosureRecord("ExampleCo", "CEO", "Q1FY26", 0.55)

    result2 = compute_baseline_deviation(upbeat_history, current_upbeat_ceo)
    print("Case 2 — chronically upbeat CEO says the same literal thing:")
    print(f"  {result2}")
