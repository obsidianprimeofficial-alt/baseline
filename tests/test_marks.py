"""PLAN A6: "Mark step done" on the evidence card and its line on day 30. Runs the page's own scripts in node
with a small stand-in for the DOM and for the browser's storage, and presses the page's own buttons."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.wording import blocks_diagnostic

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

MARK, UNDO = "Mark step done", "Undo step done"
DONE_TODAY = "Step done, "  # then the date and time from when(), then ", device time."
NOTE = "Not saved: this browser blocks storage, so this mark is kept for this visit only."
MARKED, NOT_MARKED = "Step marked done on day 29.", "Step not marked done."

HARNESS = r"""
const vm = require('vm'), fs = require('fs');
class El {
  constructor() { this.children = []; this.hidden = false; this.listeners = {}; this.dataset = {}; this.text = ''; this.value = ''; this.classList = { toggle() {} }; }
  get textContent() { return this.text + this.children.map((c) => (typeof c === 'string' ? c : c.textContent)).join(''); }
  set textContent(v) { this.text = String(v); this.children = []; }
  append(...c) { this.children.push(...c); }
  replaceChildren(...c) { this.text = ''; this.children = c; }
  setAttribute() {}
  getAttribute() { return null; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  click() { for (const f of this.listeners.click || []) f({ type: 'click', target: this }); }
  focus() {}
  querySelector() { return new El(); }
}
const ANSWERS = { quality: '2', mood: '4', vision: 'clear' };
const mem = () => ({ d: {}, getItem(k) { return k in this.d ? this.d[k] : null; }, setItem(k, v) { this.d[k] = String(v); }, removeItem(k) { delete this.d[k]; } });
const blocked = () => ({ getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } });

async function page(storage) {
  const els = {}, sel = {}, errors = [];
  const document = {
    documentElement: new El(), body: new El(), fonts: { load: async () => {} }, addEventListener() {},
    getElementById: (id) => els[id] || (els[id] = new El()), createElement: () => new El(), querySelectorAll: () => [],
    querySelector: (q) => { const m = q.match(/name="(\w+)"\]:checked/); return m ? { value: ANSWERS[m[1]] } : sel[q] || (sel[q] = new El()); },
  };
  class Chart { destroy() {} }
  Chart.defaults = {};
  const box = {
    document, Chart, localStorage: storage, setTimeout, clearTimeout, performance, URL, Blob,
    console: { error: (...a) => errors.push(a.join(' ')), log() {} },
    history: { replaceState() {}, pushState() {} }, addEventListener() {}, scrollTo() {},
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    fetch: async (p) => ({ json: async () => JSON.parse(fs.readFileSync('web/' + p, 'utf8')) }),
  };
  box.window = box;
  vm.createContext(box);
  // 03:04 UTC is 09:04 in Asia/Dhaka: the clock the page reads when nothing passes it a date.
  vm.runInContext("const RealDate = Date; globalThis.Date = class extends RealDate { constructor(...a) { a.length ? super(...a) : super('2026-11-02T03:04:00.000Z'); } };", box);
  for (const f of ['theme', 'rules', 'trend', 'projection', 'maths', 'mars', 'spe', 'reaction', 'store', 'app']) vm.runInContext(fs.readFileSync(`web/${f}.js`, 'utf8'), box);
  await new Promise((r) => setTimeout(r, 30));
  const $ = document.getElementById, run = (code) => vm.runInContext(code, box);
  return {
    $, run, errors,
    check() { $('rt-recorded').click(); $('sleep').valueAsNumber = 5; $('save').click(); },
    card(signal) { run(`renderEvidence(flagsFor(state.day).find((r) => ${signal ? `r.signal === "${signal}"` : '!r.signal'}));`); },
    open() { $('saved-open').click(); },
    nextDay() { $('next-day').click(); },
    view() {
      return { button: $('ev-mark').textContent, buttonHidden: $('ev-mark').hidden, line: $('ev-mark-line').hidden ? null : $('ev-mark-line').textContent, note: !$('ev-mark-note').hidden };
    },
    follow() { return $('follow-list').children.map((li) => li.children.at(-1).textContent); },
  };
}
(async () => { const out = await (async () => { BODY })(); console.log(JSON.stringify(out)); })().catch((e) => { console.error(e); process.exit(1); });
"""


def run(body: str):
    out = subprocess.run([NODE, "-e", HARNESS.replace("BODY", body)], capture_output=True, text=True, encoding="utf-8",
                         check=True, cwd=Path(__file__).parents[1], env={**os.environ, "TZ": "Asia/Dhaka"})
    return json.loads(out.stdout)


def test_mark_shows_the_step_as_done_with_the_device_local_time():
    out = run("""
const p = await page(mem()); p.check(); p.card('reaction_ms');
const before = p.view(); p.$('ev-mark').click();
return { before, after: p.view(), errors: p.errors };
""")
    assert out["before"] == {"button": MARK, "buttonHidden": False, "line": None, "note": False}
    assert out["after"]["button"] == UNDO
    assert out["after"]["line"].startswith(DONE_TODAY) and out["after"]["line"].endswith(", device time.")
    assert "09:04" in out["after"]["line"], "03:04 UTC is 09:04 on a device in Asia/Dhaka"
    assert out["after"]["note"] is False and out["errors"] == []


def test_every_card_with_a_step_has_the_button_and_each_card_keeps_its_own_mark():
    out = run("""
const p = await page(mem()); p.check(); p.card('reaction_ms'); p.$('ev-mark').click();
const cards = p.run('flagsFor(state.day).map((r) => r.signal || "")').map((s) => { p.card(s); return { s, ...p.view() }; });
return { cards };
""")
    assert sorted(c["s"] for c in out["cards"]) == ["", "hrv_rmssd_ms", "reaction_ms", "sleep_hours"], "three signals and the 48-hour row"
    assert all(not c["buttonHidden"] for c in out["cards"])
    assert {c["s"]: c["button"] for c in out["cards"]} == {"": MARK, "hrv_rmssd_ms": MARK, "reaction_ms": UNDO, "sleep_hours": MARK}


def test_button_sits_under_the_guidance_step_at_44_px():
    html = Path("web/index.html").read_text(encoding="utf-8")
    card = html[html.index('<div class="step-card">'):html.index('<p id="ev-source"')]
    assert card.index("<h2>Guidance</h2>") < card.index('id="ev-step"') < card.index('id="ev-mark"') < card.index('id="ev-mark-line"') < card.index('id="ev-mark-note"')
    assert '<button id="ev-mark" class="secondary" type="button">Mark step done</button>' in card
    assert re.search(r"#ev-mark \{[^}]*min-height: 44px;", html)


def test_pressing_again_undoes_the_mark_also_after_a_reload():
    out = run("""
const s = mem(), p = await page(s); p.check(); p.card('reaction_ms');
p.$('ev-mark').click(); p.$('ev-mark').click();
const undone = p.view(), stored = s.d['baseline.marks.v1'];
const q = await page(s); q.open(); q.card('reaction_ms');
return { undone, stored, reloaded: q.view() };
""")
    assert out["undone"] == {"button": MARK, "buttonHidden": False, "line": None, "note": False}
    assert json.loads(out["stored"]) == {}
    assert out["reloaded"]["button"] == MARK


def test_mark_is_kept_after_a_reload_and_reaches_day_30():
    out = run("""
const s = mem(), p = await page(s); p.check(); p.card('reaction_ms'); p.$('ev-mark').click();
const first = p.view().line;
const q = await page(s); q.open(); q.card('reaction_ms');
const reloaded = q.view(); q.nextDay();
return { first, reloaded, follow: q.follow() };
""")
    assert out["reloaded"]["button"] == UNDO and out["reloaded"]["line"] == out["first"]
    assert MARKED in out["follow"]


@pytest.mark.parametrize("button", ["saved-clear", "clear-saved"])
def test_clear_saved_days_clears_the_marks(button):
    """The first screen's button and the console's. Nothing comes back after a reload."""
    out = run(f"""
const s = mem(), p = await page(s); p.check(); p.card('reaction_ms'); p.$('ev-mark').click();
p.$('{button}').click();
const cleared = p.view(), stored = 'baseline.marks.v1' in s.d, log = 'baseline.log.v1' in s.d;
const q = await page(s);
return {{ cleared, stored, log, marks: q.run('state.marks') }};
""")
    assert out["cleared"]["button"] == MARK and out["cleared"]["line"] is None
    assert out["stored"] is False and out["log"] is False
    assert out["marks"] == {}


def test_clear_saved_days_on_day_30_redraws_the_follow_up_lines():
    out = run("""
const p = await page(mem()); p.check(); p.card('reaction_ms'); p.$('ev-mark').click(); p.nextDay();
const before = p.follow(); p.$('clear-saved').click();
return { before, after: p.follow() };
""")
    assert MARKED in out["before"]
    assert out["after"] == [NOT_MARKED] * 3


def test_start_the_demo_again_clears_the_marks_and_keeps_the_saved_log():
    """As today, the button resets the demo and keeps the saved log; a second run must not start with old ticks."""
    out = run("""
const s = mem(), p = await page(s); p.check(); p.card('reaction_ms'); p.$('ev-mark').click(); p.nextDay();
p.$('restart').click();
const stored = 'baseline.marks.v1' in s.d, log = JSON.parse(s.d['baseline.log.v1']).length;
p.open(); p.card('reaction_ms');
return { stored, log, view: p.view() };
""")
    assert out["stored"] is False and out["log"] == 1
    assert out["view"]["button"] == MARK and out["view"]["line"] is None


def test_a_new_self_check_starts_with_no_marks():
    """A mark belongs to the check it was pressed on; an old tick must not sit on a newly raised flag."""
    out = run("""
const s = mem(), p = await page(s); p.check(); p.card('reaction_ms'); p.$('ev-mark').click();
p.check(); p.card('reaction_ms');
return { view: p.view(), stored: s.d['baseline.marks.v1'] };
""")
    assert out["view"]["button"] == MARK and out["view"]["line"] is None
    assert "stored" not in out, "removed from the device, so a reload cannot bring it back"


def test_day_30_row_says_whether_the_step_was_marked_both_ways():
    out = run("""
const p = await page(mem()); p.check(); p.card('reaction_ms'); p.$('ev-mark').click(); p.nextDay();
const rows = p.$('follow-list').children.map((li) => li.textContent);
const names = p.$('follow-list').children.map((li) => li.children[0].textContent);
return { names, follow: p.follow(), rows };
""")
    by_name = dict(zip(out["names"], out["follow"]))
    assert by_name == {"Heart rate variability": NOT_MARKED, "Sleep": NOT_MARKED, "Reaction time": MARKED}
    assert all("yesterday" in r and "today." in r for r in out["rows"]), "the row keeps its recovery sentence"


def test_day_30_row_does_not_count_a_mark_pressed_on_a_day_30_card():
    """Marks are kept per day and rule. The demo's day-30 mood flag has no day-29 row, so press its rule under day 30 by hand."""
    out = run("""
const p = await page(mem()); p.check(); p.nextDay();
p.run('state.marks["30:reaction_above_personal_baseline"] = "2026-11-02T03:04:00.000Z"; renderFollowUp();');
return { follow: p.follow() };
""")
    assert out["follow"] == [NOT_MARKED] * 3


def test_blocked_storage_the_mark_works_for_this_visit_and_the_card_says_so():
    out = run("""
const s = blocked(), p = await page(s); p.check(); p.card('reaction_ms');
const before = p.view(); p.$('ev-mark').click();
const marked = p.view(); p.nextDay();
const follow = p.follow(); p.card('mood_1to5');
const q = await page(s);
return { before, marked, follow, reloaded: q.run('state.marks'), errors: p.errors };
""")
    assert out["before"]["note"] is False, "nothing to say until something is marked"
    assert out["marked"]["button"] == UNDO and out["marked"]["line"].startswith(DONE_TODAY) and out["marked"]["note"] is True
    assert f'<p id="ev-mark-note" class="meta" hidden>{NOTE}</p>' in Path("web/index.html").read_text(encoding="utf-8")
    assert MARKED in out["follow"], "day 30 still sees the mark in the same visit"
    assert out["reloaded"] == {}
    assert out["errors"] == []


def test_marks_in_store_js_are_wrapped_and_damaged_storage_is_ignored():
    out = run("""
const S = (await page(mem())).run('Store'), s = mem();
s.setItem(S.MARKS_KEY, '{not json'); const a = S.loadMarks(s);
s.setItem(S.MARKS_KEY, '[1]'); const b = S.loadMarks(s);
s.setItem(S.MARKS_KEY, JSON.stringify({ '29:x': '2026-11-02T03:04:00.000Z', '29:y': 7, '29:z': 'soon' })); const c = S.loadMarks(s);
const d = blocked();
return { a, b, c, load: S.loadMarks(d), save: S.saveMarks({ k: 'v' }, d), clear: S.clearMarks(d), ok: S.saveMarks({ k: 'v' }, s) };
""")
    assert out == {"a": {}, "b": {}, "c": {"29:x": "2026-11-02T03:04:00.000Z"}, "load": {}, "save": False, "clear": False, "ok": True}


def test_new_copy_passes_the_wording_check():
    """The Python list here; the JS port is the same list (test_js_rule_matches_python) and put() runs it on every line shown."""
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert NOTE in html, "static text, so the page's own check of its body text reads it too"
    out = run("""
const p = await page(mem()); p.check(); p.card('reaction_ms'); p.$('ev-mark').click();
const line = p.view().line, button = p.view().button; p.nextDay();
return { line, button, follow: p.follow() };
""")
    for text in [MARK, UNDO, NOTE, MARKED, NOT_MARKED, out["line"], out["button"], *out["follow"]]:
        assert blocks_diagnostic(text) == [], text
        assert "Withheld" not in text
