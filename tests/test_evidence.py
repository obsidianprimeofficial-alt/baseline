import json
import re
from pathlib import Path

import pytest

from baseline.compute.rules import DIRECTIONS, rule_multi_signal, rule_zscore
from baseline.compute.wording import blocks_diagnostic
from baseline.evidence import NO_STUDY, card_for, load_evidence_map

RESULT = {"rule": "hrv_below_personal_baseline", "signal": "hrv_rmssd_ms", "current": 40.0,
          "baseline_mean": 55.0, "z": -3.0, "window_days": 26, "status": "confirmed"}


def write(tmp_path, evidence):
    path = tmp_path / "evidence_map.json"
    path.write_text(json.dumps(evidence))
    return str(path)


def test_url_without_source_id_is_rejected(tmp_path):
    path = write(tmp_path, {"hrv_below_personal_baseline": {"source_type": "ntrs", "source_id": None,
                                                            "url": "https://ntrs.nasa.gov/"}})
    with pytest.raises(ValueError):
        load_evidence_map(path)


def test_ntrs_entry_renders_with_ntrs_prefix(tmp_path):
    # Placeholder id, title and URL for the test only; not a real citation.
    entry = {"source_type": "ntrs", "source_id": "TEST-ID", "title": "Test title", "url": "https://ntrs.nasa.gov/test",
             "strength": "Test strength."}
    evidence = load_evidence_map(write(tmp_path, {"hrv_below_personal_baseline": entry}))
    assert card_for(RESULT, evidence)["study"] == "NTRS TEST-ID, Test title, https://ntrs.nasa.gov/test"


def test_card_without_source_says_so():
    card = card_for(RESULT, {"hrv_below_personal_baseline": {"source_id": None, "url": None}})
    assert card["study"] == NO_STUDY
    assert card["telemetry"] == "simulated"
    assert card["flag_status"] == "confirmed"


def test_key_finding_is_part_of_the_study_sentence():
    """The evidence card bolds key_finding inside plain_words, so it must appear there word for word."""
    for rule, entry in load_evidence_map().items():
        if entry.get("key_finding"):
            assert entry["key_finding"] in entry["plain_words"], rule


def test_every_rule_has_a_countermeasure_step():
    """Every card shows a step and a source line; a source not yet known must say so in words."""
    rules = {rule_zscore(signal, [1.0, 2.0, 3.0], 2.0)["rule"] for signal in DIRECTIONS}
    rules.add(rule_multi_signal({1: []})["rule"])
    evidence = load_evidence_map()
    for rule in sorted(rules):
        entry = evidence.get(rule, {})
        assert entry.get("countermeasure", "").strip(), f"{rule}: no countermeasure"
        assert entry.get("countermeasure_source", "").strip(), f"{rule}: no countermeasure_source"
        assert not blocks_diagnostic(entry["countermeasure"]), rule


STRENGTH = {
    "hrv_below_personal_baseline": "Spaceflight study, 4 crew, 16-day flight. Step source: conference abstract.",
    "heart_rate_above_personal_baseline": "Spaceflight study, 4 crew, 16-day flight. Step source: NASA standard (reporting only).",
    "sleep_below_personal_baseline": "Spaceflight study, 19 ISS crew.",
    "reaction_above_personal_baseline": "Spaceflight study, 25 ISS astronauts. Lighting source: conference abstract.",
    "mood_below_personal_baseline": "Ground isolation study (Mars-500), 6 crew, not spaceflight.",
    "two_signals_in_48h": "Ground isolation study (Mars-500), 6 crew, not spaceflight.",
    "spo2_below_personal_baseline": "Evidence report: names the risk, has no SpO2 readings.",
    "core_temp_above_personal_baseline": "Study of 2 crew before and after a 115-day flight, not measured in flight.",
    "solar_particle_event": "NASA technical brief and standard, not a study.",
}


def test_every_rule_has_a_strength_line(tmp_path):
    """PLAN A2: the line comes from the Status column of docs/EVIDENCE.md, and the loader refuses a map without it."""
    evidence = load_evidence_map()
    assert {rule: entry.get("strength") for rule, entry in evidence.items()} == STRENGTH
    assert evidence["spo2_below_personal_baseline"]["source_id"] == "20150021491", "kept, and its line says it has no SpO2 readings"
    for line in STRENGTH.values():
        assert not blocks_diagnostic(f"Evidence strength: {line}"), line
    for broken in ({}, {"strength": "  "}):
        with pytest.raises(ValueError, match="no strength line"):
            load_evidence_map(write(tmp_path, {"hrv_below_personal_baseline": broken}))


def test_every_card_renders_the_strength_line():
    """Each rule's card carries its line; on the page it sits directly under the study source, whatever the rule."""
    evidence = load_evidence_map()
    for rule, line in STRENGTH.items():
        assert card_for({**RESULT, "rule": rule}, evidence)["strength"] == line, rule
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert re.search(r'<p id="ev-study" class="cite"></p>\s*<p id="ev-strength" class="cite"></p>', html)
    app = Path("web/app.js").read_text(encoding="utf-8")
    render = app[app.index("function renderEvidence(r)"):]
    assert 'put($("ev-strength"), `Evidence strength: ${e.strength}`);' in render[:render.index("\n}")]
