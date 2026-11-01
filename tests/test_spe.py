"""Solar storm alert (design B1): the live alert follows the Python rule, the replay uses NOAA's listed values,
and every line on the card passes the wording check."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from baseline.compute.radiation import spe_flag
from baseline.compute.wording import blocks_diagnostic
from baseline.evidence import load_evidence_map

NODE = shutil.which("node")
JS = (
    "const S = require('./web/spe.js');"
    "const a = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
    "const [before, ...cards] = S.replay(a.event, a.e);"
    "console.log(JSON.stringify({"
    " live: a.readings.map((r) => { const c = S.live(r, a.e); return c && S.lines(c); }),"
    " before, replay: cards.map(S.lines) }))"
)
EVENT = "cache/noaa/spe-2024-09-09.json"


def reading(flux: float) -> dict:
    """The fields scripts/build_radiation_summary.py writes, with fired decided by the Python rule."""
    flag = spe_flag([{"time_tag": "2026-09-30T09:30:00Z", "satellite": 18, "flux": flux, "energy": ">=10 MeV"}])
    return {"time_tag": flag["time_tag"], "flux_pfu": flag["current"], "threshold_pfu": flag["threshold_pfu"], "fired": flag["fired"],
            "fetched_at": "2026-09-30T09:40:58+00:00", "source_url": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-7-day.json"}


def run(readings: list[dict]) -> dict:
    data = {"readings": readings, "event": json.loads(Path(EVENT).read_text()), "e": load_evidence_map()["solar_particle_event"]}
    out = subprocess.run([NODE, "-e", JS], input=json.dumps(data), capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_alert_shows_at_exactly_10_pfu_and_not_at_9_99():
    at, below, today = run([reading(10.0), reading(9.99), json.loads(Path("web/data/radiation.json").read_text())])["live"]
    assert at is not None and "Solar protons at 10 MeV or more: 10 pfu" in at
    assert below is None
    assert today is None, "today's cache is below S1, so the console stays as it is"


def test_replay_file_holds_noaa_listed_values():
    ev = json.loads(Path(EVENT).read_text())
    assert (ev["start"], ev["maximum"], ev["peak_pfu"], ev["level"], ev["threshold_pfu"]) == \
        ("2024-09-09T16:40:00Z", "2024-09-09T22:50:00Z", 34, "S1", 10)
    urls = [s["url"] for s in ev["sources"]]
    assert "ftp://ftp.swpc.noaa.gov/pub/indices/SPE.txt" in urls
    assert any("listserver.ips.gov.au" in u for u in urls)
    assert ev["fetched_at"]
    assert json.loads(Path("web/data/spe-2024-09-09.json").read_text()) == ev, "copy the cache file to web/data/"


def test_evidence_map_has_the_step_and_both_sources():
    e = load_evidence_map()["solar_particle_event"]
    assert e["countermeasure"] == "Go to the storm shelter."
    assert "OCHMO-TB-020 Rev E" in e["countermeasure_source"]
    assert "https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf" in e["countermeasure_source"]
    assert "[V2 6100]" in e["alert_source"]
    assert "https://www.nasa.gov/wp-content/uploads/2020/10/2022-04-08_nasa-std-3001_vol_2_rev_c_final.pdf" in e["alert_source"]
    assert "https://www.swpc.noaa.gov/phenomena/solar-radiation-storm" in e["threshold_source"]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_every_alert_line_passes_the_wording_check():
    out = run([reading(12.0)])
    start, maximum = out["replay"]
    assert "Solar protons at 10 MeV or more: 34 pfu" in maximum
    assert any("16:40 UTC, 9 September 2024" in line for line in start)
    assert any("22:50 UTC, 9 September 2024" in line for line in maximum)
    assert all("not today's data" in " ".join(card) for card in (start, maximum))
    for line in [out["before"], *out["live"][0], *start, *maximum]:
        assert not blocks_diagnostic(line), line
        assert "all-clear" not in line.lower(), line


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_solar_alert_shows_the_strength_line_under_its_sources():
    """PLAN A2: on the live alert and on both replay cards, last of all, after every source line."""
    line = "Evidence strength: NASA technical brief and standard, not a study."
    out = run([reading(12.0)])
    for card in (out["live"][0], *out["replay"]):
        assert card[-1] == line
        assert card[-2].startswith("Source: NOAA GOES")
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert re.search(r'<p id="b1-source" class="meta cite"></p>\s*<p id="b1-strength" class="meta cite"></p>', html)
    assert 'put($("b1-strength"), c.strength);' in Path("web/app.js").read_text(encoding="utf-8")


def alert_html() -> str:
    html = Path("web/index.html").read_text(encoding="utf-8")
    return html[html.index('<section id="alert"'):html.index("</section>", html.index('<section id="alert"'))]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_alert_order_is_title_then_step_then_reading_level_and_time():
    """PLAN A5: lines() and the page give the same order, so reading order follows what is seen."""
    out = run([reading(12.0)])
    for card in (out["live"][0], *out["replay"]):
        assert card[1:3] == ["Shelter now", "Go to the storm shelter."]
        assert card[3].startswith("Solar protons at 10 MeV or more:")
        assert "NOAA S1 level" in card[4]
        assert " – " in card[5] and "UTC" in card[5]
        assert card[6].startswith("Source for the step:")
    html = alert_html()
    order = ['id="alert-title"', 'id="b1-step"', 'id="b1-reading"', 'id="b1-level"', 'id="b1-when"', 'id="b1-details"']
    positions = [html.index(mark) for mark in order]
    assert positions == sorted(positions), "the page order is the reading order"
    sizes = {name: int(re.search(selector + r" \{[^}]*font-size: (\d+)px", Path("web/index.html").read_text(encoding="utf-8")).group(1))
             for name, selector in {"title": "#alert h1", "step": "#b1-step", "reading": "#b1-reading"}.items()}
    assert sizes["title"] > sizes["step"] > sizes["reading"], "the step is the largest text after the title"
    assert '<h1 id="alert-title" tabindex="-1">Shelter now</h1>' in html


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_every_source_and_the_strength_line_sit_inside_the_closed_sources_control():
    """PLAN A5: closed by default, 44 px; the replay note stays outside it, and the control closes again on a new alert."""
    html = alert_html()
    box = html[html.index('<details id="b1-details" class="alert-sources">'):html.index("</details>")]
    assert "<summary>Sources</summary>" in box and "open" not in box.split(">", 1)[0]
    for inside in ('id="b1-sources"', 'id="b1-source"', 'id="b1-strength"'):
        assert inside in box and html.count(inside) == 1, inside
    full = Path("web/index.html").read_text(encoding="utf-8")
    assert re.search(r"\.alert-sources summary \{[^}]*min-height: 44px;", full)
    assert 'id="b1-when"' not in box, "the time line, with the replay note, stays outside the control"
    for card in run([reading(12.0)])["replay"]:
        assert "Replay of a real 2024 event, not today's data." in card[5]
        assert not [line for line in card[:6] if line.startswith(("Source", "Event values", "Evidence strength"))], "no source line outside"
        assert all(line.startswith(("Source", "Event values", "Evidence strength")) for line in card[6:])
    app = Path("web/app.js").read_text(encoding="utf-8")
    assert '$("b1-details").open = false;' in app[app.index("function showAlert"):app.index("// Replay: NOAA")]
