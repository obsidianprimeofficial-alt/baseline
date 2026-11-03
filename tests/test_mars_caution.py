"""PLAN R2, open item 0c: a "Caution" flag row and card when the Mars radiation rule fires. The rule itself is not changed.
Runs the page's own scripts through the stand-in page in tests/test_marks.py, with the rule's real output put in place."""

import json
import re
from pathlib import Path

from baseline.compute.radiation import MSL_CACHE, daily_dose, load_cached_msl_rad, mars_dose_flag
from baseline.compute.wording import blocks_diagnostic
from baseline.evidence import load_evidence_map
from tests.test_marks import run, pytestmark  # noqa: F401  # the same stand-in page; skipped without node

KEY = "mars_radiation_caution"
STEP = "Keep watching the radiation level, and send today's summary to the flight surgeon."
ARTEMIS = "https://science.nasa.gov/missions/artemis/artemis-2/to-protect-artemis-ii-astronauts-nasa-experts-keep-eyes-on-sun/"
FORBIDDEN = re.compile(r"dose|shelter|withheld", re.I)


def msl(latest: float) -> dict:
    """msl_rad as scripts/build_radiation_summary.py writes it, with fired decided by the Python rule."""
    daily = [{"date": f"2026-09-{d:02d}", "dose_ugy_day": 183.0 + d % 4, "n_obs": 80} for d in range(1, 31)]
    r = mars_dose_flag(daily + [{"date": "2026-10-01", "dose_ugy_day": latest, "n_obs": 82}])
    return {"date": r["date"], "dose_ugy_day": round(r["current"], 1), "n_obs": r["n_obs"], "baseline_mean": round(r["baseline_mean"], 1),
            "baseline_sd": round(r["baseline_sd"], 2), "z": round(r["z"], 2), "threshold_z": r["threshold_z"], "window_days": r["window_days"],
            "fired": r["fired"], "doi": "10.48322/20qb-4e17", "fetched_at": "2026-10-22T10:00:00+00:00"}


FIRED = msl(260.0)


def put_in(m: dict) -> str:
    return f"state.radiation.msl_rad = {json.dumps(m)};"


def test_evidence_entry_has_the_label_step_sources_and_plain_notes():
    e = load_evidence_map()[KEY]
    assert e["label"] == "Caution" and e["countermeasure"] == STEP
    source = e["countermeasure_source"]
    for needed in (ARTEMIS, "[V2 6099]", "2022-04-08_nasa-std-3001_vol_2_rev_c_final.pdf", "[V1 4029]", "nasa-std-3001-vol-1-rev-c-signature.pdf"):
        assert needed in source, needed
    assert e["caution_line"] == "The first threshold signals a caution, prompting closer monitoring and coordination with medical and flight operations teams"
    assert "real-time monitoring of space weather" in e["monitoring_line"] and "ALARA principle" in e["alara_line"]
    assert "our own 2-SD rule on the last 30 days, not NASA's numeric threshold" in e["trigger_note"] and "not published" in e["trigger_note"]
    assert "modelled on NASA's Artemis II caution practice" in e["practice_note"] and "not on a NASA Mars procedure" in e["practice_note"]
    assert e["strength"].strip()


def test_every_string_in_the_entry_passes_the_wording_check_with_no_dose_and_no_shelter():
    for field, text in load_evidence_map()[KEY].items():
        assert blocks_diagnostic(text) == [], field
        assert not FORBIDDEN.search(text), field


def test_no_row_and_no_change_on_todays_cache():
    """The page follows the Python rule on the real cache."""
    cached = mars_dose_flag(daily_dose(load_cached_msl_rad(MSL_CACHE)["data"]))
    web = json.loads(Path("web/data/radiation.json").read_text())["msl_rad"]
    assert web["fired"] == cached["fired"] is False, "the cache now fires: update this test and redo the shots"
    out = run("""
const p = await page(mem()); p.check();
return { rows: p.$('flag-list').children.map((li) => li.textContent), card: p.run('marsCaution()'), errors: p.errors };
""")
    assert out["card"] is None and out["errors"] == []
    assert not [r for r in out["rows"] if "Mars" in r]


def test_row_and_card_appear_when_the_rule_fires():
    assert FIRED["fired"] is True
    out = run(f"""
const p = await page(mem()); p.check(); p.run({json.dumps(put_in(FIRED))}); p.run('renderFlags()');
const rows = p.$('flag-list').children, li = rows.find((r) => r.textContent.includes('Mars'));
const row = li.textContent; li.children[0].click();
const read = (id) => p.$(id).textContent;
return {{ row, count: rows.filter((r) => r.textContent.includes('Mars')).length,
  title: read('ev-title'), plain: read('ev-plain'), numbers: p.$('ev-numbers').children.map((c) => c.textContent), why: read('ev-words'),
  step: read('ev-step'), source: read('ev-step-source'), strength: read('ev-strength'), note: read('ev-source'), rule: read('ev-rule'),
  study: p.$('ev-study').hidden, maths: p.$('ev-maths').hidden, mark: p.$('ev-mark').hidden, errors: p.errors }};
""")
    assert out["count"] == 1
    assert out["row"].startswith("Caution: Mars surface radiation") and "Above the usual range of the previous 30 days." in out["row"]
    assert out["title"] == "Caution: Mars surface radiation"
    assert out["step"] == STEP
    assert out["source"] == "Source: NASA Artemis II article; NASA-STD-3001 Vol 2 Rev C [V2 6099]; NASA-STD-3001 Vol 1 Rev C [V1 4029]"
    assert "our own 2-SD rule on the last 30 days, not NASA's numeric threshold" in out["why"]
    assert "modelled on NASA's Artemis II caution practice" in out["why"] and "not on a NASA Mars procedure" in out["why"]
    assert out["numbers"][:2] == ["Latest day", f"{FIRED['dose_ugy_day']:.1f} µGy per day"] and out["numbers"][-2:] == ["Status", "Caution"]
    assert out["strength"].startswith("Evidence strength: ") and out["note"].startswith("Real NASA MSL RAD data, not simulated.")
    assert out["rule"] == "Rule: mars_radiation_caution (2 SD above the mean of the previous 30 days)"
    assert out["study"] is True and out["maths"] is True and out["mark"] is False and out["errors"] == []
    for text in (out["row"], out["title"], out["plain"], *out["numbers"], out["why"], out["step"], out["source"], out["strength"], out["note"], out["rule"]):
        assert not FORBIDDEN.search(text), text
        assert blocks_diagnostic(text) == [], text


def test_card_follows_the_rule_either_side_of_two_sd():
    base = msl(184.0)
    just_below = base["baseline_mean"] + 1.9 * base["baseline_sd"]
    just_above = base["baseline_mean"] + 2.1 * base["baseline_sd"]
    below, above = msl(just_below), msl(just_above)
    assert below["fired"] is False and above["fired"] is True
    out = run(f"""
const p = await page(mem());
const at = (m) => {{ p.run('state.radiation.msl_rad = ' + JSON.stringify(m)); return p.run('marsCaution()'); }};
return {{ below: at({json.dumps(below)}), above: at({json.dumps(above)}) }};
""")
    assert out["below"] is None and out["above"]["title"] == "Caution: Mars surface radiation"


def test_queue_summary_carries_the_caution_only_when_the_rule_fires():
    out = run(f"""
const p = await page(mem()); p.check();
const send = () => {{ p.$('queue-btn').click(); return p.$('message').children.map((c) => c.textContent); }};
const quiet = send(); p.run({json.dumps(put_in(FIRED))});
return {{ quiet, fired: send(), errors: p.errors }};
""")
    assert not [l for l in out["quiet"] if "Mars" in l]
    line = [l for l in out["fired"] if "Mars" in l]
    assert len(line) == 1 and line[0].startswith("Caution: Mars surface radiation (real NASA MSL RAD, not a crew reading): ")
    assert blocks_diagnostic(line[0]) == [] and not FORBIDDEN.search(line[0]) and out["errors"] == []


def test_see_what_changed_stays_on_when_only_the_mars_rule_fired():
    out = run(f"""
const p = await page(mem()); p.check(); p.run('Rules.evaluate = () => ({{}}); recompute(state.day)');
const quiet = p.$('to-flags').hidden; p.run({json.dumps(put_in(FIRED))}); p.run('recompute(state.day)');
return {{ quiet, fired: p.$('to-flags').hidden, errors: p.errors }};
""")
    assert out["quiet"] is True and out["fired"] is False and out["errors"] == []
