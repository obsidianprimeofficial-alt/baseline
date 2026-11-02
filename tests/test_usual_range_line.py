"""PLAN A7: one line under the usual value and spread on each single-signal evidence card, saying how they are
computed. The sentence must stay true of the rule, so the rule's own numbers are checked here too."""

import json
import statistics
from pathlib import Path

from baseline.compute.rules import evaluate
from baseline.compute.wording import blocks_diagnostic
from tests.test_marks import run, pytestmark  # noqa: F401  # the same stand-in page; skipped without node

LINE = "Usual range uses your earlier days in this record, including days that were flagged."


def test_line_is_under_the_usual_spread_on_every_single_signal_card_and_not_on_the_48_hour_card():
    out = run("""
const p = await page(mem()); p.check();
const read = (s) => { p.card(s); return p.$('ev-numbers').children.map((c) => c.textContent); };
const day29 = Object.fromEntries(p.run('flagsFor(state.day).map((r) => r.signal || "")').map((s) => [s, read(s)]));
p.nextDay();
return { day29, mood: read('mood_1to5'), errors: p.errors };
""")
    cards = {**out["day29"], "mood on day 30": out["mood"]}
    assert sorted(cards) == ["", "hrv_rmssd_ms", "mood on day 30", "reaction_ms", "sleep_hours"]
    for name, children in cards.items():
        if name == "":
            assert LINE not in children, "the 48-hour row has no usual value"
            continue
        assert children.count(LINE) == 1, name
        at = children.index(LINE)
        assert children[at - 2] == "Usual spread (1 SD)", name
        assert children[at + 1] == "How far", name
    assert out["errors"] == []


def test_the_line_is_true_of_the_rule_today_left_out_and_flagged_days_counted():
    """Day 29 of the demo: days 27 and 28 were flagged for reaction time and are in its usual value and spread."""
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    rows = [dict(r, **({"sleep_hours": 5.0, "mood_1to5": 4} if r["day"] == 29 else {})) for r in rows if r["day"] <= 29]
    flags = evaluate(rows)
    r = next(x for x in flags[29] if x.get("signal") == "reaction_ms")
    earlier = [x["reaction_ms"] for x in rows if x["day"] < 29]
    assert {27, 28} <= {d for d, rs in flags.items() if any(x.get("signal") == "reaction_ms" for x in rs)}
    assert r["window_days"] == len(earlier) == 28
    assert r["baseline_mean"] == statistics.mean(earlier)
    assert r["baseline_sd"] == statistics.stdev(earlier)


def test_the_line_passes_the_wording_check():
    assert blocks_diagnostic(LINE) == []
    assert f'const USUAL_NOTE = "{LINE}";' in Path("web/app.js").read_text(encoding="utf-8")
