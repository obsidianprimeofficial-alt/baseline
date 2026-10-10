"""Write web/data/radiation.json from the cached NOAA GOES proton flux. Reads the cache only; no network."""

import json
from pathlib import Path

from baseline.compute.radiation import CACHE, CHANNEL, load_cached_protons, spe_flag

OUT = Path("web/data/radiation.json")


def summary(path: str = CACHE) -> dict:
    cached = load_cached_protons(path)
    flag = spe_flag(cached["data"])
    return {
        "channel": CHANNEL,
        "time_tag": flag["time_tag"],
        "satellite": flag["satellite"],
        "flux_pfu": flag["current"],
        "threshold_pfu": flag["threshold_pfu"],
        "fired": flag["fired"],
        "source_url": cached["source_url"],
        "fetched_at": cached["fetched_at"],
    }


def main() -> None:
    s = summary()
    OUT.write_text(json.dumps(s, indent=2) + "\n")
    print(f"wrote {OUT}: {s['flux_pfu']:.2f} pfu at {s['time_tag']}, fired {s['fired']}")


if __name__ == "__main__":
    main()
