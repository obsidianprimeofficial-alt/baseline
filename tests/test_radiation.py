import pytest

from baseline.compute.radiation import spe_flag


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
