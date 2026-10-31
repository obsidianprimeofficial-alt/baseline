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


def version(path: str) -> str:
    return hashlib.sha1(Path("web", path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:10]


def test_scripts_styles_and_fonts_carry_a_version_that_matches_their_content():
    """A phone that cached an older file must never use it under a newer page: every script, stylesheet and
    font URL carries a hash of the file, so a changed file gets a URL the browser has never cached. Line
    endings are normalised so a Windows checkout gives the same hash."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script src="([^"?]+)\?v=([0-9a-f]+)"></script>', html)
    assert [path for path, _ in scripts] == ["errors.js", "theme.js", "vendor/chart.umd.js", "rules.js", "trend.js", "projection.js", "maths.js", "spe.js", "reaction.js", "store.js", "app.js"], \
        "errors.js loads first, so it can show errors from the scripts after it; theme.js before the body paints"
    assert html.count("<script") == len(scripts), "every script tag needs ?v="
    links = re.findall(r'<link rel="(?:preload|stylesheet)" href="([^"]+)"', html)
    fonts = re.findall(r'url\("([^"]+)"\)', Path("web/tokens.css").read_text(encoding="utf-8"))
    assert "tokens.css?v=" in " ".join(links) and len(fonts) == 3
    urls = [f"{p}?v={v}" for p, v in scripts] + links + fonts
    for url in urls:
        path, _, v = url.partition("?v=")
        assert v == version(path), f"change {url} to {path}?v={version(path)}"


TOKENS = Path("web/tokens.css")


def theme_block(name: str) -> str:
    css = TOKENS.read_text(encoding="utf-8")
    return re.search(r':root\[data-theme="' + name + r'"\] \{(.*?)\}', css, re.S).group(1)


def test_both_themes_define_every_variable_the_page_uses():
    used = set(re.findall(r"var\((--[a-z-]+)\)", Path("web/index.html").read_text(encoding="utf-8")))
    used |= set(re.findall(r'"(--[a-z-]+)"', Path("web/app.js").read_text(encoding="utf-8")))
    assert {"--ink", "--flag", "--mono", "--sans"} <= used
    for name in ("light", "dark"):
        defined = set(re.findall(r"(--[a-z-]+):", theme_block(name)))
        assert used <= defined, f"{name} theme is missing {sorted(used - defined)}"
    assert "#0B1220" in theme_block("dark") and "#E6ECE8" in theme_block("light")


def test_theme_switch_is_in_the_header_and_big_enough_to_tap():
    html = Path("web/index.html").read_text(encoding="utf-8")
    header = html[html.index('<header class="top">'):html.index("</header>")]
    assert '<button id="theme-btn" class="theme-btn" type="button"' in header
    assert re.search(r"\.theme-btn \{[^}]*width: 44px; height: 44px;", html)
    app = Path("web/app.js").read_text(encoding="utf-8")
    for label in ("Switch to light theme", "Switch to dark theme"):
        assert label in app and not any(b in label.lower() for b in BLOCKED)


def test_offline_line_is_in_the_header_on_every_screen():
    """DESIGN_BRIEF [NEW]: P1 to P7 show the offline indicator. It sits in the shared header, so every screen has it."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    header = html[html.index('<header class="top">'):html.index("</header>")]
    line = "Offline – all data cached"
    assert f"</svg>{line}</span>" in header and not any(b in line.lower() for b in BLOCKED)


THEME_JS = """
const T = require('./web/theme.js');
const at = (h, m) => T.byClock(new Date(2026, 9, 29, h, m));
console.log(JSON.stringify([at(21, 59), at(22, 0), at(3, 0), at(5, 59), at(6, 0), at(12, 0)]));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_default_theme_is_dark_in_the_simulated_sleep_window():
    out = json.loads(subprocess.run([NODE, "-e", THEME_JS], capture_output=True, text=True, check=True).stdout)
    assert out == ["light", "dark", "dark", "dark", "light", "light"]
    theme = Path("web/theme.js").read_text(encoding="utf-8")
    assert "Simulated crew schedule, not a NASA figure" in theme
    assert theme.count("try {") == 2, "localStorage read and write are both wrapped"


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


PAIR_JS = """
const src = require("fs").readFileSync("web/app.js", "utf8");
const signals = src.slice(src.indexOf("const SIGNALS = {"), src.indexOf("};", src.indexOf("const SIGNALS = {")) + 2);
const text = src.slice(src.indexOf("const listWords"), src.indexOf("function sourceNote"));
const cases = JSON.parse(process.argv[1]);
console.log(JSON.stringify(cases.map(({ day, flags, r }) => new Function("state", "r",
  `${signals}\\n${text}\\nreturn [plainStatus(r), plainWords(r), pairNames(r, true)];`)({ day, flags }, r))));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_48_hour_row_names_the_signals_and_the_days():
    """A3: the 48-hour row says which signals and which days the rule counted (confirmed only, the latest day
    and the day before), and marks a signal confirmed on one of the two days only."""
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    rows = [dict(r, **({"sleep_hours": 5.0, "mood_1to5": 4} if r["day"] == 29 else {})) for r in rows if r["day"] <= 29]
    flags = evaluate(rows)  # the recorded day-29 demo: sleep 5, mood 4
    demo = next(r for r in flags[29] if r["rule"] == "two_signals_in_48h")
    one = {"rule": "two_signals_in_48h", "signals": ["hrv_rmssd_ms", "sleep_hours"], "window_days": 2}
    later = {28: [{"signal": "hrv_rmssd_ms", "status": "confirmed"}, {"signal": "sleep_hours", "status": "watch"}],
             29: [{"signal": "hrv_rmssd_ms", "status": "confirmed"}, {"signal": "sleep_hours", "status": "confirmed"}]}
    cases = [{"day": 29, "flags": flags, "r": demo}, {"day": 29, "flags": later, "r": one}]
    out = json.loads(subprocess.run([NODE, "-e", PAIR_JS, json.dumps(cases)], capture_output=True, text=True, check=True).stdout)
    assert out[0] == [
        "Flagged on days 28 and 29: heart rate variability, mood (day 28 only), reaction time and sleep.",
        "Four readings were flagged within 48 hours (days 28 and 29): heart rate variability, mood (day 28 only), "
        "reaction time and sleep. This rule fires when two or more different readings are flagged in that window.",
        "Heart rate variability, mood (day 28 only), reaction time and sleep",
    ]
    assert out[1][0] == "Flagged on days 28 and 29: heart rate variability and sleep (day 29 only)."
    assert not [p for line in out[0] + out[1] for p in BLOCKED if p in line.lower()]


def console_html() -> str:
    html = Path("web/index.html").read_text(encoding="utf-8")
    return html[html.index('<section id="console"'):html.index('<div id="radiation"')]


def test_console_charts_all_seven_signals_in_the_order_of_app_js():
    """PLAN Phase B item 1: heart rate, HRV, blood oxygen, core temperature, sleep, mood, reaction time."""
    blocks = re.findall(r'<div class="channel( bottom)?" data-signal="([a-z0-9_]+)">', console_html())
    app = Path("web/app.js").read_text(encoding="utf-8")
    channels = json.loads(re.search(r"const CHANNELS = (\[[^\]]*\]);", app).group(1))
    assert [s for _, s in blocks] == channels == [
        "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "core_temp_c", "sleep_hours", "mood_1to5", "reaction_ms"]
    assert [bool(b) for b, _ in blocks] == [False] * 6 + [True], "only the last chart shows the day axis"
    for s in channels:
        assert re.search(s + r': \{[^}]*step: [0-9.]+,', app), f"{s} needs a y-axis step"


def test_range_switch_has_both_buttons_and_starts_on_30_days():
    html = console_html()
    assert '<h1 id="console-title" tabindex="-1">Health status</h1>' in html
    switch = html[html.index('<div class="range"'):html.index('<div class="channel')]
    assert re.findall(r'<button type="button" data-range="(\d+)" aria-pressed="(true|false)">([^<]+)</button>', switch) == [
        ("7", "false", "7 days"), ("0", "true", "30 days")]
    assert re.search(r"\.range button \{[^}]*min-height: 44px;", Path("web/index.html").read_text(encoding="utf-8"))


TREND_JS = """
const R = require('./web/rules.js'), T = require('./web/trend.js');
const rows = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {};
for (const last of [29, 30]) {
  const shown = rows.filter((r) => r.day <= last), flags = R.evaluate(shown);
  for (const s of ['heart_rate_bpm', 'hrv_rmssd_ms', 'spo2_pct', 'core_temp_c', 'sleep_hours', 'mood_1to5', 'reaction_ms']) {
    out[last + ' ' + s] = { week: T.series(shown, flags, s, 7).shown, month: T.series(shown, flags, s, 0).shown };
  }
}
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_7_day_view_shows_the_same_band_and_marks_as_the_30_day_view():
    """Band and marks are computed on the full record and then cut, never recomputed on the last 7 days."""
    rows = json.loads(Path("web/data/crew_a_anomaly.json").read_text())["rows"]
    out = json.loads(subprocess.run([NODE, "-e", TREND_JS], input=json.dumps(rows), capture_output=True, text=True, check=True).stdout)
    assert len(out) == 14
    for key, v in out.items():
        week, month = v["week"], v["month"]
        last = int(key.split()[0])
        assert week["days"] == list(range(last - 6, last + 1)) and month["days"] == list(range(1, last + 1)), key
        for k in ("vals", "band", "marks"):
            assert week[k] == month[k][-7:], f"{key} {k}"
    marked = {k.split()[1] for k, v in out.items() if k.startswith("29 ") and any(v["week"]["marks"])}
    assert {"reaction_ms", "hrv_rmssd_ms", "sleep_hours"} <= marked, "the three demo flags show in the 7-day view on day 29"


HOW_TO_MEASURE = [
    ("<h2>Reaction time</h2>", "tap the field to start, then tap as soon as the dark circle appears, 1 to 3 seconds later. "
     "Five rounds; a tap before the circle or within 0.1 seconds of it repeats the round. The middle time of the five counts."),
    ('<label class="q" for="sleep">How long did you sleep last night?</label>',
     "type the hours you slept last night, or use − and + to change it by half an hour. 0 to 12 hours."),
    ("<legend>How well did you sleep?</legend>", "tap one number, from 1 (badly) to 5 (very well)."),
    ("<legend>How is your mood this morning?</legend>", "tap one number, from 1 (very low) to 5 (very good)."),
    ("<h2>Near vision</h2>", "hold the phone where you normally read, read the line below, then tap Clear or Blurred."),
]


def test_statement_labels_guidance_and_needs_flight_surgeon_attention():
    """PLAN 4a (Gate 1 labels): the step on the evidence card is headed "Guidance" and the queue screen
    "Needs flight surgeon attention"; the old headings are gone. The queue button keeps its action wording."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    evidence = html[html.index('<section id="evidence"'):html.index('<section id="queue"')]
    assert "<h2>Guidance</h2>" in evidence
    assert '<h1 id="queue-title" tabindex="-1">Needs flight surgeon attention</h1>' in html
    for old in ("Step to consider", "Queued for flight surgeon"):
        assert old not in html and old not in Path("web/app.js").read_text(encoding="utf-8"), old
    assert '<button id="queue-btn" class="primary" type="button">Queue for flight surgeon</button>' in html


def test_one_how_to_measure_line_under_each_self_check_part():
    """PLAN 4a: one "How to measure" line directly under each part, saying what the person does; the facts in
    it come from the code (reaction.js rounds, false-start cut and delay; the sleep field's range and step)."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    today = html[html.index('<section id="today"'):html.index('<p id="missing"')]
    found = re.findall(r'<p class="meta how">How to measure: ([^<]+)</p>', today)
    assert found == [line for _, line in HOW_TO_MEASURE]
    for anchor, line in HOW_TO_MEASURE:
        assert re.search(re.escape(anchor) + r'\s*<p class="meta how">How to measure: ' + re.escape(line), today), anchor
        assert not [p for p in BLOCKED if p in line.lower()]
    js = Path("web/reaction.js").read_text(encoding="utf-8")
    assert "const ROUNDS = 5;" in js and "const GUESS_MS = 100;" in js and "1000 + random * 2000" in js
    assert 'step="0.5" min="0" max="12"' in today
    assert '<label for="vision-clear">Clear</label>' in today and '<label for="vision-blurred">Blurred</label>' in today
