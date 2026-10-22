"""Write web/data/radiation.json from the cached NOAA GOES proton flux and the cached MSL RAD dose rates.
Reads the caches only; no network."""

import json
from pathlib import Path

from baseline.compute.radiation import (
    CACHE,
    CHANNEL,
    DOSE_COLUMN,
    MSL_CACHE,
    daily_dose,
    load_cached_msl_rad,
    load_cached_protons,
    mars_dose_flag,
    spe_flag,
)

OUT = Path("web/data/radiation.json")


def summary(path: str = CACHE, msl_path: str = MSL_CACHE) -> dict:
    cached = load_cached_protons(path)
    flag = spe_flag(cached["data"])
    out = {
        "channel": CHANNEL,
        "time_tag": flag["time_tag"],
        "satellite": flag["satellite"],
        "flux_pfu": flag["current"],
        "threshold_pfu": flag["threshold_pfu"],
        "fired": flag["fired"],
        "source_url": cached["source_url"],
        "fetched_at": cached["fetched_at"],
    }
    msl = load_cached_msl_rad(msl_path)
    daily = daily_dose(msl["data"])
    dose = mars_dose_flag(daily)
    out["msl_rad"] = {
        "column": DOSE_COLUMN,
        "units": msl["units"],
        "date": dose["date"],
        "dose_ugy_day": round(dose["current"], 1),
        "n_obs": dose["n_obs"],
        "baseline_mean": None if dose["baseline_mean"] is None else round(dose["baseline_mean"], 1),
        "baseline_sd": None if dose["baseline_sd"] is None else round(dose["baseline_sd"], 2),
        "z": None if dose["z"] is None else round(dose["z"], 2),
        "threshold_z": dose["threshold_z"],
        "window_days": dose["window_days"],
        "fired": dose["fired"],
        "daily": [{"date": d["date"], "dose_ugy_day": round(d["dose_ugy_day"], 1), "n_obs": d["n_obs"]} for d in daily],
        "source": msl["source"],
        "source_url": msl["source_url"],
        "doi": msl["doi"],
        "archive_url": msl["archive_url"],
        "fetched_at": msl["fetched_at"],
    }
    return out


def main() -> None:
    s = summary()
    OUT.write_text(json.dumps(s, indent=2) + "\n")
    m = s["msl_rad"]
    print(f"wrote {OUT}: GOES {s['flux_pfu']:.2f} pfu at {s['time_tag']}, fired {s['fired']}; "
          f"MSL RAD {m['dose_ugy_day']} {m['units']} on {m['date']} ({len(m['daily'])} days), fired {m['fired']}")


if __name__ == "__main__":
    main()
