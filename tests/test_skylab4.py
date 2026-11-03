"""PLAN R1 build: "Real crew record: Skylab 4". The app's own sleep rule on each crewman's own morning estimate (cache/skylab4).
Loader in src/baseline/compute/skylab4.py, same rule and same words for the page in web/skylab4.js. Roles only, no other column."""

import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.rules import CONFIRM_Z, MIN_HISTORY_DAYS
from baseline.compute.skylab4 import ROLES, evaluate_sleep, load_nights, parse_total, role_nights
from baseline.compute.wording import blocks_diagnostic

NODE = shutil.which("node")
FOUR = {"role", "mission_day", "total_sleep_h", "approximate"}
EXPECTED = {
    "CDR": {"with_value": 84, "watch": [30, 48], "confirmed": [32, 84]},
    "PLT": {"with_value": 84, "watch": [], "confirmed": [32, 84]},
    "SPT": {"with_value": 83, "watch": [32], "confirmed": [48]},
}
HEADER = "role,mission_day,total_sleep_h,light_h,heavy_h,note\n"


def night(day: int, value: float | None) -> dict:
    return {"role": "CDR", "mission_day": day, "total_sleep_h": value, "approximate": False}


def steady(days: int) -> list[dict]:
    """Nights 1 to days, 7 and 8 in turn."""
    return [night(d, 7.0 + d % 2) for d in range(1, days + 1)]


def panel_html() -> str:
    html = Path("web/index.html").read_text(encoding="utf-8")
    start = html.index('<details id="skylab"')
    return html[start:html.index("</details>", start)]


def run_js(nights: list[dict]) -> dict:
    code = (
        "const S = require('./web/skylab4.js');"
        "const nights = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "const s = S.series(nights);"
        "console.log(JSON.stringify({flags: S.evaluateSleep(nights), counts: S.countsLine(nights), notes: S.notes(nights), shown: s.shown}))"
    )
    return json.loads(subprocess.run([NODE, "-e", code], input=json.dumps(nights), capture_output=True, text=True, encoding="utf-8", check=True).stdout)


def test_loader_handles_numbers_approximate_question_marks_and_blanks():
    assert parse_total("6.5") == (6.5, False)
    assert parse_total("≈3.0") == (3.0, True)
    assert parse_total("?") == (None, False)
    assert parse_total("") == (None, False)
    with pytest.raises(ValueError):
        parse_total("about 3")


def test_loader_on_the_real_file_keeps_the_printed_rows_as_they_are(tmp_path):
    nights = load_nights()
    by = {(n["role"], n["mission_day"]): n for n in nights}
    assert len(nights) == 252
    assert by["PLT", 84] == {"role": "PLT", "mission_day": 84, "total_sleep_h": 3.0, "approximate": True}
    assert by["SPT", 84]["total_sleep_h"] is None and not by["SPT", 84]["approximate"]
    assert by["CDR", 84]["total_sleep_h"] == 5.0
    assert [k for k, n in by.items() if n["approximate"]] == [("PLT", 84)]
    assert [k for k, n in by.items() if n["total_sleep_h"] is None] == [("SPT", 84)]
    blank = tmp_path / "blank.csv"
    blank.write_text(HEADER + "CDR,1,,,,\nCDR,2,?,?,?,\nCDR,3,≈4,,,\nCDR,4,7,3,4,\n", encoding="utf-8")
    assert [(n["total_sleep_h"], n["approximate"]) for n in load_nights(str(blank))] == [(None, False), (None, False), (4.0, True), (7.0, False)]


def test_no_column_beyond_the_four_is_loaded_and_the_others_do_not_matter(tmp_path):
    """Three columns read, plus the approximate mark made from the printed total. Nothing else reaches the rule, the file or the page."""
    assert all(set(n) == FOUR for n in load_nights())
    assert all(set(n) == FOUR for n in json.loads(Path("web/data/skylab4.json").read_text(encoding="utf-8"))["nights"])
    extra = tmp_path / "extra.csv"
    extra.write_text("role,mission_day,total_sleep_h,light_h,heavy_h,note,other\nCDR,1,5,bad,bad,bad,bad\n", encoding="utf-8")
    assert load_nights(str(extra)) == [{"role": "CDR", "mission_day": 1, "total_sleep_h": 5.0, "approximate": False}]
    for path in ("src/baseline/compute/skylab4.py", "web/skylab4.js", "scripts/build_skylab4_summary.py", "web/app.js"):
        assert not re.search(r"light_h|heavy_h|\bnote\b.*skylab", Path(path).read_text(encoding="utf-8")), path


@pytest.mark.parametrize("role", ROLES)
def test_rule_gives_the_counts_in_the_report(role):
    nights = role_nights(load_nights(), role)
    fired = evaluate_sleep(nights)
    want = EXPECTED[role]
    assert sum(n["total_sleep_h"] is not None for n in nights) == want["with_value"]
    assert [d for d, r in fired.items() if r["status"] == "watch"] == want["watch"]
    assert [d for d, r in fired.items() if r["status"] == "confirmed"] == want["confirmed"]
    assert all(MIN_HISTORY_DAYS < d for d in fired)


def test_rule_is_the_apps_rule_first_flag_needs_14_nights_window_30_and_confirm_at_3():
    assert MIN_HISTORY_DAYS == 14 and CONFIRM_Z == 3.0
    assert evaluate_sleep(steady(13) + [night(14, 0.0)]) == {}, "13 nights of history are too few"
    fifteenth = evaluate_sleep(steady(14) + [night(15, 0.0)])[15]
    assert fifteenth["window_days"] == 14 and fifteenth["status"] == "confirmed" and fifteenth["rule"] == "sleep_below_personal_baseline"
    long = evaluate_sleep(steady(40) + [night(41, 0.0)])[41]
    assert long["window_days"] == 30
    high = evaluate_sleep(steady(30) + [night(31, 20.0)])
    assert high == {}, "sleep flags on the low side only"


def test_missing_nights_are_never_filled_never_history_and_never_flagged():
    nights = steady(20)
    nights[17]["total_sleep_h"] = None  # night 18
    nights[19]["total_sleep_h"] = 0.0  # night 20
    fired = evaluate_sleep(nights)
    assert 18 not in fired
    assert fired[20]["window_days"] == 18, "19 nights before night 20, one of them missing"
    without = [n for n in nights if n["total_sleep_h"] is not None]
    assert fired == evaluate_sleep(without)


def test_a_missing_night_breaks_a_run_as_a_gap_does_in_the_rule():
    fired = evaluate_sleep(steady(20) + [night(21, 6.2), night(22, None), night(23, 6.0)])
    assert fired[21]["status"] == "watch" and fired[23]["status"] == "watch"
    next_night = evaluate_sleep(steady(20) + [night(21, 6.2), night(22, 6.0)])
    assert next_night[22]["status"] == "confirmed", "two nights in a row confirm"


def test_web_data_matches_the_cache():
    fresh = runpy.run_path("scripts/build_skylab4_summary.py")["summary"]()
    assert json.loads(Path("web/data/skylab4.json").read_text(encoding="utf-8")) == fresh, "run scripts/build_skylab4_summary.py"


def same_flags(nights: list[dict], js: dict) -> None:
    py = evaluate_sleep(nights)
    assert sorted(map(int, js)) == sorted(py)
    for day, r in py.items():
        got = js[str(day)][0]
        assert (got["rule"], got["status"], got["window_days"]) == (r["rule"], r["status"], r["window_days"])
        for key in ("z", "baseline_mean", "baseline_sd"):
            assert got[key] == pytest.approx(r[key], abs=1e-9)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("role", ROLES)
def test_web_flags_equal_python_flags_for_each_role(role):
    nights = role_nights(load_nights(), role)
    same_flags(nights, run_js(nights)["flags"])


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_web_flags_equal_python_flags_with_a_missing_night_in_the_middle():
    nights = steady(20) + [night(21, 6.2), night(22, None), night(23, 6.0), night(24, 6.0), night(25, 0.0)]
    js = run_js(nights)
    same_flags(nights, js["flags"])
    assert js["shown"]["vals"][21] is None and js["shown"]["marks"][21] is None and js["shown"]["band"][21] is None
    assert js["shown"]["days"] == list(range(1, 26))


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_chart_and_words_for_each_role():
    """84 nights on every chart; band and marks from trend.js; the printed value in words; the counts in one line."""
    all_nights = load_nights()
    out = {role: run_js(role_nights(all_nights, role)) for role in ROLES}
    for role, js in out.items():
        shown = js["shown"]
        assert shown["days"] == list(range(1, 85))
        assert shown["band"][13] is None and shown["band"][14] is not None
        assert [d for d, m in zip(shown["days"], shown["marks"]) if m] == sorted(EXPECTED[role]["watch"] + EXPECTED[role]["confirmed"])
    assert out["CDR"]["counts"] == "84 of 84 nights with a value · 2 watching (days 30, 48) · 2 flagged (days 32, 84)."
    assert out["PLT"]["counts"] == "84 of 84 nights with a value · 0 watching · 2 flagged (days 32, 84)."
    assert out["SPT"]["counts"] == "83 of 84 nights with a value · 1 watching (day 32) · 1 flagged (day 48)."
    assert out["CDR"]["notes"] == ""
    assert out["PLT"]["notes"] == "Day 84: printed ≈3.0."
    assert out["SPT"]["notes"] == "Day 84: no value printed, left out."
    assert out["SPT"]["shown"]["vals"][83] is None
    for js in out.values():
        assert blocks_diagnostic(js["counts"] + " " + js["notes"]) == []


def test_panel_is_closed_under_the_real_data_box_with_the_agreed_words_and_source():
    html = Path("web/index.html").read_text(encoding="utf-8")
    panel = panel_html()
    assert panel.split(">", 1)[0] == '<details id="skylab" class="sources skylab"', "closed by default"
    assert "<summary>Real crew record: Skylab 4</summary>" in panel
    assert re.search(r'</div>\s*<details id="skylab"', html) and html.index('id="radiation"') < html.index('id="skylab"') < html.index('id="sources"')
    assert html[html.index('id="radiation"'):html.index('<details id="skylab"')].count("<details") == 0
    assert "Real NASA data · crew log estimate: each crewman's own morning estimate, not measured." in panel
    assert '<a href="https://ntrs.nasa.gov/citations/19750019675" target="_blank" rel="noopener noreferrer">NASA CR-141886, Experiment M133 final report, Tables VIII–X, NTRS 19750019675</a>' in panel
    assert re.search(r"\.sources summary \{[^}]*min-height: 44px;", html)
    assert re.search(r"\.range button \{[^}]*min-height: 44px;", html)
    buttons = re.findall(r'<button type="button" data-role="(\w+)" aria-pressed="(true|false)">(\w+)</button>', panel)
    assert buttons == [("CDR", "true", "CDR"), ("PLT", "false", "PLT"), ("SPT", "false", "SPT")]


def test_no_names_and_no_medications_on_the_panel_or_in_the_web_data():
    """Every word allowed is listed, so a person's name or a drug name cannot get in without changing this test."""
    words = set(re.findall(r"[A-Za-z]+", re.sub(r"<[^>]+>", " ", panel_html())))
    assert words <= {"Real", "crew", "record", "Skylab", "NASA", "data", "log", "estimate", "each", "crewman", "s", "own", "morning", "not", "measured",
                     "CDR", "PLT", "SPT", "Total", "sleep", "Usual", "range", "Flagged", "Watching", "Source", "CR", "Experiment", "M", "final", "report",
                     "Tables", "VIII", "X", "NTRS"}, words
    raw = json.loads(Path("web/data/skylab4.json").read_text(encoding="utf-8"))
    assert {n["role"] for n in raw["nights"]} == set(ROLES)
    assert not re.search(r"medic|scop|dex|pro/eph", json.dumps(raw) + panel_html(), re.I)
    assert blocks_diagnostic(re.sub(r"<[^>]+>", " ", panel_html()) + " " + raw["source"]) == []
