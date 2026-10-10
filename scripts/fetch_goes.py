"""Cache NOAA SWPC GOES integral proton flux (last 7 days) to cache/noaa/."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-7-day.json"
OUT = Path("cache/noaa/integral-protons-7-day.json")


def main() -> None:
    if os.environ.get("OFFLINE") == "1":
        sys.exit(f"OFFLINE=1: not fetching; {OUT} is used as is.")
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source_url": URL, "fetched_at": fetched_at, "data": resp.json()}) + "\n")
    print(f"wrote {OUT} ({len(resp.json())} rows, fetched {fetched_at})")


if __name__ == "__main__":
    main()
