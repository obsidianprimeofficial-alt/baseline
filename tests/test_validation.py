import subprocess
import sys
from pathlib import Path

from baseline.compute.rules import DIRECTIONS, evaluate
from baseline.compute.wording import blocks_diagnostic
from baseline.validation import SIZES, make_clean, make_planted, render_markdown, run, single_signal_status

REPO = Path(__file__).resolve().parents[1]


def _evaluate_signal_status(rows, signal):
    """Per-day status for one signal as produced by the full evaluate()."""
    return {
        day: r["status"]
        for day, rs in evaluate(rows).items()
        for r in rs
        if r.get("signal") == signal and r["fired"]
    }


def test_single_signal_status_matches_evaluate():
    # The fast per-signal scan must agree with the full rule exactly, on clean and planted fixtures.
    for seed in range(1, 31):
        for signal in DIRECTIONS:
            clean = make_clean(seed)
            assert single_signal_status(clean, signal) == _evaluate_signal_status(clean, signal)
            for size in SIZES:
                rows = make_planted(seed, signal, size, start_day=20)
                assert single_signal_status(rows, signal) == _evaluate_signal_status(rows, signal)


def test_same_seed_gives_identical_results():
    assert run(n=10, seed0=1000) == run(n=10, seed0=1000)


def test_4sd_shift_confirmed_in_at_least_95_percent():
    # If this fails, the rules miss a 4-SD shift: stop and report, do not change the rules.
    r = run(n=50, seed0=1000)
    worst = min(r["detection"][s][4.0]["confirmed_rate"] for s in DIRECTIONS)
    assert worst >= 0.95, f"worst 4-SD confirmed rate {worst:.2%}"


def test_clean_false_flags_match_rules_comment():
    # rules.py: ~0.64 confirmed flags per clean 30-day fixture, seeds 1-50.
    r = run(n=50, seed0=1)
    assert abs(r["false_flags"]["mean_confirmed"] - 0.64) <= 0.15


def test_markdown_passes_wording_check():
    assert blocks_diagnostic(render_markdown(run(n=10, seed0=1000))) == []


def test_validate_script_runs_and_writes(tmp_path):
    (tmp_path / "docs").mkdir()
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "validate.py"), "--n", "10"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = (tmp_path / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    assert "Validation (simulated data)" in out
    assert blocks_diagnostic(out) == []
