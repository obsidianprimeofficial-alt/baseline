"""Personal baselines and z-scores. Pure Python."""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Baseline:
    mean: float
    sd: float
    n: int


def personal_baseline(values: Sequence[float], window: int = 30) -> Baseline:
    recent = list(values)[-window:]
    return Baseline(mean=statistics.mean(recent), sd=statistics.stdev(recent), n=len(recent))


def zscore(value: float, baseline: Baseline) -> float:
    if baseline.sd == 0:
        return 0.0
    return (value - baseline.mean) / baseline.sd
