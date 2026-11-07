"""Replay of the real 20 May 2024 Mars surface radiation surge (MSL RAD, Curiosity rover; private/mars_replay_2026-11-05.md §5).
The rule is not changed: the replay file is the rule's own output on the cached readings. The page shows it on the
existing caution card in replay mode, through the stand-in page in tests/test_marks.py."""

import importlib.util
import json
import re
from pathlib import Path

from baseline.compute.radiation import DOSE_COLUMN, daily_dose
from baseline.compute.wording import blocks_diagnostic
from tests.test_marks import run, pytestmark  # noqa: F401  # the same stand-in page; skipped without node

READINGS = Path("cache/msl_rad/rad-2024-04-20-to-05-25.json")
EVENT = Path("cache/msl_rad/mars-surge-2024-05-20.json")
WEB = Path("web/data/mars-surge-2024-05-20.json")
FORBIDDEN = re.compile(r"dose|shelter|withheld", re.I)
URLS = [
    "https://cdaweb.gsfc.nasa.gov/WS/cdasr/1/dataviews/sp_phys/datasets/MSL_RAD_OBS-L2/data/20240420T000000Z,20240526T000000Z/DOSIMETRY_TOTAL_f?format=json",
    "https://www.nasa.gov/solar-system/planets/mars/nasa-watches-mars-light-up-during-epic-solar-storm/",
    "https://wrmiss.org/workshops/twentyseventh/Hassler.pdf",
    "https://doi.org/10.1007/s11207-025-02482-4",
]


def builder():
    spec = importlib.util.spec_from_file_location("build_mars_surge", "scripts/build_mars_surge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def readings() -> dict:
    return json.loads(READINGS.read_text())


def event() -> dict:
    return json.loads(EVENT.read_text(encoding="utf-8"))


def test_event_file_equals_a_fresh_run_of_the_rule_on_the_cached_readings():
    ev = event()
    assert builder().build(readings()) == ev
    assert (ev["dose_ugy_day"], ev["n_obs"], ev["baseline_mean"], ev["baseline_sd"], ev["z"], ev["window_days"], ev["fired"]) == \
        (1881.0, 139, 161.0, 10.41, 165.17, 30, True)
    assert ev["date"] == "2024-05-20" and ev["before"] == {"date": "2024-05-19", "dose_ugy_day": 131.3, "baseline_mean": 162.1}


def test_36_days_none_dropped():
    rows, ev = readings()["data"], event()
    days = sorted({r["time_tag"][:10] for r in rows if not r["flagged"] and r[DOSE_COLUMN] is not None})
    assert len(days) == 36 and days[0] == "2024-04-20" and days[-1] == "2024-05-25"
    assert [d["date"] for d in daily_dose(rows)] == days == [d["date"] for d in ev["daily"]]


def test_19_may_does_not_fire_20_may_fires_21_may_does_not():
    b, daily = builder(), daily_dose(readings()["data"])
    assert [b.flag_on(daily, d)["fired"] for d in ("2024-05-19", "2024-05-20", "2024-05-21")] == [False, True, False]
    after = b.flag_on(daily, "2024-05-21")
    assert round(after["current"], 1) == 355.1 and round(after["baseline_sd"], 2) == 314.25, "the README sentence on 21 May"


def test_peak_is_the_largest_reading_at_06_15_19():
    good = [r for r in readings()["data"] if not r["flagged"] and r[DOSE_COLUMN] is not None]
    top = max(good, key=lambda r: r[DOSE_COLUMN])
    assert event()["peak"] == {"time_tag": top["time_tag"], "ugy_day": round(top[DOSE_COLUMN], 1)} == \
        {"time_tag": "2024-05-20T06:15:19Z", "ugy_day": 8377.9}


def test_web_copy_equals_the_cache_file():
    assert WEB.read_bytes() == EVENT.read_bytes()


def lines_and_screen() -> dict:
    return run("""
const p = await page(mem());
const lines = p.run('Mars.replayLines(state.marsSurge, state.evidence.mars_radiation_caution)');
p.$('mars-replay').click(); await new Promise((r) => setTimeout(r, 1600));
const ids = ['ev-replay', 'ev-title', 'ev-plain', 'ev-numbers', 'ev-extra', 'ev-words', 'ev-strength', 'ev-replay-list', 'ev-step', 'ev-step-source', 'ev-source', 'ev-rule', 'ev-back'];
return { lines, screen: ids.map((id) => p.$(id).textContent), before: p.$('mars-replay-line').textContent,
  js: lines.map((l) => p.run('Rules.blocksDiagnostic(' + JSON.stringify(l) + ')')), button: p.run('Mars.BUTTON'), errors: p.errors };
""")


def test_every_replay_line_passes_the_wording_check_in_python_and_js():
    out = lines_and_screen()
    assert out["errors"] == [] and len(out["lines"]) > 20
    assert all(hit == [] for hit in out["js"])
    for text in [*out["lines"], *out["screen"], out["before"]]:
        assert blocks_diagnostic(text) == [], text
        assert not FORBIDDEN.search(text), text
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert f'<button id="mars-replay" class="secondary" type="button">{out["button"]}</button>' in html


def test_replay_is_labelled_8100_is_always_the_peak_no_flare_class_no_chest():
    out = lines_and_screen()
    button, before, chip, *_ = out["lines"]
    label = "Replay of a real 2024 event, not today's data."
    for text in (button, before, chip, out["screen"][0], out["screen"][-3]):  # button, line, chip, chip on screen, note
        assert "replay" in text.lower(), text
    assert label in out["lines"] and label in out["screen"][4]
    readme = Path("README.md").read_text(encoding="utf-8")
    for text in [*out["lines"], *out["screen"], *readme.splitlines()]:
        if "8,100" in text:  # the article's figure always sits with the slides' "peak" (Q1, Hrishin 7 Nov)
            assert "peak" in text, text
        assert not re.search(r"\bX ?1[0-9]|flare class|chest", text, re.I), text


def test_replay_changes_nothing_live_no_queue_line_no_mark():
    out = run("""
const p = await page(mem()); p.check();
const live = JSON.stringify(p.run('state.radiation')), mars = p.$('mars-line').textContent;
p.$('mars-replay').click(); await new Promise((r) => setTimeout(r, 1600));
const inReplay = { queue: p.$('queue-btn').hidden, mark: p.$('ev-mark').hidden, back: p.$('ev-back').dataset.go, sources: p.$('ev-replay-sources').hidden,
  title: p.$('ev-title').textContent, key: p.run('state.markKey') };
p.$('ev-mark').click();  // even a press on the hidden button stores nothing
const stored = p.run('JSON.stringify(state.marks) + "|" + localStorage.getItem("baseline.marks.v1")');
p.card('reaction_ms');
const after = { queue: p.$('queue-btn').hidden, mark: p.$('ev-mark').hidden, back: p.$('ev-back').dataset.go, replay: p.$('ev-replay').hidden,
  extra: p.$('ev-extra').hidden, sources: p.$('ev-replay-sources').hidden };
p.$('queue-btn').click();
return { inReplay, stored, after, same: JSON.stringify(p.run('state.radiation')) === live, mars: p.$('mars-line').textContent === mars,
  queue: p.$('message').children.map((c) => c.textContent), caution: p.run('marsCaution()'), errors: p.errors };
""")
    assert out["inReplay"] == {"queue": True, "mark": True, "back": "console", "sources": False, "title": "Caution: Mars surface radiation", "key": None}
    assert out["stored"] in ("{}|null", "{}|{}")
    assert out["after"] == {"queue": False, "mark": False, "back": "flags", "replay": True, "extra": True, "sources": True}
    assert out["same"] and out["mars"] and out["caution"] is None
    assert not [l for l in out["queue"] if "Mars" in l] and out["errors"] == []


def test_replay_card_swaps_the_simulated_badge_for_the_replay_chip():
    """Hrishin, 7 Nov: on the replay card only, "Simulated data" is hidden and the replay chip shows, as on the solar alert."""
    out = run("""
const p = await page(mem()); p.check();
const head = () => ({ sim: p.run('document.querySelector(".sim").hidden'), day: p.$('day-label').hidden, chip: p.$('b1-chip').hidden ? null : p.$('b1-chip').textContent });
const console0 = head();
p.$('mars-replay').click(); await new Promise((r) => setTimeout(r, 1600));
const replay = head();
p.run('show(document.getElementById("ev-back").dataset.go)'); const back = head();  // the stand-in has no delegated data-go handler
p.card('reaction_ms'); p.run('show("evidence")'); const card = head();
return { console0, replay, back, card, errors: p.errors };
""")
    simulated = {"sim": False, "day": False, "chip": None}
    assert out["console0"] == out["back"] == out["card"] == simulated
    assert out["replay"] == {"sim": True, "day": True, "chip": "Replay – real NASA data"} and out["errors"] == []


def test_every_source_url_is_one_of_the_four():
    ev = event()
    assert [s["url"] for s in ev["sources"]] == URLS
    found = re.findall(r"https?://[^\s\"']+", EVENT.read_text(encoding="utf-8"))
    assert found and all(u.rstrip(",") in URLS for u in found)
