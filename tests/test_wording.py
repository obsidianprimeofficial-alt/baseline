from baseline.compute.wording import blocks_diagnostic


def test_blocks_diagnostic_and_medication_wording():
    assert len(blocks_diagnostic("You have space anemia, take iron")) >= 2


def test_measurement_sentence_passes():
    text = "HRV is 24 percent below this crew member's 30-day average (rule hrv_below_personal_baseline, z = -2.6)."
    assert blocks_diagnostic(text) == []
