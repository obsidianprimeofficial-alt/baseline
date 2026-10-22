import json
from pathlib import Path

import pytest

from baseline.compute.radiation import (
    MIN_HISTORY_DAYS,
    MIN_OBS_PER_DAY,
    MSL_CACHE,
    daily_dose,
    load_cached_msl_rad,
    mars_dose_flag,
    spe_flag,
)


def row(t, flux, energy=">=10 MeV"):
    return {"time_tag": f"2026-09-30T{t}:00Z", "satellite": 18, "flux": flux, "energy": energy}


def test_fires_at_s1_threshold():
    r = spe_flag([row("09:00", 1.0), row("09:05", 10.0)])
    assert r["rule"] == "solar_particle_event"
    assert r["fired"] and r["current"] == 10.0 and r["time_tag"] == "2026-09-30T09:05:00Z"


def test_below_threshold_does_not_fire():
    assert not spe_flag([row("09:00", 9.99)])["fired"]


def test_uses_latest_value_not_max():
    assert not spe_flag([row("09:10", 1.0), row("09:00", 50.0)])["fired"]


def test_ignores_other_channels():
    assert not spe_flag([row("09:00", 0.3), row("09:05", 100.0, ">=1 MeV")])["fired"]


def test_missing_channel_raises():
    with pytest.raises(ValueError):
        spe_flag([row("09:00", 100.0, ">=1 MeV")])


# ---------- MSL RAD ----------

def obs(day, i, dose, flagged=False):
    """One RAD observation: day is a UTC date, i the observation index (16-minute steps)."""
    return {
        "time_tag": f"{day}T{(i * 16) // 60:02d}:{(i * 16) % 60:02d}:00Z",
        "dose_b_total": None if flagged else dose,
        "dose_b_rtg_corrected": None if flagged else dose * 0.7,
        "dose_e_total": None if flagged else dose,
        "flagged": flagged,
    }


def day_of(day, dose, n=MIN_OBS_PER_DAY):
    return [obs(day, i, dose) for i in range(n)]


def test_daily_dose_averages_unflagged_observations_per_utc_day():
    rows = day_of("2026-10-01", 180.0) + [obs("2026-10-01", 50, 190.0), obs("2026-10-01", 51, 9999.0, flagged=True)]
    rows += [obs("2026-10-02", 0, 200.0)]  # partial day: one observation
    daily = daily_dose(rows)
    assert [d["date"] for d in daily] == ["2026-10-01"], "partial days are left out"
    assert daily[0]["n_obs"] == MIN_OBS_PER_DAY + 1
    assert daily[0]["dose_ugy_day"] == pytest.approx((180.0 * MIN_OBS_PER_DAY + 190.0) / (MIN_OBS_PER_DAY + 1))


def test_mars_dose_flag_fires_two_sd_above_earlier_days():
    history = [180.0, 182.0, 181.0, 183.0, 180.0, 182.0, 181.0, 183.0, 180.0, 182.0, 181.0, 183.0, 180.0, 182.0]
    assert len(history) == MIN_HISTORY_DAYS
    daily = [{"date": f"2026-10-{i + 1:02d}", "dose_ugy_day": v, "n_obs": 80} for i, v in enumerate(history)]
    quiet = mars_dose_flag(daily + [{"date": "2026-10-15", "dose_ugy_day": 183.0, "n_obs": 80}])
    assert quiet["rule"] == "mars_dose_above_30_day_mean" and quiet["window_days"] == MIN_HISTORY_DAYS
    assert not quiet["fired"] and quiet["z"] < 2.0
    storm = mars_dose_flag(daily + [{"date": "2026-10-15", "dose_ugy_day": 260.0, "n_obs": 80}])
    assert storm["fired"] and storm["z"] > 2.0 and storm["current"] == 260.0
    assert storm["baseline_mean"] == pytest.approx(sum(history) / len(history))


def test_mars_dose_flag_needs_history():
    short = [{"date": f"2026-10-{i + 1:02d}", "dose_ugy_day": 180.0, "n_obs": 80} for i in range(MIN_HISTORY_DAYS)]
    r = mars_dose_flag(short)  # 13 earlier days, not enough
    assert not r["fired"] and r["z"] is None and r["baseline_mean"] is None and r["window_days"] == MIN_HISTORY_DAYS - 1
    with pytest.raises(ValueError):
        mars_dose_flag([])


def test_cached_msl_rad_is_real_and_covers_a_month():
    """The cache is the real NASA record, with its source and a month of complete days behind the flag."""
    cached = load_cached_msl_rad()
    assert cached["units"] == "uGy/day" and cached["doi"] == "10.48322/20qb-4e17"
    assert cached["source_url"].startswith("https://cdaweb.gsfc.nasa.gov/") and cached["archive_url"].startswith("https://pds-ppi.igpp.ucla.edu/")
    daily = daily_dose(cached["data"])
    assert len(daily) >= MIN_HISTORY_DAYS + 1
    flag = mars_dose_flag(daily)
    assert flag["window_days"] >= MIN_HISTORY_DAYS and 0 < flag["current"] < 100000  # within the dataset's VALIDMAX
    assert Path(MSL_CACHE).stat().st_size < 1_000_000, "keep the cache small enough for the public repository"
    assert json.loads(Path(MSL_CACHE).read_text())["data"], "cache must hold the observations"
