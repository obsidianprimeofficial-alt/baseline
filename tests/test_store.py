"""The daily log kept on the device (web/store.js): saved, kept after a reload, cleared, exported.
Runs the file in node with a stand-in for the browser's storage."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.wording import blocks_diagnostic

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

SETUP = """
const S = require('./web/store.js');
const mem = () => ({ d: {}, getItem(k) { return k in this.d ? this.d[k] : null; }, setItem(k, v) { this.d[k] = String(v); }, removeItem(k) { delete this.d[k]; } });
const blocked = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
const check = (i) => ({ saved_at: `2026-10-27T0${i}:00:00.000Z`, reaction_ms: 300 + i, reaction_recorded: false, sleep_hours: 7, sleep_quality_1to5: 3, mood_1to5: 4, near_vision_ok: true, note: '', heart_rate_bpm: 99 });
"""


def run(body: str):
    out = subprocess.run([NODE, "-e", SETUP + body], capture_output=True, text=True, check=True, cwd=Path(__file__).parents[1])
    return json.loads(out.stdout)


def test_saved_check_survives_a_reload_and_clear_removes_it():
    out = run("""
const s = mem();
const kept = [S.add(check(1), s), S.add(check(2), s)];
const afterReload = S.load(s);          // a reload reads the same storage again
const latest = S.latest(s);
S.clear(s);
console.log(JSON.stringify({ kept, afterReload, latest, afterClear: S.load(s) }));
""")
    assert out["kept"] == [True, True]
    assert [e["reaction_ms"] for e in out["afterReload"]] == [301, 302]
    assert out["latest"]["saved_at"] == "2026-10-27T02:00:00.000Z"
    assert "heart_rate_bpm" not in out["latest"], "only self-check fields are stored; wearable values stay simulated"
    assert out["afterClear"] == []


def test_blocked_storage_never_breaks_the_page():
    out = run("console.log(JSON.stringify({ kept: S.add(check(1), blocked), load: S.load(blocked), latest: S.latest(blocked), clear: S.clear(blocked) }));")
    assert out == {"kept": False, "load": [], "latest": None, "clear": False}


def test_damaged_or_foreign_storage_is_ignored():
    out = run("""
const s = mem(); s.setItem(S.KEY, '{not json'); const a = S.load(s);
s.setItem(S.KEY, JSON.stringify([{ saved_at: 'x', reaction_ms: 'fast' }, check(3)])); const b = S.load(s);
console.log(JSON.stringify({ a, b: b.length }));
""")
    assert out == {"a": [], "b": 1}


def test_log_keeps_at_most_max_entries():
    out = run("const s = mem(); for (let i = 0; i < S.MAX + 5; i++) S.add({ ...check(1), saved_at: 'n' + i }, s); const l = S.load(s); console.log(JSON.stringify([l.length, S.MAX, l[0].saved_at]));")
    assert out == [out[1], out[1], "n5"]


def test_csv_marks_every_row_and_never_starts_a_formula():
    out = run("""
const shown = [{ day: 1, heart_rate_bpm: 60 }, { day: 29, self_check: true, saved_at: 's2', reaction_ms: 338.3, note: '=HYPERLINK("x"), woke at 03:00' }];
const saved = [{ saved_at: 's1', reaction_ms: 300, sleep_hours: 7, mood_1to5: 4 }, { saved_at: 's2', reaction_ms: 338.3, sleep_hours: 5, mood_1to5: 4 }];
const unsaved = [{ day: 29, self_check: true, reaction_ms: 1, sleep_hours: 1, mood_1to5: 1 }];
console.log(JSON.stringify({ text: S.csv(shown, saved), unsaved: S.csv(unsaved, []), columns: S.COLUMNS }));
""")
    lines = out["text"].split("\r\n")
    assert lines[0] == ",".join(out["columns"])
    assert lines[1].startswith("1,simulated,")
    assert lines[2].startswith("29,self-check saved on this device; wearable columns simulated,s2,")
    assert "\"'=HYPERLINK(\"\"x\"\"), woke at 03:00\"" in lines[2]
    assert lines[3].startswith(",earlier self-check saved on this device,s1,"), "the check already on screen is not listed twice"
    assert len([l for l in lines if l]) == 4
    assert "self-check (not saved)" in out["unsaved"]
    assert blocks_diagnostic(out["text"] + out["unsaved"]) == []


def test_page_saves_on_save_and_offers_the_log():
    app = Path("web/app.js").read_text(encoding="utf-8")
    save = app[app.index('$("save").addEventListener'):app.index("// ---------- the daily log")]
    assert "openCheck(check, Store.add(check))" in save
    init = app[app.index("(async function init()"):]
    assert "renderSavedBox();" in init, "the saved box shows on the first screen after a reload"
    html = Path("web/index.html").read_text(encoding="utf-8")
    for el in ("saved-box", "saved-text", "saved-open", "saved-clear", "log", "saved-line", "export", "clear-saved"):
        assert f'id="{el}"' in html
    new_copy = re.sub(r"<[^>]+>", " ", html[html.index('<div id="saved-box"'):html.index("</section>", html.index('<div id="saved-box"'))]
                      + html[html.index('<div id="log"'):html.index("</section>", html.index('<div id="log"'))])
    strings = re.findall(r'"([^"]*(?:saved|Saved|device|cleared)[^"]*)"', app[app.index("// ---------- the daily log"):])
    assert blocks_diagnostic(new_copy + " ".join(strings)) == []
