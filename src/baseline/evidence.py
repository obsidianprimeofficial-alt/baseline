"""Evidence map loading and UI cards. Every source shown carries an OSDR or NTRS id and URL."""

import json
from pathlib import Path

NO_STUDY = "no matching study cached"
PREFIX = {"osdr": "OSD-", "ntrs": "NTRS "}


def load_evidence_map(path: str = "docs/evidence_map.json") -> dict:
    evidence = json.loads(Path(path).read_text())
    for rule, entry in evidence.items():
        if entry.get("url") and entry.get("source_id") is None:
            raise ValueError(f"{rule}: has a url but no source_id")
        if entry.get("source_id") is not None and entry.get("source_type") not in PREFIX:
            raise ValueError(f"{rule}: source_type must be one of {sorted(PREFIX)}")
    return evidence


def card_for(result: dict, evidence_map: dict) -> dict:
    e = evidence_map.get(result["rule"], {})
    if e.get("source_id") is not None:
        study = f"{PREFIX[e['source_type']]}{e['source_id']}, {e['title']}, {e['url']}"
    else:
        study = NO_STUDY
    return {
        "telemetry": "simulated",
        "flag_status": result.get("status"),
        "rule": result["rule"],
        "signal": result.get("signal"),
        "current": result.get("current"),
        "baseline_mean": result.get("baseline_mean"),
        "z": result.get("z"),
        "window_days": result["window_days"],
        "plain_words": e.get("plain_words"),
        "countermeasure": e.get("countermeasure"),
        "countermeasure_source": e.get("countermeasure_source"),
        "study": study,
        "status": e.get("status"),
    }
