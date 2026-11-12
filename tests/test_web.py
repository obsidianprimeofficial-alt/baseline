"""The demo page must agree with the Python reference: same data files, same flags, same blocked phrases."""

import hashlib
import json
import os
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
    ("web/data/crew_b_clean.json", "data/fixtures/crew_b_clean.json"),
    ("web/data/crew_c_heart_rate.json", "data/fixtures/crew_c_heart_rate.json"),
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
@pytest.mark.parametrize("name", ["crew_a_anomaly.json", "crew_a_clean.json", "crew_b_clean.json", "crew_c_heart_rate.json"])
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
    assert not re.search(r'src="(?:https?:)?//|<link[^>]*href="(?:https?:)?//', html), "every asset must come from web/"
    # Plain links to a source (Data sources panel) are fetched only if someone taps them.
    tags = re.findall(r'<(\w+)[^>]*\b(?:src|href|action|data)="(?:https?:)?//', html)
    assert set(tags) <= {"a"}, f"only <a> may point off the device: {tags}"


def version(path: str) -> str:
    return hashlib.sha1(Path("web", path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:10]


def test_scripts_styles_and_fonts_carry_a_version_that_matches_their_content():
    """A phone that cached an older file must never use it under a newer page: every script, stylesheet and
    font URL carries a hash of the file, so a changed file gets a URL the browser has never cached. Line
    endings are normalised so a Windows checkout gives the same hash."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script src="([^"?]+)\?v=([0-9a-f]+)"></script>', html)
    assert [path for path, _ in scripts] == ["errors.js", "theme.js", "vendor/chart.umd.js", "rules.js", "trend.js", "skylab4.js", "projection.js", "maths.js", "mars.js", "spe.js", "reaction.js", "store.js", "app.js"], \
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


def palette() -> str:
    """The one palette: dark only (Hrishin, 11 Nov 2026)."""
    css = TOKENS.read_text(encoding="utf-8")
    blocks = re.findall(r"^(:root[^{]*)\{(.*?)\}", css, re.S | re.M)
    assert [sel.strip() for sel, _ in blocks] == [":root"], "one palette on plain :root, no data-theme blocks"
    return blocks[0][1]


def test_dark_palette_defines_every_variable_the_page_uses():
    used = set(re.findall(r"var\((--[a-z-]+)\)", Path("web/index.html").read_text(encoding="utf-8")))
    used |= set(re.findall(r'"(--[a-z-]+)"', Path("web/app.js").read_text(encoding="utf-8")))
    assert {"--ink", "--flag", "--mono", "--sans"} <= used
    defined = set(re.findall(r"(--[a-z-]+):", palette()))
    assert used <= defined, f"dark palette is missing {sorted(used - defined)}"
    assert "#0B1220" in palette() and "color-scheme: dark;" in palette()


def test_offline_line_is_in_the_header_on_every_screen():
    """DESIGN_BRIEF [NEW]: P1 to P7 show the offline indicator. It sits in the shared header, so every screen has it."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    header = html[html.index('<header class="top">'):html.index("</header>")]
    line = "Offline – all data cached"
    assert f"</svg>{line}</span>" in header and not any(b in line.lower() for b in BLOCKED)


THEME_JS = r"""
// The page's theme.js as a browser runs it (no module), with a saved "light" choice from an old visit in storage.
const fs = require('fs');
const calls = [];
const storage = { getItem(k) { calls.push(['get', k]); return k === 'baseline-theme' ? 'light' : null; }, setItem(k, v) { calls.push(['set', k, v]); } };
const document = { documentElement: { setAttribute(k, v) { calls.push(['attr', k, v]); }, getAttribute() { return null; } } };
const root = {};
new Function('module', 'localStorage', 'document', 'window', fs.readFileSync('./web/theme.js', 'utf8').replace(/\}\)\(this\);\s*$/, '})(window);'))(undefined, storage, document, root);
console.log(JSON.stringify({ calls, api: Object.keys(root.Theme).sort() }));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_page_is_dark_with_a_saved_light_choice_and_has_no_switch():
    """Dark only (Hrishin, 11 Nov 2026): a saved "light" value from an old visit is never read and never applied;
    no clock default; no switch in the header or in app.js; the only palette is dark."""
    out = json.loads(subprocess.run([NODE, "-e", THEME_JS], capture_output=True, text=True, check=True).stdout)
    assert out["calls"] == [], "theme.js reads no saved choice and sets no theme"
    assert out["api"] == ["SLEEP_END_HOUR", "dailyLine"]
    theme = Path("web/theme.js").read_text(encoding="utf-8")
    assert "Simulated crew schedule, not a NASA figure" in theme
    assert "localStorage" not in theme and "getHours() >=" not in theme
    html = Path("web/index.html").read_text(encoding="utf-8")
    header = html[html.index('<header class="top">'):html.index("</header>")]
    assert "<button" not in header, "no theme switch in the header"
    app = Path("web/app.js").read_text(encoding="utf-8")
    for gone in ("theme-btn", "Switch to light theme", "Switch to dark theme", "Theme.set", "Theme.current"):
        assert gone not in html and gone not in app, gone
    css = TOKENS.read_text(encoding="utf-8")
    assert "data-theme" not in css and "color-scheme: light" not in css and "#E6ECE8" not in css
    assert "data-theme" not in html and "prefers-color-scheme" not in html + css
    palette()


DAILY_JS = """
const fs = require('fs');
const S = require('./web/store.js');
const T = require('./web/theme.js');
const mem = { d: {}, getItem(k) { return k in this.d ? this.d[k] : null; }, setItem(k, v) { this.d[k] = String(v); }, removeItem(k) { delete this.d[k]; } };
const blocked = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
const at = (d, h, m = 0) => new Date(2026, 10, d, h, m);
const entry = (date) => ({ saved_at: date.toISOString(), reaction_ms: 300, sleep_hours: 7, mood_1to5: 4 });
const line = (now, ...saved) => T.dailyLine(now, saved.map(entry));
// The same file with another wake hour: the prompt must follow the constant, not a copied number.
const moved = { exports: {} };
new Function('module', fs.readFileSync('./web/theme.js', 'utf8').replace('SLEEP_END_HOUR = 6', 'SLEEP_END_HOUR = 7'))(moved);
S.add(entry(at(1, 8)), mem);
console.log(JSON.stringify({
  next: [line(at(1, 0)), line(at(1, T.SLEEP_END_HOUR - 1, 59)), line(at(1, 5), at(0, 23))],
  nextMoved: moved.exports.dailyLine(at(1, 6, 30), []),
  due: [line(at(1, T.SLEEP_END_HOUR)), line(at(1, 23, 59)), line(at(1, 9), at(0, 23))],
  dueBlocked: T.dailyLine(at(1, 9), S.load(blocked)),
  done: [T.dailyLine(at(1, 9), S.load(mem)), line(at(1, 7), at(1, 0, 30)), line(at(1, 23, 59), at(1, 6)), line(at(1, 5), at(1, 1))],
}));
"""


def daily() -> dict:
    """In Dhaka, a check saved before 06:00 local has yesterday's UTC date, so a date cut from saved_at would be wrong."""
    return json.loads(subprocess.run([NODE, "-e", DAILY_JS], capture_output=True, text=True, check=True,
                                     encoding="utf-8", env={**os.environ, "TZ": "Asia/Dhaka"}).stdout)


NEXT_LINE = "Next daily check: 06:00 (after the planned sleep window)."
DUE_LINE = "Today's daily check is due now."
DONE_LINE = "Today's daily check is done."


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_daily_prompt_before_the_wake_hour_gives_the_next_check_time():
    """PLAN 4c: the hour comes from SLEEP_END_HOUR in web/theme.js; yesterday's check does not count."""
    out = daily()
    assert out["next"] == [NEXT_LINE] * 3
    assert out["nextMoved"] == "Next daily check: 07:00 (after the planned sleep window)."
    assert not [p for p in BLOCKED if p in NEXT_LINE.lower()]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_daily_prompt_is_due_from_the_wake_hour_with_no_check_today_or_blocked_storage():
    out = daily()
    assert out["due"] == [DUE_LINE] * 3
    assert out["dueBlocked"] == DUE_LINE
    assert not [p for p in BLOCKED if p in DUE_LINE.lower()]
    html = Path("web/index.html").read_text(encoding="utf-8")
    guide = html[html.index('<section id="guide"'):html.index('<div class="guide">')]
    assert '<span class="meta">Simulated crew schedule</span><span id="daily-line"></span>' in guide, "first screen, above the self-check"
    app = Path("web/app.js").read_text(encoding="utf-8")
    assert 'put($("daily-line"), Theme.dailyLine(new Date(), log));' in app
    code = app + Path("web/theme.js").read_text(encoding="utf-8")
    for api in ("Notification", "setInterval", "serviceWorker", "wakeLock"):
        assert api not in code, f"{api}: on-screen only, nothing wakes the phone"


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_daily_prompt_is_done_once_a_check_is_saved_today():
    """Read through web/store.js. Local dates: a check saved at 00:30 in Dhaka is today, though its UTC date is yesterday."""
    out = daily()
    assert out["done"] == [DONE_LINE] * 4
    assert not [p for p in BLOCKED if p in DONE_LINE.lower()]


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
    queue = app[app.index("function summaryLines"):]
    assert re.search(r"lines\.push\(ROUNDING_NOTE\);\s*return lines;", queue)


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


QUEUE_LINE = "Added to the on-device queue. A reply can come up to 40 minutes later: up to 20 minutes each way at Mars distance."
QUEUE_SOURCE = "NASA Human Research Program, Hazard: Distance From Earth"
QUEUE_URL = "https://www.nasa.gov/hrp/hazard-distance-from-earth/"


def test_queue_says_on_device_and_agrees_with_the_demo_only_line():
    """Audit 11 Nov A5: nothing is sent, so the queue line must not say "Sent"; it says the queue is on the device,
    and the "Demo only: nothing leaves this device." line stays under the summary."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    queue = html[html.index('<section id="queue"'):html.index('<section id="alert"')]
    assert '<p class="sent">Added to the on-device queue. ' in queue
    assert "Sent to the queue" not in html + Path("web/app.js").read_text(encoding="utf-8")
    assert queue.index("on-device queue") < queue.index('<p class="meta">Demo only: nothing leaves this device.</p>')


def test_queue_line_gives_the_mars_delay_from_nasa():
    """NASA HRP, Distance from Earth: "up to 20 minutes one way" (https://www.nasa.gov/hrp/hazard-distance-from-earth/);
    the round trip is twice that. The old 22 and 44 had no source."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    queue = html[html.index('<section id="queue"'):html.index('<section id="alert"')]
    source = f'<p class="cite">Source: <a href="{QUEUE_URL}" target="_blank" rel="noopener noreferrer">{QUEUE_SOURCE}</a></p>'
    assert re.search(re.escape(f'<p class="sent">{QUEUE_LINE}</p>') + r"\s*" + re.escape(source), queue), "source directly under the line"
    assert not [p for p in BLOCKED if p in (QUEUE_LINE + " Source: " + QUEUE_SOURCE).lower()]
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "A reply can come up to 40 minutes later: up to 20 minutes each way at Mars distance." in readme
    for text in (html, readme, Path("web/app.js").read_text(encoding="utf-8")):
        assert not re.search(r"(22|44)[ -]minute", text)


def readme_source_rows() -> list[list[str]]:
    readme = Path("README.md").read_text(encoding="utf-8")
    start = readme.index("## Data sources")
    table = readme[start:readme.index("\n## ", start)]
    return [[c.strip() for c in line.strip("|").split("|")][:5]
            for line in table.splitlines() if line.startswith("| ") and not line.startswith("| Source |")]


def test_data_sources_panel_matches_the_readme_table_and_ends_with_not_covered():
    """PLAN 4b (W2) and A4: one panel line per README "Data sources" row, word for word (source, agency, used for,
    real or simulated, id or link), the same links, closed by default, and the README "Not covered" line last."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    start = html.index('<details id="sources" class="sources">')
    panel = html[start:html.index("</details>", start)]
    assert "<summary>Data sources</summary>" in panel and "open" not in panel.split(">", 1)[0]
    assert re.search(r"\.sources summary \{[^}]*min-height: 44px;", html)
    text = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
    lines = [text(li) for li in re.findall(r"<li>(.*?)</li>", panel, re.S)]
    md = lambda c: re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", c).replace("`", "")
    rows = readme_source_rows()
    assert len(rows) >= 11
    assert lines == [" · ".join(md(c) for c in row) for row in rows]
    links = re.findall(r'<a href="([^"]+)" target="_blank" rel="noopener noreferrer">', panel)
    assert links == [u for row in rows for u in re.findall(r"\]\(([^)]+)\)", row[4])]
    not_covered = next(l for l in Path("README.md").read_text(encoding="utf-8").splitlines() if l.startswith("Not covered:"))
    assert not_covered.startswith("Not covered: blood pressure and blood sugar. ")
    assert text(panel[panel.rindex("<p"):]) == not_covered, "the not-covered line is the panel's last line"
    assert not [p for p in BLOCKED if p in text(panel).lower()]


def test_inline_numbers_use_the_text_font_and_the_crew_badge_stays_on_one_line():
    """13 Nov (Hrishin): a number inside a sentence is set in the sentence's own font with tabular figures; the
    number font stays only where a value stands alone. The crew badge never wraps, and its column grows to fit it."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    n_rule = re.search(r"^\.n \{([^}]*)\}", html, re.M).group(1)
    assert "tabular-nums" in n_rule and "nowrap" in n_rule and "--mono" not in n_rule
    assert "#b1-reading .n, #b1-level .n { font-family: var(--mono); }" in html
    badge = re.search(r"^\.crew-count \{([^}]*)\}", html, re.M).group(1)
    assert "white-space: nowrap" in badge and "flex-shrink: 0" in badge and "var(--mono)" in badge and "font-size: 16px" in badge
    assert "grid-template-columns: minmax(200px, max-content) minmax(0, 1fr) auto" in html


def test_tablet_and_laptop_breakpoints_leave_the_phone_layout_alone():
    """13 Nov (Hrishin): one page fills a tablet (700 to 1099 px) and a laptop (1100 px and wider); under 700 px
    nothing changes. The wrappers are plain blocks on a phone and hold the same elements in the same order."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    style = html[html.index("<style>"):html.index("</style>")]
    queries = re.findall(r"@media \(([^)]*)\)", style)
    assert "min-width: 700px" in queries and "min-width: 1100px" in queries
    assert not [q for q in queries if "max-width" in q], "no rule aimed below 700 px"
    for name in ("check-cols", "charts", "ev-cols"):
        assert not re.search(r"(^|\})\s*\." + name + r"\s*\{", style.split("@media (min-width: 700px)")[0]), f".{name} styled outside the breakpoints"
    tablet = style[style.index("@media (min-width: 700px) {\n  .top, main"):]
    assert ".charts .channel.bottom { grid-column: 1 / -1; }" in tablet, "reaction time spans the last row"
    order = lambda *ids: [html.index(i) for i in ids] == sorted(html.index(i) for i in ids)
    assert order('class="check-cols"', 'class="check-rt"', 'id="rt-field"', 'id="rt-recorded"', 'id="rt-again"', 'class="check-rest"', 'id="sleep"', 'id="note"', 'id="vision-blurred"', 'id="missing"')
    assert order('class="charts"', 'data-signal="heart_rate_bpm"', 'data-signal="reaction_ms"', 'id="radiation"')
    assert order('class="ev-cols"', 'class="ev-a"', 'id="ev-plain"', 'id="ev-numbers"', 'id="ev-maths"', 'class="ev-b"', 'id="ev-words"', 'id="ev-step"', 'id="ev-source"')
