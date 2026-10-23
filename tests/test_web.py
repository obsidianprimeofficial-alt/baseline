"""The demo page must agree with the Python reference: same data files, same flags, same blocked phrases."""

import hashlib
import json
import re
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


def test_every_request_happens_at_first_load():
    """The phone demo must survive the network dropping after the first load: the page's only fetch()
    is in init(), which runs once at load, and nothing else can reach the network or reload the page."""
    app = Path("web/app.js").read_text(encoding="utf-8")
    init = app[app.index("(async function init()"):]  # init is the last block in app.js
    assert app.count("fetch(") == init.count("fetch(") == 1
    for api in ("XMLHttpRequest", "import(", "new Image", "location.reload", "location.href", "sendBeacon", "WebSocket", "EventSource"):
        assert api not in app, f"{api} would need the network after load"
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert not re.search(r'(?:src|href)="(?:https?:)?//', html), "every asset must come from web/"


def test_scripts_carry_a_version_that_matches_their_content():
    """A phone that cached an older script must never run it under a newer page: every script URL carries
    a hash of the script, so a changed script gets a URL the browser has never cached. Line endings are
    normalised so a Windows checkout gives the same hash."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script src="([^"?]+)\?v=([0-9a-f]+)"></script>', html)
    assert [path for path, _ in scripts] == ["errors.js", "vendor/chart.umd.js", "rules.js", "reaction.js", "app.js"], \
        "errors.js loads first, so it can show errors from the scripts after it"
    assert html.count("<script") == len(scripts), "every script tag needs ?v="
    for path, version in scripts:
        expected = hashlib.sha1(Path("web", path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:10]
        assert version == expected, f"web/index.html: change {path}?v={version} to {path}?v={expected}"


REACTION_JS = """
const R = require('./web/reaction.js');
const s = (state, shownAt = 0, lastDownAt = -Infinity) => ({ state, shownAt, lastDownAt });
console.log(JSON.stringify({
  hit: R.press(s('go', 1000.0), 1371.4),
  touchBeforeCircle: R.press(s('waiting'), 5000),
  sameTapTouchstart: R.press(s('waiting', 0, 2000.0), 2008.0),
  tooFast: R.press(s('go', 1000.0), 1080.0),
  betweenRounds: R.press(s('pause'), 9000),
  firstTap: R.press(s('idle'), 100),
  delays: [R.delayMs(0), R.delayMs(1)],
  median: R.median([371, 571, 402, 389, 420]),
}));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_reaction_time_comes_from_the_two_recorded_timestamps():
    out = json.loads(subprocess.run([NODE, "-e", REACTION_JS], capture_output=True, text=True, check=True).stdout)
    assert out["hit"] == {"kind": "hit", "ms": 371}  # pressedAt - shownAt, both performance.now()
    assert out["touchBeforeCircle"] == {"kind": "false-start"}  # a tap before the circle repeats the round
    assert out["sameTapTouchstart"] == {"kind": "duplicate"}  # touchstart right after its pointerdown
    assert out["tooFast"] == {"kind": "false-start"}  # under 100 ms is a guess
    assert out["betweenRounds"] == {"kind": "ignore"}
    assert out["firstTap"] == {"kind": "start"}
    assert out["delays"] == [1000, 3000]
    assert out["median"] == 402


def test_recorded_day_29_reaction_fires_the_reaction_flag():
    """The page's "Use recorded day-29 self-check" button loads this value; the flag must fire every demo."""
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    day29 = evaluate([r for r in rows if r["day"] <= 29])[29]
    assert [r["status"] for r in day29 if r["rule"] == "reaction_above_personal_baseline"] == ["confirmed"]


ROUNDING_NOTE = "Numbers are shown to one decimal; z uses the unrounded values."


def test_every_evidence_card_and_the_queue_summary_show_the_rounding_note():
    """The note is static text in the evidence screen, so every card shows it; app.js never hides or replaces
    it, and the queue summary ends with the same sentence."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    evidence = html[html.index('<section id="evidence"'):html.index('<section id="queue"')]
    assert re.search(r'<dl id="ev-numbers" class="readout"></dl>\s*<p id="ev-rounding" class="meta">' + re.escape(ROUNDING_NOTE) + "</p>", evidence)
    app = Path("web/app.js").read_text(encoding="utf-8")
    assert "ev-rounding" not in app
    assert f'const ROUNDING_NOTE = "{ROUNDING_NOTE}";' in app
    queue = app[app.index('$("queue-btn")'):]
    assert re.search(r"lines\.push\(ROUNDING_NOTE\);\s*\$\(\"message\"\)\.replaceChildren", queue)


def test_demo_reaction_card_one_decimal_inputs_reproduce_z():
    """The demo card: 338.3, 281.4 and 16.3 ms as shown give the shown z = 3.5."""
    assert "const fmtZ = (r, v) => `${v.toFixed(1)} ${SIGNALS[r.signal].unit}`;" in Path("web/app.js").read_text(encoding="utf-8")
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    r = next(r for r in evaluate([r for r in rows if r["day"] <= 29])[29] if r["rule"] == "reaction_above_personal_baseline")
    shown = [round(r[k], 1) for k in ("current", "baseline_mean", "baseline_sd")]
    assert shown == [338.3, 281.4, 16.3]
    assert round((shown[0] - shown[1]) / shown[2], 1) == round(r["z"], 1) == 3.5
