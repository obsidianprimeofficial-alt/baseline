"""Trend projection card: Python reference (src/baseline/compute/trend.py) and its web port agree,
the 23 Oct design numbers are reproduced, and every card line passes the wording check."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.rules import DIRECTIONS
from baseline.compute.trend import projection, projections, slope
from baseline.compute.wording import blocks_diagnostic
from baseline.validation import SIGNALS, make_clean, make_planted

NODE = shutil.which("node")
FIXTURE = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
SPEC = {  # unit and decimals as on the page (web/app.js SIGNALS)
    "hrv_rmssd_ms": ("ms", 1), "sleep_hours": ("hours", 1), "reaction_ms": ("ms", 0), "mood_1to5": ("of 5", 1),
    "heart_rate_bpm": ("beats a minute", 0), "spo2_pct": ("percent", 1), "core_temp_c": ("°C", 2),
}


def demo(day: int) -> list[dict]:
    """The demo run: recorded day-29 reaction (the fixture value), sleep 5, mood 4; day 30 from the record."""
    rows = [dict(r) for r in FIXTURE if r["day"] <= day]
    rows[28].update(sleep_hours=5, mood_1to5=4)
    return rows


def cases() -> list[list[dict]]:
    """The demo and fixture days 29 and 30, and every day 17..30 of planted fixtures for seeds 1-30."""
    out = [demo(29), demo(30), [r for r in FIXTURE if r["day"] <= 29], FIXTURE]
    for seed in range(1, 31):
        rows = make_planted(seed, SIGNALS[seed % len(SIGNALS)], 3.0, 15 + seed % 12, length=4)
        out += [rows[:end] for end in range(17, 31)]
    return out


def test_reaction_day_29_reproduces_the_design_numbers():
    """docs/DESIGN_BRIEF.md B1 (23 Oct): 339.11, 316.28, 338.34 ms; −0.385 ms per day; −0.11 percent; top 314.10."""
    p = projection(demo(29), "reaction_ms")
    assert p["values"] == [339.11, 316.28, 338.34]
    assert round(p["slope"], 3) == -0.385 == round((338.34 - 339.11) / 2, 3)
    assert round(p["percent_per_day"], 2) == -0.11
    assert round(p["edge"], 2) == 314.10
    assert p["toward"] and p["days_back"] == 63  # (338.34 − 314.10) / 0.385 = 62.96, so day 63 is the first inside


def test_demo_cards_on_day_29_and_none_on_day_30():
    assert sorted(projections(demo(29))) == ["hrv_rmssd_ms", "reaction_ms", "sleep_hours"]
    assert projections(demo(30)) == {}


def test_no_card_unless_outside_on_all_3_days():
    rows = demo(29)
    assert projection(rows, "heart_rate_bpm") is None  # outside on day 23 only
    assert projection(rows, "mood_1to5") is None  # days 27 and 28, not 29 (mood 4 today)
    assert projection(rows[:-1] + [{**rows[-1], "day": 30}], "reaction_ms") is None  # a gap breaks the 3 days
    assert projection(rows[:2], "reaction_ms") is None


def with_last3(signal: str, values: list[float]) -> list[dict]:
    rows = make_clean(7)
    for r, v in zip(rows[-3:], values):
        r[signal] = v
    return rows


@pytest.mark.parametrize("signal, values, toward", [
    ("reaction_ms", [420.0, 410.0, 400.0], True),   # high signal moving down: toward
    ("reaction_ms", [400.0, 410.0, 420.0], False),  # moving up: away
    ("reaction_ms", [410.0, 410.0, 410.0], False),  # level
    ("sleep_hours", [2.0, 2.5, 3.0], True),         # low signal moving up: toward
    ("sleep_hours", [3.0, 2.5, 2.0], False),
])
def test_toward_away_and_level(signal, values, toward):
    p = projection(with_last3(signal, values), signal)
    assert p is not None and p["toward"] is toward
    assert p["slope"] == pytest.approx((values[2] - values[0]) / 2) == pytest.approx(slope([28, 29, 30], values))
    if toward:
        n = p["days_back"]
        inside = lambda v: v < p["edge"] if DIRECTIONS[signal] == "high" else v > p["edge"]
        assert inside(values[2] + n * p["slope"]) and not inside(values[2] + (n - 1) * p["slope"])
    else:
        assert p["days_back"] is None


JS = """
const R = require('./web/rules.js'), P = require('./web/projection.js');
const { cases, spec } = JSON.parse(require('fs').readFileSync(0, 'utf8'));
console.log(JSON.stringify(cases.map((rows) => {
  const flags = R.evaluate(rows), out = {};
  for (const s of Object.keys(R.DIRECTIONS)) {
    const p = P.projection(rows, s, flags);
    if (p) out[s] = { ...p, lines: P.lines(p, { unit: spec[s][0], dp: spec[s][1] }) };
  }
  return out;
})));
"""


def round_card(p: dict) -> dict:
    return {k: round(p[k], 9) for k in ("slope", "percent_per_day", "edge")} | {k: p[k] for k in ("days", "values", "toward", "days_back")}


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_js_projection_matches_python_and_every_line_passes_the_wording_check():
    all_cases = cases()
    run = subprocess.run([NODE, "-e", JS], input=json.dumps({"cases": all_cases, "spec": SPEC}), capture_output=True, text=True, encoding="utf-8", check=True)
    js = json.loads(run.stdout)
    branches = set()
    for rows, got in zip(all_cases, js):
        want = projections(rows)
        assert sorted(got) == sorted(want)
        for s, p in want.items():
            assert round_card(got[s]) == round_card(p), s
            assert all(not blocks_diagnostic(line) for line in got[s]["lines"]), got[s]["lines"]
            assert not any(w in line.lower() for line in got[s]["lines"] for w in ("flat", "rising", "falling"))
        branches |= {("toward" if p["toward"] else "away", (p["days_back"] or 0) > 30) for p in want.values()}
    assert branches == {("toward", False), ("toward", True), ("away", False)}, "the cases must reach every outlook line"
    day29 = js[0]["reaction_ms"]["lines"]
    assert day29 == [
        "Three days outside your usual range: 339, 316, 338 ms. Changing −0.1 percent per day. "
        "If nothing changes, it is not back inside your usual range within 30 days.",
        "Projection from your own last 3 days, not a forecast.",
    ]
