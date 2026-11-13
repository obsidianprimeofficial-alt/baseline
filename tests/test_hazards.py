"""PLAN item 5, design B3: mission-phase risks under the five HRP hazards. Static text in web/index.html, display only.
The sentences below were matched against the sources opened 4 Nov 2026; they must reach the screen unedited."""

import json
import re
from html import unescape
from pathlib import Path

from baseline.compute.wording import BLOCKED, blocks_diagnostic
from tests.test_marks import pytestmark as needs_node, run

HRP = "https://www.nasa.gov/hrp/"
STD = "https://www.nasa.gov/wp-content/uploads/2020/10/2022-04-08_nasa-std-3001_vol_2_rev_c_final.pdf"
OSTEO = "https://humanresearchroadmap.nasa.gov/evidence/reports/Osteo.pdf"
HEADINGS = ["Space radiation", "Isolation and confinement", "Distance from Earth", "Gravity fields", "Hostile closed environments"]
SENTENCES = {
    "Space radiation": ('"Invisible to the human eye, space radiation is not only stealthy but considered one of the most hazardous aspects of spaceflight."', HRP + "hazards/"),
    "Isolation and confinement": ('"Behavioral responses occur among groups of people far from Earth who are isolated and confined in a small space over a long period of time."', HRP + "hazard-isolation-and-confinement/"),
    "Distance from Earth": ('"Instructions, new supplies, medical care, and more become increasingly challenging to receive from Earth as astronauts venture deeper into space."', HRP + "hazard-distance-from-earth/"),
    "Gravity fields": ('"Floating weightlessly within a spacecraft can lead to dizziness, bone and muscle loss, vision issues, and more."', HRP + "hazard-gravity-fields/"),
    "Hostile closed environments": ('"Maintaining a safe ecosystem inside a vehicle presents unique challenges, from ensuring optimal temperatures, pressures, and lighting, to reducing noise, monitoring microbial communities, and tracking immune responses."', HRP + "hazard-hostile-closed-environments/"),
}
# Label, chip, figure line, then every (link text, URL) the card must carry.
RISKS = [
    ("Space adaptation syndrome", "Day 29: usually past",
     '"Space Adaptation Syndrome (SAS) occurs in up to 70% of first-time fliers (30% of whom may experience vomiting) during the first 48 to 72 hours of microgravity."',
     [("NASA-STD-3001 Vol 2 Rev C, [V2 7102] rationale, p.96", STD)]),
    ("Headward fluid shift", "Day 29: ongoing",
     "The total fluid shift was reported to be 2 L, most of it in the first 6 to 10 hours after entering microgravity.",
     [("NTRS 20180000936, Evidence Report: Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS), pp.69–70", "https://ntrs.nasa.gov/citations/20180000936"),
      ("NTRS 20140003729, Evidence Report: Risk of Decompression Sickness (DCS), p.11", "https://ntrs.nasa.gov/citations/20140003729")]),
    ("Bone loss", "Day 29: ongoing",
     '"Without the continuous load of Earth’s gravity, weight-bearing bones lose on average 1% to 1.5% of mineral density per month during spaceflight."',
     [("NASA Human Research Program, Hazard: Gravity Fields", HRP + "hazard-gravity-fields/"),
      ("NASA Evidence Report: Risk of Early Onset Osteoporosis Due to Space Flight, p.21", OSTEO)]),
]
ARED = "With resistive exercise on ARED, hip and spine loss has been reduced to 0.3 to 0.5% per month."


def html() -> str:
    return Path("web/index.html").read_text(encoding="utf-8")


def panel() -> str:
    h = html()
    start = h.index('<details id="hazards"')
    return h[start:h.index("</details>", start)]


def words(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def links(fragment: str) -> list[tuple[str, str]]:
    return [(words(t), u) for u, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', fragment)]


def lines() -> list[str]:
    """Every on-screen line: each element's own text."""
    return [words(t) for t in re.findall(r"<(?:summary|h3|h4|p|strong|span)\b[^>]*>(.*?)</(?:summary|h3|h4|p|strong|span)>", panel(), re.S)]


def sections() -> dict[str, str]:
    found = re.findall(r"<section>(.*?)</section>", panel(), re.S)
    return {words(re.search(r"<h4>(.*?)</h4>", s).group(1)): s for s in found}


def test_panel_is_closed_titled_and_sits_between_skylab_and_data_sources():
    h = html()
    assert "open" not in panel().split(">", 1)[0]
    assert h.index('id="skylab"') < h.index('id="hazards"') < h.index('id="sources"')
    assert "<summary>Mission-phase risks</summary>" in panel() and "<h3>Day 29 of flight</h3>" in panel()
    assert "All data cached – no live feed" in h.split('id="hazards"')[0], "design B3's line comes from the page header"
    assert "Simulated data" not in panel()
    assert "The day 29 lines are our reading of NASA's timings." in panel()


def test_five_headings_in_the_statements_order_each_with_its_nasa_sentence_and_link():
    s = sections()
    assert list(s) == HEADINGS
    for heading, (sentence, url) in SENTENCES.items():
        assert sentence in lines(), heading
        assert links(s[heading])[0][1] == url, heading
    assert "“" not in panel() and "..." not in panel() and "…" not in panel(), "no NASA sentence is cut"


def test_three_risks_sit_under_gravity_fields_with_nasas_numbers_status_and_sources():
    gravity, on_screen = sections()["Gravity fields"], lines()
    cards = re.findall(r'<div class="trend-card">(.*?)\n\s*</div>\n', gravity, re.S)
    assert len(cards) == 3
    for card, (label, chip, figure, sources) in zip(cards, RISKS):
        assert f"<strong>{label}</strong>" in card and f'<span class="chip">{chip}</span>' in card, label
        assert figure in [words(p) for p in re.findall(r"<p>(.*?)</p>", card, re.S)], label
        assert links(card) == sources, label
    assert ARED in on_screen
    for other in set(HEADINGS) - {"Gravity fields"}:
        assert 'class="chip"' not in sections()[other], other


def test_only_nasas_figures_and_no_running_bone_total():
    text = words(panel())
    assert sorted(set(re.findall(r"[\d.]+(?= ?%)", text))) == ["0.5", "1", "1.5", "30", "70"]
    assert not re.search(r"60 to 80|1\.5 to 2 lit|\blitres?\b|per cent|so far|in total|total bone", text, re.I)
    assert text.count("per month") == 2, "a rate per month, never a running total for day 29"


@needs_node
def test_every_line_passes_the_wording_check_in_python_and_on_the_page():
    on_screen = lines()
    assert len(on_screen) > 20
    for line in on_screen:
        assert blocks_diagnostic(line) == [], line
    text = words(panel())
    assert blocks_diagnostic(text) == []
    out = run(f"const p = await page(mem()); return {{ hits: p.run({json.dumps('Rules.blocksDiagnostic(' + json.dumps(text) + ')')}) }};")
    assert out["hits"] == []


def test_sm_caveat_stays_off_and_symptom_stays_blocked():
    assert "SM.pdf" not in panel() and "symptom" not in panel().lower() and "cosmonaut" not in panel().lower()
    assert "symptom" in BLOCKED


def test_sources_are_on_the_card_only():
    """D10: no Data sources row and no README row for these sources."""
    h = html()
    start = h.index('<details id="sources"')
    data_sources = h[start:h.index("</details>", start)]
    readme = Path("README.md").read_text(encoding="utf-8")
    for only_here in (OSTEO, "20140003729", "20180000936", "hazard-gravity-fields", "/hrp/hazards"):
        assert only_here in panel(), only_here
        assert only_here not in data_sources and only_here not in readme, only_here


@needs_node
def test_panel_shows_on_day_29_only():
    """Its text is about day 29, so the day 30 console does not carry it."""
    out = run("""
const p = await page(mem()); p.check(); const d29 = p.$('hazards').hidden;
p.run('recompute(NEXT)'); const d30 = p.$('hazards').hidden;
p.run('recompute(TODAY)'); return { d29, d30, back: p.$('hazards').hidden, errors: p.errors };
""")
    assert out == {"d29": False, "d30": True, "back": False, "errors": []}
