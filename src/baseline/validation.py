"""Validation harness for the detection rules. Simulated data only; it measures the
rules as they are and changes nothing.

numpy only, deterministic: the same inputs always give the same numbers. Plant known
shifts into clean simulated fixtures, run evaluate(), and count what the rules catch.
"""

from __future__ import annotations

import numpy as np

from baseline.compute.rules import CONFIRM_Z, DIRECTIONS, MIN_HISTORY_DAYS, SHORT, evaluate, rule_zscore
from baseline.fixtures import PROFILE, make_fixture

SIGNALS = list(DIRECTIONS)
SIZES = (2.5, 3.0, 4.0)
LENGTH = 3
DEMO_SIGNALS = ("hrv_rmssd_ms", "sleep_hours", "reaction_ms")
DEMO_ANOMALY_DAYS = (27, 28, 29, 30)


def make_clean(seed: int) -> list[dict]:
    """A 30-day fixture with no planted shift."""
    return make_fixture(seed, anomaly_start=None)


def _start_day(seed: int) -> int:
    """Planted-anomaly start, drawn 15..28 from the seed (so it lands in the evaluated range)."""
    return int(np.random.default_rng(seed).integers(15, 29))


def _plant(rows: list[dict], signal: str, size_sd: float, start_day: int, length: int) -> list[dict]:
    _, sd = PROFILE[signal]
    sign = 1.0 if DIRECTIONS[signal] == "high" else -1.0
    delta = sign * size_sd * sd
    for row in rows:
        if start_day <= row["day"] <= start_day + length - 1:
            row[signal] = round(row[signal] + delta, 2)
    return rows


def make_planted(seed: int, signal: str, size_sd: float, start_day: int, length: int = LENGTH) -> list[dict]:
    """Clean fixture, then `signal` shifted by size_sd x its PROFILE sd in the DIRECTIONS
    direction on days start_day..start_day+length-1."""
    return _plant(make_clean(seed), signal, size_sd, start_day, length)


def make_pair(seed: int, signals: list[str] | None = None, size_sd: float = 3, length: int = LENGTH) -> list[dict]:
    """Two signals planted on the same days (exercises the 48-hour multi-signal rule).
    signals defaults to two distinct signals drawn from the seed."""
    if signals is None:
        signals = list(np.random.default_rng(seed + 1).choice(SIGNALS, size=2, replace=False))
    start_day = _start_day(seed)
    rows = make_clean(seed)
    for signal in signals:
        _plant(rows, signal, size_sd, start_day, length)
    return rows


def single_signal_status(rows: list[dict], signal: str) -> dict[int, str]:
    """{day: "watch"|"confirmed"} for one signal, mirroring evaluate() exactly for that signal
    (the multi-signal rule never changes a per-signal status). Only the planted signal is
    evaluated, so detection scans cost 1/7 of a full evaluate()."""
    out: dict[int, str] = {}
    fired_prev = False
    for i in range(MIN_HISTORY_DAYS, len(rows)):
        r = rule_zscore(signal, [row[signal] for row in rows[:i]], rows[i][signal])
        if r["fired"]:
            out[rows[i]["day"]] = "confirmed" if abs(r["z"]) >= CONFIRM_Z or fired_prev else "watch"
        fired_prev = r["fired"]
    return out


def _multi_fired(flags: dict) -> bool:
    return any(
        r.get("rule") == "two_signals_in_48h" and r["status"] == "confirmed"
        for rs in flags.values() for r in rs
    )


def run(n: int = 200, seed0: int = 1000) -> dict:
    """Measure the rules over n fixtures. Returns the result tables (see docs/VALIDATION.md)."""
    seeds = range(seed0, seed0 + n)

    # (a) detection per signal and size; (b) lag from anomaly start to first confirmed flag.
    hits = {s: {size: {"confirmed": 0, "watch": 0} for size in SIZES} for s in SIGNALS}
    lags = {size: [] for size in SIZES}
    for seed in seeds:
        start_day = _start_day(seed)
        planted_days = range(start_day, start_day + LENGTH)
        for size in SIZES:
            for s in SIGNALS:
                status = single_signal_status(make_planted(seed, s, size, start_day), s)
                cdays = [d for d in planted_days if status.get(d) == "confirmed"]
                if cdays:
                    hits[s][size]["confirmed"] += 1
                    lags[size].append(min(cdays) - start_day)
                if any(d in status for d in planted_days):
                    hits[s][size]["watch"] += 1
    detection = {
        s: {
            size: {
                "confirmed_rate": hits[s][size]["confirmed"] / n,
                "watch_rate": hits[s][size]["watch"] / n,
            }
            for size in SIZES
        }
        for s in SIGNALS
    }
    all_lags = [x for v in lags.values() for x in v]
    median_lag_days = float(np.median(all_lags)) if all_lags else float("nan")
    median_lag_by_size = {
        size: (float(np.median(lags[size])) if lags[size] else float("nan")) for size in SIZES
    }

    # (c) false flags on clean fixtures; (d, part 2) multi-signal false-fire on the same fixtures.
    conf_counts, watch_counts, clean_multi = [], [], 0
    by_signal = {s: 0 for s in SIGNALS}
    for seed in seeds:
        flags = evaluate(make_clean(seed))
        c = w = 0
        for rs in flags.values():
            for r in rs:
                if "signal" not in r:
                    continue
                if r["status"] == "confirmed":
                    c += 1
                    by_signal[r["signal"]] += 1
                else:
                    w += 1
        conf_counts.append(c)
        watch_counts.append(w)
        clean_multi += _multi_fired(flags)
    false_flags = {
        "mean_confirmed": sum(conf_counts) / n,
        "mean_watch": sum(watch_counts) / n,
        "zero_confirmed_share": sum(c == 0 for c in conf_counts) / n,
        "by_signal": {s: by_signal[s] / n for s in SIGNALS},
    }

    # (d) two-signal rule detection on planted pairs.
    pair_hits = sum(_multi_fired(evaluate(make_pair(seed))) for seed in seeds)
    two_signal = {"detection_rate": pair_hits / n, "false_fire_rate": clean_multi / n}

    # (e) the existing demo anomaly (make_fixture default, anomaly_start=27).
    demo_hits = {s: 0 for s in DEMO_SIGNALS}
    for seed in seeds:
        rows = make_fixture(seed, anomaly_start=27)
        for s in DEMO_SIGNALS:
            status = single_signal_status(rows, s)
            if any(status.get(d) == "confirmed" for d in DEMO_ANOMALY_DAYS):
                demo_hits[s] += 1
    demo = {SHORT[s]: demo_hits[s] / n for s in DEMO_SIGNALS}

    return {
        "n": n,
        "seed0": seed0,
        "detection": detection,
        "median_lag_days": median_lag_days,
        "median_lag_by_size": median_lag_by_size,
        "false_flags": false_flags,
        "two_signal": two_signal,
        "demo": demo,
    }


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def render_markdown(results: dict) -> str:
    """Build docs/VALIDATION.md from a run() result. Plain words; passes the wording check."""
    n, seed0 = results["n"], results["seed0"]
    det = results["detection"]
    ff = results["false_flags"]
    ts = results["two_signal"]

    lines = [
        "# Validation (simulated data)",
        "",
        "Generated by `scripts/validate.py`. Do not hand-edit.",
        "",
        "## What was tested",
        "",
        "The deterministic detection rules in `src/baseline/compute` (the 2-SD personal-baseline "
        "rule, the confirm step, and the 48-hour multi-signal rule) measured against known, "
        "planted shifts. The rules were not changed; this reports them as they are.",
        "",
        "## How",
        "",
        f"Simulated Gaussian telemetry only. Each fixture is 30 days of synthetic readings around "
        f"fixed per-person means (`src/baseline/fixtures.py`), with no real crew time series "
        f"anywhere. For detection, a clean fixture is taken and one signal is shifted by a set "
        f"number of standard deviations for three days starting on a seed-chosen day (15..28), in "
        f"the direction the rule watches. For the pair case, two signals are shifted on the same "
        f"days. Seeds are fixed, so the numbers repeat exactly. This run used n={n} fixtures per "
        f"case, seeds {seed0}..{seed0 + n - 1}. Reproduce with:",
        "",
        "```",
        f"python scripts/validate.py --n {n} --seed {seed0}",
        "```",
        "",
        "## Detection rate per signal and shift size",
        "",
        "Share of fixtures where the signal gets a confirmed flag on a planted day. "
        "The watch share (a flag of watch level or higher) is in brackets.",
        "",
        "| Signal | 2.5 SD | 3 SD | 4 SD |",
        "|---|---|---|---|",
    ]
    for s in SIGNALS:
        row = f"| {SHORT[s]} "
        for size in SIZES:
            d = det[s][size]
            row += f"| {_pct(d['confirmed_rate'])} ({_pct(d['watch_rate'])}) "
        lines.append(row + "|")

    lines += [
        "",
        "## Time to first confirmed flag",
        "",
        "Median days from the planted start to the first confirmed flag, over detected fixtures.",
        "",
        "| Shift size | Median days |",
        "|---|---|",
    ]
    for size in SIZES:
        v = results["median_lag_by_size"][size]
        lines.append(f"| {size} SD | {v:.0f} |")
    lines.append(f"| all sizes | {results['median_lag_days']:.0f} |")

    lines += [
        "",
        "## False flags on clean fixtures",
        "",
        f"- Mean confirmed flags per 30-day clean fixture: **{ff['mean_confirmed']:.2f}**",
        f"- Mean watch flags per clean fixture: {ff['mean_watch']:.2f}",
        f"- Clean fixtures with zero confirmed flags: {_pct(ff['zero_confirmed_share'])}",
        "",
        "Per-signal mean confirmed flags on clean fixtures:",
        "",
        "| Signal | Mean confirmed per fixture |",
        "|---|---|",
    ]
    for s in SIGNALS:
        lines.append(f"| {SHORT[s]} | {ff['by_signal'][s]:.3f} |")

    lines += [
        "",
        "## Two-signal (48-hour) rule",
        "",
        f"- Fires on planted pairs: **{_pct(ts['detection_rate'])}**",
        f"- False fire on clean fixtures: {_pct(ts['false_fire_rate'])}",
        "",
        "## Demo anomaly",
        "",
        "The fixture used in the demo (`make_fixture`, anomaly_start=27) over the same seeds. "
        "Share where each signal gets a confirmed flag on the anomaly days.",
        "",
        "| Signal | Confirmed |",
        "|---|---|",
    ]
    for short, rate in results["demo"].items():
        lines.append(f"| {short} | {_pct(rate)} |")

    lines += [
        "",
        "## Limits",
        "",
        "- Simulated data only. No real crew time series is used anywhere.",
        "- Noise is plain Gaussian around fixed means; real readings drift, correlate and skew.",
        "- Planted shifts are clean step changes; real changes are messier.",
        "- These numbers describe how the rules respond to simulated input. They are not a "
        "statement about health outcomes.",
        "",
    ]
    return "\n".join(lines)
