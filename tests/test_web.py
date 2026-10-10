"""The demo page must agree with the Python reference: same data files, same flags, same blocked phrases."""

import json
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.rules import evaluate
from baseline.compute.wording import BLOCKED

NODE = shutil.which("node")
RUN_JS = (
    "const R = require('./web/rules.js');"
    "const rows = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
    "console.log(JSON.stringify({flags: R.evaluate(rows), blocked: R.BLOCKED}))"
)


@pytest.mark.parametrize("web, source", [
    ("web/data/crew_a_anomaly.json", "data/fixtures/crew_a_anomaly.json"),
    ("web/data/evidence_map.json", "docs/evidence_map.json"),
])
def test_web_data_matches_source(web, source):
    assert json.loads(Path(web).read_text()) == json.loads(Path(source).read_text()), f"copy {source} to {web}"


def test_web_radiation_matches_cache():
    fresh = runpy.run_path("scripts/build_radiation_summary.py")["summary"]()
    assert json.loads(Path("web/data/radiation.json").read_text()) == fresh, "run scripts/build_radiation_summary.py"


def summary(flags: dict) -> dict:
    return {str(day): [(r["rule"], r["status"], round(r.get("z", 0.0), 6)) for r in rs] for day, rs in flags.items()}


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("name", ["crew_a_anomaly.json", "crew_a_clean.json"])
def test_js_rule_matches_python(name):
    rows = json.loads(Path("data/fixtures", name).read_text())["rows"]
    out = subprocess.run([NODE, "-e", RUN_JS], input=json.dumps(rows), capture_output=True, text=True, check=True)
    js = json.loads(out.stdout)
    assert summary(js["flags"]) == summary(evaluate(rows))
    assert js["blocked"] == BLOCKED


def test_recorded_day_29_reaction_fires_the_reaction_flag():
    """The page's "Use recorded day-29 self-check" button loads this value; the flag must fire every demo."""
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    day29 = evaluate([r for r in rows if r["day"] <= 29])[29]
    assert [r["status"] for r in day29 if r["rule"] == "reaction_above_personal_baseline"] == ["confirmed"]
