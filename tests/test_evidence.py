import json

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
    entry = {"source_type": "ntrs", "source_id": "TEST-ID", "title": "Test title", "url": "https://ntrs.nasa.gov/test"}
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
