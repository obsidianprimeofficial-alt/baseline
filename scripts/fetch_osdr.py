"""Cache OSDR search results and list the top OSD hits as candidates for human review.

Writes cache/osdr/<slug>.json and appends a table to docs/EVIDENCE_candidates.md.
Never writes docs/evidence_map.json; that file is filled by hand after review.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

KEYWORDS = [
    "heart rate variability spaceflight",
    "sleep International Space Station",
    "cardiovascular microgravity",
    "cognitive performance spaceflight",
    "vision spaceflight SANS",
    "immune spaceflight",
    "bone loss microgravity",
]
SEARCH = "https://osdr.nasa.gov/osdr/data/search?"
STUDY = "https://osdr.nasa.gov/bio/repo/data/studies/OSD-{}"
STATUS = "candidate, research lead to review"
CANDIDATES = Path("docs/EVIDENCE_candidates.md")
HEADER = (
    "# Evidence candidates\n\n"
    "Raw OSDR search hits, not reviewed. Nothing here is evidence until a team member reads the study "
    "and copies it into docs/evidence_map.json by hand.\n"
)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def organism(value) -> str:
    """OSD hits give a string, some other records a list."""
    if isinstance(value, list):
        value = ", ".join(value)
    return value or "not given"


def cache(path: Path, url: str, data) -> str:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"source_url": url, "fetched_at": fetched_at, "data": data}, indent=1) + "\n")
    return fetched_at


def main() -> None:
    if os.environ.get("OFFLINE") == "1":
        sys.exit("OFFLINE=1: not fetching; cache/osdr is used as is.")
    sections = []
    for kw in KEYWORDS:
        url = SEARCH + urlencode({"term": kw, "from": 0, "size": 25})
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        hits = data["hits"]["hits"]
        for h in hits:
            if "Accession" not in h.get("_source", {}) or "Study Title" not in h["_source"]:
                print(json.dumps(h, indent=1)[:4000])
                sys.exit("OSDR hit shape differs from expected; stopping instead of guessing field names.")
        fetched_at = cache(Path("cache/osdr") / f"{slug(kw)}.json", url, data)
        osd = [h["_source"] for h in hits if h["_source"]["Accession"].startswith("OSD-")]
        rows = [
            f"| {kw} | {s['Accession']} | {s['Study Title'].replace('|', '/')} | {organism(s.get('organism'))} "
            f"| {STUDY.format(s['Accession'].removeprefix('OSD-'))} | {STATUS} |"
            for s in osd[:5]
        ] or [f"| {kw} | none | no OSD hits returned | | | |"]
        skipped = len(hits) - len(osd)
        sections.append((kw, url, fetched_at, rows, skipped))
        print(f"{kw}: {len(hits)} hits, {len(osd)} OSD, kept {min(len(osd), 5)}")

    lines = [f"\n## OSDR search run {sections[0][2]}\n"]
    lines += [f"- `{kw}`: {url} (fetched {t}; {n} non-OSD hits skipped)" for kw, url, t, _, n in sections]
    lines += ["", "| Keyword | OSD id | Title | Organism | Study URL | Status |", "|---|---|---|---|---|---|"]
    lines += [r for *_, rows, _ in sections for r in rows]
    text = CANDIDATES.read_text() if CANDIDATES.exists() else HEADER
    CANDIDATES.write_text(text + "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
