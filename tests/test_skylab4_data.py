"""PLAN R1: the real crew sleep record, cache/skylab4/. Crew log estimates, one row per role and mission day.
The screen and the rule run are in tests/test_skylab4.py. Roles only, and the report's medications column is never in the file."""

import csv
import re
from pathlib import Path

from baseline.compute.wording import blocks_diagnostic

DIR = Path("cache/skylab4")
COLUMNS = ["role", "mission_day", "total_sleep_h", "light_h", "heavy_h", "note"]
INCOMPLETE = {
    ("CDR", 84): ("5", "", "", "light and heavy blank; total only"),
    ("PLT", 84): ("≈3.0", "", "", 'light and heavy blank; total printed "≈3.0"'),
    ("SPT", 3): ("6.7", "", "", "light and heavy blank; total only"),
    ("SPT", 4): ("7", "", "", "light and heavy blank; total only"),
    ("SPT", 84): ("?", "?", "?", 'all three printed "?"'),
}
FLAGGED = {
    ("CDR", 10): ("7", "0", "7", "faint first digit (both reads: 0.0)"),
    ("PLT", 18): ("7.8", "1.8", "6", "only PLT value not a whole/half hour (both reads: 1.8 / 7.8)"),
}
# Every word the file may hold. A person's name or a drug name cannot get in without changing this line.
WORDS = {"role", "mission", "day", "total", "sleep", "h", "light", "heavy", "note", "CDR", "PLT", "SPT", "and", "blank", "only",
         "printed", "all", "three", "faint", "first", "digit", "both", "reads", "not", "a", "whole", "half", "hour", "value"}


def load() -> list[dict]:
    with open(DIR / "sleep-estimates.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_file_has_84_days_for_each_of_three_roles_and_only_the_agreed_columns():
    rows = load()
    assert len(rows) == 252
    assert list(rows[0]) == COLUMNS
    for role in ("CDR", "PLT", "SPT"):
        assert [int(r["mission_day"]) for r in rows if r["role"] == role] == list(range(1, 85))


def test_no_names_and_no_medication_column():
    text = (DIR / "sleep-estimates.csv").read_text(encoding="utf-8")
    assert {r["role"] for r in load()} == {"CDR", "PLT", "SPT"}
    assert set(re.findall(r"[A-Za-z]+", text)) <= WORDS
    assert not re.search(r"medic|scop|dex|pro/eph", text, re.I)
    assert blocks_diagnostic(text) == []


def test_totals_add_up_on_every_complete_row():
    number = re.compile(r"\d+(\.\d+)?$")
    complete = [r for r in load() if all(number.match(r[k]) for k in ("total_sleep_h", "light_h", "heavy_h"))]
    assert len(complete) == 247
    for r in complete:
        assert abs(float(r["light_h"]) + float(r["heavy_h"]) - float(r["total_sleep_h"])) < 1e-9, r


def test_incomplete_and_flagged_rows_stay_as_printed_with_their_note_and_no_other_row_has_one():
    got = {(r["role"], int(r["mission_day"])): (r["total_sleep_h"], r["light_h"], r["heavy_h"], r["note"]) for r in load()}
    expected = {**INCOMPLETE, **FLAGGED}
    assert {k: got[k] for k in expected} == expected
    assert {k for k, v in got.items() if v[3]} == set(expected)


def test_readme_says_what_the_numbers_are_and_where_they_come_from():
    readme = (DIR / "README.md").read_text(encoding="utf-8")
    for needed in ("NASA CR-141886", "NTRS 19750019675", "https://ntrs.nasa.gov/citations/19750019675", "Table VIII", "Table IX", "Table X",
                   "crew log estimate: each crewman's own morning estimate of total sleep", "two independent reads", "2 November 2026"):
        assert needed in readme, needed
    assert blocks_diagnostic(readme) == []
