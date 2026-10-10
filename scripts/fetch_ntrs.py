"""Cache NTRS search results and list the top hits as candidates for human review.

Uses the same keywords as fetch_osdr.py. Writes cache/ntrs/<slug>.json and appends a table
to docs/EVIDENCE_candidates.md. Never writes docs/evidence_map.json; that file is filled by hand.
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

from fetch_osdr import CANDIDATES, KEYWORDS, STATUS, cache, slug

SEARCH = "https://ntrs.nasa.gov/api/citations/search?"
CITATION = "https://ntrs.nasa.gov/citations/{}"


def year(hit: dict) -> str:
    """Publication year from the first publication date; NTRS submission dates are not used."""
    dates = [p["publicationDate"] for p in hit.get("publications") or [] if p.get("publicationDate")]
    return dates[0][:4] if dates else "not given"


def main() -> None:
    if os.environ.get("OFFLINE") == "1":
        sys.exit("OFFLINE=1: not fetching; cache/ntrs is used as is.")
    sections = []
    for kw in KEYWORDS:
        url = SEARCH + urlencode({"q": kw})
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("results") if isinstance(data, dict) else None
        if not isinstance(hits, list):
            print(json.dumps(data, indent=1)[:4000])
            sys.exit("NTRS response has no 'results' list; stopping instead of guessing field names.")
        for h in hits:
            if not isinstance(h, dict) or "id" not in h or "title" not in h:
                print(json.dumps(h, indent=1)[:4000])
                sys.exit("NTRS hit shape differs from expected; stopping instead of guessing field names.")
        fetched_at = cache(Path("cache/ntrs") / f"{slug(kw)}.json", url, data)
        rows = [
            f"| {kw} | {h['id']} | {' '.join(h['title'].split()).replace('|', '/')} | {year(h)} "
            f"| {CITATION.format(h['id'])} | {STATUS} |"
            for h in hits[:5]
        ] or [f"| {kw} | none | no NTRS hits returned | | | |"]
        total = data.get("stats", {}).get("total", "not given")
        sections.append((kw, url, fetched_at, rows, total))
        print(f"{kw}: {total} total, {len(hits)} returned, kept {min(len(hits), 5)}")

    lines = [f"\n## NTRS search run {sections[0][2]}\n"]
    lines += [f"- `{kw}`: {url} (fetched {t}; {n} total hits)" for kw, url, t, _, n in sections]
    lines += ["", "| Keyword | NTRS id | Title | Year | Citation URL | Status |", "|---|---|---|---|---|---|"]
    lines += [r for *_, rows, _ in sections for r in rows]
    CANDIDATES.write_text(CANDIDATES.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
