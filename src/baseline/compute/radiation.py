"""Solar particle event flag from cached NOAA GOES integral proton flux. Pure Python, no network."""

import json
from collections.abc import Sequence
from pathlib import Path

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
