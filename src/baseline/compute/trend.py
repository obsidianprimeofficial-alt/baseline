"""Trend projection from the person's own last 3 days. Deterministic; no model, no fitting beyond a
least-squares line through three points. A projection, not a forecast: the card says so."""

import math

from baseline.compute.rules import DIRECTIONS, evaluate

DAYS = 3
THRESHOLD = 2.0  # the usual range is mean ± 2 SD, the same cut rule_zscore uses


def slope(days: list[int], values: list[float]) -> float:
    """Least-squares slope per day. For 3 equally spaced days it equals (last − first) / 2."""
    n = len(days)
    mx, my = sum(days) / n, sum(values) / n
    return sum((x - mx) * (y - my) for x, y in zip(days, values)) / sum((x - mx) ** 2 for x in days)


def projection(rows: list[dict], signal: str, flags: dict[int, list[dict]] | None = None) -> dict | None:
    """The card for `signal` on the last day of `rows`, or None.

    A card exists only when the signal was outside its usual range (watch or confirmed) on each of the
    last 3 days, and those are 3 consecutive days. The usual-range edge is today's band from the same
    history the rule uses (the flag's baseline_mean and baseline_sd)."""
    if len(rows) < DAYS:
        return None
    flags = evaluate(rows) if flags is None else flags
    last = rows[-DAYS:]
    days = [r["day"] for r in last]
    if days != list(range(days[0], days[0] + DAYS)):
        return None
    hits = [next((f for f in flags.get(d, []) if f.get("signal") == signal), None) for d in days]
    if not all(hits):
        return None
    values = [r[signal] for r in last]
    today = hits[-1]
    high = DIRECTIONS[signal] == "high"
    edge = today["baseline_mean"] + (THRESHOLD if high else -THRESHOLD) * today["baseline_sd"]
    s = slope(days, values)
    toward = s < 0 if high else s > 0
    # Days until a straight line from today's value crosses back inside the edge (strictly inside, as the rule
    # fires at exactly 2 SD). None when it moves away or stays level.
    back = math.floor(abs(values[-1] - edge) / abs(s)) + 1 if toward else None
    return {
        "signal": signal,
        "days": days,
        "values": values,
        "slope": s,
        "percent_per_day": s / values[-1] * 100,
        "direction": DIRECTIONS[signal],
        "edge": edge,
        "toward": toward,
        "days_back": back,
    }


def projections(rows: list[dict]) -> dict[str, dict]:
    """Every card for the last day of `rows`, keyed by signal."""
    flags = evaluate(rows)
    out = {s: projection(rows, s, flags) for s in DIRECTIONS}
    return {s: p for s, p in out.items() if p}
