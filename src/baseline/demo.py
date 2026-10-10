"""Print the flags for the simulated demo fixtures."""

import json
from pathlib import Path

from baseline.compute.rules import evaluate


def line(day: int, r: dict) -> str:
    if "z" in r:
        return (
            f"day {day}: {r['rule']}  current {r['current']}  "
            f"baseline mean {r['baseline_mean']:.2f}  z {r['z']:.2f}"
        )
    return f"day {day}: {r['rule']}  signals {', '.join(r['signals'])}"


def split(path: str) -> tuple[list[str], list[str]]:
    """(confirmed flag lines, watch note lines)."""
    rows = json.loads(Path(path).read_text())["rows"]
    confirmed, watch = [], []
    for day, results in evaluate(rows).items():
        for r in results:
            (confirmed if r["status"] == "confirmed" else watch).append(line(day, r))
    return confirmed, watch


def main() -> None:
    print("Simulated telemetry, crew_a_anomaly.json")
    confirmed, watch = split("data/fixtures/crew_a_anomaly.json")
    print("\n".join(confirmed))
    for w in watch:
        print(f"  (watch) {w}")
    confirmed, watch = split("data/fixtures/crew_a_clean.json")
    print(f"clean fixture: {len(watch)} watch items, {len(confirmed)} confirmed flags")
    print("\n".join(confirmed + [f"  (watch) {w}" for w in watch]))


if __name__ == "__main__":
    main()
