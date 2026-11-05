"""Write the simulated records for crew B and C (data/fixtures and the page's copies in web/data)."""

import json
from pathlib import Path

from baseline.fixtures import NOTE, make_fixture
from baseline.validation import make_planted

C_NOTE = (
    "Simulated, not real crew data: the seed-9 clean record from src/baseline/fixtures.py "
    "with heart rate shifted +4 SD on days 27-29 by make_planted in src/baseline/validation.py."
)
CREW = {
    "crew_b_clean.json": (NOTE, lambda: make_fixture(8, anomaly_start=None)),
    "crew_c_heart_rate.json": (C_NOTE, lambda: make_planted(9, "heart_rate_bpm", 4.0, start_day=27)),
}

if __name__ == "__main__":
    for name, (note, rows) in CREW.items():
        text = json.dumps({"source": "simulated", "note": note, "rows": rows()}, indent=2) + "\n"
        for folder in ("data/fixtures", "web/data"):
            Path(folder, name).write_bytes(text.encode())
