"""Detection rules. Deterministic; every number here comes from the telemetry rows."""

from collections.abc import Sequence

from baseline.compute.baselines import personal_baseline, zscore

DIRECTIONS = {
    "hrv_rmssd_ms": "low",
    "sleep_hours": "low",
    "spo2_pct": "low",
    "mood_1to5": "low",
    "heart_rate_bpm": "high",
    "core_temp_c": "high",
    "reaction_ms": "high",
}

# Short names used in rule ids, e.g. "hrv_below_personal_baseline".
SHORT = {
    "hrv_rmssd_ms": "hrv",
    "sleep_hours": "sleep",
    "spo2_pct": "spo2",
    "mood_1to5": "mood",
    "heart_rate_bpm": "heart_rate",
    "core_temp_c": "core_temp",
    "reaction_ms": "reaction",
}

# 14 days, not 7: on honest Gaussian noise a 7-day baseline gave ~1.06 confirmed false flags
# per 30-day clean fixture (seeds 1-50); 14 days gives ~0.64.
MIN_HISTORY_DAYS = 14
CONFIRM_Z = 3.0


def rule_zscore(signal: str, history: Sequence[float], current: float, threshold: float = 2.0) -> dict:
    """history is the previous days only, never the current day."""
    direction = DIRECTIONS[signal]
    b = personal_baseline(history)
    z = zscore(current, b)
    return {
        "rule": f"{SHORT[signal]}_{'below' if direction == 'low' else 'above'}_personal_baseline",
        "signal": signal,
        "current": current,
        "baseline_mean": b.mean,
        "baseline_sd": b.sd,
        "z": z,
        "fired": z <= -threshold if direction == "low" else z >= threshold,
        "window_days": b.n,
        "direction": direction,
    }


def rule_multi_signal(results_by_day: dict[int, list[dict]], window_hours: int = 48) -> dict:
    """Fires when two or more different confirmed signals fall in the window ending on the latest day."""
    window_days = window_hours // 24
    last = max(results_by_day)
    signals = sorted(
        {
            r["signal"]
            for day, rs in results_by_day.items()
            if last - day < window_days
            for r in rs
            if r.get("status") == "confirmed"
        }
    )
    fired = len(signals) >= 2
    return {
        "rule": "two_signals_in_48h",
        "signals": signals,
        "fired": fired,
        "window_days": window_days,
        "status": "confirmed" if fired else None,
    }


def evaluate(rows: list[dict]) -> dict[int, list[dict]]:
    """{day: [fired RuleResults]} for every day after the first MIN_HISTORY_DAYS.

    Each result has status "watch" (one day past |z| 2) or "confirmed"
    (past |z| 3 that day, or past |z| 2 on the previous day too for the same signal).
    """
    fired: dict[int, list[dict]] = {}
    for i in range(MIN_HISTORY_DAYS, len(rows)):
        day = rows[i]["day"]
        yesterday = {r["signal"] for r in fired.get(day - 1, [])}  # a gap in the record breaks the run
        results = [rule_zscore(s, [r[s] for r in rows[:i]], rows[i][s]) for s in DIRECTIONS]
        fired[day] = [
            {**r, "status": "confirmed" if abs(r["z"]) >= CONFIRM_Z or r["signal"] in yesterday else "watch"}
            for r in results
            if r["fired"]
        ]
    out = {}
    for day, results in fired.items():
        multi = rule_multi_signal({d: rs for d, rs in fired.items() if d <= day})
        # Raised only on a day with a fresh confirmed flag, so it does not repeat on a quiet day after.
        fresh = any(r["status"] == "confirmed" for r in results)
        out[day] = results + [multi] if fresh and multi["fired"] else results
    return out
