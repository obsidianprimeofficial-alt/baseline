"""Write web/data/skylab4.json from cache/skylab4/sleep-estimates.csv and print each role's counts.
Reads the cache only; no network."""

import json
from pathlib import Path

from baseline.compute.skylab4 import ROLES, evaluate_sleep, load_nights, role_nights

OUT = Path("web/data/skylab4.json")


def summary() -> dict:
    return {
        "source": "NASA CR-141886, Experiment M133 final report, Tables VIII–X, NTRS 19750019675",
        "source_url": "https://ntrs.nasa.gov/citations/19750019675",
        "nights": load_nights(),
    }


def report() -> None:
    for role in ROLES:
        nights = role_nights(load_nights(), role)
        fired = evaluate_sleep(nights)
        with_value = sum(n["total_sleep_h"] is not None for n in nights)
        watch = [d for d, r in fired.items() if r["status"] == "watch"]
        confirmed = [d for d, r in fired.items() if r["status"] == "confirmed"]
        print(f"{role}: {with_value} nights with a value; watch {len(watch)} {watch}; confirmed {len(confirmed)} {confirmed}")


if __name__ == "__main__":
    OUT.write_text(json.dumps(summary(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    report()
