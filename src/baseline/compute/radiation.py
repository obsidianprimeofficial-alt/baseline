"""Radiation environment from cached real data. Pure Python, no network.

Two sources: NOAA GOES integral proton flux (solar particle event flag) and NASA MSL RAD, the
Radiation Assessment Detector on the Curiosity rover (Mars surface dose rate, uGy/day).
"""

import json
import statistics
from collections.abc import Sequence
from pathlib import Path

from baseline.compute.baselines import personal_baseline, zscore

CACHE = "cache/noaa/integral-protons-7-day.json"
CHANNEL = ">=10 MeV"
S1_PFU = 10.0  # NOAA S1 (minor) solar radiation storm: >=10 MeV flux at or above 10 pfu


def load_cached_protons(path: str = CACHE) -> dict:
    """{source_url, fetched_at, data}. ponytail: cache only, so OFFLINE=1 holds by construction;
    scripts/fetch_goes.py is the only thing that touches the network."""
    return json.loads(Path(path).read_text())


def spe_flag(rows: Sequence[dict], threshold_pfu: float = S1_PFU) -> dict:
    """Fires when the latest >=10 MeV flux is at or above threshold_pfu."""
    channel = [r for r in rows if r["energy"] == CHANNEL]
    if not channel:
        raise ValueError(f"no {CHANNEL} rows in the record")
    latest = max(channel, key=lambda r: r["time_tag"])  # ISO UTC strings sort by time
    return {
        "rule": "solar_particle_event",
        "signal": "proton_flux_ge10mev_pfu",
        "current": latest["flux"],
        "threshold_pfu": threshold_pfu,
        "time_tag": latest["time_tag"],
        "satellite": latest.get("satellite"),
        "fired": latest["flux"] >= threshold_pfu,
    }


# ---------- Mars surface dose from MSL RAD (Curiosity rover) ----------

MSL_CACHE = "cache/msl_rad/dose-rate-30-day.json"
DOSE_COLUMN = "dose_e_total"  # detector E, tissue-equivalent plastic: the human-relevant one
MIN_OBS_PER_DAY = 20  # ~16-minute cadence gives ~85 observations a day; fewer than 20 is a partial day
MIN_HISTORY_DAYS = 14  # same floor as the vitals rules in rules.py
DOSE_Z = 2.0


def load_cached_msl_rad(path: str = MSL_CACHE) -> dict:
    """{source, source_url, doi, archive_url, units, columns, fetched_at, data}. Cache only, no network;
    scripts/fetch_msl_rad.py is the only thing that touches the network."""
    return json.loads(Path(path).read_text())


def daily_dose(rows: Sequence[dict], column: str = DOSE_COLUMN, min_obs: int = MIN_OBS_PER_DAY) -> list[dict]:
    """Mean dose rate per UTC day from unflagged observations, oldest first.
    Days with fewer than min_obs good observations are left out (partial days)."""
    by_day: dict[str, list[float]] = {}
    for r in rows:
        if r.get("flagged") or r.get(column) is None:
            continue
        by_day.setdefault(r["time_tag"][:10], []).append(r[column])
    return [
        {"date": day, "dose_ugy_day": statistics.mean(values), "n_obs": len(values)}
        for day, values in sorted(by_day.items())
        if len(values) >= min_obs
    ]


def mars_dose_flag(daily: Sequence[dict], threshold: float = DOSE_Z) -> dict:
    """Fires when the latest day's dose is threshold SDs above the mean of the earlier days.
    Needs MIN_HISTORY_DAYS earlier days, otherwise it reports the reading and does not fire."""
    if not daily:
        raise ValueError("no complete days in the record")
    latest, history = daily[-1], [d["dose_ugy_day"] for d in daily[:-1]]
    enough = len(history) >= MIN_HISTORY_DAYS
    b = personal_baseline(history) if enough else None
    z = zscore(latest["dose_ugy_day"], b) if enough else None
    return {
        "rule": "mars_dose_above_30_day_mean",
        "signal": "mars_dose_ugy_day",
        "date": latest["date"],
        "current": latest["dose_ugy_day"],
        "n_obs": latest["n_obs"],
        "baseline_mean": b.mean if enough else None,
        "baseline_sd": b.sd if enough else None,
        "z": z,
        "threshold_z": threshold,
        "window_days": len(history),
        "fired": bool(enough and z >= threshold),
    }
