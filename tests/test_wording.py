"""The wording check: the probes it was hardened against, and the same normalised text in Python and JavaScript."""

import json
import shutil
import subprocess

import pytest

from baseline.compute.wording import BLOCKED, blocks_diagnostic, normalise

NODE = shutil.which("node")
RUN_JS = (
    "const R = require('./web/rules.js');"
    "const texts = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
    "console.log(JSON.stringify(texts.map((t) => [R.normalise(t), R.blocksDiagnostic(t)])))"
)

MUST_BLOCK = [
    "You may have insomnia.",
    "This suggests depression.",
    "Use melatonin before bed.",
    "You might  have a sleep disorder.",
    "you\nhave a fever",
    "you have a cold",
    "take\trest",
    "This could be a sign of anxiety.",
    "Try a sleeping pill.",
    "Consider ibuprofen.",
    "Your condition is worsening.",
    "This is a symptom of fatigue.",
]
STILL_PASSES = [  # known limit: real copy uses digits and non-ASCII signs, so the shared list cannot block these
    "Sleep deprivation is likely.",
    "...rose by three hundred.",
    "Yоu have a cold",
]
CORRECT = [
    "Your heart rate is outside your usual range.",
    "The design of the study",
    "ambient light",
    "secure storage",
]
PARITY = [
    *MUST_BLOCK, *STILL_PASSES, *CORRECT,
    "",
    "   ",
    "  Leading and trailing  ",
    "tab\tnew\nline\r\nfeed\fvertical\vend",
    "no-break em thin line para narrow ideographic　end",
    "UPPER Case ÄÖ İ Σ final ΣΣ",
    "Up to 5 mg, then 10 mg. Or 3 mg per day; 4 mGy",
]


def test_blocks_diagnostic_and_medication_wording():
    assert len(blocks_diagnostic("You have space anemia, take iron")) >= 2


def test_measurement_sentence_passes():
    text = "HRV is 24 percent below this crew member's 30-day average (rule hrv_below_personal_baseline, z = -2.6)."
    assert blocks_diagnostic(text) == []


@pytest.mark.parametrize("text", MUST_BLOCK)
def test_probe_is_blocked(text):
    assert blocks_diagnostic(text), text


@pytest.mark.parametrize("text", STILL_PASSES + CORRECT)
def test_probe_passes(text):
    assert blocks_diagnostic(text) == [], text


def test_list_has_the_9_old_terms_then_the_67_new_ones_with_no_repeat():
    assert len(BLOCKED) == 76 == len(set(BLOCKED))
    assert BLOCKED[:9] == ["you have", "you are suffering", "diagnos", "disease", "condition:", "take ", "dose", "medication", "prescri"]


def test_normalise_gives_one_space_between_words_and_one_at_each_end():
    assert normalise("  Fever\n\tNOW  ") == " fever now "


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_js_normalises_and_blocks_as_python_does():
    out = subprocess.run([NODE, "-e", RUN_JS], input=json.dumps(PARITY), capture_output=True, text=True, encoding="utf-8", check=True)
    assert json.loads(out.stdout) == [[normalise(t), blocks_diagnostic(t)] for t in PARITY]
