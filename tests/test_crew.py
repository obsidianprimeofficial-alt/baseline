"""PLAN item 6: the crew-of-three flight-surgeon view. Runs the page's own scripts through the stand-in page of test_marks.py."""

import json
import runpy
from pathlib import Path

from baseline.compute.rules import evaluate
from baseline.compute.wording import blocks_diagnostic
from baseline.fixtures import NOTE, make_fixture
from baseline.validation import make_planted
from tests.test_marks import run, pytestmark  # noqa: F401  # skipped without node

ROUNDING = "Numbers are shown to one decimal; z uses the unrounded values."
RAIL_A = [
    "Crew member A, day 29. Telemetry is simulated.",
    "Reaction time: 338.3 ms, usual 281.4 ms over 28 days, z = +3.5, flagged (rule reaction_above_personal_baseline).",
    "Heart rate variability: 42.0 ms, usual 53.9 ms over 28 days, z = −2.9, flagged (rule hrv_below_personal_baseline).",
    "Sleep: 5.0 hours, usual 6.8 hours over 28 days, z = −2.8, flagged (rule sleep_below_personal_baseline).",
    "Heart rate variability, mood (day 28 only), reaction time and sleep flagged within 48 hours, days 28 and 29 (rule two_signals_in_48h).",
    "Self-check: reaction 338 ms (recorded, simulated), slept 5.0 hours, sleep quality 2 of 5, mood 4.0 of 5, near vision clear.",
    "Sleep note: Woke at 03:00 for a docking",
    ROUNDING,
]
RAIL_C = [
    "Crew member C, day 29. Telemetry is simulated.",
    "Heart rate: 74.6 beats a minute, usual 62.1 beats a minute over 28 days, z = +3.3, flagged (rule heart_rate_above_personal_baseline).",
    "Sleep: 6.4 hours, usual 7.0 hours over 28 days, z = −2.1, watching (rule sleep_below_personal_baseline).",
    ROUNDING,
]
# The phone's demo day 29, then the screen's text; used to compare before and after a crew visit.
DEMO = "p.$('note').value = 'Woke at 03:00 for a docking'; p.check();"
READ_ROWS = """
const rows = p.$('crew-rows').children.map((li) => ({
  who: li.children[0].children[0].textContent, count: li.children[0].children[1].textContent, cls: li.className,
  lines: li.children[1].children.map((c) => c.textContent), button: li.children[2]?.textContent ?? null }));
const rail = p.$('crew-queue').children.map((m) => m.children.map((c) => c.textContent));
"""
PHONE = """
const phone = () => JSON.parse(JSON.stringify({ rows: p.run('state.rows'), flags: p.run('state.flags'), day: p.run('state.day'), marks: p.run('state.marks'),
  list: p.$('flag-list').textContent, title: p.$('flags-title').textContent, card: p.$('ev-plain').textContent, source: p.$('ev-source').textContent,
  mark: p.view(), queueHidden: p.$('queue-btn').hidden, label: p.$('day-label').textContent, maths: p.$('maths-numbers').textContent }));
"""


def load(name):
    return json.loads(Path("data/fixtures", name).read_text(encoding="utf-8"))


def test_crew_files_equal_their_functions_output_and_say_what_they_are():
    b, c = load("crew_b_clean.json"), load("crew_c_heart_rate.json")
    assert b["rows"] == make_fixture(8, anomaly_start=None) and b["note"] == NOTE and b["source"] == "simulated"
    assert c["rows"] == make_planted(9, "heart_rate_bpm", 4.0, start_day=27) and c["source"] == "simulated"
    assert all(w in c["note"] for w in ("seed-9", "+4 SD", "days 27-29", "make_planted", "Simulated"))
    assert c["note"] == runpy.run_path("scripts/make_crew_fixtures.py")["C_NOTE"]


def test_day_29_under_the_python_rules():
    day29 = lambda name: evaluate(load(name)["rows"][:29])[29]  # noqa: E731
    assert day29("crew_b_clean.json") == []
    c = {r["signal"]: r["status"] for r in day29("crew_c_heart_rate.json")}
    assert c == {"heart_rate_bpm": "confirmed", "sleep_hours": "watch"}, "no 48-hour row either"


def test_rows_use_the_phones_flag_wording_and_labels_only():
    out = run(f"const p = await page(mem()); {READ_ROWS} return {{ rows, errors: p.errors }};")
    assert out["errors"] == []
    assert out["rows"] == [
        {"who": "Crew member A", "count": "3 flags", "cls": "crew-row flagged confirmed", "button": "Open evidence", "lines": [
            "Reaction time", "338 ms today. Your usual: 281 ms.", "Well outside your usual range, third day running.", "Awaiting flight surgeon"]},
        {"who": "Crew member B", "count": "0 flags", "cls": "crew-row ", "button": None, "lines": ["No flags today"]},
        {"who": "Crew member C", "count": "1 flag · 1 watching", "cls": "crew-row flagged confirmed", "button": "Open evidence", "lines": [
            "Heart rate", "75 beats a minute today. Your usual: 62 beats a minute.", "Well outside your usual range, third day running.", "Awaiting flight surgeon"]},
    ]


def test_crew_counts_are_the_phones_count_and_a_watching_reading_is_not_a_flag():
    """Audit 11 Nov A6: a crew row counts single readings as the phone's console does (not the 48-hour row);
    a reading still being watched is shown apart, never counted as a flag."""
    out = run(f"const p = await page(mem()); {DEMO} {READ_ROWS} return {{ rows, phone: p.$('console-summary').textContent }};")
    counts = {r["who"]: r["count"] for r in out["rows"]}
    assert out["phone"] == "3 readings are outside your usual range today."
    assert counts == {"Crew member A": "3 flags", "Crew member B": "0 flags", "Crew member C": "1 flag · 1 watching"}


def test_rail_holds_only_the_flagged_crew_and_every_line_passes_the_wording_check():
    out = run(f"const p = await page(mem()); {READ_ROWS} return {{ rail }};")
    assert out["rail"] == [RAIL_A, RAIL_C]
    assert not [line for summary in out["rail"] for line in summary if blocks_diagnostic(line)]


def test_crew_a_equals_the_phones_day_29():
    out = run(f"""
const p = await page(mem()); {READ_ROWS} {DEMO}
const strip = (r) => r.map((x) => ({{ ...x, saved_at: undefined }}));
p.card('reaction_ms'); p.$('queue-btn').click();
return {{ rail, queue: p.$('message').children.map((c) => c.textContent), phoneFlags: p.run('state.flags[29]'), crewFlags: p.run('state.crewData.A.flags[29]'),
  phoneRows: strip(p.run('state.rows')), crewRows: strip(p.run('state.crewData.A.rows')) }};
""")
    assert out["crewFlags"] == out["phoneFlags"]
    assert out["crewRows"] == out["phoneRows"]
    assert out["rail"][0] == out["queue"] == RAIL_A


def test_a_crew_visit_leaves_the_phones_state_marks_and_day_30_lines_as_they_were():
    out = run(f"""
const walk = async (visit) => {{
  const p = await page(mem()); {PHONE} {DEMO}
  p.card('reaction_ms'); p.$('ev-mark').click(); p.$('ev-maths').click();
  const before = phone();
  if (visit) for (const who of ['A', 'C']) {{
    p.run(`setCrew("${{who}}"); show("flags"); renderEvidence(flagsFor(29).find((r) => r.signal)); show("evidence");`);
    p.$('ev-maths').click(); p.run('show("crew")');
  }}
  const after = phone(), chrome = [p.$('flags-back').textContent, p.$('flags-back').dataset.go, p.$('flags-who').hidden, p.$('ev-who').hidden]; p.nextDay();
  return {{ before, after, chrome, follow: p.follow(), day30: p.$('flag-list').textContent, title: p.$('flags-title').textContent, label: p.$('day-label').textContent }};
}};
const seen = await walk(true), control = await walk(false);
return {{ seen, control }};
""")
    assert out["seen"]["after"] == out["seen"]["before"]
    assert out["seen"]["chrome"] == ["Back to the chart", "console", True, True]
    assert out["seen"]["before"]["mark"]["button"] == "Undo step done"
    assert {k: out["seen"][k] for k in ("follow", "day30", "title", "label")} == {k: out["control"][k] for k in ("follow", "day30", "title", "label")}
    assert "Step marked done on day 29." in out["seen"]["follow"]


def test_on_the_crew_path_the_list_and_card_are_that_persons_without_the_astronauts_actions():
    out = run("""
const p = await page(mem()); p.run('setCrew("C"); show("flags"); renderEvidence(flagsFor(29).find((r) => r.signal === "sleep_hours")); show("evidence");');
const c = { who: [p.$('flags-who').textContent, p.$('ev-who').textContent], hidden: [p.$('flags-who').hidden, p.$('ev-who').hidden, p.$('queue-btn').hidden, p.$('ev-mark').hidden],
  back: p.$('flags-back').textContent, go: p.$('flags-back').dataset.go, list: p.$('flag-list').textContent, title: p.$('flags-title').textContent, card: p.$('ev-plain').textContent, source: p.$('ev-source').textContent, label: p.$('day-label').textContent };
p.run('setCrew("A"); renderEvidence(flagsFor(29).find((r) => r.signal === "sleep_hours"));');
const a = { who: p.$('ev-who').textContent, note: p.$('ev-note').textContent, source: p.$('ev-source').textContent, hidden: p.$('ev-mark').hidden };
return { c, a, errors: p.errors };
""")
    c, a = out["c"], out["a"]
    assert c["who"] == ["Crew member C"] * 2 and c["hidden"] == [False, False, True, True]
    assert (c["back"], c["go"]) == ("Back to crew status", "crew")
    assert "75 beats a minute today." in c["list"] and c["title"] == "What changed today" and c["label"] == "Day 29"
    assert "6.4 hours" in c["card"] and c["source"] == "Today's value and your usual range come from the simulated record."
    assert a["who"] == "Crew member A" and a["note"] == "Your note: Woke at 03:00 for a docking" and a["hidden"] is True
    assert a["source"] == "Today's value comes from your self-check. Your usual range comes from the simulated record."
    assert out["errors"] == []


def test_browser_back_and_forward_set_the_right_person_on_the_shared_screens():
    out = run(f"""
const p = await page(mem()); {DEMO}
p.card('reaction_ms');
const phoneCard = p.$('ev-plain').textContent, list = p.$('flag-list').textContent;
p.run('setCrew("C"); show("flags"); renderEvidence(flagsFor(29).find((r) => r.signal === "heart_rate_bpm")); show("evidence");');
const crewCard = p.$('ev-plain').textContent;
const go = (s) => {{ p.run(`onPop({{ state: ${{JSON.stringify(s)}} }})`); return {{ crew: p.run('state.crew'), card: p.$('ev-plain').textContent, list: p.$('flag-list').textContent, last: p.history().at(-1) }}; }};
const toCrew = go({{ screen: 'crew', crew: null }}), toPhone = go({{ screen: 'evidence', crew: null }}), forward = go({{ screen: 'evidence', crew: 'C' }}), console = go({{ screen: 'console', crew: null }});
return {{ phoneCard, list, crewCard, toCrew, toPhone, forward, console, errors: p.errors }};
""")
    assert out["toCrew"]["crew"] is None and out["toCrew"]["card"] == out["phoneCard"], "leaving redraws the phone's card"
    assert out["toPhone"]["card"] == out["phoneCard"] and out["toPhone"]["list"] == out["list"]
    assert out["forward"]["crew"] == "C" and out["forward"]["card"] == out["crewCard"], "forward returns to the crew card"
    assert out["console"]["list"] == out["list"] and out["errors"] == []


def test_address_with_the_hash_opens_the_view_and_other_entries_do_not():
    out = run("""
const direct = await page(mem(), '#crew'), plain = await page(mem());
plain.run('onPop({ state: null })');
const typed = await page(mem(), '#crew'); typed.run('onPop({ state: null })');
const fresh = await page(mem()); fresh.run('onPop({ state: { screen: "flags", crew: null } })');
return { direct: direct.history(), plain: plain.history(), typed: typed.shown(), plainShown: plain.shown(), fresh: fresh.shown(), wide: direct.run('document.body.wide') };
""")
    assert out["direct"] == [["replace", "guide"], ["replace", "crew"]]
    assert out["plain"] == [["replace", "guide"]]
    assert out["typed"] == "crew" and out["plainShown"] == "guide"
    assert out["fresh"] == "guide", "a phone screen with no saved check still falls back to the guide"
    assert out["wide"] is True


def test_console_link_shows_on_day_29_only_and_the_first_screen_has_no_new_control():
    out = run(f"const p = await page(mem()); {DEMO} const d29 = p.$('to-crew').hidden; p.nextDay(); return {{ d29, d30: p.$('to-crew').hidden, label: p.$('day-label').textContent }};")
    assert out == {"d29": False, "d30": True, "label": "Day 30"}
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert '<button id="to-crew" class="text-button" type="button" data-go="crew">Flight surgeon view</button>' in html
    guide = html[html.index('<section id="guide"'):html.index('<section id="today"')]
    assert "crew status" not in guide and "Flight surgeon view" not in guide and "to-crew" not in guide
    console = html[html.index('<section id="console"'):html.index('<section id="flags"')]
    assert "to-crew" in console


def test_static_copy_passes_the_wording_check_and_stacks_on_a_phone():
    html = Path("web/index.html").read_text(encoding="utf-8")
    crew = html[html.index('<section id="crew"'):html.index('<section id="alert"')]
    for line in ("Flight surgeon – crew status", "Three crew, one screen. Each row is that person checked against their own normal.", "Queued summaries", "Demo only: nothing leaves this device."):
        assert line in crew and not blocks_diagnostic(line)
    assert ".wide .top, .wide main { max-width: 1360px; }" in html
    assert "@media (min-width: 900px) { .crew-grid { grid-template-columns:" in html, "two columns only on a laptop"


def test_history_entries_carry_whose_screen_it_is():
    out = run("""
const p = await page(mem());
p.run('setCrew("C"); show("flags");'); const onCrew = p.history().at(-1);
p.run('show("crew");'); const back = p.history().at(-1);
return { onCrew, back, crew: p.run('state.crew') };
""")
    assert out["onCrew"] == ["push", "flags", "C"]
    assert out["back"] == ["push", "crew", None] and out["crew"] is None


def test_crew_view_says_day_29_while_the_phone_is_on_day_30_and_the_phone_keeps_its_day():
    out = run(f"""
const p = await page(mem()); {DEMO} p.nextDay();
p.run('show("crew")'); const crew = p.$('day-label').textContent;
p.$('crew-rows').children[2].children[2].click(); const list = [p.$('flags-title').textContent, p.$('day-label').textContent];
p.run('onPop({{ state: {{ screen: "console", crew: null }} }})');
return {{ crew, list, phone: [p.$('flags-title').textContent, p.$('day-label').textContent], day: p.run('state.day') }};
""")
    assert out["crew"] == "Day 29"
    assert out["list"] == ["What changed today", "Day 29"]
    assert out["phone"] == ["What changed on day 30", "Day 30"] and out["day"] == 30


def test_a_phone_mark_does_not_show_on_a_crew_card_for_the_same_rule():
    out = run(f"""
const p = await page(mem()); {DEMO} p.card('sleep_hours'); p.$('ev-mark').click(); const phone = p.view().line;
p.run('setCrew("A"); renderEvidence(flagsFor(29).find((r) => r.signal === "sleep_hours"));');
return {{ phone, crew: p.view(), marks: p.run('Object.keys(state.marks)') }};
""")
    assert out["phone"].startswith("Step done, ")
    assert out["crew"]["line"] is None and out["crew"]["buttonHidden"] is True
    assert out["marks"] == ["29:sleep_below_personal_baseline"]


def test_going_back_to_the_maths_draws_its_chart_again():
    out = run(f"""
const p = await page(mem()); {DEMO} p.card('reaction_ms'); p.$('ev-maths').click();
p.run('globalThis.first = state.mathsChart; onPop({{ state: {{ screen: "maths", crew: null }} }})');
return {{ redrawn: p.run('state.mathsChart !== first') }};
""")
    assert out["redrawn"] is True


def test_start_the_demo_again_forgets_the_card_to_redraw():
    out = run(f"const p = await page(mem()); {DEMO} p.card('reaction_ms'); p.$('restart').click(); return {{ card: p.run('state.card') }};")
    assert out["card"] is None
