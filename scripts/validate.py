"""Run the validation harness, print a short summary, write docs/VALIDATION.md.

    python scripts/validate.py --n 200 --seed 1000
"""

import argparse
from pathlib import Path

from baseline.validation import SHORT, SIGNALS, SIZES, render_markdown, run

OUT = Path("docs/VALIDATION.md")


def summary(results: dict) -> str:
    ff = results["false_flags"]
    ts = results["two_signal"]
    worst4 = min(results["detection"][s][4.0]["confirmed_rate"] for s in SIGNALS)
    lines = [
        f"n={results['n']} seeds {results['seed0']}..{results['seed0'] + results['n'] - 1}",
        f"detection (confirmed) at 4 SD, worst signal: {100 * worst4:.1f}%",
        f"mean confirmed false flags per clean 30-day fixture: {ff['mean_confirmed']:.2f} "
        f"(zero-confirmed {100 * ff['zero_confirmed_share']:.1f}%)",
        f"two-signal rule: fires on pairs {100 * ts['detection_rate']:.1f}%, "
        f"false fire on clean {100 * ts['false_fire_rate']:.1f}%",
        "detection at 3 SD (confirmed): "
        + ", ".join(f"{SHORT[s]} {100 * results['detection'][s][3.0]['confirmed_rate']:.0f}%" for s in SIGNALS),
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Validation harness for the detection rules.")
    p.add_argument("--n", type=int, default=200, help="fixtures per case")
    p.add_argument("--seed", type=int, default=1000, help="first seed")
    args = p.parse_args()

    results = run(n=args.n, seed0=args.seed)
    print(summary(results))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_markdown(results) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
