"""Show the maths (design B2): the histogram view uses the same numbers as the evidence card, counts every
history day once, draws the 2-SD lines at mean ± 2 SD, and every line passes the wording check."""

import json
import re
import shutil
import subprocess
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from baseline.compute.wording import blocks_diagnostic

NODE = shutil.which("node")
FIXTURE = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
SPEC = {  # name, unit, decimals and chart step as on the page (web/app.js SIGNALS)
    "hrv_rmssd_ms": ("Heart rate variability", "ms", 1, 10), "sleep_hours": ("Sleep", "hours", 1, 1),
    "reaction_ms": ("Reaction time", "ms", 0, 50), "mood_1to5": ("Mood", "of 5", 1, 2),
    "heart_rate_bpm": ("Heart rate", "beats a minute", 0, 10), "spo2_pct": ("Blood oxygen", "percent", 1, 2),
    "core_temp_c": ("Core temperature", "°C", 2, 0.25),
}
JS = """
const R = require('./web/rules.js'), M = require('./web/maths.js');
const { cases, spec } = JSON.parse(require('fs').readFileSync(0, 'utf8'));
console.log(JSON.stringify(cases.map((rows) => {
  const day = rows.at(-1).day, flags = R.evaluate(rows)[day] || [];
  return flags.filter((f) => f.signal).map((f) => {
    const [name, unit, dp, step] = spec[f.signal], v = M.view(rows, f.signal, { name, unit, dp, step });
    return { flag: f, view: v, lines: M.lines(v, { name, unit, dp, step }) };
  });
})));
"""


def demo(day: int) -> list[dict]:
    """The demo run: recorded day-29 reaction (the fixture value), sleep 5, mood 4; day 30 from the record."""
    rows = [dict(r) for r in FIXTURE if r["day"] <= day]
    rows[28].update(sleep_hours=5, mood_1to5=4)
    return rows


def run(cases: list[list[dict]]) -> list[list[dict]]:
    out = subprocess.run([NODE, "-e", JS], input=json.dumps({"cases": cases, "spec": SPEC}),
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


@pytest.fixture(scope="module")
def views():
    if NODE is None:
        pytest.skip("node is not installed")
    day29, day30 = run([demo(29), demo(30)])
    return {29: day29, 30: day30}


def test_demo_flags_are_the_ones_the_view_covers(views):
    assert sorted(v["flag"]["signal"] for v in views[29]) == ["hrv_rmssd_ms", "reaction_ms", "sleep_hours"]
    assert [(v["flag"]["signal"], v["flag"]["status"]) for v in views[30]] == [("mood_1to5", "watch")]


def test_view_numbers_equal_the_evidence_card(views):
    for v in views[29] + views[30]:
        f, m = v["flag"], v["view"]
        assert (m["mean"], m["sd"], m["z"], m["today"], m["n"]) == (f["baseline_mean"], f["baseline_sd"], f["z"], f["current"], f["window_days"])
        card_z = f"{abs(f['z']):.1f}".removesuffix(".0")  # the card's "How far" value, without the ×
        assert f" = {card_z} spreads " in v["lines"]["sum"]


def test_reaction_day_29_matches_the_design_numbers(views):
    m = next(v for v in views[29] if v["flag"]["signal"] == "reaction_ms")
    assert (m["view"]["first"], m["view"]["last"], m["view"]["n"]) == (1, 28, 28)
    assert (round(m["view"]["mean"], 2), round(m["view"]["sd"], 2)) == (281.43, 16.33)
    assert m["lines"]["sum"] == "Today is (338.3 − 281.4) ÷ 16.3 = 3.5 spreads above your usual."


def test_histogram_counts_every_history_day_and_lines_sit_at_two_sd(views):
    for v in views[29] + views[30]:
        m, b = v["view"], v["view"]["bins"]
        assert sum(b["counts"]) == m["n"] and len(b["counts"]) == 10
        assert m["low"] == pytest.approx(m["mean"] - 2 * m["sd"]) and m["high"] == pytest.approx(m["mean"] + 2 * m["sd"])
        assert b["lo"] <= min(m["low"], m["today"]) and b["hi"] >= max(m["high"], m["today"])


def test_every_maths_line_passes_the_wording_check(views):
    for v in views[29] + views[30]:
        for line in v["lines"].values():
            assert not blocks_diagnostic(line), line


def test_the_written_sum_reproduces_the_shown_z(views):
    """Today, usual and spread are shown with as many decimals as the sum needs, so the sum on screen works out."""
    for v in views[29] + views[30]:
        m = re.fullmatch(r"Today is \((\S+) − (\S+)\) ÷ (\S+) = (\S+) spreads (above|below) your usual\.", v["lines"]["sum"])
        assert m, v["lines"]["sum"]
        a, b, s, z = (Decimal(x) for x in m.groups()[:4])
        assert ((a - b) / s).quantize(Decimal("0.1"), ROUND_HALF_UP) == z.quantize(Decimal("0.1")), v["lines"]["sum"]
