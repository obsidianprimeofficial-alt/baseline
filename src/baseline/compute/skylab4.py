"""Real crew record: the Skylab 4 sleep estimates in cache/skylab4 through the app's own sleep rule. Pure Python, no network.

Crew log estimates, not measurements. Reads role, mission_day and total_sleep_h only; a missing night is
never filled in, never counted as history and never flagged.
"""

import csv
from pathlib import Path

from baseline.compute.rules import CONFIRM_Z, MIN_HISTORY_DAYS, rule_zscore

CSV = "cache/skylab4/sleep-estimates.csv"
SIGNAL = "sleep_hours"
ROLES = ("CDR", "PLT", "SPT")


def parse_total(printed: str) -> tuple[float | None, bool]:
    """(value, approximate). "≈3.0" is 3.0 marked approximate; "?" and blank are missing."""
    text = printed.strip()
    if text in ("", "?"):
        return None, False
    return (float(text[1:]), True) if text.startswith("≈") else (float(text), False)


def load_nights(path: str = CSV) -> list[dict]:
    """One dict per role and night: role, mission_day, total_sleep_h, approximate."""
    with open(Path(path), encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    nights = []
    for r in rows:
        value, approximate = parse_total(r["total_sleep_h"])
        nights.append({"role": r["role"], "mission_day": int(r["mission_day"]), "total_sleep_h": value, "approximate": approximate})
    return nights


def evaluate_sleep(nights: list[dict]) -> dict[int, dict]:
    """{mission_day: fired result with status} for one role, nights in order. Same steps as rules.evaluate, one signal."""
    history: list[float] = []
    fired: dict[int, dict] = {}
    for night in nights:
        day, value = night["mission_day"], night["total_sleep_h"]
        if value is None:
            continue
        if len(history) >= MIN_HISTORY_DAYS:
            r = rule_zscore(SIGNAL, history, value)
            if r["fired"]:
                fired[day] = {**r, "status": "confirmed" if abs(r["z"]) >= CONFIRM_Z or day - 1 in fired else "watch"}
        history.append(value)
    return fired


def role_nights(nights: list[dict], role: str) -> list[dict]:
    return [n for n in nights if n["role"] == role]

