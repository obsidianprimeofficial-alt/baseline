"""Cache the real 20 May 2024 Mars surface radiation surge (MSL RAD, Curiosity rover) and build its replay file.

Two files in cache/msl_rad/ and one web copy:
    rad-2024-04-20-to-05-25.json    the readings, same record format as dose-rate-30-day.json
    mars-surge-2024-05-20.json      the replay: the rule's output on 20 May 2024, the daily values and the sources
    web/data/mars-surge-2024-05-20.json   copy of the replay file for the page

Usage:
    python scripts/build_mars_surge.py           # rebuild the replay file from the cached readings (no network)
    python scripts/build_mars_surge.py --fetch   # fetch the readings once from NASA SPDF CDAWeb, then rebuild

The rule is not changed: daily_dose() and mars_dose_flag() from src/baseline/compute/radiation.py, called on the
record up to each day, as the console does for the latest day. The replay stops at 20 May (the surge day).
Never uses fetch_msl_rad.py's main(): it always writes the live cache, dose-rate-30-day.json.
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_msl_rad import compact, request_url  # noqa: E402

from baseline.compute.radiation import DOSE_COLUMN, daily_dose, mars_dose_flag  # noqa: E402

START, STOP = datetime(2024, 4, 20, tzinfo=timezone.utc), datetime(2024, 5, 26, tzinfo=timezone.utc)
SURGE, BEFORE = "2024-05-20", "2024-05-19"
READINGS = Path("cache/msl_rad/rad-2024-04-20-to-05-25.json")
EVENT = Path("cache/msl_rad/mars-surge-2024-05-20.json")
WEB = Path("web/data/mars-surge-2024-05-20.json")

ARTICLE = "https://www.nasa.gov/solar-system/planets/mars/nasa-watches-mars-light-up-during-epic-solar-storm/"
SLIDES = "https://wrmiss.org/workshops/twentyseventh/Hassler.pdf"
PAPER = "https://doi.org/10.1007/s11207-025-02482-4"


def flag_on(daily: list[dict], date: str) -> dict:
    """The rule on the record up to and including date (mars_dose_flag judges the last day it is given)."""
    return mars_dose_flag([d for d in daily if d["date"] <= date])


def build(readings: dict) -> dict:
    rows = readings["data"]
    daily = daily_dose(rows)
    surge, before = flag_on(daily, SURGE), flag_on(daily, BEFORE)
    peak = max((r for r in rows if r["time_tag"].startswith(SURGE) and not r["flagged"] and r[DOSE_COLUMN] is not None),
               key=lambda r: r[DOSE_COLUMN])
    return {
        "event": "Mars surface radiation surge, 20 May 2024",
        "column": DOSE_COLUMN,
        "before": {"date": before["date"], "dose_ugy_day": round(before["current"], 1), "baseline_mean": round(before["baseline_mean"], 1)},
        "date": surge["date"],
        "dose_ugy_day": round(surge["current"], 1),
        "n_obs": surge["n_obs"],
        "baseline_mean": round(surge["baseline_mean"], 1),
        "baseline_sd": round(surge["baseline_sd"], 2),
        "z": round(surge["z"], 2),
        "threshold_z": surge["threshold_z"],
        "window_days": surge["window_days"],
        "fired": surge["fired"],
        "peak": {"time_tag": peak["time_tag"], "ugy_day": round(peak[DOSE_COLUMN], 1)},
        "daily": [{"date": d["date"], "dose_ugy_day": round(d["dose_ugy_day"], 1), "n_obs": d["n_obs"]} for d in daily],
        "note": "Daily values are means of unflagged readings, not weighted by time. The replay stops at 20 May.",
        "doi": readings["doi"],
        "rdr_version": readings["rdr_version"],
        "sources": [
            {"name": "NASA SPDF CDAWeb, MSL_RAD_OBS-L2", "url": readings["source_url"], "doi": readings["doi"]},
            {"name": "NASA, NASA Watches Mars Light Up During Epic Solar Storm", "url": ARTICLE,
             "line": "If astronauts had been standing next to NASA's Curiosity Mars rover at the time, they would have received a radiation "
                     "dose of 8,100 micrograys — equivalent to 30 chest X-rays. | While not deadly, it was the biggest surge measured by "
                     "Curiosity's Radiation Assessment Detector, or RAD, since the rover landed 12 years ago."},
            {"name": "MSL RAD team slides, A Solar Cycle of Radiation Measurements on the Surface of Mars, p.17", "url": SLIDES,
             "line": "Dose Rate: 8,100 µGy (peak), ~1,900 µGy (ave); row unit µGy/day"},
            {"name": "Posner, Richardson and Zeitlin, Solar Physics 300, 102 (2025)", "url": PAPER,
             "line": "The peak dose rate of this event on the Martian surface, 352 μGy/hr, while not negligible, is about two orders of "
                     "magnitude below threshold levels of acute radiation effects."},
        ],
        "fetched_at": readings["fetched_at"],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fetch", action="store_true", help="fetch the readings from CDAWeb first (needs the network)")
    args = p.parse_args()
    if args.fetch:
        if os.environ.get("OFFLINE") == "1":
            sys.exit("OFFLINE=1: not fetching.")
        import requests

        url = request_url(START, STOP)
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=120)
        resp.raise_for_status()
        READINGS.write_text(json.dumps(compact(resp.json(), url, datetime.now(timezone.utc).isoformat(timespec="seconds"))) + "\n")
    event = build(json.loads(READINGS.read_text()))
    EVENT.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copyfile(EVENT, WEB)
    print(f"{event['date']}: {event['dose_ugy_day']} µGy per day, usual {event['baseline_mean']}, spread {event['baseline_sd']}, "
          f"z {event['z']}, fired {event['fired']}; {len(event['daily'])} days; peak {event['peak']}")


if __name__ == "__main__":
    main()
