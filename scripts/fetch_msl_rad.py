"""Cache MSL RAD (Curiosity rover) dose rates for the last 30 days to cache/msl_rad/.

Source: NASA SPDF CDAWeb REST API, dataset MSL_RAD_OBS-L2 ("MSL/RAD Level 2 observational
radiation data", PI D. Hassler, SwRI-Boulder; DOI 10.48322/20qb-4e17). It serves the same
RAD_RDR product that the PDS PPI node archives as MSL-M-RAD-3-RDR-V1.0, but as a compact JSON
record of one variable instead of a 68 MB text file per sol.

Usage:
    python scripts/fetch_msl_rad.py              # fetch the last 30 days (needs the network)
    python scripts/fetch_msl_rad.py --days 60
    python scripts/fetch_msl_rad.py --from-file response.json   # convert a saved API response

The cache keeps only the quality-filtered dose-rate variable (DOSIMETRY_TOTAL_f, uGy/day):
three values per observation (Total Dose B, RTG-corrected Dose B, Total Dose E), the observation
time and whether the record is flagged. Observations are ~16 minutes apart (8 minutes when count
rates are high).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://cdaweb.gsfc.nasa.gov/WS/cdasr/1/dataviews/sp_phys/datasets/MSL_RAD_OBS-L2"
VARIABLE = "DOSIMETRY_TOTAL_f"
ARCHIVE_URL = "https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/"
DOI = "10.48322/20qb-4e17"
OUT = Path("cache/msl_rad/dose-rate-30-day.json")
COLUMNS = ("dose_b_total", "dose_b_rtg_corrected", "dose_e_total")
FILL = -1.0e31


def request_url(start: datetime, stop: datetime) -> str:
    fmt = "%Y%m%dT%H%M%SZ"
    return f"{API}/data/{start.strftime(fmt)},{stop.strftime(fmt)}/{VARIABLE}?format=json"


def compact(response: dict, source_url: str, fetched_at: str) -> dict:
    """Turn the CDAWeb JSON (one CDF, variables EPOCH / DOSIMETRY_TOTAL_f / FLAGGED_DATA) into our cache record."""
    cdf = response["CDF"][0]
    variables = {v["name"]: v for v in cdf["cdfVariables"]["variable"]}
    attrs = {a["name"]: [e.get("value") for e in a["entry"]] for a in cdf["cdfGAttributes"]["attribute"]}
    units = next(
        (e["value"] for a in variables[VARIABLE]["cdfVAttributes"]["attribute"] if a["name"] == "UNITS" for e in a["entry"]),
        "",
    )
    if not units.startswith("uGray/day"):
        sys.exit(f"unexpected units {units!r}; the cache format assumes uGy/day")

    epochs = [r["value"][0] for r in variables["EPOCH"]["cdfVarData"]["record"]]
    doses = [r["value"][0] for r in variables[VARIABLE]["cdfVarData"]["record"]]
    flags = [r["value"][0] for r in variables["FLAGGED_DATA"]["cdfVarData"]["record"]]
    if not len(epochs) == len(doses) == len(flags):
        sys.exit("EPOCH, dose and flag records differ in length")

    rows = []
    for epoch, dose, flag in zip(epochs, doses, flags):
        values = [float(x) for x in dose.split()]
        if len(values) != 3:
            sys.exit(f"expected 3 dose values per record, got {dose!r}")
        row = {"time_tag": epoch[:19] + "Z"}  # 2026-09-20T00:15:08.000000000Z -> 2026-09-20T00:15:08Z
        for name, value in zip(COLUMNS, values):
            row[name] = None if value <= FILL else round(value, 3)
        row["flagged"] = flag.strip() != ""
        rows.append(row)

    return {
        "source": "NASA SPDF CDAWeb, dataset MSL_RAD_OBS-L2: MSL/RAD Level 2 observational radiation data (D. Hassler, SwRI-Boulder)",
        "source_url": source_url,
        "doi": DOI,
        "archive_url": ARCHIVE_URL,
        "product": attrs.get("Standard_data_product_id", ["RAD_RDR"])[0],
        "rdr_version": attrs.get("Rdr_version", ["unknown"])[0],
        "variable": VARIABLE,
        "units": "uGy/day",
        "columns": list(COLUMNS),
        "column_labels": ["Total Dose B (silicon)", "RTG-corrected Dose B (silicon)", "Total Dose E (tissue-equivalent plastic)"],
        "cadence_note": attrs.get("Time_resolution", [""])[0],
        "fetched_at": fetched_at,
        "data": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--from-file", help="a saved CDAWeb JSON response; no network")
    p.add_argument("--fetched-at", help="ISO time to record when using --from-file (default: now)")
    args = p.parse_args()

    now = datetime.now(timezone.utc)
    stop = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = stop - timedelta(days=args.days)
    url = request_url(start, stop)

    if args.from_file:
        response = json.loads(Path(args.from_file).read_text())
        fetched_at = args.fetched_at or now.isoformat(timespec="seconds")
        url = response.get("_request_url", url)
    else:
        if os.environ.get("OFFLINE") == "1":
            sys.exit(f"OFFLINE=1: not fetching; {OUT} is used as is.")
        import requests

        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=120)
        resp.raise_for_status()
        response = resp.json()
        fetched_at = now.isoformat(timespec="seconds")

    record = compact(response, url, fetched_at)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record) + "\n")
    good = sum(1 for r in record["data"] if not r["flagged"])
    print(f"wrote {OUT} ({len(record['data'])} observations, {good} unflagged, "
          f"{record['data'][0]['time_tag']} to {record['data'][-1]['time_tag']}, fetched {fetched_at})")


if __name__ == "__main__":
    main()
